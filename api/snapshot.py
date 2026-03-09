import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from powercurve_core import build_snapshot_payload


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        force_refresh = "refresh=1" in self.path
        payload = build_snapshot_payload(force=force_refresh)

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "s-maxage=300, stale-while-revalidate=900")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))
