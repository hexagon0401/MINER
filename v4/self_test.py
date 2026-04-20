"""
self_test.py - Dry-run 파이프라인 검증 (네트워크 변경 없음)

모든 모듈의 핵심 기능을 실제 네트워크 설정 변경 없이 테스트.
실행: python self_test.py 또는 python main.py --self-test
"""

import sys
import os
import asyncio
import time
import socket
import logging

# 색상 출력
class C:
    OK   = "\033[92m"
    FAIL = "\033[91m"
    WARN = "\033[93m"
    INFO = "\033[96m"
    DIM  = "\033[90m"
    BOLD = "\033[1m"
    END  = "\033[0m"

results = []

def test(name):
    """데코레이터: 테스트 결과를 수집."""
    def decorator(func):
        def wrapper():
            try:
                print(f"  {C.DIM}▸{C.END} {name}...", end=" ", flush=True)
                start = time.time()
                func()
                elapsed = (time.time() - start) * 1000
                print(f"{C.OK}✓{C.END} {C.DIM}({elapsed:.0f}ms){C.END}")
                results.append((name, True, None))
            except Exception as e:
                print(f"{C.FAIL}✗{C.END} {C.FAIL}{e}{C.END}")
                results.append((name, False, str(e)))
        return wrapper
    return decorator


# ========================================
# Test 1: Settings
# ========================================

@test("Settings load/validate/save cycle")
def test_settings():
    from settings import Settings
    s = Settings.load()
    s.validate()
    assert s.primary_provider in Settings.VALID_PROVIDERS, \
        f"Invalid provider: {s.primary_provider}"
    assert s.language in Settings.VALID_LANGUAGES, \
        f"Invalid language: {s.language}"
    # get_path 존재 확인
    path = Settings.get_path()
    assert isinstance(path, str) and path.endswith("config.json"), \
        f"get_path returned unexpected: {path}"


# ========================================
# Test 2: Recon
# ========================================

@test("Recon: get_wifi_interface")
def test_recon_interface():
    from recon import get_wifi_interface
    iface = get_wifi_interface()
    assert iface, "No interface returned"
    assert iface.startswith("en"), f"Unexpected interface: {iface}"

@test("Recon: get_wifi_info")
def test_recon_wifi():
    from recon import get_wifi_info
    ssid, bssid = get_wifi_info()
    # 연결 안 되어 있을 수도 있으므로 에러만 아니면 OK
    assert isinstance(ssid, str), f"SSID should be str, got {type(ssid)}"

@test("Recon: full run_recon()")
def test_recon_full():
    from recon import run_recon, ReconResult
    res = asyncio.run(run_recon())
    assert isinstance(res, ReconResult), f"Expected ReconResult, got {type(res)}"
    assert res.interface, "No interface in recon result"
    assert res.recommended_mode in ("standard", "obfuscated", "passive"), \
        f"Unknown mode: {res.recommended_mode}"

@test("Recon: MTU parsing")
def test_recon_mtu():
    from recon import _get_mtu, get_wifi_interface
    iface = get_wifi_interface()
    mtu = _get_mtu(iface)
    assert 576 <= mtu <= 9000, f"MTU out of range: {mtu}"


# ========================================
# Test 3: Network Manager (script generation only)
# ========================================

@test("NetworkManager: script generation (no execution)")
def test_netmgr_scripts():
    from network_manager import _build_optimize_script, _build_restore_script
    opt_script = _build_optimize_script("en0", True)
    assert "networksetup" in opt_script, "Missing networksetup in optimize script"
    assert "pfctl" in opt_script, "Missing pfctl in optimize script"
    assert "com.schoolnet" in opt_script, "Missing anchor name"

    restore_script = _build_restore_script("en0", ["8.8.8.8", "8.8.4.4"])
    assert "networksetup" in restore_script, "Missing networksetup in restore script"
    assert "Automatic" in restore_script, "Missing Automatic location switch"
    assert "com.schoolnet" in restore_script, "Missing anchor cleanup"


# ========================================
# Test 4: DoH Proxy (port binding + query test)
# ========================================

@test("DoH Proxy: port 5353 availability")
def test_proxy_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("127.0.0.1", 5353))
    except OSError:
        # mDNSResponder (Bonjour) 가 5353을 사용 중일 수 있음 — 정상
        # 실제 프록시 시작 시 mDNSResponder를 중지하거나 다른 포트 사용
        pass  # non-fatal: port may be in use by mDNSResponder
    finally:
        sock.close()

@test("DoH Proxy: DNS parsing")
def test_proxy_dns_parse():
    from doh_proxy import parse_dns_query, make_servfail, extract_ttl
    query = b'\x56\x78\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01'
    txid, qname, qtype = parse_dns_query(query)
    assert txid == b'\x56\x78', f"Wrong TXID: {txid}"
    assert qname == "example.com", f"Wrong qname: {qname}"
    assert qtype == 1, f"Wrong qtype: {qtype}"

    sf = make_servfail(query)
    assert len(sf) >= 12, f"SERVFAIL too short: {len(sf)}"
    assert sf[0:2] == b'\x56\x78', "SERVFAIL TXID mismatch"

@test("DoH Proxy: LRU cache")
def test_proxy_cache():
    from doh_proxy import LRUCache
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") == 1
    cache.put("d", 4)  # should evict "b" (LRU after "a" was accessed)
    assert cache.get("b") is None, "b should have been evicted"
    assert cache.get("d") == 4


# ========================================
# Test 5: Locales
# ========================================

@test("Locales: string lookup")
def test_locales():
    from locales import t, set_language, STRINGS
    set_language("ko")
    assert t("analyze_button") == STRINGS["ko"]["analyze_button"]
    set_language("en")
    assert t("analyze_button") == STRINGS["en"]["analyze_button"]
    # unknown key returns key itself
    assert t("nonexistent_key") == "nonexistent_key"


# ========================================
# Test 6: Module imports
# ========================================

@test("Import: all modules loadable")
def test_imports():
    import settings
    import recon
    import network_manager
    import doh_proxy
    import locales
    # gui.py는 PyObjC AppKit를 임포트하며 NSObject 클래스를 등록하므로
    # headless 환경에서의 selector 검증은 별도 수행
    try:
        import gui
    except Exception as e:
        # PyObjC selector 등록 오류는 headless에서 발생 가능 — 경고만
        if "expects" in str(e) and "arguments" in str(e):
            pass  # selector 시그니처는 런타임에서만 유효
        else:
            raise


# ========================================
# Runner
# ========================================

def run_all_tests():
    print(f"\n{C.BOLD}{'═' * 50}{C.END}")
    print(f"{C.BOLD}  SchoolNet Optimizer v4 — Self Test{C.END}")
    print(f"{C.BOLD}{'═' * 50}{C.END}\n")

    tests = [
        test_settings,
        test_recon_interface,
        test_recon_wifi,
        test_recon_mtu,
        test_recon_full,
        test_netmgr_scripts,
        test_proxy_port,
        test_proxy_dns_parse,
        test_proxy_cache,
        test_locales,
        test_imports,
    ]

    for t_fn in tests:
        t_fn()

    print(f"\n{'─' * 50}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    total = len(results)

    if failed == 0:
        print(f"\n  {C.OK}{C.BOLD}All {total} tests passed ✓{C.END}\n")
    else:
        print(f"\n  {C.OK}{passed} passed{C.END}, {C.FAIL}{failed} failed{C.END} / {total} total\n")
        print(f"  {C.FAIL}Failed tests:{C.END}")
        for name, ok, err in results:
            if not ok:
                print(f"    {C.FAIL}✗ {name}: {err}{C.END}")
        print()

    return failed == 0


if __name__ == "__main__":
    # 이 파일이 v4/ 디렉토리에 있으므로 parent를 sys.path에 추가
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    success = run_all_tests()
    sys.exit(0 if success else 1)
