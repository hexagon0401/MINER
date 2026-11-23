"""Separate allowlisted component evidence from human-readable command errors."""
import json
import time
from .health_model import Observation

class ServiceProbeError(ValueError):
    def __init__(self,cause):
        self.reason_code='RIOT_PROBE_TIMEOUT' if isinstance(cause,TimeoutError) else 'RIOT_PROBE_FAILED'
        super().__init__('Riot 서비스 확인 실패. 분리 경로 상태와 별도로 재검사하세요. / Riot service check failed; routing health is separate; no direct fallback.')

def probe_event(request_id,generation,*,error=None):
    reason=error.reason_code if error else 'RIOT_TLS_RESPONSE'
    status='PASS' if error is None else 'TIMEOUT' if reason=='RIOT_PROBE_TIMEOUT' else 'FAIL'
    return Observation('riot_service',status,request_id,generation,time.time(),60,'LIVE_PROBE',reason).event()

def emit_probe(request_id,generation,error=None):print(json.dumps(probe_event(request_id,generation,error=error)),flush=True)
