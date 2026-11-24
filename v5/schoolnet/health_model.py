"""G1 observation model, not a privileged supervisor or live IPC endpoint."""
from dataclasses import dataclass,asdict
from enum import Enum
import math
import re
import time

class Component(str,Enum):
    ENGINE='engine'
    ROUTE='route'
    PROXY='proxy'
    RIOT_SERVICE='riot_service'
    GAME='game'

STATES={Component.ENGINE:{'UNKNOWN','READY','STOPPED','FAILED'},Component.ROUTE:{'UNKNOWN','ACTIVE','RESTORED','FAILED'},Component.PROXY:{'UNKNOWN','CONNECTED','DEGRADED','FAILED'},Component.RIOT_SERVICE:{'NOT_RUN','PASS','FAIL','TIMEOUT','UNKNOWN'},Component.GAME:{'NOT_OBSERVED','DIRECT_OBSERVED','BLOCKED_OR_UNREACHABLE','UNKNOWN'}}
EVIDENCE={'CODE_TEST','LIVE_PROBE','PASSIVE_OBSERVATION','USER_REPORT','NONE'}
REASONS={'ENGINE_READY','ENGINE_STOPPED','ROUTE_ACTIVE','CLEANUP_COMPLETED','CLEANUP_FAILED','RIOT_TLS_RESPONSE','RIOT_PROBE_FAILED','RIOT_PROBE_TIMEOUT','PROXY_UNAVAILABLE','CLIENT_OS_DNS_BYPASS'}

@dataclass(frozen=True)
class Observation:
    component:str
    status:str
    request_id:str
    generation:int
    observed_at:float
    ttl_seconds:int
    evidence:str
    reason_code:str
    def __post_init__(self):
        component=Component(self.component)
        if self.status not in STATES[component]:raise ValueError('Invalid component state')
        if not isinstance(self.request_id,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',self.request_id):raise ValueError('Invalid request ID')
        if type(self.generation) is not int or self.generation<0:raise ValueError('Invalid generation')
        if type(self.observed_at) not in (int,float) or not math.isfinite(self.observed_at):raise ValueError('Invalid timestamp')
        if type(self.ttl_seconds) is not int or not 0<=self.ttl_seconds<=300:raise ValueError('Invalid TTL')
        if self.evidence not in EVIDENCE or self.reason_code not in REASONS:raise ValueError('Invalid evidence or reason')
    def effective(self,now=None):
        age=(time.time() if now is None else now)-self.observed_at
        return self.status if 0<=age<self.ttl_seconds else 'UNKNOWN'
    def event(self):return {'event':'component_status',**asdict(self),'statistics_verified':False}

class HealthState:
    """Reject stale generation/request updates; no command execution or persistence."""
    def __init__(self):self.generation=0;self.pending={};self.values={}
    def begin(self,component,request_id,generation):
        component=Component(component)
        Observation(component.value,'NOT_RUN' if component==Component.RIOT_SERVICE else 'UNKNOWN',request_id,generation,time.time(),30,'NONE','ENGINE_READY')
        if generation<self.generation:raise ValueError('Old generation')
        if generation>self.generation:self.values.clear();self.pending.clear();self.generation=generation
        self.pending[component]=request_id
    def accept(self,observation,now=None):
        component=Component(observation.component)
        if observation.generation!=self.generation or self.pending.get(component)!=observation.request_id:return False
        old=self.values.get(component)
        if old and observation.observed_at<=old.observed_at:return False
        if observation.effective(now)=='UNKNOWN':return False
        self.values[component]=observation;return True
    def status(self,component,now=None):
        value=self.values.get(Component(component));return value.effective(now) if value else 'UNKNOWN'
