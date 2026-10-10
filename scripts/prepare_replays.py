"""Resize local replay assets before packaging; preserve frames, FPS and aspect ratio."""
import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    dimensions=parser.add_mutually_exclusive_group()
    dimensions.add_argument('--max-size',type=int,default=480)
    dimensions.add_argument('--height',type=int,help='Altezza esatta (es. 480p), proporzioni conservate; usare originali')
    args=parser.parse_args()
    if args.destination.exists():parser.error('La destinazione deve essere nuova')
    if not 32<=args.max_size<=2160:parser.error('Dimensione non valida')
    if args.height is not None and (not 32<=args.height<=2160 or args.height%2):
        parser.error('Altezza non valida: deve essere pari, da 32 a 2160')
    import cv2
    videos=sorted(args.source.glob('*.mp4'))
    if not videos:parser.error('Nessun MP4')
    args.destination.mkdir(parents=True)
    reports=[]
    for video in videos:
        capture=cv2.VideoCapture(str(video));writer=None
        try:
            if not capture.isOpened():raise RuntimeError('Video non apribile: '+str(video))
            fps=capture.get(cv2.CAP_PROP_FPS)
            expected=round(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if not 0<fps<=240:raise RuntimeError('FPS non valido')
            count=0
            while True:
                ok,frame=capture.read()
                if not ok:break
                height,width=frame.shape[:2]
                if args.height is not None:
                    ratio=args.height/height
                    size=(max(2,round(width*ratio/2)*2),args.height)
                else:
                    ratio=min(1,args.max_size/max(height,width))
                    size=(max(2,round(width*ratio)//2*2),max(2,round(height*ratio)//2*2))
                frame=cv2.resize(frame,size,interpolation=cv2.INTER_LINEAR)
                if writer is None:
                    writer=cv2.VideoWriter(str(args.destination/video.name),cv2.VideoWriter_fourcc(*'mp4v'),fps,size)
                    if not writer.isOpened():raise RuntimeError('Encoder MP4 non disponibile')
                writer.write(frame);count+=1
            if count!=expected:raise RuntimeError(f'Frame persi: {video.name} {count}/{expected}')
            reports.append(dict(video=video.name,width=size[0],height=size[1],fps=fps,frames=count))
        finally:
            capture.release()
            if writer is not None:writer.release()
    (args.destination/'manifest.json').write_text(json.dumps(reports,indent=2))
    print('REPLAY_ASSETS_OK',json.dumps(reports))


if __name__=='__main__':main()
