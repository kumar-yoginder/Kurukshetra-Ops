from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import Mock,patch
from pydantic import ValidationError
from router_inventory.models import LanRecord,WirelessRecord,RouterConfig,Session
from router_inventory.client import RouterClient
from router_inventory.service import DeviceAssembler
from router_inventory.repository import InventoryRepository

class InventoryTests(unittest.TestCase):
 def test_merge_keeps_lease_distinct_from_association(self):
  lan=[LanRecord(macAddress='02:00:00:00:00:01',hostName='iPhone',ipv4Address='192.0.2.2'),
       LanRecord(macAddress='00:00:00:00:00:02',hostName='Unidentified',ipv4Address='192.0.2.3')]
  rows=DeviceAssembler().merge(lan,[WirelessRecord(macAddress='02:00:00:00:00:01',radio='5 GHz')],{'192.0.2.2':15})
  self.assertTrue(rows[0].wifi_connected);self.assertTrue(rows[0].private_mac)
  self.assertEqual(rows[0].dns_queries_24h,15);self.assertFalse(rows[1].wifi_connected)
  self.assertEqual(rows[1].type,'Unknown')
 def test_invalid_mac_rejected(self):
  with self.assertRaises(ValidationError):LanRecord(macAddress='invalid')
 def test_secrets_redacted_and_newline_rejected(self):
  session=Session(authorization='Bearer secret-example',cookie='session=private-example')
  self.assertNotIn('secret-example',repr(session))
  with self.assertRaises(ValidationError):Session(authorization='Bearer x\nBad: 1',cookie='x')
 def test_config_rejects_unknown_fields(self):
  with self.assertRaises(ValidationError):RouterConfig(address='192.0.2.1',certificate_sha256='0'*64,token_file='/tmp/example',unsafe=True)
 def test_certificate_pin_blocks_session_transmission(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'session.json';path.write_text(json.dumps({'authorization':'Bearer example','cookie':'session=example'}));path.chmod(0o600)
   config=RouterConfig(address='192.0.2.1',certificate_sha256='0'*64,token_file=path)
   connection=Mock();connection.sock.getpeercert.return_value=b'wrong-certificate'
   with patch('router_inventory.client.http.client.HTTPSConnection',return_value=connection):
    with self.assertRaises(ValueError):RouterClient(config)._read('getLanClients')
   connection.request.assert_not_called()
 def test_failed_collection_does_not_erase_previous_state(self):
  with tempfile.TemporaryDirectory() as folder:
   repo=InventoryRepository(Path(folder));repo.unavailable(100,'No session')
   data=json.loads(repo.snapshot.read_text());self.assertEqual(data['state'],'unavailable');self.assertIsNone(data['updated'])
 def test_private_state_permissions(self):
  with tempfile.TemporaryDirectory() as folder:
   repo=InventoryRepository(Path(folder)/'private');repo.unavailable(100,'Test')
   self.assertEqual(repo.snapshot.stat().st_mode&0o777,0o600)
   self.assertEqual(repo.directory.stat().st_mode&0o777,0o700)
if __name__=='__main__':unittest.main()
