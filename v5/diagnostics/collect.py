#!/usr/bin/env python3
"""MINER read-only support recorder. No account/packet/raw-log export, no uploads."""
import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
if not getattr(sys,"frozen",False) and str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
VERSION='2.0.3'
PHASES=('before','connected','in_game','post_game','after_stop','error')
HOSTS=('www.cloudflare.com','auth.riotgames.com','www.leagueoflegends.com')
OUTCOMES=('unknown','loaded','timeout_30s','error')
CLIENT_EVENTS=('none','ready_check_missing','presence_mismatch','party_failure')
COMMAND_TIMEOUT=4


def now():return datetime.now(timezone.utc).isoformat()


def command(args,timeout=COMMAND_TIMEOUT):
    """Only fixed read-only commands enter here. Never put raw errors in reports."""
    begin=time.monotonic()
    try:
        result=subprocess.run(list(map(str,args)),stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,
                              **({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}))
        return {'ok':result.returncode==0,'exit':result.returncode,'ms':round((time.monotonic()-begin)*1000),'truncated':len(result.stdout)>131072},result.stdout[:131072]
    except subprocess.TimeoutExpired:return {'ok':False,'error':'timeout','ms':round((time.monotonic()-begin)*1000)},''
    except OSError as exc:return {'ok':False,'error':type(exc).__name__},''


class Privacy:
    def __init__(self):self.key=secrets.token_bytes(32)
    def label(self,value):return hmac.new(self.key,str(value).encode(),hashlib.sha256).hexdigest()[:12]
    def address(self,value):
        try:
            ip=ipaddress.ip_address(value.split('%')[0]);kind='miner_dns' if str(ip) in ('172.30.255.2','fdfe:dcba:9876::2') else 'synthetic' if ip in ipaddress.ip_network('198.18.0.0/15') or ip in ipaddress.ip_network('fdfe:dcba:9876:1000::/64') else 'loopback' if ip.is_loopback else 'private' if ip.is_private else 'public'
            return {'id':self.label(value),'family':ip.version,'kind':kind}
        except ValueError:return None


def warp_state(cli):
    from schoolnet.warp import connected
    result={}
    for key,args in [('version',['--version']),('status',['status']),('settings',['settings']),('mode_help',['mode','--help'])]:
        meta,text=command([cli,*args]);result[key+'_command']=meta
        if key=='version':
            found=re.search(r'\b\d{4}\.\d+\.\d+\.\d+\b',text);result['version']=found[0] if found else 'unknown'
        elif key=='status':result['connected']=connected(text) if meta['ok'] else None
        elif key=='mode_help':result['supports_warp_mode']=bool(re.search(r'(?<![\w+\-])warp(?![\w+\-])',text)) if meta['ok'] else None
        else:
            mode=re.search(r'^\s*(?:\([^\n)]*\)\s*)?Mode:\s*(\w+)([^\n]*)',text,re.M)
            result['mode']=mode[1] if mode and mode[1] in ('WarpProxy','Warp','DnsOverHttps','WarpWithDnsOverHttps','DnsOverTls','TunnelOnly') else 'unknown'
            port=re.search(r'\bport\s+(\d+)\b',mode[2]) if mode else None
            result['port']=int(port[1]) if port else None
            protocol=re.search(r'\b(MASQUE|WireGuard)\b',text,re.I);result['transport']=protocol[1].upper() if protocol else 'unknown'
    return result


def route(text,privacy):
    interface=re.search(r'^\s*interface:\s*(\S+)',text,re.M)
    return {'interface':privacy.label(interface[1]),'interface_class':'tunnel' if interface[1].startswith(('utun','tun')) else 'physical_or_other'} if interface else {'unavailable':True}


def powershell(script):
    return command(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',script],timeout=6)


def network_state(system,privacy):
    result={}
    if system=='Darwin':
        for key,target in [('default','8.8.8.8'),('game_ip','104.160.131.3'),('synthetic','198.18.0.1')]:
            meta,text=command(['/sbin/route','-n','get',target]);result[key]={**meta,**route(text,privacy)}
        meta,text=command(['/usr/sbin/scutil','--dns']);result['dns_command']=meta
        addresses=re.findall(r'nameserver\[\d+\]\s*:\s*(\S+)',text)
        result['dns']=[privacy.address(v) for v in sorted(set(addresses)) if privacy.address(v)]
        meta,text=command(['/usr/sbin/scutil','--proxy']);result['proxy_command']=meta
        result['system_proxy']={key:bool(re.search(r'\b'+key+r'\s*:\s*1\b',text)) for key in ('HTTPEnable','HTTPSEnable','SOCKSEnable','ProxyAutoConfigEnable')}
        meta,text=command(['/bin/ps','-ww','-A','-o','pid=,pcpu=,rss=,comm=']);result['process_command']=meta
        entries=[];identities=[]
        from diagnostics.app_identity import running_identity
        for line in text.splitlines():
            fields=line.strip().split(None,3)
            if len(fields)!=4:continue
            try:
                name=Path(fields[3]).name
                entries.append({'name':name,'cpu':float(fields[1]),'rss_bytes':int(fields[2])*1024})
                if name=='MINER' and len(identities)<8:identities.append(running_identity(int(fields[0]),fields[3]))
            except ValueError:continue
        result['running_miner_apps']=identities
        names=[item['name'] for item in entries]
    elif system=='Windows':
        script="""$ErrorActionPreference='Stop'; $routes=@(); foreach($ip in @('8.8.8.8','104.160.131.3','198.18.0.1')){ $r=Find-NetRoute -RemoteIPAddress $ip | Where-Object {$_.DestinationPrefix} | Select-Object -First 1; $a=Get-NetAdapter -IncludeHidden | Where-Object {$_.ifIndex -eq $r.InterfaceIndex} | Select-Object -First 1; $routes+=@{target=$ip;index=$r.InterfaceIndex;description=$a.InterfaceDescription} }; $d=@(Get-DnsClientServerAddress | Where-Object {$_.ServerAddresses.Count -gt 0} | Select-Object InterfaceIndex,ServerAddresses); $p=Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings'; @{routes=$routes;dns=$d;proxyEnabled=[bool]$p.ProxyEnable;pac=[bool]$p.AutoConfigURL;processes=@(Get-Process MINER,sing-box,warp-svc,'Cloudflare WARP',LeagueClient,LeagueClientUx,'League of Legends',vgc -ErrorAction SilentlyContinue | Select-Object ProcessName,CPU,WorkingSet64);vgc=(Get-Service vgc -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status)} | ConvertTo-Json -Depth 6 -Compress"""
        meta,text=powershell(script);result['windows_command']=meta;names=[];entries=[]
        try:
            data=json.loads(text)
            for name,item in zip(('default','game_ip','synthetic'),data.get('routes',[])):
                result[name]={'interface':privacy.label(item.get('index')),'interface_class':'tunnel' if re.search(r'Wintun|sing.box|Cloudflare|TAP',str(item.get('description')),re.I) else 'physical_or_other'}
            result['dns']=[privacy.address(v) for row in data.get('dns',[]) for v in row.get('ServerAddresses',[]) if privacy.address(v)]
            result['system_proxy']={'enabled':data.get('proxyEnabled'),'pac':data.get('pac')};entries=[{'name':item.get('ProcessName',''),'cpu':item.get('CPU') or 0,'rss_bytes':item.get('WorkingSet64') or 0} for item in data.get('processes',[])];names=[item['name'] for item in entries]
            result['vanguard_service']=data.get('vgc')
        except (TypeError,ValueError):result['parse_error']=True
    else:return {'unsupported_platform':True}
    patterns={'miner':r'^MINER(?:\.exe)?$','engine':r'^sing-box(?:\.exe)?$','warp':r'^(?:warp-svc|Cloudflare WARP)(?:\.exe)?$','client':r'^(?:LeagueClient(?:Ux)?|RiotClientServices)(?:\.exe)?$','game':r'^(?:LeagueofLegends|League of Legends)(?:\.exe)?$'}
    result['processes']={key:sum(bool(re.match(pattern,name,re.I)) for name in names) for key,pattern in patterns.items()}
    result['resources']={key:{'rss_bytes':sum(item['rss_bytes'] for item in entries if re.match(pattern,item['name'],re.I)),'cpu_value':round(sum(item['cpu'] for item in entries if re.match(pattern,item['name'],re.I)),2),'cpu_metric':'ps_lifetime_percent' if system=='Darwin' else 'cumulative_seconds'} for key,pattern in patterns.items()}
    return result


def app_paths(system):
    if system=='Darwin':return [Path.home()/'Library/Application Support/SchoolNet v5 Alpha',Path('/Library/Application Support/SchoolNet v5 Alpha')]
    return [Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'MINER/Beta1',Path(os.environ.get('ProgramData',r'C:\ProgramData'))/'MINER-Privileged-Recovery/strata-profile']


def files_state(system,log_reader=None):
    result={'locations':[]}
    if system=='Darwin':
        from diagnostics.app_identity import bundle_metadata,startup_events
        installed=bundle_metadata(Path('/Applications/MINER.app'))
        result['version']=installed['version'];result['installed_app']=installed
        result['version_source']='system_applications_plist_not_running_process'
        result['startup_events']=startup_events()
        result['startup_events_source']='recent_file_tail_not_current_process_verified'
        result['vanguard_applicable']=False
    else:
        result['vanguard_applicable']=system=='Windows'
        result['version']='unavailable'
        if os.name=='nt':
            import winreg
            for access in (winreg.KEY_READ|winreg.KEY_WOW64_64KEY,winreg.KEY_READ|winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{CC8E6450-572D-4EC7-A85E-715E3F3A5021}_is1',0,access) as key:
                        value=str(winreg.QueryValueEx(key,'DisplayVersion')[0])
                        if re.fullmatch(r'\d+\.\d+\.\d+(?:[.+-][\w.-]+)?',value):result['version']=value
                except OSError:pass
    for index,base in enumerate(app_paths(system)):
        row={'location':index,'exists':base.exists(),'files':{}}
        for relative in ('profile.json','profile/profile.json','sing-box.json','profile/sing-box.json','network-dns-v1.json','profile/network-dns-v1.json','session.json','engine.log','engine-runtime.log','profile/engine-runtime.log','startup-error.log','helper.log','Updates/install.log','fakeip-cache.db','profile/fakeip-cache.db'):
            path=base/relative
            try:
                if path.is_symlink() or not path.is_file():continue
                stat=path.stat();item={'bytes':stat.st_size,'modified_utc':datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat()}
                if relative.endswith('profile.json') and stat.st_size<65536:
                    data=json.loads(path.read_text());item['profile']={key:data.get(key) for key in ('proxy_port','mtu') if type(data.get(key)) is int}
                    if data.get('platform') in ('macos','windows'):item['profile']['platform']=data['platform']
                elif relative.endswith('.log'):
                    with path.open('rb') as f:f.seek(max(0,stat.st_size-131072));tail=f.read(131072).decode('utf-8','replace')
                    item['events']={key:len(re.findall(pattern,tail,re.I)) for key,pattern in {'timeout':'timed? ?out|timeout','reset':'connection reset','refused':'connection refused','dns':'\\bdns\\b','restore':'restor|recover','permission':'permission|not permitted','socks':'socks|proxy','forced_stop':'forced to stop|forced stop','cancel':'cancel'}.items()}
                    item['van_codes']=sorted(set(re.findall(r'\bVAN\s*-?\s*\d{1,6}\b',tail,re.I)))[:20]
                    if log_reader is not None:item['error_window']=log_reader.read(path)
                row['files'][relative]=item
            except PermissionError:row['files'][relative]={'error':'permission_denied'}
            except (OSError,ValueError):row['files'][relative]={'error':'unreadable'}
        result['locations'].append(row)
    return result


def socket_check(port):
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=1.5) as sock:
            sock.sendall(b'\x05\x01\x00');reply=b''
            while len(reply)<2:
                part=sock.recv(2-len(reply))
                if not part:break
                reply+=part
        return {'listening':True,'socks5_no_auth':reply==b'\x05\x00'}
    except OSError as exc:return {'listening':False,'error':type(exc).__name__}


def probe(kind,host,port):
    if kind=='riot_service':
        if host!='auth.riotgames.com':raise ValueError('Unsupported Riot service probe host')
        from schoolnet.warp import verify_client_service
        return verify_client_service(port)
    if kind=='warp':
        from schoolnet.warp import verify_trace
        return verify_trace(port,timeout=4)
    if host not in HOSTS:raise ValueError('Unsupported diagnostic host')
    if kind=='dns':
        values=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        return {'answers':len(values),'synthetic':any(ipaddress.ip_address(item[4][0]) in ipaddress.ip_network('198.18.0.0/15') or ipaddress.ip_address(item[4][0]) in ipaddress.ip_network('fdfe:dcba:9876:1000::/64') for item in values)}
    import ssl,urllib.request,urllib.error,http.client
    context=ssl.create_default_context()
    if getattr(sys,'frozen',False):context.load_verify_locations(str(Path(sys._MEIPASS)/'cacert.pem'))
    if kind=='proxy_https':
        from schoolnet.probe import socks_connect
        with socket.create_connection(('127.0.0.1',port),timeout=4) as sock:
            socks_connect(sock,host,443)
            with context.wrap_socket(sock,server_hostname=host) as tls:
                tls.settimeout(4)
                tls.sendall(('HEAD / HTTP/1.1\r\nHost: '+host+'\r\nConnection: close\r\n\r\n').encode('ascii'))
                response=http.client.HTTPResponse(tls);response.begin()
                return {'tls_verified':True,'http_status':response.status,'via':'socks5h','direct_fallback':False}
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=context))
    try:
        with opener.open('https://'+host+'/',timeout=4) as response:return {'tls_verified':True,'http_status':response.status}
    except urllib.error.HTTPError as exc:return {'tls_verified':True,'http_status':exc.code}


def child_probe(kind,host,port):
    args=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve())]
    meta,text=command([*args,'--probe',kind,'--host',host,'--port',str(port)],timeout=12 if kind=='riot_service' else 7)
    try:return {**meta,**json.loads(text)} if text else meta
    except ValueError:return {**meta,'parse_error':True}


def findings(snapshot):
    result=[];w=snapshot['warp'];n=snapshot['network'];phase=snapshot['phase']
    if w.get('mode')=='WarpProxy' and phase=='after_stop':result.append('proxy_mode_remains_after_stop')
    if w.get('mode')=='Warp' and w.get('connected') is True:result.append('warp_full_tunnel_connected')
    if w.get('mode')=='WarpProxy' and w.get('connected') is False:result.append('warp_disconnected')
    if w.get('mode')=='WarpProxy' and not snapshot['socks'].get('socks5_no_auth'):result.append('local_socks_unavailable')
    a=n.get('default',{});b=n.get('game_ip',{})
    if a.get('interface') and b.get('interface') and a['interface']!=b['interface']:result.append('reference_game_ip_uses_different_interface')
    if a.get('interface_class')=='tunnel':result.append('default_route_uses_tunnel')
    if phase=='after_stop' and any(v['kind']=='miner_dns' for v in n.get('dns',[])):result.append('miner_dns_remains_after_stop')
    if any(n.get('system_proxy',{}).values()):result.append('system_proxy_or_pac_enabled')
    if snapshot.get('error_code') and snapshot['system']=='Darwin':result.append('mac_error_requires_exact_dialog_context_not_vanguard_assumption')
    for host,probes in snapshot.get('active_probes',{}).items():
        if host in HOSTS and probes.get('proxy_https',{}).get('tls_verified') and not probes.get('os_https',{}).get('tls_verified'):
            result.append('proxy_tls_works_but_os_path_fails:'+host)
    result.append('actual_game_udp_and_anticheat_result_not_proven')
    return result


class Recorder:
    def __init__(self,port=40000,active=False,warp_cli=None):
        from diagnostics.log_events import LogWindows
        self.log_reader=LogWindows();self.privacy=Privacy();self.samples=[];self.port=port;self.active=active;self.cli=warp_cli;self.begin=time.monotonic()
    def snapshot(self,phase,error_code=None,statistics_result='unknown',cycle=None,client_event='none'):
        if statistics_result not in OUTCOMES or cycle is not None and (type(cycle) is not int or not 1<=cycle<=10):raise ValueError('Invalid test annotation')
        if client_event not in CLIENT_EVENTS:raise ValueError('Invalid client event')
        from schoolnet.warp import resolve_cli
        system=platform.system();row={'at':now(),'elapsed_s':round(time.monotonic()-self.begin,2),'phase':phase,'system':system,'os_version':platform.release(),'architecture':platform.machine(),'app':files_state(system,self.log_reader)}
        try:row['warp']=warp_state(resolve_cli(self.cli))
        except (ValueError,OSError):row['warp']={'unavailable':True}
        row['network']=network_state(system,self.privacy);row['socks']=socket_check(self.port)
        from diagnostics.client_flows import collect as client_flows
        row['client_transport']=client_flows(system,command)
        row['client_event']={'kind':client_event,'evidence':'USER_REPORT' if client_event!='none' else 'NONE','delivery_verified_by_tool':False}
        if system=='Darwin':row['os_product_version']=platform.mac_ver()[0] or 'unknown'
        row['statistics']={'result':statistics_result,'evidence':'USER_REPORT' if statistics_result!='unknown' else 'NONE','verified_by_tool':False,'cycle':cycle}
        if error_code:row['error_code']=error_code
        if self.active:
            print('검사: WARP HTTPS (최대 7초)',flush=True)
            row['active_probes']={'warp':child_probe('warp',HOSTS[0],self.port)}
            for host in HOSTS:
                print('검사: '+host+' DNS / OS TLS / SOCKS TLS (각 최대 7초)',flush=True)
                row['active_probes'][host]={'dns':child_probe('dns',host,self.port),'os_https':child_probe('https',host,self.port),'proxy_https':child_probe('proxy_https',host,self.port)}
                if host=='auth.riotgames.com':row['active_probes'][host]['resolved_proxy_https']=child_probe('riot_service',host,self.port)
            # Checks themselves can create engine errors. Advance the log cursor
            # separately so they are not labelled as new client-only errors in
            # the next phase. Concurrent app traffic remains explicitly mixed.
            during=files_state(system,self.log_reader)
            row['logs_during_active_checks']=[{'location':loc['location'],'file':name,'error_window':info['error_window']} for loc in during.get('locations',[]) for name,info in loc.get('files',{}).items() if 'error_window' in info]
            row['probe_period_log_origin']='mixed_app_and_diagnostic_traffic_not_attributed'
        row['collected_until']=now()
        row['findings']=findings(row)
        from diagnostics.strata_assessment import assess
        row['strata_assessment']=assess(row)
        if phase in ('connected','in_game','post_game') and row['strata_assessment']['session']['state']=='SELECTIVE_NOT_OBSERVED':
            print('분리 연결이 관측되지 않았습니다. 진단 도구 버전과 앱 버전은 다릅니다. 게임 종료 후 MINER 연결 상태와 실행 중인 앱 버전을 확인하세요. / Selective session not observed; recorder version is not app version.',flush=True)
        self.samples.append(row);return row
    def save(self,output):
        output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
        report={'schema':1,'tool_version':VERSION,'read_only':True,'active_probes':self.active,'uploaded':False,'privacy':'No raw logs, addresses, SSID, accounts, tokens, packet captures or browsing history. Address/interface IDs are random-session HMACs.','samples':self.samples}
        encoded=json.dumps(report,ensure_ascii=False,indent=2).encode()
        overview=['MINER local diagnostics '+VERSION,'Active DNS/TLS checks: '+('ON' if self.active else 'OFF'),'Read-only; no network settings changed; no automatic upload.','Known reference game IP is a route check only, not your actual game server.','WARP Local Proxy mode is expected while MINER runs. MASQUE UDP transport is a separate setting.','Findings are hypotheses / observed state, not proof of game or anti-cheat compatibility.','']
        for row in self.samples:
            overview.append(row['at']+' '+row['phase']+': '+', '.join(row['findings']))
            overview.append('  Installed target version: '+str(row.get('app',{}).get('version','unknown'))+' (not proof of running image version)')
            for item in row.get('network',{}).get('running_miner_apps',[]):
                overview.append('  Running bundle metadata: '+str(item.get('version','unknown'))+' build '+str(item.get('build','unknown'))+' location='+item.get('location_kind','unresolved'))
            overview.append('  Selective session observation: '+row.get('strata_assessment',{}).get('session',{}).get('state','NOT_VERIFIED'))
            overview.append('  Client symptom (user report): '+row.get('client_event',{}).get('kind','none'))
            transport=row.get('client_transport',{})
            overview.append('  Client socket query: '+('OK' if transport.get('query_ok') else 'UNKNOWN')+'; TCP state is not chat/notification success.')
            for flow in transport.get('flows',[]):overview.append('    '+json.dumps(flow,sort_keys=True))
        overview.append('\nCompare before / connected / in_game / post_game / after_stop in this SAME session. Review report.json before sharing.')
        # Atomic replacement: an interrupted save leaves the last valid report intact.
        fd,name=tempfile.mkstemp(prefix='.miner-report-',dir=output.parent)
        try:
            os.close(fd)
            with zipfile.ZipFile(name,'w',zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('report.json',encoded);archive.writestr('SUMMARY.txt','\n'.join(overview))
            os.replace(name,output)
        finally:Path(name).unlink(missing_ok=True)
        return output


def main(argv=None):
    # Frozen Windows apps ignore PYTHONUTF8; redirected CI and legacy consoles
    # can default to cp1252 and fail before the first Korean instruction.
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='replace')
    p=argparse.ArgumentParser(description='MINER local read-only diagnostic recorder / 로컬 진단')
    p.add_argument('--version',action='version',version=VERSION)
    p.add_argument('--output',type=Path)
    p.add_argument('--phase',choices=PHASES,default='error')
    p.add_argument('--statistics-result',choices=OUTCOMES,default='unknown')
    p.add_argument('--client-event',choices=CLIENT_EVENTS,default='none')
    p.add_argument('--cycle',type=int,choices=range(1,11))
    p.add_argument('--interactive',action='store_true')
    p.add_argument('--active',action='store_true',help='Opt in to fixed DNS and TLS requests. Never changes routing or WARP mode.')
    p.add_argument('--warp-cli');p.add_argument('--port',type=int,default=40000)
    p.add_argument('--error-code',type=lambda s:s if re.fullmatch(r'[A-Za-z0-9 _-]{1,40}',s) else p.error('Use an error CODE only; no account details'))
    p.add_argument('--probe',choices=('dns','https','proxy_https','warp','riot_service'),help=argparse.SUPPRESS);p.add_argument('--host',choices=HOSTS,default=HOSTS[0],help=argparse.SUPPRESS)
    args=p.parse_args(argv)
    if not 1024<=args.port<=65535:p.error('Port must be 1024..65535')
    if args.probe:
        try:print(json.dumps(probe(args.probe,args.host,args.port)));return 0
        except Exception as exc:
            from schoolnet.protocol_output import transport_detail
            print(json.dumps({'ok':False,'error':type(exc).__name__,**transport_detail(exc)}));return 1
    interactive=args.interactive or (getattr(sys,'frozen',False) and len(sys.argv)==1)
    output=args.output or Path.home()/'Desktop'/('MINER-Diagnostics-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.zip')
    if interactive and not args.active:
        try:args.active=input('외부 DNS·TLS 검사 허용? 고정 Cloudflare/Riot/LoL 요청만 사용합니다. [y/N]: ').strip().lower()=='y'
        except (KeyboardInterrupt,EOFError):return 0
    recorder=Recorder(args.port,args.active,args.warp_cli)
    print('MINER Diagnostics: read-only / 읽기 전용. No automatic upload / 자동 업로드 없음.',flush=True)
    print('DNS/TLS 외부 검사 / active probes: '+('ON' if args.active else 'OFF'),flush=True)
    try:
        while True:
            phase=args.phase;code=args.error_code;client_event=args.client_event
            if interactive:
                print('\n1 연결 전(before)  2 MINER 연결(connected)  3 게임 중(in_game)  4 통계창(post_game)  5 중지 후(after_stop)  6 오류(error)  0 저장·종료',flush=True)
                value=input('현재 단계 / phase [0-6]: ').strip()
                if value=='0':break
                if value not in ('1','2','3','4','5','6'):continue
                phase=PHASES[int(value)-1]
                if phase=='error':
                    symptom=input('클라이언트 증상: 1 수락창 누락 / 2 온라인·오프라인 불일치 / 3 파티 오류 / Enter 기타: ').strip()
                    client_event={'1':'ready_check_missing','2':'presence_mismatch','3':'party_failure'}.get(symptom,'none')
                    entered=input('오류 CODE만 입력 (없으면 Enter): ').strip()
                    code=entered if re.fullmatch(r'[A-Za-z0-9 _-]{1,40}',entered) else None
            print('Collecting / 수집 중: '+phase+' (각 명령에 시간 제한이 있습니다)',flush=True)
            outcome=args.statistics_result
            if interactive and phase=='post_game':
                value=input('통계창 결과: 1 표시됨 / 2 30초 이상 무한 로딩 / 3 오류 / Enter 미확인: ').strip()
                outcome={'1':'loaded','2':'timeout_30s','3':'error'}.get(value,'unknown')
            row=recorder.snapshot(phase,code,outcome,args.cycle,client_event);recorder.save(output)
            print('Saved / 저장: '+str(output)+'\n'+', '.join(row['findings']),flush=True)
            if not interactive:break
    except (KeyboardInterrupt,EOFError):pass
    if recorder.samples:recorder.save(output);print('Report / 진단 파일: '+str(output),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
