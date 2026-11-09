#!/usr/bin/env python3
"""Install or remove the current user's bounded private inventory schedule."""
import argparse
from pathlib import Path
import shlex
import subprocess

root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--remove',action='store_true');args=parser.parse_args()
marker='# kurukshetra-private-router-inventory'
result=subprocess.run(['crontab','-l'],capture_output=True,text=True)
if result.returncode!=0 and not(result.returncode==1 and 'no crontab' in result.stderr.lower()):
    raise SystemExit('Cannot safely read existing schedule')
lines=[line for line in result.stdout.splitlines() if not line.endswith(marker)]
if not args.remove:
    python=root/'.venv-router/bin/python'
    if not python.is_file():raise SystemExit('Prepare the isolated Python environment first')
    lines.append('* * * * * '+shlex.quote(str(python))+' '+shlex.quote(str(root/'scripts/monitoring/collect-router-inventory.py'))+' >/dev/null 2>&1 '+marker)
subprocess.run(['crontab','-'],input='\n'.join(lines)+'\n',text=True,check=True)
print('Private router schedule '+('removed' if args.remove else 'installed: every minute'))
