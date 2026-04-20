"""
doh_proxy.py - Pure-Python asyncio UDP DoH proxy
"""

import asyncio
import struct
import time
import random
import httpx
import logging
from collections import OrderedDict

from recon import ReconResult, PROVIDERS
from settings import Settings

class LRUCache:
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

def parse_dns_query(data: bytes):
    if len(data) < 12:
        return None, None, None
    
    transaction_id = data[0:2]
    qdcount = struct.unpack('>H', data[4:6])[0]
    
    if qdcount != 1:
        return transaction_id, None, None

    idx = 12
    qname_parts = []
    while idx < len(data):
        length = data[idx]
        if length == 0:
            idx += 1
            break
        elif (length & 0xC0) == 0xC0: 
            idx += 2
            break
        idx += 1
        qname_parts.append(data[idx:idx+length].decode('utf-8', 'ignore'))
        idx += length
        
    qname = ".".join(qname_parts)
    qtype = struct.unpack('>H', data[idx:idx+2])[0]
    
    return transaction_id, qname, qtype

def extract_ttl(data: bytes, qname: str) -> int:
    return 60

UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
]

class DoHProxyProtocol(asyncio.DatagramProtocol):
    def __init__(self, proxy):
        self.proxy = proxy

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        asyncio.create_task(self.proxy.handle_query(data, addr, self.transport))

class DoHProxy:
    def __init__(self, recon: ReconResult, config: Settings):
        self.recon = recon
        self.config = config
        self.mode = recon.recommended_mode
        self.provider_name = recon.recommended_provider or config.primary_provider
        self.port = 5353
        self.cache = LRUCache(500)
        self.provider_fails = {k: 0.0 for k in PROVIDERS}
        self.stop_event = asyncio.Event()
        self.transport = None
        self.client = httpx.AsyncClient(http2=True)

    async def start(self):
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: DoHProxyProtocol(self),
            local_addr=('127.0.0.1', self.port)
        )
        logging.info(f"DoH Proxy started on 127.0.0.1:{self.port} (mode: {self.mode})")
        await self.stop_event.wait()

    async def stop(self):
        self.stop_event.set()
        if self.transport:
            self.transport.close()
        await self.client.aclose()
        logging.info("DoH Proxy stopped.")

    def _build_doh_headers(self, mode: str) -> dict:
        headers = {
            "Content-Type": "application/dns-message",
            "Accept": "application/dns-message"
        }
        if mode == "obfuscated":
            headers["User-Agent"] = random.choice(UA_POOL)
            headers["Accept-Language"] = random.choice(["ko-KR,ko;q=0.9", "en-US,en;q=0.9"])
            headers["Cache-Control"] = "no-cache"
        return headers

    def _make_servfail(self, query_id: bytes) -> bytes:
        return query_id + b'\x81\x02\x00\x00\x00\x00\x00\x00\x00\x00'

    async def handle_query(self, data: bytes, addr: tuple, transport):
        txid, qname, qtype = parse_dns_query(data)
        if not txid:
            return

        cache_key = (qname, qtype)
        cached = self.cache.get(cache_key)
        if cached:
            ans_bytes, exp_time = cached
            if time.time() < exp_time:
                resp = txid + ans_bytes[2:]
                transport.sendto(resp, addr)
                return

        response_bytes = await self.resolve(data, qname, qtype)
        
        if response_bytes:
            final_resp = txid + response_bytes[2:]
            transport.sendto(final_resp, addr)
            
            ttl = extract_ttl(final_resp, qname)
            self.cache.put(cache_key, (final_resp, time.time() + ttl))
        else:
            final_resp = self._make_servfail(txid)
            transport.sendto(final_resp, addr)

    async def _fetch_provider(self, name: str, data: bytes) -> bytes:
        now = time.time()
        if now - self.provider_fails.get(name, 0) < 60:
            return None 

        url = PROVIDERS[name]
        try:
            resp = await self.client.post(
                url,
                headers=self._build_doh_headers(self.mode),
                content=data,
                timeout=3.0
            )
            resp.raise_for_status()
            return resp.content
        except Exception:
            self.provider_fails[name] = now
            return None

    async def resolve(self, raw_query: bytes, qname: str, qtype: int) -> bytes:
        if self.mode == "obfuscated":
            await asyncio.sleep(random.uniform(0, 0.150))

        if self.mode in ("standard", "obfuscated"):
            reachable = [name for name, ok in self.recon.doh_reachable.items() if ok]
            if not reachable:
                reachable = list(PROVIDERS.keys())
            
            tasks = [self._fetch_provider(name, raw_query) for name in reachable]
            for t in asyncio.as_completed(tasks):
                res = await t
                if res:
                    return res

        elif self.mode == "passive":
            for name in PROVIDERS:
                res = await self._fetch_provider(name, raw_query)
                if res:
                    return res

        return None
