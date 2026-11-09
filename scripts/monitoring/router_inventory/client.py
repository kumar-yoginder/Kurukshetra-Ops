"""Allowlisted router reads and guest login with pre-request certificate pinning."""
import hashlib
import http.client
import json
from http.cookies import SimpleCookie
import ssl
import uuid
from .models import RouterConfig, Session, LanRecord, WirelessRecord, Credentials, LoginResult
from .repository import atomic_json

class AuthenticationRequired(RuntimeError):pass
class LoginRejected(RuntimeError):pass

class RouterClient:
    def __init__(self,config:RouterConfig):
        self.config=config;self.session=None;self.cookies={}
        path=config.token_file
        if path.exists():
            if path.stat().st_mode & 0o077:raise ValueError('session must be owner-only')
            self.session=Session.model_validate_json(path.read_text())
            jar=SimpleCookie();jar.load(self.session.cookie.get_secret_value())
            self.cookies={key:cookie.value for key,cookie in jar.items()}

    def _exchange(self,method,params):
        if method not in ('preLogin','login','postLogin','getLanClients','getWirelessClients'):
            raise ValueError('router operation not allowlisted')
        address=str(self.config.address)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname=False;context.verify_mode=ssl.CERT_NONE
        connection=http.client.HTTPSConnection(address,443,timeout=8,context=context)
        try:
            connection.connect()
            fingerprint=hashlib.sha256(connection.sock.getpeercert(binary_form=True)).hexdigest()
            if fingerprint!=self.config.certificate_sha256.lower():raise ValueError('certificate pin mismatch')
            headers={'Authorization':self.session.authorization.get_secret_value() if self.session else 'Bearer null',
                'Content-Type':'application/json','Referer':'https://'+address+'/','Origin':'https://'+address}
            if self.cookies:headers['Cookie']='; '.join(key+'='+value for key,value in self.cookies.items())
            connection.request('POST','/WCGI',json.dumps({'jsonrpc':'2.0','method':method,'params':params,'id':str(uuid.uuid4())}),headers)
            response=connection.getresponse()
            if response.status in (401,403):raise AuthenticationRequired()
            if response.status!=200:raise RuntimeError('router HTTP failure')
            for header,value in response.getheaders():
                if header.lower()=='set-cookie':
                    jar=SimpleCookie();jar.load(value)
                    self.cookies.update({key:cookie.value for key,cookie in jar.items()})
            return json.loads(response.read(1024*1024))
        finally:connection.close()

    def login(self):
        config=self.config
        if not config.username_file or not config.password_file:raise LoginRejected()
        for path in (config.username_file,config.password_file):
            if path.stat().st_mode & 0o077:raise ValueError('credential files must be owner-only')
        credentials=Credentials(username=config.username_file.read_text().strip(),password=config.password_file.read_text().rstrip('\r\n'))
        self.session=None;self.cookies={}
        try:
            self._exchange('preLogin',{})
            response=self._exchange('login',{'username':credentials.username,'password':credentials.password.get_secret_value()})
            if response.get('status')!='OK':raise LoginRejected()
            result=LoginResult.model_validate(response.get('results'))
            authorization='Bearer '+result.token.get_secret_value()
            response=self._exchange('postLogin',{'authHeader':authorization})
            if response.get('status')!='OK':raise LoginRejected()
            if not self.cookies.get('sysauth'):raise LoginRejected()
            self.session=Session(authorization=authorization,cookie='; '.join(k+'='+v for k,v in self.cookies.items()))
            atomic_json(config.token_file,{'authorization':self.session.authorization.get_secret_value(),'cookie':self.session.cookie.get_secret_value()})
        except AuthenticationRequired:raise LoginRejected() from None

    def _read(self,method):
        if self.session is None:raise AuthenticationRequired()
        data=self._exchange(method,{})
        if not isinstance(data.get('results'),list):raise AuthenticationRequired()
        return data['results']

    def read_devices(self):
        return ([LanRecord.model_validate(r) for r in self._read('getLanClients')],
                [WirelessRecord.model_validate(r) for r in self._read('getWirelessClients')])
