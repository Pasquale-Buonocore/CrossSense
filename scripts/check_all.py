"""Offline regression suite; only host processes and temporary files, no board."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arduino-json',type=Path,required=True)
    parser.add_argument('--node',default='node')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    def run(command):
        print('RUN',*map(str,command),flush=True)
        subprocess.run(list(map(str,command)),cwd=root,check=True)
    for folder in ('dashboard','vision','scripts'):
        run([sys.executable,'-B','-m','unittest','discover','-s',f'{folder}/tests','-p','test_*.py'])
    for name in ('app','providers','vision','replay'):
        run([args.node,f'dashboard/tests/{name}.test.cjs'])
    with tempfile.TemporaryDirectory(prefix='crosssense-tests-') as temporary:
        tests=[('step1_test',[]),('rt_protocol_test',[]),('standard_cycle_test',[]),('adaptive_test',[]),
               ('sketch_cycle_test',['-DCROSSSENSE_STANDARD_CYCLE=0']),('sketch_cycle_test',['-DCROSSSENSE_STANDARD_CYCLE=1'])]
        for name,flags in tests:
            exe=Path(temporary)/(name+('.exe' if sys.platform=='win32' else ''))
            run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-pedantic','-I',args.arduino_json.resolve(),
                 '-I',root/'firmware/tests/stubs',*flags,root/'firmware/tests'/f'{name}.cpp','-o',exe])
            run([exe])
    print('ALL_CHECKS_OK')


if __name__=='__main__':main()
