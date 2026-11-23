"""Real SCM lifetime, Job cleanup, restart and denied nonowner peer tests.

Uses a separate fixture executable and a disposable local CI account. No DNS,
WARP, Riot traffic or game process is created. Never part of the app package.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time


def until(check,timeout=15):
    deadline=time.monotonic()+timeout
    while not check():
        if time.monotonic()>deadline:raise TimeoutError('SCM fixture deadline')
        time.sleep(.1)


def run(installation,work):
    import win32api,win32con,win32security,win32net,win32netcon,win32serviceutil,win32service,pywintypes
    from windows.strata_service import NAME,root,request
    base=Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--console','--name','MINER-SCM-Fixture',
        '--hidden-import','win32timezone','--paths',str(base),'--distpath',str(installation/'SCMFixture'),
        '--workpath',str(work/'scm-pyinstaller'),'--specpath',str(work),str(base/'windows/service_fixture.py')],check=True,timeout=300)
    executable=installation/'SCMFixture/MINER-SCM-Fixture/MINER-SCM-Fixture.exe'
    win32serviceutil.InstallService(None,NAME,'MINER STRATA CI Fixture',exeName=str(executable),startType=win32service.SERVICE_DEMAND_START)
    username='MINERStrataCI';account=False;child=None
    try:
        win32serviceutil.StartService(NAME)
        until(lambda:win32serviceutil.QueryServiceStatus(NAME)[1]==win32service.SERVICE_RUNNING)
        generation=request('status')['generation']
        # This requester's process exits, while the SCM service owns the worker.
        code='from windows.strata_service import request; from schoolnet.config import Profile; request("connect",'+str(generation)+',Profile(platform="windows"))'
        subprocess.run([sys.executable,'-c',code],check=True,cwd=base,timeout=20)
        until(lambda:request('status')['state']=='READY')
        proof=json.loads((root()/'strata-fixture.json').read_text())
        child=win32api.OpenProcess(win32con.SYNCHRONIZE,False,proof['child'])
        import win32event
        assert win32event.WaitForSingleObject(child,0)==win32con.WAIT_TIMEOUT
        assert proof['service']==win32serviceutil.QueryServiceStatusEx(NAME)['ProcessId']
        # Real nonowner kernel token; the pipe ACL must reject access.
        win32net.NetUserAdd(None,1,{'name':username,'password':'A!'+secrets.token_urlsafe(24),'priv':win32netcon.USER_PRIV_USER,
            'home_dir':None,'comment':'Disposable MINER CI peer','flags':win32netcon.UF_SCRIPT,'script_path':None})
        account=True
        # Obtain a token without retaining or logging its randomly generated password.
        password='B!'+secrets.token_urlsafe(24)
        win32net.NetUserSetInfo(None,username,1003,{'password':password})
        token=win32security.LogonUser(username,'.',password,win32con.LOGON32_LOGON_INTERACTIVE,win32con.LOGON32_PROVIDER_DEFAULT)
        try:
            win32security.ImpersonateLoggedOnUser(token)
            try:request('status')
            except pywintypes.error as exc:assert exc.winerror==5
            else:raise AssertionError('Nonowner pipe access accepted')
        finally:win32security.RevertToSelf();token.Close()
        # Crash the supervisor: its kernel Job must reap the fixture child.
        process=win32api.OpenProcess(win32con.PROCESS_TERMINATE,False,proof['service'])
        try:win32api.TerminateProcess(process,1)
        finally:process.Close()
        assert win32event.WaitForSingleObject(child,5000)==win32con.WAIT_OBJECT_0
        until(lambda:win32serviceutil.QueryServiceStatus(NAME)[1]==win32service.SERVICE_STOPPED)
        win32serviceutil.StartService(NAME)
        until(lambda:win32serviceutil.QueryServiceStatus(NAME)[1]==win32service.SERVICE_RUNNING)
        assert request('status')['state']=='RECOVERY_REQUIRED'
        request('stop',generation+1);until(lambda:request('status')['state']=='STOPPED')
        return {'separate_ci_fixture':True,'scm_owns_child_after_client_exit':True,'nonowner_pipe_denied':True,
                'service_crash_job_cleanup':True,'restart_requires_recovery':True,'dns_changed':False,'warp_changed':False}
    finally:
        if child:child.Close()
        if account:win32net.NetUserDel(None,username)
        try:
            if win32serviceutil.QueryServiceStatus(NAME)[1]!=win32service.SERVICE_STOPPED:
                state=request('status')
                if state['state']!='STOPPED':request('stop',state['generation']);until(lambda:request('status')['state']=='STOPPED')
                win32serviceutil.StopService(NAME);win32serviceutil.WaitForServiceStatus(NAME,win32service.SERVICE_STOPPED,15)
        finally:win32serviceutil.RemoveService(NAME)
        (root()/'strata-fixture.json').unlink(missing_ok=True)
