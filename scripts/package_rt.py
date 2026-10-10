"""Build the standalone App Lab directory without duplicating dashboard sources."""
import argparse
from pathlib import Path
import shutil

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('destination',type=Path)
args=parser.parse_args()
if args.destination.exists(): parser.error('La destinazione deve essere nuova')
shutil.copytree(root/'firmware',args.destination,ignore=shutil.ignore_patterns('__pycache__','tests'))
shutil.copytree(root/'dashboard',args.destination/'python'/'dashboard',ignore=shutil.ignore_patterns('__pycache__','tests'))
print(args.destination.resolve())
