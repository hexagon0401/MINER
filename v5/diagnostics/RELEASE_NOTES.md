# MINER Local Diagnostics v1.0.0

MINER 1.2.2와 WARP 2026.8.2100.0에서 보고된 끊김·모드 복귀 문제를 로컬에서 구분하기 위한 **별도 진단 도구**입니다. 정식 MINER 앱 업데이트가 아니며 기존 앱·Homebrew 최신 버전을 바꾸지 않습니다.

Mac은 칩에 맞는 ZIP을 풀고 `시작.command`, Windows는 `MINER-Diagnostics.exe`를 실행하세요. Python·관리자 권한이 필요하지 않습니다. 실행 차단 시 파일 출처와 SHA-256을 확인하고 해당 파일의 실행 허용을 사용하세요. Mac ad-hoc 서명(공증 없음), Windows 미서명입니다.

같은 진단 창에서 **1 연결 전 → 2 연결 후 → 3 게임 중 → 4 통계창 → 5 MINER 중지 후** 순서로 기록하세요. 이미 문제가 나면 6으로 오류부터 남길 수 있습니다. 0으로 종료합니다. 바탕화면의 같은 `MINER-Diagnostics-*.zip`이 단계마다 갱신됩니다. 수집 중에는 게임 단계에 맞춰 WARP를 끄거나 모드를 바꾸지 마세요.

읽기 전용이며 WARP·DNS·라우팅·방화벽·Vanguard를 변경하지 않고 자동 업로드하지 않습니다. 원본 로그·SSID·계정·토큰·IP 주소·브라우징 기록은 내보내지 않습니다. 익명 상태 비교, 설정의 포트/MTU, 오류 건수와 코드만 수집합니다. `--active` 옵션을 별도로 지정하면 고정 Cloudflare/Riot/LoL 호스트의 DNS/TLS 요청도 수행합니다. 기본값은 로컬 검사입니다.

각 ZIP의 README_KO.md에 실행·개인정보·해석·한계를 적었습니다. ZIP 안 report.json을 확인한 뒤 개발자에게 직접 전달해 주세요. 네이티브 패키징 검사는 실제 학교망·WARP·LoL·Vanguard 성공을 의미하지 않습니다. Windows 검사는 Server 2025입니다. Mac의 오류를 Windows Vanguard 오류로 자동 분류하지 않습니다.
