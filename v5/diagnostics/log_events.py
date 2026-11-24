"""Allowlisted error shapes, never raw log text, hostnames, tokens or IP values."""
from collections import Counter
import ipaddress
import json
import os
import re

LIMIT=131072
CAUSES={
    'connection_refused':r'connection refused|actively refused',
    'connection_reset':r'connection reset|forcibly closed',
    'timeout':r'timed? ?out|deadline exceeded',
    'tls_certificate':r'certificate verify|certificate verification|unknown authority|certificate has expired',
    'tls_handshake':r'tls.*handshake|handshake.*fail',
    'dns_failure':r'no such host|server misbehaving|NXDOMAIN|SERVFAIL|dns.*(?:failed|failure|refused)',
    'socks_server_failure':r'socks.*(?:general failure|server failure|host unreachable|network unreachable|connection not allowed|unsupported|connect failed)',
    'remote_closed':r'\bEOF\b|closed by.*(?:remote|peer)|unexpected end',
    'network_unreachable':r'network is unreachable|no route to host',
    'broken_pipe':r'broken pipe',
    'cancelled':r'context cancel|operation cancel',
    'permission_denied':r'permission denied|operation not permitted',
}
FAMILIES=('riotgames.com','riotgames.net','riotcdn.net','pvp.net','leagueoflegends.com','lolstatic.com','lolesports.com')


def classify(text):
    shapes=Counter();unknown=0;classified=0;lines=text.splitlines()
    for line in lines:
        if line.startswith('{'):
            try:
                event=json.loads(line)
                if event.get('event')=='engine_error_categories':
                    summary=event['summary']
                    for item in summary.get('patterns',[])[:24]:
                        component=item['component'];cause=item['cause'];family=item['domain_family'];endpoint=item['endpoint_class'];count=item['count']
                        if component not in ('warp_outbound','dns','tun','unclassified') or cause not in CAUSES or family not in (*FAMILIES,'unclassified') or not set(endpoint.split('+')).issubset({'local_proxy_40000','miner_dns','synthetic','loopback','private','public','unclassified'}) or type(count) is not int or not 0<=count<=8192:continue
                        shapes[(component,cause,family,endpoint)]+=count
                    count=summary.get('unclassified_warning_error_lines',0)
                    if type(count) is int and 0<=count<=8192:unknown+=count
                    count=summary.get('classified_error_lines',0)
                    if type(count) is int and 0<=count<=8192:classified+=count
                    continue
            except (ValueError,TypeError,KeyError,AttributeError):pass
        if not re.search(r'\b(?:ERROR|WARN)\b|(?:Error|Exception):',line,re.I):continue
        causes=[key for key,pattern in CAUSES.items() if re.search(pattern,line,re.I)]
        if not causes:
            if re.search(r'\b(?:ERROR|WARN)\b',line):unknown+=1
            continue
        classified+=1
        component='warp_outbound' if re.search(r'outbound/socks|\[warp\]',line,re.I) else 'dns' if re.search(r'\bdns[:/\[]',line,re.I) else 'tun' if re.search(r'inbound/tun',line,re.I) else 'unclassified'
        families=[family for family in FAMILIES if re.search(r'(?<![a-z0-9_-])(?:[a-z0-9_-]+\.)*'+re.escape(family)+r'(?=[:/\s\]\)]|$)',line,re.I)] or ['unclassified']
        endpoints=set()
        if re.search(r'127\.0\.0\.1:40000\b|\[::1\]:40000\b',line):endpoints.add('local_proxy_40000')
        for address in re.findall(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])',line):
            try:
                ip=ipaddress.ip_address(address)
                endpoints.add('miner_dns' if address=='172.30.255.2' else 'synthetic' if ip in ipaddress.ip_network('198.18.0.0/15') else 'loopback' if ip.is_loopback else 'private' if ip.is_private else 'public')
            except ValueError:pass
        endpoint='+'.join(sorted(endpoints)) or 'unclassified'
        for cause in causes:
            for family in families:shapes[(component,cause,family,endpoint)]+=1
    return {'processed_lines':len(lines),'classified_error_lines':classified,'unclassified_warning_error_lines':unknown,
            'patterns':[dict(zip(('component','cause','domain_family','endpoint_class'),key),count=count) for key,count in shapes.most_common(24)]}


class LogWindows:
    def __init__(self):self.positions={}
    def read(self,path):
        # Track positions in memory only. Identity and raw boundary bytes are
        # never exported. Detect both rotation and copy-truncate/regrowth.
        with path.open('rb') as f:
            stat=os.fstat(f.fileno());identity=(stat.st_dev,stat.st_ino);size=stat.st_size
            previous=self.positions.get(path);scope='baseline_tail';start=max(0,size-LIMIT)
            if previous:
                old_identity,end,anchor=previous
                if identity==old_identity and size>=end:
                    f.seek(max(0,end-len(anchor)));same=f.read(len(anchor))==anchor
                    if same:start=max(end,size-LIMIT);scope='since_previous_sample'
                    else:scope='replaced_or_truncated_tail'
                else:scope='rotated_or_truncated_tail'
            requested=previous[1] if previous and scope=='since_previous_sample' else 0
            f.seek(start);data=f.read(min(LIMIT,size-start));end=start+len(data)
            f.seek(max(0,end-64));anchor=f.read(min(64,end))
            self.positions[path]=(identity,end,anchor)
        # A bounded tail can begin mid-line; do not classify that partial line.
        if start>requested and b'\n' in data:data=data.split(b'\n',1)[1]
        return {'scope':scope,'window_start_bytes':start,'window_end_bytes':end,'bytes_not_in_window':max(0,start-requested),**classify(data.decode('utf-8','replace'))}
