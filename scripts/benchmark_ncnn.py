"""Offline NCNN calibration inputs, paired timing, and replay trajectory checks.

Timing measures the NCNN forward pass, not dashboard FPS. Replay counts are an
application regression check; neither counts nor FP32 agreement measure mAP.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def inputs(video_dir, size, frame_size, every, offset, pattern='output_*.mp4'):
    import cv2
    import numpy as np
    from ultralytics.data.augment import LetterBox

    letterbox = LetterBox((size, size), auto=False, stride=32)
    for video in sorted(video_dir.glob(pattern)):
        cap = cv2.VideoCapture(str(video))
        if not cap.isOpened():
            raise ValueError(f'Cannot open {video}')
        index = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if index % every == offset:
                    height, width = frame.shape[:2]
                    if max(height, width) > frame_size:
                        ratio = frame_size / max(height, width)
                        frame = cv2.resize(frame, (round(width * ratio), round(height * ratio)))
                    image = letterbox(image=frame)
                    tensor = np.ascontiguousarray(image[..., ::-1].transpose(2, 0, 1), dtype=np.float32) / 255
                    yield video.name, index, tensor
                index += 1
        finally:
            cap.release()
        if not index:
            raise ValueError(f'Empty video: {video}')


def calibrate(args):
    import numpy as np

    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    for video, frame, tensor in inputs(args.video_dir, args.imgsz, args.frame_size, args.every, 0):
        path = args.output / f'{Path(video).stem}-{frame:05d}.npy'
        np.save(path, tensor)
        records.append(dict(video=video, frame=frame, path=str(path.resolve())))
    if not records:
        raise ValueError('No calibration inputs')
    (args.output / 'inputs.txt').write_text(''.join(r['path'] + '\n' for r in records))
    (args.output / 'manifest.json').write_text(json.dumps(dict(imgsz=args.imgsz,
        frame_size=args.frame_size, preprocessing='resize limit; square letterbox 114; RGB CHW float32 /255',
        samples=records), indent=2))
    return dict(samples=len(records), manifest=str(args.output / 'manifest.json'))


def timing(args):
    import ncnn
    import numpy as np
    import yaml

    nets, times = [], [[] for _ in args.model]
    for path in args.model:
        metadata = yaml.safe_load((path / 'metadata.yaml').read_text())
        if metadata['imgsz'] != [args.imgsz, args.imgsz]:
            raise ValueError(f'Export size mismatch: {path}')
        net = ncnn.Net()
        net.opt.num_threads = args.threads
        if net.load_param(str(path / 'model.ncnn.param')) or net.load_model(str(path / 'model.ncnn.bin')):
            raise ValueError(f'NCNN load failed: {path}')
        nets.append(net)
    from itertools import islice
    samples = list(islice(inputs(args.video_dir, args.imgsz, args.frame_size,
        args.every, args.every // 2, '*.mp4'), args.max_samples))
    if not samples:
        raise ValueError('No evaluation inputs')

    def forward(net, tensor):
        with net.create_extractor() as ex:
            if ex.input(net.input_names()[0], ncnn.Mat(tensor)):
                raise ValueError('NCNN input failed')
            outputs = []
            for name in sorted(net.output_names()):
                code, result = ex.extract(name)
                if code:
                    raise ValueError(f'NCNN extract failed: {name} ({code})')
                outputs.append(np.array(result).copy())
            return outputs

    for net in nets:
        for _ in range(args.warmup):
            forward(net, samples[0][2])
    differences = [[] for _ in nets]
    for index, (_, _, tensor) in enumerate(samples):
        outputs = [None] * len(nets)
        # Rotate model order to reduce bias from changing load/temperature.
        for k in range(len(nets)):
            slot = (index + k) % len(nets)
            began = time.perf_counter()
            outputs[slot] = forward(nets[slot], tensor)
            times[slot].append((time.perf_counter() - began) * 1000)
        for slot in range(1, len(nets)):
            differences[slot].append(max(float(np.max(np.abs(a - b)))
                for a, b in zip(outputs[0], outputs[slot])))
    return dict(kind='NCNN forward only; raw output differences are not accuracy',
        threads=args.threads, imgsz=args.imgsz, frame_size=args.frame_size,
        inputs=[dict(video=video, frame=frame) for video, frame, _ in samples],
        models=[dict(path=str(path), bytes=(path / 'model.ncnn.bin').stat().st_size,
            samples=len(times[i]), median_ms=float(np.median(times[i])),
            p95_ms=float(np.percentile(times[i], 95)),
            max_raw_output_difference=max(differences[i]) if differences[i] else 0)
            for i, path in enumerate(args.model)])


def replays(args):
    import yaml
    from vision.pipeline import VisionService
    from vision.zones import ZoneStore

    class Sink:
        def publish(self, observation):
            pass

    expected = json.loads(args.expected.read_text())['videos']
    reports = []
    with tempfile.TemporaryDirectory() as temp:
        for model in args.model:
            metadata = yaml.safe_load((model / 'metadata.yaml').read_text())
            if metadata['imgsz'] != [args.imgsz, args.imgsz]:
                raise ValueError(f'Export size mismatch: {model}')
            for video in sorted(args.video_dir.glob('output_*.mp4')):
                service = VisionService(Sink(), ZoneStore(Path(temp) / 'zones.json'),
                    video, model, imgsz=args.imgsz, frame_size=args.frame_size,
                    confidence=args.confidence, inference_threads=args.threads)
                began = time.perf_counter()
                service.run()
                if service.status != 'completed':
                    raise RuntimeError(service.error)
                metrics = service.events.snapshot()
                counts = {k: metrics[k] for k in expected[video.name]}
                report = dict(model=str(model), video=video.name, frames=service.serial,
                    imgsz=args.imgsz, frame_size=args.frame_size, confidence=args.confidence,
                    seconds=time.perf_counter() - began, counts=counts,
                    expected=expected[video.name], counts_match=counts == expected[video.name])
                reports.append(report)
                print(json.dumps(report), flush=True)
    return dict(kind='actual VisionService without MCU; count regression, not mAP', replays=reports)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['calibrate', 'timing', 'replays'])
    parser.add_argument('--model', type=Path, nargs='+', default=[])
    parser.add_argument('--video-dir', type=Path, required=True)
    parser.add_argument('--imgsz', type=int, default=320)
    parser.add_argument('--frame-size', type=int, default=480)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--every', type=int, default=30)
    parser.add_argument('--warmup', type=int, default=4)
    parser.add_argument('--max-samples', type=int, default=66)
    parser.add_argument('--confidence', type=float, default=.15)
    parser.add_argument('--expected', type=Path, default=ROOT / 'simulation/expected-events.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.imgsz < 32 or args.imgsz % 32 or min(args.frame_size, args.threads, args.every, args.max_samples) < 1:
        parser.error('imgsz must be a positive multiple of 32; sizes/threads/every must be positive')
    if args.mode != 'calibrate' and not args.model:
        parser.error('--model required for timing/replays')
    os.environ['YOLO_OFFLINE'] = 'true'
    os.environ['YOLO_AUTOINSTALL'] = 'false'
    if os.environ.get('BOARD_NAME') == 'unoq':
        # Match App Lab's main.py: import the base image's headless OpenCV.
        base_site = Path(sys.base_prefix) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
        sys.path.insert(0, str(base_site))
        try:
            import cv2
        finally:
            sys.path.pop(0)
    import torch
    import cv2
    torch.set_num_threads(1)
    cv2.setNumThreads(1)
    report = globals()[args.mode](args)
    report['host'] = dict(machine=platform.machine(), system=platform.system())
    if args.mode != 'calibrate':
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
