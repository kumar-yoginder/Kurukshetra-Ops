#!/usr/bin/env python3
"""Loopback-only documentation preview using synthetic fixtures and real UI assets.

Never reads private configuration, production snapshots, credentials or databases.
Do not expose this unauthenticated demonstration server outside loopback.
"""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "config/portal/www"
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/portal.css": ("portal.css", "text/css"),
    "/portal.js": ("portal.js", "text/javascript"),
    "/fonts/inter.ttf": ("fonts/inter.ttf", "font/ttf"),
    "/fonts/space-grotesk.ttf": ("fonts/space-grotesk.ttf", "font/ttf"),
    "/fonts/jetbrains-mono.ttf": ("fonts/jetbrains-mono.ttf", "font/ttf"),
}

def fixtures():
    now = int(time.time())
    stamp = datetime.now(timezone.utc).isoformat()
    devices = []
    for index, (name, kind, connected, count) in enumerate([
        ("Demo laptop", "Mac / likely macOS", True, 3200),
        ("Demo phone", "iPhone / likely iOS", True, 1800),
        ("Demo tablet", "iPad / likely iPadOS", True, 1200),
        ("Demo workstation", "Likely Windows", True, 2400),
        ("Demo server", "Unknown", False, 800),
        ("Demo accessory", "Unknown", True, 600),
    ], 1):
        devices.append({"mac": "Hidden - demo record " + str(index), "name": name,
            "addresses": ["Hidden in documentation"], "type": kind,
            "type_evidence": "hostname hint" if kind != "Unknown" else "unclassified",
            "private_mac": True, "wifi_connected": connected,
            "radio": "5 GHz" if connected else None, "dns_queries_24h": count})
    history = [{"mac": d["mac"], "name": d["name"], "type": d["type"],
        "first_observed": now - 86400, "last_observed": now,
        "wifi_observations": 120 if d["wifi_connected"] else 0} for d in devices]
    hourly = [160, 130, 90, 70, 120, 200, 310, 420, 390, 450, 480, 410,
              460, 520, 490, 530, 610, 580, 720, 840, 690, 510, 340, 260]
    def sample(down, up, response, tor=None):
        return {"checked": stamp, "test_state": "complete", "download_mbps": down,
            "upload_mbps": up, "response_ms": response, "download_bytes": 262144 if tor else 4194304,
            "upload_bytes": 65536 if tor else 1048576, "verified_tor": tor}
    return {
        "/inventory/inventory.json": {"updated": now, "attempted": now,
            "state": "available", "devices": devices, "history": history, "dns_available": True},
        "/dns-activity.json": {"updated": stamp, "state": "available", "queries": sum(hourly),
            "window_hours": 24, "hourly_queries": hourly, "client_count": len(devices)},
        "/status.json": {"updated": stamp, "services": [{"name": name, "state": "healthy"}
            for name in ["Pi-hole", "HTTPS gateway", "Central identity", "Web application firewall", "Private inventory", "Tor gateway"]],
            "tor": {"peers": [{"name": "Demo peer", "recent": True, "handshake_age_seconds": 30}]}},
        "/tor-metrics.json": {"checked": stamp, "verified_tor": True,
            "exit_ip": "Hidden in documentation", "sample_mbps": 1.2, "test_state": "complete"},
        "/speed-metrics.json": {"updated": stamp, "interval_seconds": 900,
            "internet": sample(100, 20, 90), "tor": sample(1.2, 0.6, 1200, True)},
    }

class Preview(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        demo = fixtures()
        if path in demo:
            body = (json.dumps(demo[path], indent=2, ensure_ascii=False) + "\n").encode()
            content = "application/json"
        elif path in STATIC:
            name, content = STATIC[path]
            body = (WEB / name).read_bytes()
            if path == "/":
                html = body.decode().replace("<body>", '<body><div class="documentation-banner">DOCUMENTATION PREVIEW · SYNTHETIC DATA · ALL IDENTIFIERS HIDDEN</div>')
                body = html.encode()
            elif path == "/portal.css":
                body += b"\n.documentation-banner{padding:12px 20px;background:#123039;color:#b6f6ff;font:12px/1.6 system-ui,sans-serif;letter-spacing:.08em;text-align:center}\n"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8877)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use an unprivileged TCP port")
    print("Synthetic documentation preview on loopback port", args.port, flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Preview).serve_forever()
