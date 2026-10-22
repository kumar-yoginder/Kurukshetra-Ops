#!/usr/bin/env python3
"""Publish an explicit allowlist of public source files; never private profiles."""
import hashlib
import os
from pathlib import Path
import tempfile
root = Path(__file__).resolve().parents[2]
source = root / 'scripts/tor-client'
target = root / 'config/nginx/www/client'
files = {'ubuntu': ['tor-client.sh', 'trial.sh', 'local.env.example'], 'windows': ['windows-tor.ps1', 'open-tor-chrome.ps1']}
def publish(path, content):
    if path.is_symlink():
        raise SystemExit('Refusing symlink in generated download tree')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.publish-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(content)
            os.fchmod(output.fileno(), 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
manifest = []
for platform, names in files.items():
    for name in names:
        path = source / platform / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit('Expected a regular public source file: ' + platform + '/' + name)
        data = path.read_bytes()
        publish(target / platform / name, data)
        manifest.append(hashlib.sha256(data).hexdigest() + '  ' + platform + '/' + name)
publish(target / 'SHA256SUMS', ('\n'.join(manifest)+'\n').encode())
for name in ('tor-client.sh','trial.sh','windows-tor.ps1'):
    legacy = target / name
    if legacy.is_file() or legacy.is_symlink(): legacy.unlink()
print('Published allowlisted Ubuntu and Windows downloads with SHA256 manifest')
