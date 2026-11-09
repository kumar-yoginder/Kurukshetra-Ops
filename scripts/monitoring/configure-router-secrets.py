#!/usr/bin/env python3
"""Local interactive setup; never accept passwords as command-line arguments."""
import getpass
import json
import os
from pathlib import Path
import tempfile

root=Path(__file__).resolve().parents[2]
def private_write(path,value):
    fd,name=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:os.fchmod(stream.fileno(),0o600);stream.write(value)
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def main():
    os.umask(0o077)
    config=root/'config/router-inventory';secrets=config/'secrets';secrets.mkdir(parents=True,exist_ok=True,mode=0o700)
    old=json.loads((config/'local.json').read_text())
    if not __import__('re').fullmatch('[a-fA-F0-9]{64}',old['certificate_sha256']):raise SystemExit('Valid reviewed router certificate pin required')
    password=getpass.getpass('Router guest password (input hidden): ')
    confirmation=getpass.getpass('Confirm guest password: ')
    if not password or password!=confirmation:raise SystemExit('Passwords do not match; no credential files changed')
    private_write(secrets/'username','guest\n');private_write(secrets/'password',password)
    container_config={'address':old['address'],'certificate_sha256':old['certificate_sha256'],
        'token_file':'/app/data/router-inventory/session.json',
        'username_file':'/run/secrets/router_username','password_file':'/run/secrets/router_password'}
    private_write(config/'container.json',json.dumps(container_config, indent=2, ensure_ascii=False)+'\n')
    for directory in (root/'data/router-inventory',root/'data/dns-activity'):
        directory.mkdir(parents=True,exist_ok=True,mode=0o700);directory.chmod(0o700)
    env=root/'.env';text=env.read_text() if env.exists() else ''
    lines=[line for line in text.splitlines() if not line.startswith(('INVENTORY_UID=','INVENTORY_GID='))]
    lines.extend([f'INVENTORY_UID={os.getuid()}',f'INVENTORY_GID={os.getgid()}'])
    private_write(env,'\n'.join(lines)+'\n')
    print('Private guest secrets and container configuration prepared. No login or container startup performed.')

if __name__=='__main__':main()
