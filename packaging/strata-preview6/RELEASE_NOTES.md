# MINER STRATA 2.0.0 Preview 6 — WARP 목적지 DNS 분리

Riot 내부 가상 주소와 WARP의 목적지 주소 해석이 간섭하지 않도록 연결 방식을 보완했습니다. MINER는 지정 Riot 호스트의 실제 주소를 WARP 경유 HTTPS DNS로 조회한 뒤 WARP SOCKS에 실제 IP를 전달합니다. 내부 가상 IP는 클라이언트→MINER 구간에서만 사용합니다.

- HTTPS DNS는 숫자 주소 `1.1.1.1:443`으로 WARP 프록시를 거쳐 연결하고 `cloudflare-dns.com`의 TLS 인증서를 검증합니다. Riot 주소 조회에 OS/학교 DNS를 사용하거나 직접 연결로 자동 전환하지 않습니다.
- Riot TCP의 원래 TLS 호스트 이름·인증서 검증은 그대로 유지합니다. 게임 실제 IP와 일반 사이트의 기본 경로는 바꾸지 않습니다.
- Riot 서비스 확인도 동일한 HTTPS DNS→실제 IP 방식으로 변경했습니다. 도구 → WARP 연결 확인의 재검사가 성공하면 이전 경고를 해제합니다. 검사는 기본 HTTPS 도달 여부이며 실제 로그인·친구 상태·매칭 알림·통계 성공의 증명은 아닙니다.
- SOCKS 거부 번호·TLS 인증서 오류를 진단에서 구분합니다. 진단 2.0.3은 기존 원시 호스트 이름 SOCKS 검사와 수정 경로를 별도로 기록합니다. 예전 `curl --socks5-hostname ... auth.riotgames.com`은 수정한 MINER 경로를 거치지 않으므로 결과를 구분해야 합니다.
- 게임·클라이언트를 열어 둔 수동 시작 허용과 중지·DNS 복구 절차를 유지합니다.

## 검증 범위

실제 sing-box 1.12.0과 무해한 프록시 fixture로 기존 호스트 이름 경로의 거부, 수정한 검증된 TLS DNS·실제 IP 연결·지속 TCP 송수신을 재현합니다. DNS 인증서 이름을 틀리게 하면 실패하고 원래 DNS나 호스트 이름 경로로 fallback하지 않는 것도 검사합니다. 두 Mac 아키텍처의 실제 선택 TUN·DNS·복구 시험에서도 이 프록시 fixture를 사용합니다. 실제 Cloudflare WARP의 내부 구현을 측정하거나 실제 LoL 기능 성공을 입증한 시험은 아닙니다.

이번 배포는 Mac Apple Silicon/Intel DMG입니다. Windows 공통 코드도 회귀 검사하지만 새 Windows EXE는 포함하지 않습니다. main·ALPHA·Homebrew·기존 프리릴리스는 보존합니다. 사용자 원본 진단·주소·계정·쿠키는 배포 자료에 포함하지 않습니다.

## 설치

MINER만 정상 중지·종료하고 새 앱을 시스템 `/Applications`에 교체합니다. About에서 Preview 6를 확인한 뒤 시작하세요. 연결 후 도구 → WARP 연결 확인으로 재검사하고 Riot 클라이언트에서 다시 시도를 눌러 확인하세요. 매번 클라이언트를 종료하라는 차단은 없습니다. 실제 게임·친구 목록·수락창은 사용자 기기 검증이 필요합니다. Developer ID가 설정되지 않은 경우 ad-hoc 서명·미공증 배포입니다.
