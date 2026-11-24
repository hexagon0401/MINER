# MINER STRATA 2.0.0 Preview 3 — 클라이언트를 열어 둔 채 시작

LoL 로비·클라이언트가 실행 중이라는 이유만으로 MINER 시작을 거부하던 검사를 제거했습니다. 클라이언트를 종료하거나 재실행하라는 확인창 없이 기존 시작 절차를 진행합니다. 클라이언트를 강제 종료하지 않습니다.

- 실제 경기 프로세스가 실행 중이면 경로를 바꾸기 전에 기존처럼 차단합니다.
- Mac의 긴 프로세스 경로가 잘리지 않도록 읽어 게임과 클라이언트를 구분합니다.
- 선택 DNS·TUN·WARP Local Proxy 원리와 Stop 복구는 유지합니다. 이미 열린 TCP 소켓과 앱 내부 DNS 캐시는 강제로 이동·삭제하지 않으므로, 기존 요청이 즉시 복구된다고 보장하지 않습니다.
- 앱에 포함된 사용 안내를 새 시작 동작에 맞췄습니다. 진단 도구 2.0.1을 함께 제공합니다. 진단 도구 버전은 앱 버전과 별개입니다.

이번 배포는 macOS Apple Silicon/Intel DMG입니다. 공통 시작 검사 변경은 Windows 소스에도 적용되며 Windows CI 회귀 검사로 확인합니다. Windows 설치본은 기존 [Preview 1](https://github.com/hexagon0401/MINER/releases/tag/miner-strata-v2.0.0-preview.1)을 유지합니다. main·ALPHA·Homebrew·기존 프리릴리스를 덮어쓰지 않습니다.

## 검증과 설치

두 Mac 아키텍처에서 패키징한 CLI를 무해한 LeagueClient/LeagueofLegends 이름의 대기 프로세스와 함께 실행해, 열린 클라이언트 허용·실제 게임 이름 차단·프로세스 미종료를 검사합니다. 실제 LoL 프로그램이 아닌 fixture 검사입니다. 기존 일반 Finder 실행·재열기·종료, UI, helper, 선택 네트워크, 업데이트·DMG 검사도 배포 전에 통과해야 합니다. 검증 JSON의 `session_preflight`에 결과를 기록합니다.

실제 LoL 로비·게임·통계창 및 학교망 검증은 미완료입니다. 시작 차단 제거와 통계창 문제 해결은 구분합니다.

MINER를 정상 중지·종료한 뒤 DMG의 앱을 시스템 `/Applications`에 교체하고 `open -n "/Applications/MINER.app"`으로 여세요. 앱 교체 때 MINER 자체는 종료해야 하지만, 연결할 때마다 Riot/LoL 클라이언트를 닫을 필요는 없습니다. 실제 경기 중에는 설치·연결 전환을 하지 마세요. Developer ID가 설정되지 않았다면 ad-hoc 서명·미공증 배포입니다.
