"""Local CrossSense dashboard; no hardware side effects."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    handler = partial(SimpleHTTPRequestHandler, directory=str(Path(__file__).parent / 'static'))
    with ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f'CrossSense: http://{args.host}:{args.port}', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
