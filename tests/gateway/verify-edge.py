"""Non-mutating deployed-gateway checks; run on the Pi without a browser session."""
from pathlib import Path
import json
import socket
import subprocess

root = Path(__file__).resolve().parents[2]
host = next(line.split("=", 1)[1] for line in (root / ".env").read_text().splitlines() if line.startswith("GATEWAY_HOST="))
cases = [
    ("GET", "/", None, 401),
    ("GET", "/status.json", None, 401),
    ("GET", "/inventory/inventory.json", None, 401),
    ("GET", "/inventory/", None, 404),
    ("GET", "/inventory/app.js", None, 404),
    ("GET", "/speed-metrics.json", None, 401),
    ("GET", "/api/stats/summary", None, 401),
    ("GET", "/client/ubuntu/tor-client.sh", None, 401),
    ("GET", "/client/windows/windows-tor.ps1", None, 401),
    ("GET", "/auth/", None, 200),
    ("PATCH", "/api/config", "https://" + host, 401),
    ("PATCH", "/api/config", "https://invalid.example", 403),
    ("PATCH", "/inventory/test", "https://" + host, 403),
    ("TRACE", "/", None, 405),
    ("GET", "/?q=%3Cscript%3Ealert(1)%3C/script%3E", None, 403),
]
for method, path, origin, expected in cases:
    command = ["curl", "--silent", "--show-error", "--max-time", "15", "--cacert", str(root / "certs/ca.crt"), "--resolve", host + ":443:127.0.0.1", "-X", method, "-H", "Accept: application/json", "-o", "/dev/null", "-w", "%{http_code}", "https://" + host + path]
    if origin:
        command.extend(["-H", "Origin: " + origin])
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    assert result.stdout == str(expected), (method, path, result.stdout, expected)
    print("PASS", method, path, expected)
for port in (80, 8765):
    try:
        with socket.create_connection(("127.0.0.1", port), 2):
            raise AssertionError("Unexpected direct web listener: " + str(port))
    except OSError:
        print("PASS direct port closed", port)
for path in (root / "config/nginx/www/status.json", root / "config/nginx/www/dns-activity.json", root / "data/router-inventory/inventory.json"):
    content = path.read_text()
    json.loads(content)
    assert content.endswith("\n") and '\n  "' in content
    print("PASS readable JSON", path.name)
