# MINER BETA 1 — Windows

베타 1.1 기반 Windows x64 첫 프리릴리스입니다. 베타 2 학교 기능은 포함하지 않습니다.

- 기존 베타 아이콘·학교·캐릭터와 곡선 땅굴 UI, 실제 상태에 연결한 5단계 표시
- 시작 → WARP Local Proxy 40000 → SOCKS 원격 DNS/TLS 검증 → Windows TUN 분리 라우팅
- 중지·종료 → 엔진 정상 정리 → WARP UDP Traffic and DNS 복귀 확인. 복귀 실패 시 창을 유지하고 재시도 가능
- 관리자 권한(UAC), 중복 실행 방지, 한국어/영어 설정(Ctrl+,), 개발자 About
- 설치·제거 프로그램 및 SHA-256·자동 검증 기록 제공

## 설치

Windows 10 1809 이상 / Windows 11의 x64 PC용입니다. 개인용 Cloudflare WARP를 별도로 설치·등록한 뒤 Setup.exe로 설치하세요. 실행 시 관리자 권한이 필요합니다. 제거 전 MINER에서 중지 후 종료하세요. Windows 설정의 설치된 앱에서 제거할 수 있습니다. 사용자 설정·로그는 `%LOCALAPPDATA%\MINER\Beta1`에 보존합니다. WARP와 기존 버전은 삭제하지 않습니다.

실제 Windows TUN 생성/정상 종료, 패키지 UI, 설치·제거는 CI에서 검증합니다. 실제 WARP 연결·학교망·게임·Vanguard 호환성은 사용자 환경 테스트가 필요합니다. 게임 성능이나 모든 학교에서의 작동은 보장하지 않습니다. 이 배포본은 Authenticode 서명이 없어 Windows SmartScreen 경고가 나타날 수 있습니다. 보안 기능을 전역 해제하지 마세요.
