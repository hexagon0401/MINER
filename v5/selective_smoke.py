"""Native CI routing/DNS test. Uses a loopback SOCKS fixture, never real WARP.

Only ephemeral CI hosts should run this privileged test. Original DNS is
journaled and recovered before the TUN/forwarder is removed.
"""
import argparse
from dataclasses import replace
import ipaddress
import json
import os
from pathlib import Path
import platform
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.request

from schoolnet.config import Profile,build_config,FAKE_V4,DNS_V4,DNS_V6
from schoolnet.dns_forwarder import Forwarder,recv_exact
from schoolnet.network_dns import Backend,Lease,command,powershell,probe_dns,normalized
from schoolnet.runtime import write_json
from resolution_fixture import Fixture,ORIGIN

def synthetic_aaaa(host):
    """Query the actual selective DNS listener, independent of OS scope/cache."""
    question=b''.join(bytes([len(part)])+part.encode('ascii') for part in host.split('.'))+b'\0'
    query=b'\x61\x62\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'+question+b'\x00\x1c\x00\x01'
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.settimeout(3);sock.connect((DNS_V4,53));sock.send(query);reply=sock.recv(4096)
    if len(reply)<12 or reply[:2]!=query[:2] or reply[3]&15:raise ValueError('AAAA DNS fixture failed')
    def skip_name(offset):
        while offset<len(reply):
            length=reply[offset];offset+=1
            if length&192==192:return offset+1
            if length==0:return offset
            offset+=length
        raise ValueError('Truncated DNS name')
    offset=skip_name(12)+4
    for _ in range(struct.unpack('!H',reply[6:8])[0]):
        offset=skip_name(offset)
        kind,cls,ttl,size=struct.unpack('!HHIH',reply[offset:offset+10]);offset+=10
        if kind==28 and size==16:return socket.inet_ntop(socket.AF_INET6,reply[offset:offset+size])
        offset+=size
    raise ValueError('No AAAA DNS fixture answer')


def route_interface(ip):
    if platform.system()=='Darwin':
        text=command(['/sbin/route','-n','get',ip])
        import re
        found=re.search(r'^\s*interface:\s*(\S+)',text,re.M)
        if not found:raise ValueError('Route not found')
        return found[1]
    # Find-NetRoute returns route and source-address objects; select the route.
    return powershell("Find-NetRoute -RemoteIPAddress '"+ip+"' | Where-Object {$_.DestinationPrefix} | Select-Object -First 1 -ExpandProperty InterfaceIndex").strip()


def same_dns(backend,snapshot):
    current=backend.current(snapshot)
    if snapshot['system']=='Darwin':return normalized(current)==normalized(snapshot['manual'])
    by_family={int(item['AddressFamily']):normalized(item['ServerAddresses']) for item in current}
    return all(by_family.get(2 if item['family']=='IPv4' else 23,[])==normalized(item['servers']) for item in snapshot['families'])


def ordinary_https():
    # Uses the OS resolver and normal TLS certificate verification.
    with urllib.request.urlopen('https://github.com/robots.txt',timeout=15) as response:
        if response.status!=200:raise ValueError('Ordinary HTTPS failed')
        response.read(2048)


def run(engine,directory,guardian_executable=None):
    engine=Path(engine).resolve();directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    system=platform.system()
    if system not in ('Windows','Darwin'):raise ValueError('Native macOS/Windows only')
    if system=='Windows':
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():raise ValueError('Administrator required')
    elif os.geteuid()!=0:raise ValueError('Root required')
    physical=route_interface('8.8.8.8')
    backend=Backend();lease=Lease(directory,backend);original=lease.prepare()
    snapshot=lease.snapshot;child=guardian=None
    fixture=Fixture(directory/'proxy-dns-fixture');proxy=fixture.server
    report={'loopback_proxy_fixture':True,'warp_live_tested':False,'game_live_tested':False}
    try:
        with Forwarder(original) as relay:
            profile=Profile(platform='macos' if system=='Darwin' else 'windows',proxy_port=proxy.server_address[1],dns_forward_port=relay.port)
            config=fixture.configure(build_config(profile));path=directory/'selective.json';write_json(path,config)
            with (directory/'selective-smoke.log').open('w') as log:
                child=subprocess.Popen([str(engine),'run','-c',str(path)],cwd=directory,stdout=log,stderr=log)
                try:
                    deadline=time.monotonic()+25
                    while not probe_dns():
                        if child.poll() is not None:raise ValueError((directory/'selective-smoke.log').read_text())
                        if time.monotonic()>deadline:raise ValueError('Selective DNS listener never became ready')
                        time.sleep(.15)
                    assert route_interface('8.8.8.8')==physical,'Default Internet route changed'
                    assert route_interface('104.160.131.3')==physical,'Real game IP captured by TUN'
                    assert route_interface('198.18.0.1')!=physical,'Synthetic Riot route missing'
                    report['real_ip_routes_bypass_tun']=True
                    if system=='Windows':
                        from schoolnet.dns_guard import spawn
                        guardian=spawn(directory,child.pid,executable=guardian_executable)
                    lease.activate()
                    ordinary_https();report['ordinary_os_dns_and_tls']=True
                    if system=='Darwin':
                        import ssl
                        from unittest.mock import patch
                        from schoolnet.client_path import verify as verify_client_path
                        context=ssl.create_default_context(cafile=str(fixture.cert))
                        proxy.origin_tls=True
                        try:
                            with patch('schoolnet.client_path.ssl.create_default_context',return_value=context):report['os_client_path']=verify_client_path()
                        finally:proxy.origin_tls=False
                        assert report['os_client_path']['os_dns_synthetic'] and report['os_client_path']['tls_verified']
                        assert proxy.destinations==[(ORIGIN,443)]
                        proxy.destinations.clear()
                    fake=socket.gethostbyname('login.riotgames.com')
                    assert ipaddress.ip_address(fake) in ipaddress.ip_network(FAKE_V4),'OS DNS did not return synthetic Riot address'
                    with socket.create_connection((fake,443),timeout=10) as session:
                        session.settimeout(10)
                        for phase in ('client-login','game-start','mid-game','post-game-statistics'):
                            payload=(phase+'\n').encode();session.sendall(payload)
                            assert recv_exact(session,len(payload))==payload
                            # Normal applications work while the same client TCP
                            # stays open; no disconnect/mode switch at phase boundaries.
                            ordinary_https()
                    assert proxy.destinations==[(ORIGIN,443)],'Session replaced or hostname lost'
                    report['remote_dns_and_continuous_client_tcp']=True
                    report['proxy_doh_real_ip_no_hostname_recursion']=True
                    assert not proxy.rejected_hostnames,'Origin hostname reached the recursive proxy resolver'
                    # Explicit AF_INET6 query; no external IPv6 connectivity is
                    # needed for a synthetic address routed through this TUN.
                    from schoolnet.config import FAKE_V6
                    try:os_ipv6=socket.getaddrinfo('login.riotgames.com',443,socket.AF_INET6,socket.SOCK_STREAM)[0][4][0]
                    except socket.gaierror:os_ipv6=None
                    resolved=ipaddress.ip_address(os_ipv6) if os_ipv6 else None
                    mapped=resolved.ipv4_mapped if resolved else None
                    native_synthetic=bool(resolved and resolved in ipaddress.ip_network(FAKE_V6))
                    mapped_synthetic=bool(mapped and mapped in ipaddress.ip_network(FAKE_V4))
                    report['os_resolver_aaaa_address_class']='synthetic_v6' if native_synthetic else 'synthetic_v4_mapped' if mapped_synthetic else 'non_synthetic_v6' if resolved else 'no_result'
                    report['os_resolver_aaaa_synthetic']=native_synthetic or mapped_synthetic
                    if system=='Windows' or snapshot.get('dns_mode'):assert report['os_resolver_aaaa_synthetic'],'OS AAAA selective DNS regression'
                    report['os_resolver_aaaa_boundary']='NONE_OBSERVED' if report['os_resolver_aaaa_synthetic'] else 'OS_SCOPE_CACHE_OR_IPV6_POLICY_REQUIRES_FIELD_TEST'
                    ipv6=(synthetic_aaaa('login.riotgames.com'),443)
                    assert ipaddress.ip_address(ipv6[0]) in ipaddress.ip_network(FAKE_V6),'Selective listener AAAA must be synthetic'
                    with socket.socket(socket.AF_INET6,socket.SOCK_STREAM) as session6:
                        session6.settimeout(10);session6.connect(ipv6);session6.sendall(b'ipv6');assert recv_exact(session6,4)==b'ipv6'
                    assert proxy.destinations[-1]==(ORIGIN,443)
                    report['synthetic_ipv6_remote_dns_tcp']=True
                    # A game process also uses Riot HTTPS services. Its TCP must
                    # not fall into the old all-game-traffic direct exception.
                    if system=='Darwin':
                        source=directory/'game-service.c';probe=directory/'LeagueofLegends'
                        source.write_text(r'''#include <sys/socket.h>
#include <sys/time.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
int main(int n,char **v){
 if(n!=2)return 2;
 int s=socket(AF_INET,SOCK_STREAM,0);struct timeval t={5,0};
 setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&t,sizeof(t));setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,&t,sizeof(t));
 struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_port=htons(443);inet_pton(AF_INET,v[1],&a.sin_addr);
 if(connect(s,(void*)&a,sizeof(a)))return 3;
 char b[9];if(send(s,"post-game",9,0)!=9)return 4;
 if(recv(s,b,9,MSG_WAITALL)!=9 || memcmp(b,"post-game",9))return 5;
 close(s);puts("post-game");return 0;
}''')
                        subprocess.run(['/usr/bin/clang',str(source),'-o',str(probe)],check=True,timeout=30)
                        stats=socket.gethostbyname('stats.riotgames.com')
                        result=subprocess.run([str(probe),stats],capture_output=True,text=True,timeout=10,check=True)
                        assert result.stdout.strip()=='post-game'
                        assert proxy.destinations[-1]==(ORIGIN,443)
                        assert any(q[0]=='stats.riotgames.com' for q in proxy.dns_questions)
                        report['game_service_tcp_proxied']=True

                    lease.close();assert same_dns(backend,snapshot),'DNS settings not restored exactly'
                    report['original_dns_recovered_before_engine_stop']=True
                    if guardian:
                        guardian.wait(timeout=10);assert guardian.returncode==0;guardian=None
                    # Reapply, then simulate an unexpected engine crash.
                    lease.prepare()
                    if system=='Windows':guardian=spawn(directory,child.pid,executable=guardian_executable)
                    lease.activate();child.kill();child.wait(timeout=10)
                    if guardian:
                        guardian.wait(timeout=20)
                        assert guardian.returncode==0,'Recovery guardian failed'
                        guardian=None
                    else:
                        # Same recovery transaction used by launchd helper polling.
                        Lease.recover(directory)
                    assert same_dns(backend,snapshot),'Crash recovery did not restore original DNS'
                    report['engine_crash_dns_recovered']=True
                    ordinary_https();report['ordinary_https_after_recovery']=True
                finally:
                    lease.close()
                    if child.poll() is None:child.terminate();child.wait(timeout=15)
                    if guardian:guardian.wait(timeout=20)
    finally:
        fixture.close()
    assert route_interface('8.8.8.8')==physical
    report.update(ok=True,system=system,windows_guardian_tested=system=='Windows',dhcp_or_manual_mode_preserved=True,
        source_commit=os.environ.get('GITHUB_SHA'),packaged_guardian_verified=bool(guardian_executable))
    receipt=directory/'selective.verification.json'
    write_json(receipt,report)
    if system=='Darwin':receipt.chmod(0o644)  # Sanitized booleans, read by the unprivileged packager.
    print(json.dumps(report,indent=2));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine',required=True);parser.add_argument('--directory',required=True)
    args=parser.parse_args();run(args.engine,args.directory)
