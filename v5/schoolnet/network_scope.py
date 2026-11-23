"""Read-only DNS lease/NIC checks. Never apply settings on a new adapter."""
import re
from .config import DNS_V4,DNS_V6


def check(snapshot):
    from .network_dns import Backend,command,powershell,normalized
    try:
        Backend(snapshot['system']).validate(snapshot)
        if snapshot['system']=='Darwin':
            route=command(['/sbin/route','-n','get','default'],timeout=2)
            found=re.search(r'^\s*interface:\s*(\S+)',route,re.M)
            if not found or found[1]!=snapshot['interface']:return {'healthy':False,'reason_code':'DEFAULT_INTERFACE_CHANGED'}
            raw=command(['/usr/sbin/networksetup','-getdnsservers',snapshot['service']],timeout=2)
            values=[value for value in raw.splitlines() if value in (DNS_V4,DNS_V6)]
            if len(values)!=2 or len(raw.splitlines())!=2:return {'healthy':False,'reason_code':'DNS_LEASE_CHANGED'}
        else:
            # Use the validated GUID, not caller-provided script fragments.
            script=Backend('Windows').win_adapter(snapshot)
            script+="$r=Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Sort-Object @{Expression={$_.RouteMetric+$_.InterfaceMetric}} | Select-Object -First 1; if(!$r -or $r.ifIndex -ne $a.ifIndex){'NIC_CHANGED'}else{(Get-DnsClientServerAddress -InterfaceIndex $a.ifIndex).ServerAddresses -join ','}"
            raw=powershell(script).strip()
            if raw=='NIC_CHANGED':return {'healthy':False,'reason_code':'DEFAULT_INTERFACE_CHANGED'}
            if set(normalized(raw.split(',')))!=set(normalized([DNS_V4,DNS_V6])):return {'healthy':False,'reason_code':'DNS_LEASE_CHANGED'}
        return {'healthy':True,'reason_code':'SCOPE_UNCHANGED'}
    except Exception:return {'healthy':None,'reason_code':'SCOPE_CHECK_UNAVAILABLE'}
