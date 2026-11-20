# MINER ALPHA v1.2.2

macOS 연결 준비 중 명령이 끝나지 않아 중지·종료가 막히는 코드 경로를 수정했습니다. 응답 시간 제한, 연결 취소, 늦게 승인된 시작의 취소, 중지·상태 확인 명령의 직렬화를 추가했습니다.

- DNS 복구 오류 시 도우미 반복 재시작 방지, 사라진 네트워크 서비스 기록의 안전한 보관, PID와 준비 상태 구분.
- DNS 적용 도중 SIGTERM의 복구 재진입 방지. 정상 DNS 복구 후 엔진 종료.
- 지정 Riot 서비스 TCP를 게임 프로세스의 직접 연결 예외보다 먼저 처리. 실제 게임 IP/일반 브라우저의 OS 경로 유지.
- Mac·Windows 자동 업데이트/이전 파일 정리 유지. 기존 앱 삭제 불필요. Mac 도우미 갱신 시 최초 관리자 승인 가능.

업데이트 후 처음 한 번 Riot/LoL을 완전히 종료하고 MINER 연결 후 다시 실행하세요. 로그인부터 인게임·통계창까지 MINER와 WARP Local Proxy를 유지하세요. 설정 → 앱 업데이트 → 업데이트 확인/설치, Homebrew는 `brew update && brew upgrade --cask miner`를 사용합니다.

Apple Silicon·Intel DMG와 Windows x64 Setup.exe, SHA-256, 플랫폼 검증 JSON을 제공합니다. 배포는 네이티브 명령/취소·UI·선택 경로·DNS 복구·설치 교체 검사 통과 후 진행됩니다. Mac 게임 이름 TCP 시험은 로컬 SOCKS 기반이며 실제 WARP/LoL 통계창 성공을 입증하지 않습니다. Windows 자동 검증은 Server 2025이며 실제 Windows 11·학교망·LoL·Vanguard·사용자 macOS 27.1.1은 미검증입니다. Mac ad-hoc 및 Windows 미서명 여부는 각 검증 JSON을 확인하세요. ALPHA는 제품 세대 코드명이며 이번 배포는 정식 업데이트입니다.
