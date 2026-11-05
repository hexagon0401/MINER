"""
doh_proxy.py - Pure-Python asyncio UDP DoH proxy (v2)

Fixes vs v1:
- [Critical] provider_fails 초기화 버그: 0.0 → float('-inf')로 변경
  (v1에서 시작 후 60초 동안 모든 DNS 쿼리 SERVFAIL 발생하던 버그)
- TTL 실제 파싱: DNS 응답에서 첫 번째 RR TTL 추출
- SERVFAIL: Question 섹션 포함한 올바른 DNS 응답 구성
- 쿼리 deduplication: 동일 (qname, qtype) 진행 중 쿼리 중복 요청 방지
- provider 우선순위 failover: primary 먼저, 실패 시 나머지 순차 시도
- threading.Event ready: proxy 준비 완료 신호 (gui sleep(1) 대체)
- 종료 시 진행 중 task 취소
- httpx.AsyncClient를 start() 안에서 생성 (이벤트 루프 보장)
"""

import asyncio
import struct
import threading
import time
import random
import httpx
import logging
from collections import OrderedDict

from typing import Tuple, Optional, Union
from recon import ReconResult, PROVIDERS
from settings import Settings

# ──────────────────────────────────────────────
# LRU Cache
# ──────────────────────────────────────────────

class LRUCache:
    def __init__(self, capacity: int):
        self._cache: OrderedDict = OrderedDict()
        self._cap = capacity

    def get(self, key):
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, key, value):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self._cap:
            self._cache.popitem(last=False)

# ──────────────────────────────────────────────
# DNS 파싱 유틸
# ──────────────────────────────────────────────

def parse_dns_query(data: bytes) -> Tuple[Optional[bytes], Optional[str], Optional[int]]:
    if len(data) < 12:
        return None, None, None

    txid    = data[0:2]
    qdcount = struct.unpack(">H", data[4:6])[0]
    if qdcount != 1:
        return txid, None, None

    idx = 12
    parts = []
    while idx < len(data):
        length = data[idx]
        if length == 0:
            idx += 1
            break
        if (length & 0xC0) == 0xC0:
            idx += 2
            break
        idx += 1
        parts.append(data[idx: idx + length].decode("utf-8", "ignore"))
        idx += length

    if idx + 2 > len(data):
        return txid, ".".join(parts), 1

    qtype = struct.unpack(">H", data[idx: idx + 2])[0]
    return txid, ".".join(parts), qtype


def extract_ttl(response: bytes) -> int:
    """DNS 응답 첫 번째 RR의 TTL 파싱. 실패 시 60 반환."""
    try:
        if len(response) < 12:
            return 60
        ancount = struct.unpack(">H", response[6:8])[0]
        if ancount == 0:
            return 60

        # Question 섹션 건너뛰기
        idx = 12
        qdcount = struct.unpack(">H", response[4:6])[0]
        for _ in range(qdcount):
            while idx < len(response):
                length = response[idx]
                if length == 0:
                    idx += 1
                    break
                if (length & 0xC0) == 0xC0:
                    idx += 2
                    break
                idx += 1 + length
            idx += 4  # QTYPE + QCLASS

        # Answer 첫 번째 RR: NAME(2 if compressed) + TYPE(2) + CLASS(2) + TTL(4)
        if (response[idx] & 0xC0) == 0xC0:
            idx += 2  # 압축 포인터
        else:
            while idx < len(response) and response[idx] != 0:
                idx += 1 + response[idx]
            idx += 1

        if idx + 8 > len(response):
            return 60

        ttl = struct.unpack(">I", response[idx + 4: idx + 8])[0]
        return max(ttl, 5)   # 최소 5초 보장
    except Exception:
        return 60


def make_servfail(query: bytes) -> bytes:
    """원본 쿼리의 헤더+Question 섹션을 그대로 포함한 SERVFAIL 응답."""
    if len(query) < 12:
        return query[:2] + b'\x81\x82\x00\x00\x00\x00\x00\x00\x00\x00'

    txid    = query[0:2]
    qdcount = query[4:6]  # 원본 QDCOUNT 유지
    # Flags: QR=1, OPCODE=0, AA=0, TC=0, RD=1, RA=1, RCODE=2(SERVFAIL)
    flags   = b'\x81\x82'
    header  = txid + flags + qdcount + b'\x00\x00\x00\x00\x00\x00'
    # Question 섹션 (query[12:]) 복사
    question = query[12:]
    return header + question


UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

COOLDOWN = 60.0   # provider 실패 후 재시도 대기 시간(초)

# ──────────────────────────────────────────────
# Protocol & Proxy
# ──────────────────────────────────────────────

class DoHProxyProtocol(asyncio.DatagramProtocol):
    def __init__(self, proxy: "DoHProxy"):
        self.proxy = proxy

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple):
        asyncio.create_task(self.proxy.handle_query(data, addr, self.transport))

    def error_received(self, exc: Exception):
        logging.warning(f"DoH UDP error: {exc}")


class DoHProxy:
    def __init__(self, recon: ReconResult, config: Settings):
        self.recon    = recon
        self.config   = config
        self.mode     = recon.recommended_mode
        self.primary  = recon.recommended_provider or config.primary_provider
        self.port     = 5353

        self.cache    = LRUCache(500)

        # [Fix] v1: {k: 0.0} → 시작 후 60초 동안 모든 provider 차단되는 버그
        # float('-inf') 사용 시 now - (-inf) = inf > COOLDOWN → 항상 허용
        self.provider_fails: dict[str, float] = {k: float("-inf") for k in PROVIDERS}

        # 진행 중 쿼리 deduplication: (qname, qtype) → asyncio.Future
        self._pending: dict[tuple, asyncio.Future] = {}

        self._stop_event = asyncio.Event()
        self._tasks:  set[asyncio.Task] = set()
        self.transport = None
        self._client:  Optional[httpx.AsyncClient] = None

        # gui.py에서 sleep(1) 대신 사용하는 준비 완료 신호
        self.ready = threading.Event()

    async def start(self):
        loop = asyncio.get_running_loop()
        # httpx.AsyncClient를 이벤트 루프 안에서 생성 (v1: __init__에서 생성해 루프 불일치 가능)
        self._client = httpx.AsyncClient(
            http2=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: DoHProxyProtocol(self),
            local_addr=("127.0.0.1", self.port),
        )
        logging.info(f"DoH Proxy v2 started on 127.0.0.1:{self.port} (mode: {self.mode})")
        self.ready.set()   # GUI 스레드에 준비 완료 알림
        await self._stop_event.wait()

    async def stop(self):
        self._stop_event.set()

        # 진행 중인 모든 비동기 task 취소
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        if self.transport:
            self.transport.close()
        if self._client:
            await self._client.aclose()
        logging.info("DoH Proxy stopped.")

    # ──────────────────────────────────────────
    # 쿼리 처리
    # ──────────────────────────────────────────

    async def handle_query(self, data: bytes, addr: tuple, transport):
        task = asyncio.current_task()
        self._tasks.add(task)
        try:
            await self._handle(data, addr, transport)
        finally:
            self._tasks.discard(task)

    async def _handle(self, data: bytes, addr: tuple, transport):
        txid, qname, qtype = parse_dns_query(data)
        if not txid:
            return

        # 캐시 확인
        cache_key = (qname, qtype)
        cached = self.cache.get(cache_key)
        if cached:
            ans, exp = cached
            if time.time() < exp:
                transport.sendto(txid + ans[2:], addr)
                return

        # Deduplication: 동일 쿼리가 이미 진행 중이면 그 결과 대기
        if cache_key in self._pending:
            try:
                result = await asyncio.shield(self._pending[cache_key])
                if result:
                    transport.sendto(txid + result[2:], addr)
                else:
                    transport.sendto(make_servfail(data), addr)
            except asyncio.CancelledError:
                transport.sendto(make_servfail(data), addr)
            return

        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[cache_key] = fut
        try:
            response = await self._resolve(data, qname, qtype)
            fut.set_result(response)

            if response:
                transport.sendto(txid + response[2:], addr)
                ttl = extract_ttl(response)
                self.cache.put(cache_key, (response, time.time() + ttl))
            else:
                transport.sendto(make_servfail(data), addr)
        except Exception as e:
            logging.debug(f"Query error for {qname}: {e}")
            if not fut.done():
                fut.set_result(None)
            transport.sendto(make_servfail(data), addr)
        finally:
            self._pending.pop(cache_key, None)

    # ──────────────────────────────────────────
    # DoH 조회
    # ──────────────────────────────────────────

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/dns-message",
            "Accept":       "application/dns-message",
        }
        if self.mode == "obfuscated":
            # DPI 우회: User-Agent/Accept-Language 랜덤화
            # (TLS로 암호화되므로 HTTP 헤더 자체보다 SNI 은닉이 더 효과적이지만
            #  일부 미들박스가 평문 SNI 기반 차단 전에 패턴 매칭하는 경우를 대비)
            h["User-Agent"]      = random.choice(UA_POOL)
            h["Accept-Language"] = random.choice(["ko-KR,ko;q=0.9", "en-US,en;q=0.9"])
            h["Cache-Control"]   = "no-cache"
        return h

    async def _fetch(self, name: str, data: bytes) -> Optional[bytes]:
        now = time.time()
        # cooldown 중이면 건너뜀
        if now - self.provider_fails.get(name, float("-inf")) < COOLDOWN:
            return None
        url = PROVIDERS[name]
        try:
            resp = await self._client.post(
                url, headers=self._headers(), content=data, timeout=4.0
            )
            resp.raise_for_status()
            return resp.content
        except Exception:
            self.provider_fails[name] = now
            return None

    async def _resolve(self, raw: bytes, qname: str, qtype: int) -> Optional[bytes]:
        # Removed artificial delay for 'obfuscated' mode to improve UI responsiveness.
        # Obfuscation relies on multiplexing and User-Agent shuffling.

        if self.mode == "passive":
            # passive: 모든 provider 순차 시도
            for name in PROVIDERS:
                res = await self._fetch(name, raw)
                if res:
                    return res
            return None

        # standard / obfuscated: primary 먼저, 실패 시 나머지로 fallback
        reachable = [n for n, ok in self.recon.doh_reachable.items() if ok] or list(PROVIDERS)

        # primary를 앞으로 정렬
        ordered = sorted(reachable, key=lambda n: (n != self.primary))

        for name in ordered:
            res = await self._fetch(name, raw)
            if res:
                return res

        return None
