"""Separate allowlisted component evidence from human-readable command errors."""
import json
import time
from .health_model import Observation

def transport_detail(cause):
    """Allowlisted failure information; never stringify a raw transport error."""
    import ssl
    from .probe import SocksConnectError
    from .client_path import ClientPathError
    if isinstance(cause,ClientPathError):return {'failure_stage':'CLIENT_OS_PATH','failure_code':cause.code}
    if isinstance(cause,ServiceProbeError):return dict(cause.transport)
    if isinstance(cause,SocksConnectError):
        return {'failure_stage':'SOCKS_CONNECT','failure_code':'SOCKS_REPLY_'+str(cause.reply_code)}
    if isinstance(cause,ssl.SSLCertVerificationError):
        return {'failure_stage':'TLS','failure_code':'CERTIFICATE_VERIFY_FAILED'}
    if isinstance(cause,ssl.SSLError):
        return {'failure_stage':'TLS','failure_code':'TLS_ERROR'}
    return {'failure_stage':'UNCLASSIFIED_TRANSPORT','failure_code':'TIMEOUT' if isinstance(cause,TimeoutError) else 'TRANSPORT_ERROR'}

class ServiceProbeError(ValueError):
    def __init__(self,cause):
        self.transport=transport_detail(cause)
        self.reason_code='RIOT_PROBE_TIMEOUT' if isinstance(cause,TimeoutError) or self.transport['failure_code']=='CLIENT_PATH_TIMEOUT' else 'RIOT_PROBE_FAILED'
        if self.transport['failure_code']=='OS_DNS_OUTSIDE_SELECTED_SPACE':self.reason_code='CLIENT_OS_DNS_BYPASS'
        detail=self.transport['failure_code']
        prefix='OS의 Riot 선택 경로 확인 실패' if self.transport['failure_stage']=='CLIENT_OS_PATH' else 'Riot 서비스 확인 실패'
        super().__init__(prefix+' ['+detail+']. 분리 경로 상태와 별도로 재검사하세요. / Riot service check failed; routing health is separate; no direct fallback.')

def probe_event(request_id,generation,*,error=None):
    reason=error.reason_code if error else 'RIOT_TLS_RESPONSE'
    status='PASS' if error is None else 'TIMEOUT' if reason=='RIOT_PROBE_TIMEOUT' else 'FAIL'
    return Observation('riot_service',status,request_id,generation,time.time(),60,'LIVE_PROBE',reason).event()

def emit_probe(request_id,generation,error=None):print(json.dumps(probe_event(request_id,generation,error=error)),flush=True)
