"""Verify fixed Riot HTTPS through OS-selected FakeIP, not a direct proxy dial."""
import http.client
import ipaddress
from pathlib import Path
import queue
import socket
import ssl
import sys
import threading
import time

LOOKUPS=threading.BoundedSemaphore(2)

class ClientPathError(ValueError):
    def __init__(self,code):
        self.code=code
        super().__init__(code)

def resolve_os(host,timeout):
    if not LOOKUPS.acquire(blocking=False):raise ClientPathError('OS_DNS_LOOKUP_BUSY')
    result=queue.Queue(maxsize=1)
    def work():
        try:result.put((True,socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)))
        except OSError:result.put((False,None))
        finally:LOOKUPS.release()
    threading.Thread(target=work,daemon=True,name='MINER bounded OS lookup').start()
    try:ok,values=result.get(timeout=timeout)
    except queue.Empty:raise ClientPathError('CLIENT_PATH_TIMEOUT') from None
    if not ok or not values or len(values)>32:raise ClientPathError('OS_DNS_LOOKUP_FAILED')
    addresses=[]
    for item in values:
        address=ipaddress.ip_address(item[4][0].split('%')[0])
        if address.version==6 and address.ipv4_mapped:address=address.ipv4_mapped
        expected=ipaddress.ip_network('198.18.0.0/15') if address.version==4 else ipaddress.ip_network('fdfe:dcba:9876:1000::/64')
        if address not in expected:raise ClientPathError('OS_DNS_OUTSIDE_SELECTED_SPACE')
        if str(address) not in addresses:addresses.append(str(address))
    return sorted(addresses,key=lambda value:':' in value)

def verify(timeout=8):
    host='auth.riotgames.com';deadline=time.monotonic()+timeout;active=[None]
    def remaining():
        value=deadline-time.monotonic()
        if value<=0:raise ClientPathError('CLIENT_PATH_TIMEOUT')
        return value
    def abort():
        try:
            if active[0] is not None:active[0].shutdown(socket.SHUT_RDWR)
        except OSError:pass
    timer=threading.Timer(timeout,abort);timer.daemon=True;timer.start()
    try:
        addresses=resolve_os(host,min(3,remaining()))
        with socket.create_connection((addresses[0],443),timeout=remaining()) as sock:
            active[0]=sock
            context=ssl.create_default_context()
            if getattr(sys,'frozen',False):context.load_verify_locations(cafile=str(Path(sys._MEIPASS)/'cacert.pem'))
            with context.wrap_socket(sock,server_hostname=host) as tls:
                active[0]=tls;tls.settimeout(remaining())
                tls.sendall(b'HEAD / HTTP/1.1\r\nHost: auth.riotgames.com\r\nConnection: close\r\n\r\n')
                response=http.client.HTTPResponse(tls);response.begin()
                if not 100<=response.status<=599:raise ClientPathError('CLIENT_HTTP_INVALID')
                return {'os_dns_synthetic':True,'tls_verified':True,'http_status':response.status,'via':'os_fakeip_tun_proxy_doh',
                        'client_process_traffic_verified':False,'login_update_or_game_verified':False}
    except ClientPathError:raise
    except ssl.SSLCertVerificationError:raise ClientPathError('CLIENT_TLS_CERTIFICATE_FAILED') from None
    except TimeoutError:raise ClientPathError('CLIENT_PATH_TIMEOUT') from None
    except (OSError,ValueError,http.client.HTTPException):raise ClientPathError('CLIENT_PATH_TRANSPORT_FAILED') from None
    finally:timer.cancel()
