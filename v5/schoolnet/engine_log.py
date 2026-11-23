"""Bounded, category-only engine output. Never store original network log lines."""
import json
import os
from pathlib import Path
import threading
import time


class EngineLog:
    def __init__(self,stream,path,limit=1024*1024):
        self.stream=stream;self.path=Path(path);self.limit=limit;self.error=None
        self.thread=threading.Thread(target=self.run,daemon=True,name='MINER bounded engine log');self.thread.start()
    def run(self):
        from diagnostics.log_events import classify
        pending=b''
        try:
            while True:
                chunk=self.stream.read1(8192)
                if not chunk:break
                pending+=chunk
                while b'\n' in pending or len(pending)>8192:
                    if b'\n' in pending:line,pending=pending.split(b'\n',1)
                    else:line,pending=pending[:8192],pending[8192:]
                    result=classify(line[:8192].decode('utf-8','replace'))
                    if not result['classified_error_lines'] and not result['unclassified_warning_error_lines']:continue
                    encoded=(json.dumps({'event':'engine_error_categories','at':time.time(),'summary':result})+'\n').encode()
                    previous=self.path.with_name(self.path.name+'.previous')
                    if self.path.is_symlink() or previous.is_symlink():raise ValueError('Log path is a link')
                    if self.path.exists() and self.path.stat().st_size+len(encoded)>self.limit:os.replace(self.path,previous)
                    with self.path.open('ab') as output:output.write(encoded)
                    if os.name!='nt':self.path.chmod(0o644)  # Sanitized categories readable by the non-root diagnostic recorder.
        except Exception as exc:self.error=type(exc).__name__
        finally:self.stream.close()
    def finish(self):
        self.thread.join(3)
        if self.thread.is_alive() or self.error:raise ValueError('Engine log recorder needs attention')
