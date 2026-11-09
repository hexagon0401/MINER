"""Shared copy and Windows accessibility preferences."""
import ctypes
import sys
WORDS = {
'ko': {'start':'시작', 'stop':'중지', 'settings':'설정', 'idle':'탈옥 준비', 'cli_check':'WARP CLI 확인', 'proxy_connect':'프록시 연결', 'tls_verify':'보안 연결 검증', 'warp_ready':'WARP 연결 확인', 'engine_check':'라우팅 설정 검사', 'engine_start':'네트워크 엔진 시작', 'running':'연결 완료', 'restoring':'WARP Traffic and DNS 복귀 중…', 'restored':'중지 완료 · WARP 복귀 확인', 'error':'연결을 완료하지 못했습니다', 'interrupted':'이전 연결이 정상 종료되지 않았습니다', 'about':'개발자 소개', 'hint':'클라이언트 WARP · 게임 직접 연결', 'close':'닫기', 'language':'언어', 'theme':'화면 테마', 'system':'시스템 설정', 'dark':'어둡게', 'light':'밝게', 'reduce':'동작 줄이기', 'details':'오류 상세', 'retry':'WARP 복귀 재시도', 'help':'개인용 WARP를 먼저 설치하고 등록해 주세요.', 'recovery':'중지를 눌러 엔진 정리와 WARP 복귀를 확인해 주세요.', 'opening':'연결 경로를 점검하고 있습니다.', 'log':'로그 폴더 열기'},
'en': {'start':'Start', 'stop':'Stop', 'settings':'Settings', 'idle':'Ready to dig', 'cli_check':'Checking WARP CLI', 'proxy_connect':'Connecting proxy', 'tls_verify':'Verifying secure connection', 'warp_ready':'WARP verified', 'engine_check':'Checking routing', 'engine_start':'Starting network engine', 'running':'Connected', 'restoring':'Restoring WARP Traffic and DNS…', 'restored':'Stopped · WARP restored', 'error':'Could not complete the connection', 'interrupted':'The previous session did not finish', 'about':'About the developer', 'hint':'Client via WARP · game direct', 'close':'Close', 'language':'Language', 'theme':'Appearance', 'system':'Use system settings', 'dark':'Dark', 'light':'Light', 'reduce':'Reduce motion', 'details':'Error details', 'retry':'Retry WARP restoration', 'help':'Install and register personal Cloudflare WARP first.', 'recovery':'Press Stop to confirm engine cleanup and WARP restoration.', 'opening':'Checking your connection path.', 'log':'Open logs folder'}}


def windows_appearance():
    """Read Windows accessibility preferences; unsupported calls keep safe defaults."""
    result = {'reduced':False, 'contrast':False}
    if sys.platform != 'win32': return result
    try:
        enabled = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
            result['reduced'] = not bool(enabled.value)
        class Contrast(ctypes.Structure):
            _fields_=[('size',ctypes.c_uint),('flags',ctypes.c_uint),('scheme',ctypes.c_wchar_p)]
        hc=Contrast(); hc.size=ctypes.sizeof(hc)
        if ctypes.windll.user32.SystemParametersInfoW(0x42,hc.size,ctypes.byref(hc),0):
            result['contrast']=bool(hc.flags & 1)
    except (AttributeError, OSError): pass
    return result


WORDS['ko'].update({'disconnecting':'긴급 정지 중…', 'disconnected':'긴급 정지 완료',
    'disconnected_hint':'WARP 연결이 해제되었습니다. 일반 인터넷은 유지됩니다.',
    'kill_hint':'MINER 엔진 정리 후 WARP 연결 해제 · 일반 인터넷 유지',
    'layout':'버튼 스타일', 'rounded':'A · 플로팅 버튼', 'flush':'B · 일체형 버튼',
    'pearl':'Pearl White', 'kill':'KILL SWITCH'})
WORDS['en'].update({'disconnecting':'Emergency stop…', 'disconnected':'Emergency stop complete',
    'disconnected_hint':'WARP is disconnected. Your regular internet remains available.',
    'kill_hint':'Stop MINER and disconnect WARP; regular internet stays available',
    'layout':'Button style', 'rounded':'A · Floating controls', 'flush':'B · Integrated controls',
    'pearl':'Pearl White', 'kill':'KILL SWITCH'})
WORDS['ko'].update({'updates':'앱 업데이트','update_check':'업데이트 확인','update_install':'업데이트 설치',
    'update_checking':'최신 정식 버전을 확인하고 있습니다.','update_downloading':'설치 파일 다운로드·SHA-256 검증 중…',
    'update_current':'최신 버전입니다.','update_available':'새 버전:','update_stop':'먼저 연결을 중지한 뒤 업데이트하세요.'})
WORDS['en'].update({'updates':'App updates','update_check':'Check for updates','update_install':'Install update',
    'update_checking':'Checking the latest official release.','update_downloading':'Downloading and verifying installer…',
    'update_current':'You are up to date.','update_available':'New release:','update_stop':'Stop MINER before updating.'})
WORDS['ko']['auto_updates']='새 버전 자동 확인·알림'
WORDS['en']['auto_updates']='Automatically check and notify'
WORDS['ko']['hint']='게임·일반 앱 직접 연결 · 경기 중 연결 유지'
WORDS['en']['hint']='Game and ordinary apps direct · keep MINER connected'
