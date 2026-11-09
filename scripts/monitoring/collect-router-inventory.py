#!/usr/bin/env python3
"""CLI entry point; use the isolated router-inventory Python environment."""
import os
from pathlib import Path
from router_inventory.service import InventoryCollector

if __name__=='__main__':
    os.umask(0o077)
    raise SystemExit(InventoryCollector(Path(__file__).resolve().parents[2]).run())
