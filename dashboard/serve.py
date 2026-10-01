"""Build the dashboard data (if missing) and serve the dashboard on localhost.

    uv run python dashboard/serve.py            # http://127.0.0.1:8765
    uv run python dashboard/serve.py --rebuild  # regenerate data/ first
"""

import argparse
import functools
import http.server
import socketserver
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript", ".json": "application/json"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    if args.rebuild or not (HERE / "data" / "meta.json").exists():
        import build_data

        build_data.main()

    socketserver.TCPServer.allow_reuse_address = True
    handler = functools.partial(Handler, directory=str(HERE))
    with socketserver.ThreadingTCPServer(("127.0.0.1", args.port), handler) as httpd:
        url = f"http://127.0.0.1:{args.port}/"
        print(f"Dashboard running at {url}  (Ctrl+C to stop)")
        if not args.no_open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
