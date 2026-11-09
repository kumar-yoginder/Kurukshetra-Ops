#!/usr/bin/env python3
"""Serve exactly two read-only routes on loopback for SSH-tunnel access."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
from router_inventory.models import Inventory

ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'config/router-inventory/www'
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') not in ('127.0.0.1:8765','localhost:8765'):
            self.send_error(403);return
        path=self.path.split('?',1)[0]
        if path not in ('/','/inventory.json','/app.js','/styles.css'):
            self.send_error(404);return
        try:
            target=ROOT/'data/router-inventory/inventory.json' if path=='/inventory.json' else ASSETS/({'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'}[path])
            data=target.read_bytes()
            if path=='/inventory.json':data=Inventory.model_validate_json(data).model_dump_json(indent=2).encode() + b"\n"
        except OSError:self.send_error(503);return
        self.send_response(200)
        self.send_header('Content-Type',{'/':'text/html; charset=utf-8','/inventory.json':'application/json','/app.js':'text/javascript','/styles.css':'text/css'}[path])
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'none'; connect-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers();self.wfile.write(data)
    def log_message(self,*args):pass

if __name__=='__main__':
    print('Private inventory listening on loopback port 8765; use an SSH tunnel.',flush=True)
    ThreadingHTTPServer((os.environ.get('PRIVATE_BIND','127.0.0.1'),8765),Handler).serve_forever()
