# MINER STRATA 2.0.0 Preview 1

실제 MacBook 시험을 위한 **프리릴리스**입니다. 정식 ALPHA 1.2.3·기존 릴리스·Homebrew cask는 유지합니다. 통계창 무한 로딩이나 게임 지연을 해결했다고 판정한 버전은 아닙니다.

## 변경 사항

- 엔진·선택 경로·WARP·Riot 검사 상태를 분리합니다. 고정 Riot HTTPS 검사 실패는 실제 통계 API 실패와 구분합니다.
- Mac launchd/root helper 연결 수명을 유지하고 메뉴 막대에서 다시 열기·중지·종료를 제공합니다. 창 닫기와 명시적 종료를 구분합니다.
- Windows SCM 서비스가 세션·Job Object·DNS guardian을 소유합니다. 요청 ID·세대·소유 사용자 검사와 서버 PID 확인을 적용합니다.
- 원문 엔진 로그 대신 비민감 오류 종류를 최대 약 1MiB×2로 보존합니다. DNS·NIC 외부 변경을 감지해 사용자 재연결을 안내합니다.
- 같은 선택 FakeIP 경로와 SOCKS5 원격 DNS를 유지합니다. 추측으로 Riot 도메인을 확장하거나 기본 경로를 전체 TUN으로 변경하지 않습니다.
- 통계창 결과를 사용자 보고로 기록하는 별도 진단 도구와 10회 시험 CSV를 제공합니다.

## 다운로드·검증

Mac AppleSilicon·Intel DMG, Windows x64 Setup.exe, 플랫폼별 진단 ZIP, SHA256SUMS와 네이티브 검사 JSON을 첨부합니다. Mac은 실제 native UI/helper/선택 TUN/DNS 복구를, Windows는 설치·업그레이드·제거와 SCM/Job/IPC fixture를 검사합니다. 네트워크 검사는 로컬 SOCKS fixture이며 실제 WARP·LoL 시험이 아닙니다. Windows CI는 Windows Server 2025입니다.

서명/공증 여부는 각 `.verification.json`이 기준입니다. ad-hoc Mac 앱은 Apple 공증 앱이 아니며 Windows 설치본은 Authenticode 미서명입니다.

## 사용자 MacBook 시험

첨부 `MACBOOK_TEST_KO.md`를 따라 기존 앱에서 중지·복귀 후 교체하고, 연결을 유지한 채 로그인→게임→통계창을 10회 확인해 주세요. `STRATA_TEST_RESULTS.csv`와 진단 ZIP에 실패 시각·통계창 30초 기준 결과를 기록합니다. 자동 업로드는 없습니다.

## 남은 출시 gate

- 실제 MacBook LoL 통계창 연속 10회, 장시간 연결·게임 RTT/FPS/CPU/RAM 비교
- Windows 11·실제 WARP·Riot/Vanguard 호환성
- 로그아웃 시 사용자 WARP 완전 복귀, 다중 사용자·실기 업그레이드/롤백
- 실제 실패 통계 종단점 식별, DoH·DNS 캐시와 분류 누락의 현장 검증

프리뷰 자동 업데이트와 정식 cask 승격은 보류합니다. 새 프리뷰는 GitHub에서 수동 교체합니다. 기존 설치 식별자와 데이터 경로를 유지하므로 ALPHA와 동시에 실행하지 마세요.
