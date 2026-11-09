#!/usr/bin/env python3
"""Interactive centralized identity bootstrap. Passwords are never CLI arguments."""
import getpass
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from pydantic import BaseModel,ConfigDict,Field,SecretStr

ROOT=Path(__file__).resolve().parents[2]
IMAGE='kurukshetra/pihole-bridge:2026.11.09'

class PortalInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    hostname:str=Field(pattern=r'^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z][a-z0-9-]+$')
    username:str=Field(pattern=r'^[a-z][a-z0-9_.-]{2,31}$')
    password:SecretStr

def write(path,text,mode=0o600):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,temporary=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:os.fchmod(stream.fileno(),mode);stream.write(text)
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)

class GatewayBootstrap:
    def configure(self):
        os.umask(0o077)
        private=ROOT/'config/gateway/private'
        if (private/'identity/users.yml').exists():raise SystemExit('Central identity already configured; refusing to replace accounts or encryption keys.')
        hostname=input('Gateway hostname [dwarka.gateway]: ').strip() or 'dwarka.gateway'
        username=input('Central portal username: ').strip()
        password=getpass.getpass('Central portal password (at least 15 characters): ')
        confirmation=getpass.getpass('Confirm central portal password: ')
        if password!=confirmation or len(password)<15:raise SystemExit('Password confirmation failed or password is too short; no settings changed.')
        try:settings=PortalInput(hostname=hostname,username=username,password=password)
        except ValueError:raise SystemExit('Invalid hostname or username; no settings changed.') from None
        certificate=subprocess.run(['openssl','x509','-in',str(ROOT/'certs/server.crt'),'-noout','-checkhost',hostname],capture_output=True,text=True)
        if certificate.returncode!=0 or "does match certificate" not in certificate.stdout:raise SystemExit('Certificate does not cover that hostname; fix certificate coverage first.')
        # Hash inside a network-disabled helper; plaintext travels only through stdin.
        hashing="import sys;from argon2 import PasswordHasher;print(PasswordHasher(time_cost=3,memory_cost=65536,parallelism=2).hash(sys.stdin.read()))"
        result=subprocess.run(['docker','run','--rm','-i','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true',IMAGE,'python','-c',hashing],input=settings.password.get_secret_value(),text=True,capture_output=True,check=True)
        digest=result.stdout.strip()
        if not digest.startswith('$argon2id$'):raise SystemExit('Password hashing failed; no configuration written.')
        config_text=(ROOT/'config/identity/configuration.template.json').read_text().replace('__GATEWAY_HOST__',hostname)
        config=json.loads(config_text)
        write(private/'identity/configuration.yml',json.dumps(config,indent=2,ensure_ascii=False)+'\n')
        users={'users':{username:{'displayname':username,'password':digest}}}
        write(private/'identity/users.yml',json.dumps(users,indent=2,ensure_ascii=False)+'\n')
        for key in ('session','storage','reset_jwt'):
            target=private/'secrets'/key
            if not target.exists():write(target,secrets.token_urlsafe(64)+'\n')
        # Preserve the currently running Pi-hole credential without displaying it.
        info=json.loads(subprocess.check_output(['docker','inspect','pihole'],text=True))[0]
        existing=next((value.split('=',1)[1] for value in info['Config']['Env'] if value.startswith('FTLCONF_webserver_api_password=')),None)
        if not existing:raise SystemExit('Pi-hole credential unavailable; refusing to disable backend authentication.')
        write(private/'secrets/pihole_password',existing)
        write(private/'bridge/settings.json',json.dumps({'gateway_host':hostname,'pihole_password_file':'/run/secrets/pihole_password'},indent=2)+'\n')
        for name in ('edge','router'):
            text=(ROOT/'config/gateway/templates'/name/'default.conf.template').read_text().replace('__GATEWAY_HOST__',hostname)
            directory=private/name;directory.mkdir(parents=True,exist_ok=True,mode=0o755);directory.chmod(0o755)
            write(directory/'default.conf',text,0o644)
        for name in ('identity','bridge'):(private/name).chmod(0o700)
        for name in ('identity','gateway-migration'):
            (ROOT/'data'/name).mkdir(parents=True,exist_ok=True,mode=0o700)
        health=ROOT/'data/identity/healthcheck.env'
        if not health.exists():write(health,'')
        env=ROOT/'.env';lines=env.read_text().splitlines()
        lines=[line for line in lines if not line.startswith(('GATEWAY_HOST=','GATEWAY_UID=','GATEWAY_GID='))]
        lines.extend([f'GATEWAY_HOST={hostname}',f'GATEWAY_UID={os.getuid()}',f'GATEWAY_GID={os.getgid()}'])
        write(env,'\n'.join(lines)+'\n')
        print('Central identity prepared. Password stored only as an Argon2id hash. Gateway not switched yet.')

if __name__=='__main__':GatewayBootstrap().configure()
