"""Compile the actual dashboard-only sketch for host replay and integration tests."""
import argparse
from pathlib import Path
import subprocess


def build(destination, arduino_json, compiler='g++'):
    root = Path(__file__).resolve().parents[1]
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([compiler,'-std=c++11','-Wall','-Wextra','-Werror','-pedantic',
        '-DCROSSSENSE_STANDARD_CYCLE=1','-I',str(Path(arduino_json).resolve()),
        '-I',str(root/'firmware/tests/stubs'),str(root/'firmware/tests/native_bridge.cpp'),
        '-o',str(destination)],check=True)
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arduino-json',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(build(args.output,args.arduino_json))
