"""Demand-start Windows SCM host. SYSTEM owns the job and recovery guardian."""
import json
import os
from pathlib import Path
import sys
import threading
import time
import uuid

NAME='MINERStrata'
PIPE=r'\\.\pipe\MINER.Strata.v2'
def root():return Path(os.environ.get('ProgramData',r'C:\ProgramData'))/'MINER-Privileged-Recovery'
def sid():
    import win32api,win32security
    token=win32security.OpenProcessToken(win32api.GetCurrentProcess(),win32security.TOKEN_QUERY)
    try:return win32security.ConvertSidToStringSid(win32security.GetTokenInformation(token,win32security.TokenUser)[0])
    finally:token.Close()
def session_id():
    import ctypes
    value=ctypes.c_ulong()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(),ctypes.byref(value)):raise ctypes.WinError()
    return value.value
def config():
    p=root()/'strata-service.json'
    if p.is_symlink():raise ValueError('Invalid service config')
    data=json.loads(p.read_text())
    if set(data)!={'owner','owner_session'} or type(data['owner_session']) is not int or data['owner_session']<1 or not __import__('re').fullmatch(r'S-1-5-21-\d+-\d+-\d+-\d+',data['owner']):raise ValueError('Invalid service owner')
    return data

def install():
    import win32serviceutil,win32service,pywintypes
    from schoolnet.runtime import is_admin,write_json
    from schoolnet.network_dns import journal_path
    if not is_admin():raise ValueError('Administrator approval required')
    executable=Path(sys.executable).resolve();program=Path(os.environ['ProgramFiles']).resolve()
    if not getattr(sys,'frozen',False) or not executable.is_relative_to(program):raise ValueError('Install MINER in Program Files before enabling STRATA service')
    # Program Files location alone is insufficient: reject user-writable trees.
    from schoolnet.network_dns import powershell
    literal=str(executable.parent).replace("'","''")
    unsafe=powershell("$a=Get-Acl -LiteralPath '"+literal+"'; @($a.Access | Where-Object { $_.AccessControlType -eq 'Allow' -and ($_.FileSystemRights -band 278) -and $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18','S-1-5-32-544','S-1-3-0','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464') }).Count").strip()
    if unsafe!='0':raise ValueError('Installation directory is writable by non-administrators')
    journal_path(root(),True)
    if not (root()/'strata-service.json').exists():write_json(root()/'strata-service.json',{'owner':sid(),'owner_session':session_id()})
    if config()['owner']!=sid():raise ValueError('Service belongs to another user')
    try:win32serviceutil.QueryServiceStatus(NAME)
    except pywintypes.error as exc:
        if exc.winerror!=1060:raise
        win32serviceutil.InstallService(None,NAME,'MINER STRATA Connection Service',exeName=str(executable),exeArgs='--strata-service',startType=win32service.SERVICE_DEMAND_START)
    try:win32serviceutil.StartService(NAME)
    except Exception:
        if win32serviceutil.QueryServiceStatus(NAME)[1]!=win32service.SERVICE_RUNNING:raise

class Backend:
    def __init__(self):self.emergency=threading.Event()
    def preflight(self,profile):
        self.emergency.clear()
        from schoolnet.session_safety import require_clean_start
        if profile.platform!='windows':raise ValueError('Wrong platform')
        require_clean_start()
        from schoolnet.runtime import write_json
        self.directory=root()/'strata-profile';self.directory.mkdir(exist_ok=True)
        write_json(self.directory/'profile.json',profile.to_dict())
    def run(self,profile,stop,phase,observe):
        from windows.controller import session
        session(self.directory,Path(sys._MEIPASS)/'engine/sing-box.exe',stop,phase,observe=observe,persistent=True,emergency=self.emergency)
    def recover(self):
        from schoolnet.network_dns import Lease
        from schoolnet import warp
        Lease.recover(root())
        if self.emergency.is_set():warp.deactivate()
        else:warp.restore()
    def probe(self,observe):
        from schoolnet import warp
        from schoolnet.protocol_output import probe_event,ServiceProbeError
        profile=json.loads((self.directory/'profile.json').read_text())
        rid=uuid.uuid4().hex
        try:warp.verify_client_service(profile['proxy_port'])
        except Exception as exc:observe(probe_event(rid,0,error=ServiceProbeError(exc)));raise
        observe(probe_event(rid,0))

def host(backend_factory=Backend):
    import servicemanager,win32service,win32serviceutil,win32event,win32pipe,win32file,win32security,pywintypes,ctypes
    from schoolnet.supervisor import Supervisor
    from schoolnet.lease_owner import Ownership
    class Service(win32serviceutil.ServiceFramework):
        _svc_name_=NAME;_svc_display_name_='MINER STRATA Connection Service'
        def GetAcceptedControls(self):
            return super().GetAcceptedControls() | win32service.SERVICE_ACCEPT_SESSIONCHANGE
        def SvcOtherEx(self,control,event_type,data):
            session=data[0] if isinstance(data,tuple) else data
            if control==win32service.SERVICE_CONTROL_SESSIONCHANGE and event_type==6 and session==config()['owner_session']:self.actor.stop_event.set()
        def SvcShutdown(self):self.SvcStop()
        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if hasattr(self,'quit'):self.quit.set()
            if hasattr(self,'actor'):self.actor.stop_event.set()
            try:
                h=win32file.CreateFile(PIPE,0xC0000000,0,None,3,0,None);h.Close()
            except Exception:pass
        def SvcDoRun(self):
            ctypes.windll.kernel32.AllocConsole()
            self.quit=threading.Event();owner=config()['owner'];record=Ownership(root()/'strata-owner.json',owner);old=record.read()
            self.actor=Supervisor(owner,backend_factory(),record.save,old['generation'])
            if old['unfinished']:self.actor.state='RECOVERY_REQUIRED';self.actor.reason='PREVIOUS_SESSION_UNFINISHED'
            security=pywintypes.SECURITY_ATTRIBUTES()
            security.SECURITY_DESCRIPTOR=win32security.ConvertStringSecurityDescriptorToSecurityDescriptor('D:P(A;;GA;;;SY)(A;;GA;;;'+owner+')',1)
            handle=win32pipe.CreateNamedPipe(PIPE,3|0x00080000,4|2|1,1,65536,65536,3000,security)
            try:
                while not self.quit.is_set():
                    connected=False
                    try:
                        try:win32pipe.ConnectNamedPipe(handle,None)
                        except pywintypes.error as exc:
                            if exc.winerror==536:time.sleep(.05);continue
                            if exc.winerror!=535:
                                try:win32pipe.DisconnectNamedPipe(handle)
                                except pywintypes.error:pass
                                time.sleep(.05);continue
                        connected=True
                        deadline=time.monotonic()+3;data=None
                        while not self.quit.is_set() and time.monotonic()<deadline:
                            try:data=win32file.ReadFile(handle,16384)[1];break
                            except pywintypes.error as exc:
                                if exc.winerror!=232:raise
                                time.sleep(.05)
                        if not data:continue
                        win32pipe.ImpersonateNamedPipeClient(handle)
                        try:
                            token=win32security.OpenThreadToken(__import__('win32api').GetCurrentThread(),win32security.TOKEN_QUERY,True)
                            try:peer=win32security.ConvertSidToStringSid(win32security.GetTokenInformation(token,win32security.TokenUser)[0])
                            finally:token.Close()
                        finally:win32security.RevertToSelf()
                        try:response={'ok':True,'status':self.actor.request(json.loads(data),peer)}
                        except (ValueError,TypeError,KeyError):response={'ok':False,'error':'REQUEST_REJECTED'}
                        win32file.WriteFile(handle,json.dumps(response).encode())
                    except (pywintypes.error,ValueError):pass
                    finally:
                        if connected:
                            try:win32pipe.DisconnectNamedPipe(handle)
                            except pywintypes.error:pass
            finally:handle.Close()
            if self.actor.worker:self.actor.worker.join(65)
    servicemanager.Initialize();servicemanager.PrepareToHostSingle(Service);servicemanager.StartServiceCtrlDispatcher()

def request(operation,generation=0,profile=None):
    import win32file,win32pipe,win32serviceutil,pywintypes,ctypes
    message={'api_version':'strata-2','request_id':uuid.uuid4().hex,'expected_generation':generation,'operation':operation}
    if profile is not None:message['profile']=profile.to_dict()
    win32pipe.WaitNamedPipe(PIPE,5000)
    handle=win32file.CreateFile(PIPE,0xC0000000,0,None,3,0,None)
    try:
        server=ctypes.c_ulong()
        identify=ctypes.windll.kernel32.GetNamedPipeServerProcessId
        identify.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];identify.restype=ctypes.c_int
        if not identify(int(handle),ctypes.byref(server)):raise ctypes.WinError()
        if server.value!=win32serviceutil.QueryServiceStatusEx(NAME)['ProcessId']:raise ValueError('Untrusted service endpoint')
        win32pipe.SetNamedPipeHandleState(handle,2|1,None,None)
        win32file.WriteFile(handle,json.dumps(message).encode())
        deadline=time.monotonic()+12
        while True:
            try:data=win32file.ReadFile(handle,65536)[1];break
            except pywintypes.error as exc:
                if exc.winerror!=232:raise
                if time.monotonic()>=deadline:raise TimeoutError('Service response deadline')
                time.sleep(.05)
        response=json.loads(data)
        if not response.get('ok'):raise ValueError(response.get('error','SERVICE_ERROR'))
        return response['status']
    finally:handle.Close()

def maintenance(remove=False):
    """Installer bridge: refuse active/recovery sessions; never terminate an engine."""
    import win32serviceutil,win32service,pywintypes
    from schoolnet.runtime import is_admin
    if not is_admin():raise ValueError('Administrator approval required')
    try:state=win32serviceutil.QueryServiceStatus(NAME)[1]
    except pywintypes.error as exc:
        if exc.winerror==1060:return
        raise
    if state==win32service.SERVICE_RUNNING:
        snapshot=request('status');request('prepare_update',snapshot['generation'])
        win32serviceutil.StopService(NAME)
        win32serviceutil.WaitForServiceStatus(NAME,win32service.SERVICE_STOPPED,30)
    elif state!=win32service.SERVICE_STOPPED:raise ValueError('Service is changing state; retry later')
    if remove:win32serviceutil.RemoveService(NAME)
