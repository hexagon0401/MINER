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
import socketserver
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

class Proxy(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10)
        if recv_exact(self.request,3)!=b'\x05\x01\x00':raise ValueError('Unexpected SOCKS greeting')
        self.request.sendall(b'\x05\x00')
        header=recv_exact(self.request,4)
        if header!=b'\x05\x01\x00\x03':raise ValueError('Riot destination must use remote DNS')
        host=recv_exact(self.request,recv_exact(self.request,1)[0]).decode()
        port=struct.unpack('!H',recv_exact(self.request,2))[0]
        self.server.destinations.append((host,port))
        self.request.sendall(b'\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x00')
        while True:
            try:data=self.request.recv(1024)
            except socket.timeout:return
            if not data:return
            self.request.sendall(data)

class Server(socketserver.ThreadingTCPServer):
    daemon_threads=True


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
    with urllib.request.urlopen('https://api.github.com/zen',timeout=15) as response:
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
    proxy=Server(('127.0.0.1',0),Proxy);proxy.destinations=[]
    threading.Thread(target=proxy.serve_forever,daemon=True).start()
    report={'loopback_proxy_fixture':True,'warp_live_tested':False,'game_live_tested':False}
    try:
        with Forwarder(original) as relay:
            profile=Profile(platform='macos' if system=='Darwin' else 'windows',proxy_port=proxy.server_address[1],dns_forward_port=relay.port)
            config=build_config(profile);path=directory/'selective.json';write_json(path,config)
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
                    assert proxy.destinations==[('login.riotgames.com',443)],'Session replaced or hostname lost'
                    report['remote_dns_and_continuous_client_tcp']=True
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
        proxy.shutdown();proxy.server_close()
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
