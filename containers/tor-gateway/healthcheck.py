#!/usr/bin/python3
import os,pwd,socket,subprocess
subprocess.run(["wg","show","wg0"],check=True,stdout=subprocess.DEVNULL)
subprocess.run(["nft","list","table","inet","tor_gateway"],check=True,stdout=subprocess.DEVNULL)
account=pwd.getpwnam("debian-tor")
os.setgroups([]); os.setgid(account.pw_gid); os.setuid(account.pw_uid)
with open("/var/lib/tor/control_auth_cookie","rb") as f:
    cookie=f.read().hex()
with socket.create_connection(("127.0.0.1",9051),timeout=3) as s:
    f=s.makefile("rwb",buffering=0)
    f.write(("AUTHENTICATE "+cookie+"\r\n").encode())
    if not f.readline().startswith(b"250 "): raise SystemExit(1)
    f.write(b"GETINFO status/bootstrap-phase\r\n")
    line=f.readline()
    if b"PROGRESS=100" not in line: raise SystemExit(1)
