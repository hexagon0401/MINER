"""Native SCM/pipe boundary test. Never starts a tunnel or WARP."""
import subprocess
import time


def run(executable):
    import win32serviceutil,win32service
    from windows.strata_service import NAME,request
    subprocess.run([str(executable),'--strata-install'],check=True,timeout=45)
    try:
        deadline=time.monotonic()+15
        while win32serviceutil.QueryServiceStatus(NAME)[1]!=win32service.SERVICE_RUNNING:
            if time.monotonic()>deadline:raise TimeoutError('SCM startup deadline')
            time.sleep(.1)
        states=[request('status') for _ in range(4)]
        assert all(value['state']=='STOPPED' and value['statistics_verified'] is False for value in states)
        # Authorized client detaches; a new client attaches to the same service.
        process=win32serviceutil.QueryServiceStatusEx(NAME)['ProcessId']
        assert process>0
        assert request('status')['generation']==states[0]['generation']
        assert win32serviceutil.QueryServiceStatusEx(NAME)['ProcessId']==process
        request('prepare_update',states[0]['generation'])
        return {'scm_installed_host_executed':True,'owner_pipe_authenticated':True,
                'server_process_verified':True,'reattach_same_service':True,
                'engine_started':False,'warp_changed':False,
                'active_session_gui_crash_tested':False,'nonowner_live_peer_tested':False}
    finally:
        subprocess.run([str(executable),'--strata-maintenance','--remove-service'],check=True,timeout=45)
