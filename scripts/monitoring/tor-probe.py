#!/usr/bin/env python3
"""Runs inside the Tor namespace. SOCKS only; never falls back to direct HTTP."""
import datetime
import http.client
import ipaddress
import json
import os
import socket
import ssl
import struct
import time

def exact(sock, count):
    data = b''
    while len(data) < count:
        part = sock.recv(count - len(data))
        if not part:
            raise OSError('short SOCKS reply')
        data += part
    return data

def download(host, path, limit, body=None):
    start = time.monotonic()
    with socket.create_connection(('127.0.0.1', 9050), timeout=30) as raw:
        raw.sendall(b'\x05\x01\x00')
        if exact(raw, 2) != b'\x05\x00':
            raise OSError('SOCKS authentication failed')
        name = host.encode('ascii')
        raw.sendall(b'\x05\x01\x00\x03' + bytes([len(name)]) + name + struct.pack('!H', 443))
        reply = exact(raw, 4)
        if reply[:2] != b'\x05\x00':
            raise OSError('SOCKS connection failed')
        size = {1: 4, 4: 16}.get(reply[3])
        if reply[3] == 3:
            size = exact(raw, 1)[0]
        if size is None:
            raise OSError('invalid SOCKS reply')
        exact(raw, size + 2)
        with ssl.create_default_context().wrap_socket(raw, server_hostname=host) as connection:
            method = 'POST' if body is not None else 'GET'
            headers = method + ' ' + path + ' HTTP/1.1\r\nHost: ' + host + '\r\nUser-Agent: Kurukshetra-status/1\r\nAccept-Encoding: identity\r\nConnection: close\r\n'
            if body is not None:
                headers += 'Content-Type: application/octet-stream\r\nContent-Length: ' + str(len(body)) + '\r\n'
            connection.sendall((headers + '\r\n').encode('ascii'))
            if body is not None:
                connection.sendall(body)
            response = http.client.HTTPResponse(connection)
            response.begin()
            if response.status != 200:
                raise OSError('test endpoint unavailable')
            payload = response.read(limit + 1)
            if len(payload) > limit:
                raise OSError('response exceeded limit')
    return payload, time.monotonic() - start

result = {'checked': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'verified_tor': False, 'exit_ip': None, 'sample_mbps': None, 'response_ms': None,
          'sample_bytes': 262144, 'upload_bytes': 65536, 'upload_mbps': None, 'test_state': 'unavailable'}
try:
    payload, elapsed = download('check.torproject.org', '/api/ip', 8192)
    info = json.loads(payload)
    if info.get('IsTor') is not True or not ipaddress.ip_address(info['IP']).is_global:
        raise ValueError('Tor path not verified')
    result.update(verified_tor=True, exit_ip=info['IP'], response_ms=round(elapsed * 1000))
    result['test_state'] = 'partial'
    _, elapsed = download('speed.cloudflare.com', '/__down?bytes=0', 0)
    result['response_ms'] = round(elapsed * 1000)
    payload, elapsed = download('speed.cloudflare.com', '/__down?bytes=262144', 262144)
    if len(payload) != 262144:
        raise ValueError('incomplete sample')
    result.update(sample_mbps=round(len(payload) * 8 / elapsed / 1000000, 3))
    _, elapsed = download('speed.cloudflare.com', '/__up', 8192, os.urandom(65536))
    result.update(upload_mbps=round(65536 * 8 / elapsed / 1000000, 3), test_state='complete')
except (OSError, ValueError, KeyError, http.client.HTTPException):
    pass
print(json.dumps(result))
