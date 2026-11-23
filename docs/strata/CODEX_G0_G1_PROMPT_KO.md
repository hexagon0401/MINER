# Codex 첫 작업 프롬프트 — G0 + G1 (복사해서 사용)

현재 작업 저장소는 `hexagon0401/MINER`이다. 첨부 ZIP은 코드 전체가 아닌 설계/연구자료다. Git main 최신 SHA와 첨부 기준 SHA `7889545ea4c41301b0f75995f541d9c8164e9d16`의 차이를 먼저 확인해라. 새 작업 브랜치 `codex/strata-2.0-g0-g1`에서만 수정하고 main/릴리스를 직접 수정·게시하지 마라.

우선 `START_HERE_KO.md`, `AUDIT_AND_CORRECTIONS_KO.md`, `planning/01_BLUEPRINT_KO.md`, `planning/04_TEST_MATRIX_KO.md`, `planning/05_CODEX_BACKLOG.json`, `reference/MINER_1.2.3_to_2.0.0_HANDOFF_KO.md`를 읽어라. 원본 스쿨넷 문서는 일반 네트워크 원리와 학교별 미확정 항목을 구분한다.

G0:
1) 실제 Git checkout의 완전성과 누락된 community/macos/packaging 모듈 확인. 전체 테스트 수집 오류가 없는지 확인. 현재 1.2.3 로직의 service_verify, WARP restore, DNS lease/guardian, Mac/Win 종료 수명 기록.
2) `warp.py:restore()`는 사용자 이전 상태 복원이 아니라 `mode warp` 고정 복귀이므로 상태/명세를 바로잡는다. 사용자 설정 스냅샷/협력적 소유권 복구는 설계 및 테스트 범위로 올린다.
3) 기존 실제 통계 실패 원인은 미확정. DNS나 가상 IP 규칙, Riot 주소 목록을 증거 없이 변경하지 마라.

G1:
4) Mac의 service-check 실패가 `phase=error`가 되어 실제 ENGINE ON을 전체 고장처럼 보이게 하는 문제를 수정. 엔진 경로/프록시 준비 vs Riot 외부 검증의 상태를 분리하라. 진행 JSON을 사용자 오류 제목에서 제거하라. 실패 자체를 정상/성공으로 숨기지 마라.
5) Windows에서는 G2 장기 supervisor가 존재하기 전 `finally`의 DNS·엔진 정리 코드를 삭제하지 마라. 우선 올바른 오류 분류/상태 판정/테스트를 구현하라. G2에서 명시적 소유자 및 guardian이 증명된 뒤에만 오류 후 지속 연결 정책으로 바꿔라.
6) 요청 ID/상태 TTL/근거/세대번호를 설계하고 필요한 독립 unit 및 failure-injection 테스트를 추가하라. 서비스/게임 실제 성공을 단일 HEAD 검사 성공으로 주장하지 마라.

필수 산출물: 변경파일 목록, diff, 구현 경계, 실행한 테스트 명령과 PASS/FAIL, 남은 위험, G2 진입 여부. 실제 네트워크/WARP/LoL 실기 실행 또는 공개 릴리스는 명시적 승인 없이는 수행하지 마라. 학교·게임 서비스 사용 규정 준수.
