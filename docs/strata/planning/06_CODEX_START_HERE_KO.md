# Codex 실무 실행 가이드 (기획만 완료 / 코드 수정 전 지시)

## 기본 컨텍스트

1. `planning/01_BLUEPRINT_KO.md`의 사실·미확정·금지 가정을 먼저 읽는다.
2. `reference/MINER_1.2.3_to_2.0.0_HANDOFF_KO.md` 1~17장과 `reference/` 원문, 실제 GitHub 작업 저장소의 `v5/` 코드를 확인한다.
3. 이 ZIP에는 전체 소스가 없다. 실제 GitHub `hexagon0401/MINER` 저장소를 작업 대상으로 열고 SHA를 검사한다. 새 브랜치를 만들어 개발한다. 기존 패키지의 부분 source snapshot으로 repository 파일을 덮어쓰지 않는다.
4. 각 단계에서 README/DESIGN/CI 증거와 실제 검증의 범위를 분리한다. 현재 보고된 통계 무한 로딩과 4/5 오류는 미해결로 시작한다.

## 공통 운영 규칙

- 네트워크 소유권·DNS 복구·권한 경계를 바꾸는 변경은 단일 단계로 나눠 테스트한다.
- 맥/윈도우 각각 실제 소유자(daemon/service)와 GUI를 구분한다. root 명령 실행 및 arbitrary path IPC 금지.
- 가상의 학교 차단 정책이나 Riot 목적지 IP를 만들어 넣지 않는다.
- Riot TCP를 WARP 실패 시 직접으로 돌리거나 전체 호스트 WARP 터널을 자동 전환하지 않는다.
- 실제 게임/WARP 라이브 시험 없이 완료라고 쓰지 않는다. CI fixture 성공과 구분한다.
- 원본 DNS lease/journal 및 Homebrew/installer 식별자와 사용자 파일을 자동 삭제하지 않는다.
- 사용자 기기 네트워크 설정을 자동 변경하거나 원격 배포/릴리스하지 않는다. 실제 동작은 사용자가 승인한 환경에서만 수행한다.

## Prompt 1 — G0/G1 / health 상태부터 독립 구현

먼저 `CODEX_G0_G1_PROMPT_KO.md` 및 `AUDIT_AND_CORRECTIONS_KO.md`의 보완 사항을 우선하고 `planning/05_CODEX_BACKLOG.json`의 G0/G1 수행. Windows에서는 G2 이전 finally의 안전 복구를 삭제하지 않는다. `v5/macos/App.swift`에서 `service_verify` 예외가 phase=error 및 engine=running을 동시에 나타내는 지점을 확인하고, `windows/controller.py`와 비교한다. 컴포넌트별 상태모델을 최소 구현해 엔진/선택 DNS 준비와 Riot 외부 TLS 검사 실패를 분리한다. 단일 HEAD 결과를 통계 API 성공으로 표시하지 않는다. 진행 JSON이 사용자 오류 제목에 노출되지 않도록 분리한다. 소스/테스트 변경 diff와 실제 통과한 테스트 명령·범위를 제시하라. WARP 실기 성공을 주장하지 말라.`

## Prompt 2 — G2 / 수명 서비스

`G1 완료 후 G2-01~05 수행. Mac 기존 helper와 launchd 서비스를 보존하면서 GUI가 종료되어도 명시적 Stop 전까지 엔진·DNS 복구 소유권이 유지되도록 설계/구현한다. Windows는 관리된 서비스가 Job Object와 guardian을 소유하도록 하되 사용자/관리자 경계와 IPC ACL을 시험한다. 로그아웃 기본 Stop, 재부팅 자동연결 OFF, 외부 DNS 변경 무단 덮어쓰기 금지. UI crash, Stop 반복, 중복 Connect, network change 장애 주입 테스트를 작성하라.`

## Prompt 3 — G3/G4 / 관측·경로 정확성

`G2 안정화 뒤 비민감 통계창 진단 이벤트를 구현한다. H1~H5를 확인/기각/미확인으로 분리한다. 확인된 문제에만 route change PoC를 적용한다. 로컬 SOCKS fixture, IPv4/IPv6, DoH, DNS cache, 일반 앱 경로 회귀를 테스트한다. 단순 Riot.exe direct 또는 broad 0/0 TUN으로 회귀하지 말라.`

## Prompt 4 — G5/G6 / 정식화

`session migration, sleep/wake, updater 계약, cask, CI, installer 및 서명·공증을 감사한다. 실제 사용자 승인 환경에서의 Mac Riot 게임·통계 10회 시험과 Windows 11/Vanguard 실기 검증은 별도의 수동 gate로 남긴다. 이 gate가 끝나기 전 새 버전의 '문제 해결됨' 메시지나 정식 릴리스를 만들지 말라.`
