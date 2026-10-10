"""Serves this folder as a static site: python3 doctors_requirement/nmg_view/serve.py  ->  http://127.0.0.1:8780"""
import functools
import http.server
import pathlib
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8780
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(pathlib.Path(__file__).resolve().parent))
print(f"NMG Lite view at http://127.0.0.1:{PORT}")
http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler).serve_forever()
