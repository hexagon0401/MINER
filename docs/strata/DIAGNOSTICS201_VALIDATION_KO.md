# Diagnostics 2.0.1 검증 및 Preview 2 전달 완료

2026-11-24 KST 기준. 이 변경은 읽기 전용 진단 개선이며 네트워크 엔진 수정이나 게임·통계창 문제 해결 선언이 아닙니다. 사용자 원본 진단 및 개별 기록은 공개 저장소에 포함하지 않았습니다.

- 배포 소스: `458b30a8caab77d7e3699e73095d8828b679fe34`.
- [진단 2.0.1 프리릴리스](https://github.com/hexagon0401/MINER/releases/tag/miner-diagnostics-v2.0.1): macOS Apple Silicon / Intel, Windows x64 ZIP·SHA-256·검증 JSON 게시 완료.
- [네이티브 CI](https://github.com/hexagon0401/MINER/actions/runs/45295636662): 세 플랫폼 빌드·패키징된 진단 실행·읽기 전용 보고서 검사 통과. Mac 두 플랫폼은 긴 실행 경로의 별도 앱 fixture에서 실제 프로세스 경로와 bundle 메타데이터 수집도 검사했습니다.
- 로컬 공통 회귀 검사: 고정 sing-box fixture를 사용해 199개 통과. 실제 WARP·학교망·게임 연결 검사는 아닙니다.
- 게시한 Apple Silicon 진단 ZIP을 다시 다운로드하여 SHA-256 및 ZIP 무결성 확인. SHA-256: `43df409aef30cf4e3ede5096364de18e3223b65fea23cb0d38f004374b721ece`.
- [macOS Preview 2](https://github.com/hexagon0401/MINER/releases/tag/miner-strata-v2.0.0-preview.2)의 누락된 `MACBOOK_TEST_KO.md`, `STRATA_TEST_RESULTS.csv`를 복구했습니다. CI에서 나머지 모든 배포 자산의 ID·digest가 그대로인지 확인했습니다. 기존 DMG를 덮어쓰지 않았습니다.

진단 도구 버전과 앱 버전은 별개입니다. 실행 경로의 bundle 메타데이터 또한 메모리에 로드된 이미지 버전의 증명은 아닙니다. 새 보고서는 이 한계와 현재 분리 구성 요소 관측 여부를 구분합니다. 과거 로그 baseline을 이번 오류의 근거로 간주하지 않습니다.

Mac 앱 수정본 설치 및 실제 게임→통계창 재시험은 [시험 안내](MACBOOK_TEST_KO.md)를 따릅니다. 네트워크·게임 실기는 미검증입니다. main, ALPHA, 정식 자동 업데이트 및 Homebrew cask는 변경하지 않았습니다.
