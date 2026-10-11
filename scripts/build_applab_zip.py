"""Prepare max-480 replay assets and build a verified Arduino App Lab ZIP.

Run from any directory:

    python scripts/build_applab_zip.py

The source MP4 files are physically resized before packaging. ``frame_size`` is
also written to ``vision-source.json`` so the runtime keeps the same upper
bound. Aspect ratio, FPS and frame count are preserved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def rooted(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as content:
        for block in iter(lambda: content.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def has_cv2(python: Path) -> bool:
    try:
        result = subprocess.run(
            [str(python), "-c", "import cv2"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def find_video_python(explicit: Path | None) -> Path:
    candidates = []
    if explicit is not None:
        candidates.append(rooted(explicit))
    candidates.extend(
        [
            Path(sys.executable),
            ROOT / ".local" / "replay-venv" / "Scripts" / "python.exe",
            ROOT / ".local" / "replay-venv" / "bin" / "python",
        ]
    )
    seen = set()
    for candidate in candidates:
        key = str(candidate.resolve())
        if key not in seen and candidate.is_file() and has_cv2(candidate):
            return candidate
        seen.add(key)
    raise RuntimeError(
        "OpenCV (cv2) non trovato. Prepara l'ambiente .local/replay-venv "
        "oppure passa --video-python al relativo interprete Python."
    )


def validate_zip(path: Path, expected_frame_size: int) -> dict:
    required = {
        "app.yaml",
        "README.md",
        "python/main.py",
        "python/requirements.txt",
        "python/vision-source.json",
        "python/asset-manifest.json",
        "python/controller-cycle.enabled",
        "sketch/sketch.ino",
        "sketch/sketch.yaml",
    }
    with zipfile.ZipFile(path) as archive:
        crc_error = archive.testzip()
        if crc_error is not None:
            raise RuntimeError(f"CRC non valido nello ZIP: {crc_error}")
        names = set(archive.namelist())
        missing = sorted(required - names)
        if missing:
            raise RuntimeError("File App Lab mancanti: " + ", ".join(missing))
        app_manifest = archive.read("app.yaml").decode()
        if "name: CrossSense HackTurin Demo" not in app_manifest:
            raise RuntimeError("Nome App Lab inatteso nel manifest")
        readme = archive.read("README.md").decode()
        for expected in ("# CrossSense HackTurin Demo", "## Cosa vedrai", "## Come avviare la demo", "**Play**"):
            if expected not in readme:
                raise RuntimeError(f"README della demo incompleto: manca {expected}")
        if b'id="video-empty-state"' not in archive.read("python/dashboard/static/index.html"):
            raise RuntimeError("Guida visuale alla selezione video assente")
        if b"def preload(self):" not in archive.read("python/vision/pipeline.py"):
            raise RuntimeError("Precaricamento YOLO assente")
        config = json.loads(archive.read("python/vision-source.json"))
        if config.get("frame_size") != expected_frame_size:
            raise RuntimeError(
                f"frame_size inatteso: {config.get('frame_size')!r}; "
                f"atteso {expected_frame_size}"
            )
        if "video" in config:
            raise RuntimeError("Il pacchetto seleziona ancora un video automaticamente")
        metadata = archive.read("python/vision/assets/yolo26n_ncnn_model/metadata.yaml").decode()
        match = re.search(r"(?m)^imgsz:\s*\r?\n-\s*(\d+)\s*\r?\n-\s*(\d+)\s*$", metadata)
        model_size = tuple(map(int, match.groups())) if match else None
        if model_size != (config["imgsz"], config["imgsz"]):
            raise RuntimeError(f"Export NCNN incompatibile nello ZIP: {model_size}")
        manifest = json.loads(archive.read("python/asset-manifest.json"))
        for name, metadata in manifest["assets"].items():
            data = archive.read("python/vision/assets/" + name)
            if len(data) != metadata["bytes"]:
                raise RuntimeError(f"Dimensione asset non valida: {name}")
            if hashlib.sha256(data).hexdigest() != metadata["sha256"]:
                raise RuntimeError(f"Hash asset non valido: {name}")
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "frame_size": config["frame_size"],
        "imgsz": config["imgsz"],
        "inference_threads": config.get("inference_threads"),
        "app_name": "CrossSense HackTurin Demo",
    }


def exported_imgsz(model: Path) -> tuple[int, int] | None:
    metadata = model / "metadata.yaml"
    if not metadata.is_file():
        return None
    match = re.search(r"(?m)^imgsz:\s*\r?\n-\s*(\d+)\s*\r?\n-\s*(\d+)\s*$", metadata.read_text())
    return (int(match.group(1)), int(match.group(2))) if match else None


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(".local/demo-video-source-20261011"),
        help="Cartella degli MP4 sorgente (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(".local/export-320/yolo26n_ncnn_model"),
        help="Modello NCNN da includere (default: %(default)s)",
    )
    parser.add_argument(
        "--zones-file",
        type=Path,
        default=Path(".local/active-zones-20261011.json"),
        help="Zone iniziali della dashboard (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(f"dist/crosssense-applab-max480-320-{timestamp}.zip"),
        help="ZIP finale; deve avere estensione .zip (default con timestamp)",
    )
    parser.add_argument("--max-size", type=int, default=480)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--confidence", type=float, default=0.15)
    parser.add_argument("--inference-threads", type=int, choices=range(1, 5), default=2)
    parser.add_argument("--loop-video", action="store_true", help="Ripeti automaticamente il video a fine replay")
    parser.add_argument(
        "--video-python",
        type=Path,
        help="Interprete Python con cv2; normalmente viene trovato automaticamente",
    )
    args = parser.parse_args()

    source = rooted(args.source)
    model = rooted(args.model)
    zones_file = rooted(args.zones_file)
    output = rooted(args.output)
    if output.suffix.lower() != ".zip":
        parser.error("--output deve terminare con .zip")
    destination = output.with_suffix("")
    if output.exists() or destination.exists():
        parser.error("Output già esistente; usa un nome diverso")
    if not source.is_dir() or not any(source.glob("*.mp4")):
        parser.error(f"Nessun MP4 sorgente in {source}")
    if not model.exists():
        parser.error(f"Modello assente: {model}")
    model_size = exported_imgsz(model) if model.is_dir() else None
    if model.is_dir() and model_size != (args.imgsz, args.imgsz):
        parser.error(
            f"Il modello NCNN dichiara imgsz={model_size}; richiesto "
            f"{args.imgsz}x{args.imgsz}. Usare un export coerente."
        )
    if not zones_file.is_file():
        parser.error(f"File zone assente: {zones_file}")
    if not 32 <= args.max_size <= 2160:
        parser.error("--max-size deve essere compreso tra 32 e 2160")

    video_python = find_video_python(args.video_python)
    temp_root = ROOT / ".local"
    temp_root.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="applab-build-", dir=temp_root) as temporary:
        prepared = Path(temporary) / "replays-max480"
        subprocess.run(
            [
                str(video_python),
                str(ROOT / "scripts" / "prepare_replays.py"),
                "--source",
                str(source),
                "--destination",
                str(prepared),
                "--max-size",
                str(args.max_size),
            ],
            check=True,
        )
        report = json.loads((prepared / "manifest.json").read_text())
        command = [
            sys.executable,
            str(ROOT / "scripts" / "package_rt.py"),
            str(destination),
            "--video-dir",
            str(prepared),
            "--model",
            str(model),
            "--zones-file",
            str(zones_file),
            "--controller-cycle",
            "--frame-size",
            str(args.max_size),
            "--imgsz",
            str(args.imgsz),
            "--confidence",
            str(args.confidence),
            "--inference-threads",
            str(args.inference_threads),
            "--zip",
        ]
        if args.loop_video:
            command.append("--loop-video")
        subprocess.run(command, check=True)

    result = validate_zip(output, args.max_size)
    print("VIDEO_PREPARATI")
    print(json.dumps(report, indent=2))
    print("APP_LAB_ZIP_OK")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
