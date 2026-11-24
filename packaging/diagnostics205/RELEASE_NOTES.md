# MINER Diagnostics 2.0.5

별도 읽기 전용 진단 도구입니다. MINER 앱을 업데이트하거나 연결 설정을 변경하지 않습니다. [Preview 7 앱](https://github.com/hexagon0401/MINER/releases/tag/miner-strata-v2.0.0-preview.7)은 그대로 유지합니다.

- OS DNS 관측에서 IPv4-mapped IPv6 가상 주소를 정규화하고 실제 주소가 섞인 응답도 구분합니다. 이전 synthetic=false 하나만으로 경로 실패를 확정하지 않습니다.
- 분리 구성 요소가 켜졌어도 고정 Riot 주소의 OS DNS가 선택 주소를 반환하지 않으면 별도 조사 대상으로 표시합니다.
- macOS Riot Client/Helper 이름을 소켓 집계에 포함합니다. TCP 상태는 실제 업데이트·로그인 성공의 증명이 아닙니다.
- 원본 로그·주소·계정·토큰·패킷을 내보내지 않으며 자동 업로드·DNS 변경·WARP 변경·클라이언트 종료는 없습니다. 외부 고정 DNS/TLS 검사는 별도 선택입니다.

오류 상태에서 실행해 외부 검사 y → 6 오류 → 0 저장·종료로 기록합니다. 원시 호스트 이름 SOCKS 경로와 WARP 경유 HTTPS DNS·실제 IP 경로는 서로 다른 검사입니다. 결과 ZIP은 검토 후 직접 공유하세요.

Mac은 ad-hoc 서명·미공증, Windows는 미서명입니다. 네이티브 검증은 로컬 fixture이며 실제 학교망·Riot 업데이트·게임 성공 검사는 아닙니다.
