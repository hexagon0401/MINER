"""Read-only proof inputs; these never assert physical school presence."""
from pathlib import Path
from schoolnet.runtime import doctor
from schoolnet.macos_service import status

CHECKS=('engine_running','native_platform','engine_schema','warp_local_proxy_mode','socks5_greeting','warp_trace')


def diagnose(directory, engine, warp_cli=None):
    running = status()['running']
    if not running:
        return {'schemaVersion':1,'passed':False,'checks':dict.fromkeys(CHECKS,False),'failureCode':'engine_not_running'}
    result=doctor(Path(directory),engine,warp_cli)
    checks={k:bool(result['checks'].get(k,False)) for k in CHECKS if k!='engine_running'}
    checks['engine_running']=bool(status()['running'])
    return {'schemaVersion':1,'passed':all(checks.values()),'checks':checks,
            'failureCode':None if all(checks.values()) else 'diagnostic_failed'}
