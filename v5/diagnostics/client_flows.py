"""Read client socket metadata only; never export addresses, PIDs or credentials."""
from collections import Counter
import ipaddress
import json
import os
from pathlib import Path
import re

ROLES = {'leagueclient': 'league_backend', 'leagueclientux': 'league_ui',
         'leagueclientuxrender': 'league_ui', 'riotclientservices': 'riot_launcher',
         'riotclientux': 'riot_launcher', 'riotclientuxrender': 'riot_launcher'}
STATES = {'ESTABLISHED', 'SYN_SENT', 'SYN_RECEIVED', 'CLOSE_WAIT', 'FIN_WAIT_1',
          'FIN_WAIT_2', 'CLOSING', 'LAST_ACK', 'TIME_WAIT', 'CLOSED', 'UNKNOWN'}
PORTS = {443: 'https_candidate', 5223: 'chat_tls_candidate',
         5222: 'chat_tcp_candidate', 2099: 'platform_tcp_candidate'}


def role(name):
    return ROLES.get(Path(name).name.casefold().removesuffix('.exe'))


def shape(address, port, state, owner):
    try:
        ip = ipaddress.ip_address(address.split('%')[0])
        if ip.version == 6 and ip.ipv4_mapped: ip = ip.ipv4_mapped
        if type(port) is not int or not 1 <= port <= 65535 or owner not in ROLES.values(): return None
    except (ValueError, AttributeError): return None
    synthetic = ip in ipaddress.ip_network('198.18.0.0/15') if ip.version == 4 else ip in ipaddress.ip_network('fdfe:dcba:9876:1000::/64')
    destination = 'synthetic' if synthetic else 'loopback' if ip.is_loopback else 'real_address'
    state = state.upper().replace('-', '_')
    aliases = {'SYNRECEIVED': 'SYN_RECEIVED', 'SYNSENT': 'SYN_SENT', 'CLOSEWAIT': 'CLOSE_WAIT',
               'FINWAIT1': 'FIN_WAIT_1', 'FINWAIT2': 'FIN_WAIT_2', 'LASTACK': 'LAST_ACK', 'TIMEWAIT': 'TIME_WAIT'}
    state = aliases.get(state, state)
    return owner, PORTS.get(port, 'other_tcp'), destination, state if state in STATES else 'UNKNOWN'


def summarize(rows, *, query_ok, client_count=None, truncated=False):
    counts = Counter(value for value in rows if value is not None)
    return {'query_ok': query_ok, 'client_process_count': client_count, 'truncated': truncated,
            'flows': [dict(zip(('role', 'port_class', 'destination_class', 'tcp_state'), key), count=count)
                      for key, count in sorted(counts.items())],
            'evidence': 'OS_TCP_SOCKET_METADATA_ONLY', 'chat_login_verified': False,
            'ready_check_delivery_verified': False, 'addresses_exported': False,
            'limitation': 'Port classes are candidates, not identified Riot services; TCP established is not application success.'}


def parse_macos(text, owners):
    rows = []; owner = None; peer = None; state = 'UNKNOWN'
    def finish():
        if owner and peer and '->' in peer:
            endpoint = peer.rsplit('->', 1)[1]
            match = re.fullmatch(r'(?:\[([^\]]+)\]|([^:]+)):(\d+)', endpoint)
            if match: rows.append(shape(match[1] or match[2], int(match[3]), state, owner))
    for line in text.splitlines():
        if not line: continue
        if line.startswith('p'):
            finish(); owner = owners.get(line[1:]); peer = None; state = 'UNKNOWN'
        elif line.startswith('f'):
            finish(); peer = None; state = 'UNKNOWN'
        elif line.startswith('n'): peer = line[1:]
        elif line.startswith('TST='): state = line[4:]
    finish()
    return rows


def collect(system, command):
    if system == 'Darwin':
        meta, text = command(['/bin/ps', '-ww', '-U', str(os.getuid()), '-o', 'pid=,comm='])
        if not meta.get('ok'): return summarize([], query_ok=False)
        owners = {}
        for line in text.splitlines():
            fields = line.strip().split(None, 1)
            if len(fields) == 2 and fields[0].isdigit() and role(fields[1]): owners[fields[0]] = role(fields[1])
        if not owners: return summarize([], query_ok=True, client_count=0)
        truncated = len(owners) > 24 or bool(meta.get('truncated'))
        selected = dict(list(owners.items())[:24])
        meta, text = command(['/usr/sbin/lsof', '-nP', '-a', '-p', ','.join(selected), '-iTCP', '-FpfntT'], timeout=4)
        return summarize(parse_macos(text, selected) if meta.get('ok') else [], query_ok=bool(meta.get('ok')),
                         client_count=len(owners), truncated=truncated or bool(meta.get('truncated')))
    if system == 'Windows':
        script = """$ErrorActionPreference='Stop'; $session=(Get-Process -Id $PID).SessionId;
        $clients=@(Get-Process -Name LeagueClient,LeagueClientUx,LeagueClientUxRender,RiotClientServices,RiotClientUx,RiotClientUxRender -ErrorAction SilentlyContinue | Where-Object {$_.SessionId -eq $session});
        $owners=@{}; foreach($p in ($clients | Select-Object -First 24)){$owners[[string]$p.Id]=$p.ProcessName};
        $rows=@(); if($owners.Count){
          foreach($c in @(Get-NetTCPConnection -ErrorAction Stop | Where-Object {$owners.ContainsKey([string]$_.OwningProcess)} | Select-Object -First 1025)){
            $rows+=@{name=$owners[[string]$c.OwningProcess];address=$c.RemoteAddress;port=[int]$c.RemotePort;state=[string]$c.State}
          }
        }; @{count=$clients.Count;truncated=($clients.Count -gt 24);rows=$rows} | ConvertTo-Json -Depth 4 -Compress"""
        meta, text = command(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script], timeout=6)
        try:
            data = json.loads(text)
            if not meta.get('ok') or type(data.get('count')) is not int: raise ValueError()
            rows = [shape(item.get('address'), item.get('port'), str(item.get('state')), role(str(item.get('name'))))
                    for item in data.get('rows', [])[:1024]]
            return summarize(rows, query_ok=True, client_count=data['count'], truncated=data.get('truncated') is True or len(data.get('rows', [])) > 1024)
        except (ValueError, TypeError, AttributeError): return summarize([], query_ok=False)
    return summarize([], query_ok=False)
