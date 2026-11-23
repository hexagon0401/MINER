"""Single-owner command actor. No OS paths or shell operations cross this boundary."""
from collections import OrderedDict
from dataclasses import replace
import copy
import json
import threading
import time
import uuid

OPERATIONS={'status','connect','stop','retry_probe','prepare_update','disconnect'}
class Supervisor:
    def __init__(self,owner,backend,persist=lambda state:None,generation=0):
        self.owner=owner;self.backend=backend;self.persist=persist;self.lock=threading.RLock();self.generation=generation
        self.state='STOPPED';self.components={};self.reason=None;self.stop_event=threading.Event();self.worker=None;self.cache=OrderedDict();self.probing=False;self.session_id=uuid.uuid4().hex;self.stage='idle';self.completed=0
    def snapshot(self):
        with self.lock:
            return {'api_version':'strata-2','generation':self.generation,'state':self.state,'phase':self.stage,'completed':self.completed,'reason_code':self.reason,'components':copy.deepcopy(self.components),'statistics_verified':False,'observed_at':time.time()}
    def observe(self,event,generation=None):
        from .health_model import Observation
        value=Observation(**{k:event[k] for k in Observation.__dataclass_fields__})
        with self.lock:
            if generation is not None and generation!=self.generation:return
            value=replace(value,request_id=self.session_id,generation=self.generation)
            old=self.components.get(value.component)
            if old and value.observed_at<old['observed_at']:return
            if old and value.observed_at==old['observed_at']:
                # Windows Python 3.12 can report consecutive wall timestamps in
                # one clock tick. Wait for a real tick; never invent future UTC.
                deadline=time.monotonic()+.05
                while time.time()<=old['observed_at'] and time.monotonic()<deadline:time.sleep(.001)
                if time.time()<=old['observed_at']:return
                value=replace(value,observed_at=time.time())
            self.components[value.component]=value.event()
    def phase(self,phase,count):
        with self.lock:
            if self.state=='STOPPING':return
            self.stage=phase;self.completed=max(0,min(int(count),5))
            if phase=='running':
                riot=self.components.get('riot_service',{})
                self.state='DEGRADED' if riot.get('status') in ('FAIL','TIMEOUT') else 'READY'
            elif phase=='connection_warning':self.state='DEGRADED'
    def request(self,message,peer):
        with self.lock:
            if peer!=self.owner:raise ValueError('OWNER_MISMATCH')
            if not isinstance(message,dict) or set(message)-{'api_version','request_id','expected_generation','operation','profile'}:raise ValueError('INVALID_REQUEST')
            if message.get('api_version')!='strata-2':raise ValueError('API_VERSION')
            rid=message.get('request_id');op=message.get('operation')
            if not isinstance(rid,str) or len(rid)!=32 or any(c not in '0123456789abcdef' for c in rid) or op not in OPERATIONS:raise ValueError('INVALID_REQUEST')
            expected=message.get('expected_generation')
            if type(expected) is not int:raise ValueError('INVALID_GENERATION')
            signature=json.dumps(message,sort_keys=True)
            if rid in self.cache:
                old,result=self.cache[rid]
                if signature!=old:raise ValueError('REQUEST_ID_REUSED')
                return copy.deepcopy(result)
            if op!='status' and expected!=self.generation:raise ValueError('GENERATION_CONFLICT')
            if op=='connect':
                if self.state!='STOPPED':raise ValueError('SESSION_ACTIVE_OR_RECOVERY_REQUIRED')
                from .config import Profile
                profile=Profile(**message.get('profile',{})).validate()
                self.backend.preflight(profile)
                self.generation+=1;self.session_id=rid;self.state='STARTING';self.reason=None;self.components={};self.stop_event=threading.Event()
                try:self.persist({'generation':self.generation,'unfinished':True})
                except Exception:
                    self.state='RECOVERY_REQUIRED';self.reason='OWNERSHIP_WRITE_FAILED';raise
                self.worker=threading.Thread(target=self.run,args=(profile,self.generation),daemon=True);self.worker.start()
            elif op in ('stop','disconnect'):
                if op=='disconnect':self.backend.emergency.set()
                if self.state!='STOPPED':
                    self.state='STOPPING';self.stop_event.set()
                    if not self.worker or not self.worker.is_alive():
                        self.worker=threading.Thread(target=self.recover,daemon=True);self.worker.start()
            elif op=='retry_probe':
                if self.state not in ('READY','DEGRADED') or self.probing:raise ValueError('PROBE_NOT_AVAILABLE')
                self.probing=True;threading.Thread(target=self.probe,args=(self.generation,),daemon=True).start()
            elif op=='prepare_update' and self.state!='STOPPED':raise ValueError('STOP_BEFORE_UPDATE')
            result=self.snapshot()
            # status is observational; do not cache an old snapshot on polling.
            if op!='status':
                self.cache[rid]=(signature,result)
                while len(self.cache)>128:self.cache.popitem(last=False)
            return result
    def run(self,profile,generation):
        try:
            self.backend.run(profile,self.stop_event,self.phase,lambda event:self.observe(event,generation))
            with self.lock:self.state='STOPPED';self.persist({'generation':self.generation,'unfinished':False})
        except Exception:
            with self.lock:self.state='RECOVERY_REQUIRED';self.reason='SESSION_OR_CLEANUP_FAILED'
    def recover(self):
        try:
            self.backend.recover()
            with self.lock:self.state='STOPPED';self.reason=None;self.persist({'generation':self.generation,'unfinished':False})
        except Exception:
            with self.lock:self.state='RECOVERY_REQUIRED';self.reason='CLEANUP_FAILED'
    def probe(self,generation):
        try:
            self.backend.probe(lambda event:self.observe(event,generation))
            with self.lock:
                if generation==self.generation and self.state=='DEGRADED':self.state='READY';self.reason=None
        except Exception:
            with self.lock:
                if generation==self.generation and self.state in ('READY','DEGRADED'):self.state='DEGRADED';self.reason='RIOT_PROBE_FAILED'
        finally:
            with self.lock:self.probing=False
