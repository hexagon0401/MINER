"""Bounded TLS-verified DoH through WARP. Never query the OS for Riot origins."""
import http.client
import ipaddress
from pathlib import Path
import secrets
import socket
import ssl
import struct
import sys
import time
from .probe import socks_connect


def parse_answer(query, body):
    if len(body)<12 or body[:2]!=query[:2] or body[2]&0xfa!=0x80 or body[3]&15 or body[4:6]!=b'\0\1':
        raise ValueError('Invalid proxy DNS response')
    if body[12:len(query)]!=query[12:]:raise ValueError('Proxy DNS question mismatch')
    count=struct.unpack('!H',body[6:8])[0]
    if count>64:raise ValueError('Proxy DNS answer exceeds limit')
    offset=len(query)
    for _ in range(count):
        for _ in range(128):
            if offset>=len(body):raise ValueError('Truncated proxy DNS name')
            length=body[offset];offset+=1
            if length&192==192:
                if offset>=len(body):raise ValueError('Truncated proxy DNS pointer')
                offset+=1;break
            if length==0:break
            if length>63 or offset+length>len(body):raise ValueError('Invalid proxy DNS name')
            offset+=length
        else:raise ValueError('Proxy DNS name exceeds limit')
        if offset+10>len(body):raise ValueError('Truncated proxy DNS record')
        kind,cls,ttl,size=struct.unpack('!HHIH',body[offset:offset+10]);offset+=10
        if offset+size>len(body):raise ValueError('Truncated proxy DNS data')
        if kind==1 and cls==1 and size==4:
            address=ipaddress.ip_address(body[offset:offset+4])
            if address.is_global:return str(address)
        offset+=size
    raise ValueError('Proxy DNS returned no public IPv4 origin')


def resolve_origin(host, port, deadline, active):
    question=b''.join(bytes([len(part)])+part.encode('ascii') for part in host.split('.'))+b'\0\0\1\0\1'
    query=secrets.token_bytes(2)+b'\1\0\0\1\0\0\0\0\0\0'+question
    def remaining():
        value=deadline-time.monotonic()
        if value<=0:raise TimeoutError('Proxy DNS deadline exceeded')
        return value
    with socket.create_connection(('127.0.0.1',port),timeout=remaining()) as sock:
        active[0]=sock;socks_connect(sock,'1.1.1.1',443);sock.settimeout(remaining())
        context=ssl.create_default_context()
        if getattr(sys,'frozen',False):context.load_verify_locations(cafile=str(Path(sys._MEIPASS)/'cacert.pem'))
        with context.wrap_socket(sock,server_hostname='cloudflare-dns.com') as tls:
            active[0]=tls;tls.settimeout(remaining())
            tls.sendall(b'POST /dns-query HTTP/1.1\r\nHost: cloudflare-dns.com\r\nContent-Type: application/dns-message\r\nAccept: application/dns-message\r\nConnection: close\r\nContent-Length: '+str(len(query)).encode()+b'\r\n\r\n'+query)
            response=http.client.HTTPResponse(tls);response.begin()
            if response.status!=200:raise ValueError('Proxy DNS HTTPS response failed')
            body=response.read(4097)
            if len(body)>4096:raise ValueError('Proxy DNS response exceeds limit')
    return parse_answer(query,body)
