"""Scoped, journaled DNS changes; never change a default route or an unrelated adapter."""
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import socket
import struct
import subprocess
import time

from .config import DNS_V4, DNS_V6

JOURNAL = 'network-dns-v1.json'


def command(args):
    return subprocess.run(args,check=True,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15).stdout


def powershell(body):
    executable=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    return command([str(executable),'-NoProfile','-NonInteractive','-Command',
        "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); "+body])


def addresses(values):
    result=[]
    for value in values:
        try:
            if not isinstance(value,str) or len(value)>128:continue
            if '%' in value and (':' not in value or not re.fullmatch(r'[^%]+%[A-Za-z0-9_.-]+',value)):continue
            address=ipaddress.ip_address(value.split('%')[0])
            reserved=('172.30.255.0/30','fdfe:dcba:9876::/126','198.18.0.0/15','fdfe:dcba:9876:1000::/64')
            if address.is_unspecified or address.is_multicast or any(address.version==ipaddress.ip_network(net).version and address in ipaddress.ip_network(net) for net in reserved):continue
            result.append(value)
        except (ValueError,AttributeError): continue
    return list(dict.fromkeys(result))[:8]


def normalized(values):
    return [str(ipaddress.ip_address(v.split('%')[0])) for v in values]


class Backend:
    def __init__(self, system=None):self.system=system or platform.system()

    def capture(self):
        if self.system=='Darwin':
            route=command(['/sbin/route','-n','get','default'])
            found=re.search(r'^\s*interface:\s*(\S+)\s*$',route,re.M)
            if not found: raise ValueError('No physical default interface')
            interface=found[1]
            if interface.startswith('utun'):raise ValueError('Another full tunnel is active; use WARP Local Proxy first')
            services=command(['/usr/sbin/networksetup','-listnetworkserviceorder'])
            service=None;name=None
            for line in services.splitlines():
                match=re.match(r'^\(\d+\) (.+)$',line)
                if match:name=match[1]
                if re.search(r'Device:\s*'+re.escape(interface)+r'\)',line): service=name;break
            if not service:raise ValueError('Cannot identify the active macOS network service')
            manual=addresses(command(['/usr/sbin/networksetup','-getdnsservers',service]).splitlines())
            dns=command(['/usr/sbin/scutil','--dns'])
            blocks=re.split(r'resolver #\d+',dns)
            candidates=[]
            for block in blocks:
                if 'mdns' in block or 'nameserver[' not in block:continue
                if 'if_index' in block and '('+interface+')' not in block:continue
                candidates.extend(re.findall(r'nameserver\[\d+\]\s*:\s*(\S+)',block))
            effective=manual or addresses(candidates)
            effective=[value+('%'+interface) if ':' in value and ipaddress.ip_address(value.split('%')[0]).is_link_local and '%' not in value else value for value in effective]
            if not effective:raise ValueError('No original system DNS servers; no settings changed')
            return {'schema':1,'system':'Darwin','interface':interface,'service':service,'manual':manual,'servers':effective}
        if self.system!='Windows':raise ValueError('Scoped DNS requires macOS or Windows')
        raw=powershell(r"""
        $r=Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Sort-Object @{Expression={$_.RouteMetric+$_.InterfaceMetric}} | Select-Object -First 1;
        if(!$r){$r=Get-NetRoute -DestinationPrefix '::/0' | Sort-Object RouteMetric | Select-Object -First 1};
        if(!$r){throw 'No physical default route'};
        $a=Get-NetAdapter -IncludeHidden | Where-Object {$_.ifIndex -eq $r.InterfaceIndex} | Select-Object -First 1;
        if(!$a){throw 'Default adapter not found'};
        $families=@(); foreach($f in @('IPv4','IPv6')){
          $d=Get-DnsClientServerAddress -InterfaceIndex $a.ifIndex -AddressFamily $f;
          $base=if($f -eq 'IPv4'){'Tcpip'}else{'Tcpip6'};
          $p=Get-ItemProperty -LiteralPath ("HKLM:\SYSTEM\CurrentControlSet\Services\"+$base+"\Parameters\Interfaces\"+$a.InterfaceGuid) -ErrorAction SilentlyContinue;
          $families+=@{family=$f;manual=[bool]$p.NameServer;servers=@($d.ServerAddresses)}
        };
        @{schema=1;system='Windows';interface=[string]$a.ifIndex;guid=[string]$a.InterfaceGuid;families=$families} | ConvertTo-Json -Depth 5 -Compress
        """)
        snapshot=json.loads(raw)
        all_servers=[]
        for family in snapshot['families']:
            for value in family['servers']:
                if ':' in value and ipaddress.ip_address(value.split('%')[0]).is_link_local and '%' not in value:
                    value+='%'+snapshot['interface']
                all_servers.append(value)
        snapshot['servers']=addresses(all_servers)
        if not snapshot['servers']:raise ValueError('No original system DNS servers; no settings changed')
        return snapshot

    def current(self, snapshot):
        self.validate(snapshot)
        if self.system=='Darwin':
            raw=command(['/usr/sbin/networksetup','-getdnsservers',snapshot['service']])
            values=[]
            for line in raw.splitlines():
                try:ipaddress.ip_address(line);values.append(line)
                except ValueError:pass
            return values
        value=powershell(self.win_adapter(snapshot)+"Get-DnsClientServerAddress -InterfaceIndex $a.ifIndex | Select-Object AddressFamily,ServerAddresses | ConvertTo-Json -Depth 4 -Compress")
        result=json.loads(value)
        return result if isinstance(result,list) else [result]

    def validate(self, snapshot):
        if snapshot.get('schema')!=1 or snapshot.get('system')!=self.system:raise ValueError('Invalid DNS recovery journal')
        if not snapshot.get('servers') or addresses(snapshot['servers'])!=snapshot['servers']:raise ValueError('Invalid original DNS addresses')
        if self.system=='Darwin':
            name=snapshot.get('service','')
            if not isinstance(name,str) or not 1<=len(name)<=255 or any(c in name for c in '\r\n\x00'):raise ValueError('Invalid service name')
            if addresses(snapshot.get('manual',[]))!=snapshot.get('manual',[]):raise ValueError('Invalid manual DNS addresses')
        else:
            if not re.fullmatch(r'\{?[a-fA-F0-9-]{36}\}?',snapshot.get('guid','')):raise ValueError('Invalid network adapter identity')
            if {entry.get('family') for entry in snapshot.get('families',[])}!={'IPv4','IPv6'} or len(snapshot['families'])!=2:raise ValueError('Incomplete adapter DNS recovery record')
            for entry in snapshot.get('families',[]):
                if entry.get('family') not in ('IPv4','IPv6') or type(entry.get('manual')) is not bool:raise ValueError('Invalid adapter DNS family')
                if addresses(entry['servers'])!=entry['servers']:raise ValueError('Invalid DNS recovery addresses')

    def win_adapter(self,snapshot):
        self.validate(snapshot)
        guid=snapshot['guid'].strip('{}')
        return f"$a=Get-NetAdapter -IncludeHidden | Where-Object {{$_.InterfaceGuid -and $_.InterfaceGuid.ToString().Trim('{{','}}') -eq '{guid}'}} | Select-Object -First 1; if(!$a){{throw 'Original adapter is unavailable'}}; "

    def apply(self,snapshot):
        self.validate(snapshot)
        if self.system=='Darwin':command(['/usr/sbin/networksetup','-setdnsservers',snapshot['service'],DNS_V4,DNS_V6])
        else:
            script=self.win_adapter(snapshot)
            for family,server in [('IPv4',DNS_V4),('IPv6',DNS_V6)]:
                script+=f"$d=Get-DnsClientServerAddress -InterfaceIndex $a.ifIndex -AddressFamily {family}; if($d){{Set-DnsClientServerAddress -InputObject $d -ServerAddresses '{server}'}}; "
            powershell(script)
        self.flush()

    def restore(self,snapshot):
        current=self.current(snapshot)
        if self.system=='Darwin':
            if current and set(normalized(current)).issubset(set(normalized([DNS_V4,DNS_V6]))):
                command(['/usr/sbin/networksetup','-setdnsservers',snapshot['service'],*(snapshot['manual'] or ['Empty'])])
            elif DNS_V4 in current or DNS_V6 in current:
                raise ValueError('DNS settings changed externally; temporary DNS recovery needs review')
        else:
            by_family={int(entry['AddressFamily']):entry['ServerAddresses'] for entry in current}
            script=self.win_adapter(snapshot)
            for original in snapshot['families']:
                family=original['family'];number=2 if family=='IPv4' else 23;stub=DNS_V4 if number==2 else DNS_V6
                if normalized(by_family.get(number,[]))!=normalized([stub]):continue
                script+=f"$d=Get-DnsClientServerAddress -InterfaceIndex $a.ifIndex -AddressFamily {family}; "
                if original['manual']:
                    values=','.join("'"+value+"'" for value in original['servers'])
                    script+=f"Set-DnsClientServerAddress -InputObject $d -ServerAddresses @({values}); "
                else:script+="Set-DnsClientServerAddress -InputObject $d -ResetServerAddresses; "
            powershell(script)
        self.flush()
        # Never remove the journal while one of our temporary DNS values remains.
        current=self.current(snapshot)
        values=current if self.system=='Darwin' else [v for item in current for v in item['ServerAddresses']]
        if set(normalized(values))&set(normalized([DNS_V4,DNS_V6])):raise ValueError('Temporary DNS still active; recovery journal preserved')

    def flush(self):
        if self.system=='Darwin':
            command(['/usr/bin/dscacheutil','-flushcache'])
            subprocess.run(['/usr/bin/killall','-HUP','mDNSResponder'],capture_output=True,timeout=5)
        else:powershell('Clear-DnsClientCache')


def journal_path(directory, secure=False):
    if os.name!='nt':return Path(directory)/JOURNAL
    root=Path(os.environ.get('ProgramData',r'C:\ProgramData'))/'MINER-Privileged-Recovery'
    if root.is_symlink() or (root.exists() and getattr(root.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Recovery directory must not be a reparse point')
    if secure:
        if root.exists():
            literal=str(root).replace("'","''")
            owner=powershell("(Get-Acl -LiteralPath '"+literal+"').GetOwner([Security.Principal.SecurityIdentifier]).Value").strip()
            if owner not in ('S-1-5-18','S-1-5-32-544'):raise ValueError('Recovery directory is not administrator-owned; preserving it')
        root.mkdir(exist_ok=True)
        command(['icacls',str(root),'/setowner','*S-1-5-32-544'])
        # Reset explicit grants as well: inherited or pre-existing user grants
        # must not let a non-admin replace the privileged recovery journal.
        literal=str(root).replace("'","''")
        powershell("$acl=[Security.AccessControl.DirectorySecurity]::new(); $acl.SetAccessRuleProtection($true,$false); "+
            "$acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')); "+
            "foreach($sid in @('S-1-5-18','S-1-5-32-544')){$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))}; Set-Acl -LiteralPath '"+literal+"' -AclObject $acl")
    return root/JOURNAL


def probe_dns(server=DNS_V4,port=53,timeout=.25):
    query=b'\x68\x12\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x0cminer-health\x07invalid\x00\x00\x01\x00\x01'
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout);sock.connect((server,port));sock.send(query);response=sock.recv(1024)
        return len(response)>12 and response[:2]==query[:2] and response[3]&15==0 and b'\x7f\x00\x00\x01' in response
    except OSError:return False


class Lease:
    def __init__(self,directory,backend=None,path=None):
        self.directory=Path(directory);self.backend=backend or Backend();self.snapshot=None
        self.path=Path(path) if path is not None else journal_path(directory,True)
    def prepare(self):
        self.recover(self.directory,self.backend,self.path)
        self.snapshot=self.backend.capture();self.backend.validate(self.snapshot)
        return self.snapshot['servers']
    def activate(self):
        from .runtime import write_json
        write_json(self.path,self.snapshot)  # Durable intent precedes OS mutation.
        try:self.backend.apply(self.snapshot)
        except Exception:
            self.backend.restore(self.snapshot);self.path.unlink(missing_ok=True);raise
    def close(self):self.recover(self.directory,self.backend,self.path)
    @staticmethod
    def recover(directory,backend=None,path=None):
        explicit=path is not None
        path=Path(path) if explicit else journal_path(directory)
        if not path.exists():return
        if os.name=='nt' and not explicit:path=journal_path(directory,True)
        if path.is_symlink():raise ValueError('DNS journal must not be a symlink')
        snapshot=json.loads(path.read_text())
        (backend or Backend()).restore(snapshot)
        path.unlink(missing_ok=True)
