"""Private line protocol for an isolated Arduino SDK process. No GPIO commands."""
import contextlib
import json
import sys


def main():
    with contextlib.redirect_stdout(sys.stderr):
        from arduino.app_utils import Bridge
    print('READY',flush=True)
    for line in sys.stdin:
        try:
            method,payload=json.loads(line)
            if method!='crosssense_update':raise ValueError('RPC sconosciuta')
            with contextlib.redirect_stdout(sys.stderr):
                result=Bridge.call(method,payload)
            response={'result':result}
        except Exception as exc:
            response={'error':str(exc)}
        print(json.dumps(response),flush=True)


if __name__=='__main__':main()
