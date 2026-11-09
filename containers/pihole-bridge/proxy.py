"""Authenticated Pi-hole session bridge. No passwordless backend or direct host port."""
import http.client
import json
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit,unquote
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pydantic import BaseModel,ConfigDict,Field,SecretStr

class Settings(BaseModel):
    model_config=ConfigDict(extra='forbid')
    gateway_host:str=Field(pattern=r'^[a-zA-Z0-9.-]+$')
    pihole_password_file:Path

class NativeSession(BaseModel):
    model_config=ConfigDict(extra='ignore')
    sid:SecretStr
    csrf:SecretStr
    validity:int=Field(gt=0)
    valid:bool

class Bridge:
    def __init__(self,settings):self.settings=settings;self.sessions={};self.lock=threading.RLock()
    def authorize(self,cookie,method,path,client):
        conn=http.client.HTTPConnection('identity',9091,timeout=5)
        try:
            conn.request('GET','/api/authz/auth-request',headers={
                'Cookie':cookie,'X-Original-Method':method,
                'X-Original-URL':'https://'+self.settings.gateway_host+path,
                'X-Forwarded-Proto':'https','X-Forwarded-Host':self.settings.gateway_host,
                'X-Forwarded-For':client})
            response=conn.getresponse();response.read(65536)
            username=response.getheader('Remote-User')
            return username if response.status==200 and username else None
        finally:conn.close()
    def native_session(self,username,refresh=False):
        with self.lock:
            cached=self.sessions.get(username)
            if cached and cached[1]>time.monotonic() and not refresh:return cached[0]
            password=self.settings.pihole_password_file.read_text().rstrip('\r\n')
            conn=http.client.HTTPConnection('pihole',80,timeout=8)
            try:
                conn.request('POST','/api/auth',json.dumps({'password':password}),{'Content-Type':'application/json'})
                response=conn.getresponse();data=json.loads(response.read(65536))
                if response.status!=200:raise RuntimeError('native authentication unavailable')
                session=NativeSession.model_validate(data['session'])
                if not session.valid:raise RuntimeError('native authentication unavailable')
                self.sessions[username]=(session,time.monotonic()+max(1,session.validity-30))
                return session
            finally:conn.close()

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def setup(self):super().setup();self.connection.settimeout(15)
    def respond(self,status,data,content='application/json',headers=()):
        self.send_response(status);self.send_header('Content-Type',content)
        self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
        for name,value in headers:self.send_header(name,value)
        self.end_headers()
        if self.command!='HEAD':self.wfile.write(data)
        self.close_connection=True
    def dispatch(self):
        path=urlsplit(self.path)
        decoded=unquote(path.path)
        if path.scheme or path.netloc or not self.path.startswith('/') or not decoded.startswith(('/admin/','/api/')) or '..' in decoded.split('/') or self.headers.get('Host')!=bridge.settings.gateway_host:
            self.respond(404,b'{"error":"not_found"}');return
        if self.command not in ('GET','HEAD','OPTIONS') and self.headers.get('Origin')!='https://'+bridge.settings.gateway_host:
            self.respond(403,b'{"error":"origin_rejected"}');return
        if self.headers.get('Transfer-Encoding'):
            self.respond(400,b'{"error":"unsupported_transfer_encoding"}');return
        try:
            user=bridge.authorize(self.headers.get('Cookie',''),self.command,self.path,self.headers.get('X-Gateway-Client-IP',''))
            if user is None:self.respond(401,b'{"error":"authentication_required"}');return
            if path.path=='/admin/scripts/js/logout.js':
                script=b'''document.addEventListener('DOMContentLoaded',()=>{document.getElementById('logout-button')?.addEventListener('click',async e=>{e.preventDefault();try{const r=await fetch('/auth/api/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({targetURL:location.origin+'/auth/'})});if(!r.ok)throw Error();location.assign('/auth/');}catch{alert('Sign-out could not be confirmed. Use the central Account page.');}});});'''
                self.respond(200,script,'text/javascript');return
            if path.path=='/api/auth' and self.command=='DELETE':
                self.respond(405,b'{"error":"use_central_logout"}');return
            length=int(self.headers.get('Content-Length','0'))
            if length<0 or length>2*1024*1024:self.respond(413,b'{"error":"request_too_large"}');return
            body=self.rfile.read(length) if length else None
            for attempt in range(2):
                session=bridge.native_session(user,refresh=attempt==1)
                headers={key:value for key,value in self.headers.items() if key.lower() in ('accept','content-type','user-agent','origin','referer')}
                headers.update({'Host':bridge.settings.gateway_host,'X-FTL-SID':session.sid.get_secret_value(),
                    'X-FTL-CSRF':session.csrf.get_secret_value(),'X-CSRF-TOKEN':session.csrf.get_secret_value()})
                conn=http.client.HTTPConnection('pihole',80,timeout=45)
                try:
                    conn.request(self.command,self.path,body,headers)
                    response=conn.getresponse();data=response.read(8*1024*1024+1)
                    if len(data)>8*1024*1024:raise RuntimeError('response exceeds limit')
                    if response.status==401 and attempt==0:continue
                    passthrough=[(name,value) for name,value in response.getheaders() if name.lower() in ('location','content-security-policy','x-frame-options','x-content-type-options')]
                    self.respond(response.status,data,response.getheader('Content-Type','application/octet-stream'),passthrough);return
                finally:conn.close()
        except Exception:
            self.respond(503,b'{"error":"service_unavailable"}')
    do_GET=dispatch;do_HEAD=dispatch;do_POST=dispatch;do_PUT=dispatch;do_PATCH=dispatch;do_DELETE=dispatch;do_OPTIONS=dispatch
    def log_message(self,*args):pass

if __name__=='__main__':
    settings=Settings.model_validate_json(Path('/config/settings.json').read_text())
    bridge=Bridge(settings)
    ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
