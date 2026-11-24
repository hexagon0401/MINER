# MINER Diagnostics 2.0.1

이 파일은 **진단 도구**이며 MINER 앱을 설치·업데이트하거나 연결하지 않습니다. Mac 앱 수정본은 [STRATA Preview 2 DMG](https://github.com/hexagon0401/MINER/releases/tag/miner-strata-v2.0.0-preview.2)입니다.

- Mac의 고정 Applications 설치본과 실행 경로의 bundle 버전·build·위치 종류를 구분합니다. AppTranslocation/DMG/사용자 Applications/다른 복사본을 분류하며 실제 경로는 내보내지 않습니다. 메모리에 로드된 이미지 버전을 검증했다고 표시하지 않습니다.
- 긴 프로세스 경로가 잘리지 않도록 수집하고, macOS 커널/제품 버전을 분리합니다.
- 전체 WARP·비활성 분리 엔진·닫힌 로컬 포트를 지속 분리 연결 실패로 혼동하지 않습니다. WarpProxy에서 실제 ConnectionRefused가 난 경우는 관측 오류로 분류합니다.
- 과거 baseline 로그를 새 통계창 오류로 간주하지 않습니다. startup 기록도 최근 파일 tail이며 현재 실행의 증명으로 취급하지 않습니다.
- 관측한 선택 경로 구성 요소, 설치본과 다른 실행 복사본, 버전/build 차이를 요약합니다. SOCKS 성공이나 구성 요소 관측은 게임·통계 성공이 아닙니다.

기본은 읽기 전용·로컬 검사이며 자동 업로드·설정 변경이 없습니다. 능동 TLS/DNS 검사는 별도 동의가 필요합니다. Mac은 ad-hoc/미공증, Windows는 미서명입니다.
