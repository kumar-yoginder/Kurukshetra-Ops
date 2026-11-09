import sys
sys.path.insert(0,"/app")
import proxy
from unittest.mock import Mock
import unittest
import http.client
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

class BridgeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=ThreadingHTTPServer(("127.0.0.1",0),proxy.Handler)
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
 def setUp(self):
  proxy.bridge=Mock();proxy.bridge.settings=proxy.Settings(gateway_host="gateway.example.test",pihole_password_file=Path("/unused"))
  proxy.bridge.authorize.return_value=None
 def request(self,method,path,headers=None):
  connection=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=2)
  connection.request(method,path,headers={"Host":"gateway.example.test",**(headers or {})})
  response=connection.getresponse();body=response.read();status=response.status;connection.close();return status,body
 def test_anonymous_request_denied_before_backend(self):
  status,_=self.request("GET","/admin/");self.assertEqual(status,401);proxy.bridge.native_session.assert_not_called()
 def test_foreign_origin_denied_before_session(self):
  status,_=self.request("POST","/api/dns/blocking",{"Origin":"https://evil.example"});self.assertEqual(status,403);proxy.bridge.authorize.assert_not_called()
 def test_absolute_uri_rejected(self):
  status,_=self.request("GET","http://evil.example/admin/");self.assertEqual(status,404)
 def test_traversal_rejected(self):
  status,_=self.request("GET","/admin/%2e%2e/api/auth");self.assertEqual(status,404)
 def test_wrong_host_rejected(self):
  status,_=self.request("GET","/admin/",{"Host":"evil.example"});self.assertEqual(status,404)
 def test_identity_outage_fails_closed(self):
  proxy.bridge.authorize.side_effect=OSError("offline")
  status,body=self.request("GET","/api/stats/summary");self.assertEqual(status,503);self.assertNotIn(b"offline",body);proxy.bridge.native_session.assert_not_called()
 def test_backend_logout_is_not_an_independent_identity(self):
  proxy.bridge.authorize.return_value="operator"
  status,_=self.request("DELETE","/api/auth",{"Origin":"https://gateway.example.test"});self.assertEqual(status,405)
 def test_oversize_request_rejected(self):
  proxy.bridge.authorize.return_value="operator"
  status,_=self.request("POST","/api/test",{"Origin":"https://gateway.example.test","Content-Length":"3000000"});self.assertEqual(status,413)

if __name__=="__main__":unittest.main()
