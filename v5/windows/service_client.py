"""GUI attachment only: service owns sessions, jobs and recovery guardians."""
import time
from windows.strata_service import install,request
from windows.controller import prepare

def session(directory,engine,stop,emit,restore_only=False,emergency=None,observe=None,attach_only=False):
    if attach_only:
        import win32serviceutil,win32service,pywintypes
        from windows.strata_service import NAME
        try:running=win32serviceutil.QueryServiceStatus(NAME)[1]==win32service.SERVICE_RUNNING
        except pywintypes.error as exc:
            if exc.winerror!=1060:raise
            running=False
        if not running:emit('idle',0);return
    install();state=request('status');generation=state['generation']
    if restore_only:state=request('disconnect' if emergency and emergency.is_set() else 'stop',generation)
    elif state['state']=='STOPPED' and not attach_only:state=request('connect',generation,prepare(directory));generation=state['generation']
    stopping=restore_only;disconnecting=bool(restore_only and emergency and emergency.is_set())
    while True:
        if stop.is_set() and not stopping:
            state=request('disconnect' if emergency and emergency.is_set() else 'stop',generation);stopping=True
            disconnecting=bool(emergency and emergency.is_set())
        elif stopping and emergency and emergency.is_set() and not disconnecting:
            state=request('disconnect',generation);disconnecting=True
        state=request('status');generation=state['generation']
        for event in state['components'].values():
            if observe:observe(event)
        phase={'STARTING':'engine_start','READY':'running','DEGRADED':'connection_warning','STOPPING':'restoring','STOPPED':'restored','RECOVERY_REQUIRED':'error'}[state['state']]
        if state['state']=='STARTING':phase=state['phase'] if state['phase']!='idle' else 'cli_check'
        if state['state']=='STOPPED' and emergency and emergency.is_set():phase='disconnected'
        emit(phase,5 if phase in ('running','connection_warning') else state['completed'] if state['state']=='STARTING' else 0)
        if state['state']=='STOPPED':return
        if state['state']=='RECOVERY_REQUIRED':raise ValueError('Service recovery required. Press Stop to retry.')
        time.sleep(.5)
