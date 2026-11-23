# MINER ALPHA v1.2.3

기존 LoL 세션을 유지한 채 연결 경로가 바뀌는 상황을 줄이고, 엔진 준비와 실제 서비스 응답을 구분하는 앱 안정성 업데이트입니다. 통계창 무한 로딩의 완전한 해결 여부는 실제 기기·학교망에서 추가 확인이 필요합니다.

- 게임/LoL 클라이언트가 열려 있으면 WARP 변경 전에 시작을 중단합니다. **LoL 완전 종료 → MINER 연결 완료 → Riot/LoL 실행** 순서로 사용하세요. 앱이나 게임을 강제 종료하지 않습니다.
- 엔진 준비 후 auth.riotgames.com의 SOCKS 원격 DNS·TLS·HTTPS 응답을 확인해야 연결 완료를 표시합니다. HTTP 4xx는 응답으로 구분하며 로그인·통계 API 검증을 의미하지 않습니다.
- WARP Connected 표시와 SOCKS 응답을 구분합니다. 응답이 없으면 경고하며 Connecting 상태에서 connect를 반복하지 않습니다. 경기 중 엔진·전체 터널을 자동 재설정하지 않습니다.
- 복귀 시 Connected와 모드 반영의 지연을 기다리며 이미 복귀한 연결을 불필요하게 끊지 않습니다.
- 큰 DNS 응답이 UDP에서 잘리면 같은 원래 DNS 서버에 TCP로 재시도합니다. 공개 DNS로 임의 전환하지 않습니다. 일반 브라우저·실제 게임 IP의 OS 경로는 유지합니다.

Mac Apple Silicon·Intel DMG 및 Windows x64 Setup.exe를 제공합니다. 설정 → 앱 업데이트 → 업데이트 확인/설치 또는 `brew update && brew upgrade --cask miner`를 사용하세요. 기존 앱을 삭제할 필요는 없습니다. 도우미 업데이트 시 첫 관리자 승인이 필요할 수 있습니다.

필수 네이티브 UI·시작 전 검사·선택 경로·DNS 복구·설치 교체/롤백 검사 통과 후 게시합니다. 실제 WARP·학교망·LoL 통계 API·Vanguard·사용자 macOS에서의 성공은 미검증입니다. Windows 자동 검증은 Server 2025입니다. Mac ad-hoc(공증 없음), Windows Authenticode 미서명일 수 있으며 각 검증 JSON을 확인하세요. 기존 세대·배타적 태그·설치 파일은 보존합니다.
