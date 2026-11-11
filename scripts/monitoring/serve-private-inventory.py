#!/usr/bin/env python3
"""Internal read-only inventory snapshot endpoint; authenticated by the gateway."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
from pydantic import ValidationError
from router_inventory.models import Inventory

ROOT = Path(__file__).resolve().parents[2]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Host") not in ("127.0.0.1:8765", "localhost:8765"):
            self.send_error(403)
            return
        if self.path != "/inventory.json":
            self.send_error(404)
            return
        try:
            snapshot = Inventory.model_validate_json((ROOT / "data/router-inventory/inventory.json").read_bytes())
            data = (snapshot.model_dump_json(indent=2) + "\n").encode()
        except (OSError, ValidationError):
            self.send_error(503)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *args):
        pass

if __name__ == "__main__":
    print("Internal inventory JSON endpoint listening on port 8765.", flush=True)
    ThreadingHTTPServer((os.environ.get("PRIVATE_BIND", "127.0.0.1"), 8765), Handler).serve_forever()
