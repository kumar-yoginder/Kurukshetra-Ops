"""Container lifecycle: bounded collection, backoff and internal JSON endpoint."""
import os
from pathlib import Path
import runpy
import signal
import threading
from .service import InventoryCollector

class CollectionLoop(threading.Thread):
    def __init__(self,root):
        super().__init__(daemon=True);self.collector=InventoryCollector(root);self.stop=threading.Event()
    def run(self):
        delay=60
        while not self.stop.is_set():
            success=self.collector.run()==0
            delay=60 if success else min(900,max(60,delay*2))
            self.stop.wait(delay)

if __name__=='__main__':
    os.umask(0o077)
    root=Path(__file__).resolve().parents[3]
    worker=CollectionLoop(root);worker.start()
    runpy.run_path(str(root/'scripts/monitoring/serve-private-inventory.py'),run_name='__main__')
