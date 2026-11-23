# MINER STRATA 2.0.0 — 검수 결과 및 기존 설계 수정 지시

기준: 2026-11-23 KST / 1.2.3 source main `7889545ea4c41301b0f75995f541d9c8164e9d16`
검증: 이전 `MINER_2.0.0_CODEX_WORKPACKAGE.zip` ZIP 무결성 정상, 이전 원본 체크섬 기록 존재, JSON 로딩·작업 의존성 참조 정상. `python -m pytest -q tests/test_config.py tests/test_updates.py tests/test_session_safety.py tests/test_diagnostic_log_events.py`에서는 29 passed, 18 subtests passed (Linux Python 3.13, 네트워크 실기 아님).

## A. 이번에 재현된 실제 결함/문서 충돌

### A01 — 이전 ZIP의 source/는 부분 스냅샷이다 [확인]
- 88개 소스 파일 포함. 실제 GitHub main 트리는 1,478개 엔트리 (파일·디렉터리 모두 포함)다. 양쪽 수치를 파일 수로 직접 비교하지 말 것.
- 이전 ZIP 내부에서 전체 `python -m pytest -q tests`를 실행하면 **수집 단계에 5개 에러** 발생한다. 누락: `v5/community/catalog.py`, `v5/macos/dmg_layout.py`, `v5/macos/retry_release.py`, `packaging/homebrew/generate.py`. 실제 GitHub main에는 4개가 존재함을 GitHub 트리로 확인했다.
- 처방: ZIP의 source/로 새 standalone 프로젝트를 만들지 말 것. GitHub repo를 checkout하고 그 위에서 개발·테스트한다. 원본 패키지와 배포 바이너리 해시는 코드 기준선 증거로만 사용한다.

### A02 — WARP '원래 설정 복구' 설명이 현재 코드와 다름 [확인]
- `v5/schoolnet/warp.py`의 `restore()`는 `disconnect → mode warp → connect`다. 이전 연결/모드/Disconnected 상태를 무조건 원상복원하는 함수가 아니다.
- `planning/01_BLUEPRINT_KO.md` 일부 'WARP 원래 모드 복귀' 표현은 **2.0 목표**로만 취급한다. 현재 1.2.3이 제공한다고 해석하면 안 된다.
- 처방: G0에 시작 전 WARP 설정/접속 소유권/사용자 외부 변경 관측 기록. G2 서비스 수명 설계에서 '원래 상태 보존·충돌 시 확인' 정책을 추가하거나, 제품 정책상 기본 복귀를 `Warp`로 고정할 것인지 명시적으로 결정한다. 원래 설정을 저장할 경우 토큰·키·인증정보를 보관하지 않는다.

### A03 — G1 Windows 장애 처리 완료 조건이 위험할 수 있다 [확인된 설계 충돌]
- 현재 `v5/windows/controller.py`는 `warp.verify_client_service()` 예외 발생 시 `finally`에서 DNS 복구 및 엔진 정리를 수행한다.
- 이전 테스트 T003 '단일 서비스 검사 실패면 엔진을 무조건 정리하지 않는다'를 G1 단계에서 즉시 구현하면, 지속 supervisor 없는 Windows에서 고아 엔진/변조된 DNS를 남길 위험이 있다.
- 수정: **G1에는 '원인 분류 + 오류 표시 개선 + 기존 정리 보전'을 통과 기준**으로 둔다. G2의 소유 주체가 구현·검증된 뒤 Windows 지속형 DEGRADED 모드로 전환한다. Mac의 기동 중 엔진 생존과 Windows의 현재 정리는 별도 상태/증거로 표시한다.

## B. 기존 계획에서 보강해야 하는 P0·P1

### B01 — GUI 종료 vs 앱 종료 vs 로그아웃 vs 서비스 충돌을 명세에서 구분 [P0]
- 닫기(윈도우만 숨김)·메뉴 Quit·UI kill·사용자 로그아웃·재부팅은 다른 이벤트다. root/서비스가 실행 중인 상태에서 로그아웃한 사용자의 DNS가 남지 않도록 owner/guardian 계약 필요.
- macOS launchd LaunchAgent/LaunchDaemon과 사용자 세션·SMAppService 등 구현 선택은 기기/권한/서명 조건을 먼저 검증. Windows Job Object 소유권은 서비스 쪽으로 이전하며, GUI 프로세스에 남겨두지 않는다.

### B02 — 다중 WARP 사용자/외부 조작 및 세션 재진입 [P0]
- MINER가 WARP에 독점 소유권을 갖는다고 가정하면 안 된다. 앱 밖에서 WARP 모드/연결이 변경되거나 다른 VPN이 들어올 때 무조건 덮어쓰기/재시작하지 않는다.
- 시작 전 Riot/League 프로세스 검사 및 기존 TCP/DNS 캐시는 1.2.3 미해결 경계. UI뿐 아니라 Supervisor의 `connect` 경로에도 동일 사전 검증을 적용.

### B03 — 원인 추적에 필요한 최신 현장 증거 부족 [P0]
- 보고된 통계 무한 로딩의 진단은 1.2.2 / diagnostics v1.0.0, `active_probes=false` 자료. 1.2.3 `service_verify`의 실제 예외 텍스트는 미확인. 'WARP Connected/SOCKS OK'로 Riot 통계 API 성공을 추정하지 않는다.
- 후속으로 진단 v1.0.1 사용자 동의 기반 비교 자료/비민감 오류 종류를 수집한다. Riot 계정 토큰·쿠키·패킷 본문·원본 log 업로드는 기본 금지. 실패 원인 불명이라면 라우팅 CIDR/도메인을 임의 확장하지 않는다.

### B04 — IPC/상태 스키마의 완료 조건 부족 [P1]
- 기존 `planning/03_STATUS_SCHEMA_DRAFT.json`의 `status`는 임의 문자열을 허용한다. 컴포넌트별 enum, 상태 전환 유효성, timestamp/TTL 만료, restart generation, 중복 request_id, 에러 코드, 로컬 권한 경계를 G1/G2에서 고정하라.
- `READY=내부 엔진 준비`와 `Riot 기능 성공`을 별도 유지. 연결 성공 화면이 게임 동작·통계 성공을 보증한다고 표현하지 않는다.

### B05 — 배포명 변경 전 업데이터 bridge 필요 [P0]
- 기존 v1.2.3 업데이터는 `ALPHA`·`miner-alpha-v{version}`·`MINER-ALPHA-v{version}` 계약이 고정되어 있다.
- **브랜드** MINER STRATA 2.0.0으로 정하되, 실제 release 계약 변경 전에 호환판(예: ALPHA 1.2.x bridge) 또는 ALPHA 메타데이터 유지 중 하나를 검증해야 한다. 1.2.4는 아직 존재하는 릴리스라고 주장하지 않는다.
- bundle ID, helper ID, DNS journal, 설치 GUID, cask 이름 등은 최초 전환에서 동시 변경하지 않는다. 수동 rollback/동일 사용자 install/uninstall 시나리오 포함.

### B06 — 장기 서비스의 로그·성능·업데이트 범위 [P1]
- 기존 `v5/windows/controller.py`는 15초 상태 루프에서 `last_warning=None`을 다시 대입하므로 반복 경고 로그 억제가 의도대로 유지되지 않을 수 있다(이관서 6장 코드 검토 기록).
- 장기 서비스에서는 엔진 로그의 증가율·rotation·보존 기한·메모리 idle usage를 테스트한다. diagnostics 화면의 로컬 원본 로그 보기와 외부 내보내기는 서로 다르므로 외부 내보내기는 반드시 비민감화한다.
- UI가 꺼진 동안에도 updater가 임의 설치/강제 재시작을 시작하지 않도록 소유권과 사용자 승인 절차를 분리한다.

### B07 — 보안 및 사용 권한 [P1]
- 학교망 정책/장비와 실제 UDP 허용 규칙은 미확정. 연구 문서의 일반 계층 모델을 특정 학교의 실측 사실로 만들지 않는다. 학교 인터넷 이용 규정 준수 아래에서만 실험.
- Riot 공식 고객지원의 VPN/가속기 사용 관련 계정 잠금/제한 가능성을 배포 경고에 명시. 자동 계정 제재라고 단정하지 않는다.

## C. 보완 테스트 (원래 T001~T020 외 추가)

| ID | 단계 | 시험 | 기대 |
|---|---|---|---|
| T003-revised | G1 | Windows Riot 외부 검사 실패 | 명확한 오류 코드+현재 안전 cleanup 보전, 고아 엔진·DNS 방치 없음 |
| T021 | G0/G2 | 사전 WARP Disconnected / DNS-only / Warp / WarpProxy | 각 시작 상태와 복구 정책의 정확한 기록, 모드 소유권 혼동 금지 |
| T022 | G2 | WARP UI/외부 도구가 MINER 동작 중 모드 변경 | 덮어쓰기 루프 금지, 충돌 상태 표시 |
| T023 | G2 | 창 Close / Quit / UI kill / logout / reboot 구분 | 지속 서비스 정책, 명시적 Stop, 자동 복구 검증 |
| T024 | G2 | daemon 강제 종료/guardian 고장/로그아웃 | DNS lease 안전성, 복구 필요 표시, 유실된 소유자 복원 |
| T025 | G2 | 다중 사용자 및 IPC 위조/구 버전 연결 | 권한 없는 제어 거부, 요청 ID 멱등, 세대 일치 확인 |
| T026 | G3 | 실제 통계 실패 vs 테스트용 HEAD 실패 | 서로 다른 독립 상태, 미검증은 미검증으로 표현 |
| T027 | G5 | ALPHA 1.2.3 → bridge → STRATA 2.0 / 롤백 | 업데이터, cask, 설치 식별자, 저장된 journal 보존 |
| T028 | G6 | 8GB Apple Silicon 등 저메모리 장치 | idle/ingame CPU·RAM·로그 증가율·경로 지연 측정, 절대 성능치 조작 금지 |
| T029 | G5 | Windows 장기 상태 감시 반복 경고 | 동일 경고 로그 폭증 억제, 마지막 경고 상태 유지 |
| T030 | G5 | 24h 지속 supervisor 로그/메모리 | rotation·최대 보존량·idle 자원 증가율 점검 |

## D. 작업 경계/현재 결과

- 1.2.3 소스만으로 통계창 무한 로딩의 정확한 원인을 확정할 수 없다.
- 서버/학교 실제 정책, Riot 실제 현재 도메인/IP/UDP 목적지는 실험 증거가 없는 한 가정하지 않는다.
- 설계 검수는 수행했지만 STRATA 소스 구현, 배포, Mac/Windows 실기 검증은 수행하지 않았다.
