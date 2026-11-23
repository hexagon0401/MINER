# STRATA G0/G1 작업 기록

이 문서는 G0/G1 완료 당시의 보관 기록입니다. 이후 G2~G6 진행과 프리뷰 배포 경계는 [현재 구현 상태](IMPLEMENTATION_STATUS_KO.md)를 확인하세요.

## 범위와 기준선

- 기준 전체 체크아웃: `7889545ea4c41301b0f75995f541d9c8164e9d16`, tracked blob 1,228개. 첨부 partial snapshot으로 소스를 덮어쓰지 않았다.
- 원격 main 확인도 동일 SHA. 작업 브랜치: `codex/strata-2.0-g0-g1`.
- 이관 체크섬 검증: 135개, 오류 0개.
- 기존 README, ALPHA 이미지, archive, cask, 업데이터 명명 계약·버전·앱/도우미 ID·Windows 설치 GUID는 보존한다. 정식 배포를 하지 않는다.
- 실제 전체 저장소에 community/catalog.py, macos/dmg_layout.py, macos/retry_release.py, packaging/homebrew/generate.py가 존재한다. 전체 unittest discover로 수집 오류를 검증한다.

## G0: 현재 구현과 조사 경계

1. Mac service_verify 실패 시 엔진은 살아 있으면서 phase=error가 될 수 있다. Windows는 finally에서 DNS·엔진을 정리한다.
2. `warp.restore()`는 **고정 Warp+Connected 복귀**이며 시작 전 사용자 모드·Disconnected 상태를 복원하는 함수가 아니다.
3. G0는 비민감 previous_configuration(mode, connected, restore_policy, exclusive_ownership=false)을 WARP 준비 결과에 추가한다. 토큰·계정·설정 원문은 저장하지 않는다. 실제 소유권 보존·외부 변경 충돌 복구는 G2다.
4. 시작 모드 Warp/WarpProxy/DNS-only/Disconnected의 정책을 unit fixture로 확인한다. 이 snapshot은 WARP 독점 소유권을 의미하지 않는다.
5. 통계 실패는 1.2.2/diagnostics 1.0.0 active_probes=false 자료다. 1.2.3 실제 service_verify 예외 원문은 미확인이다. 학교 정책·목적지 범위를 추측해 변경하지 않는다.

현장 단계 계약: 사용자가 before/connected/in_game/post_game/after_stop/error를 선택하고 시간·버전·능동 검사 허용 여부를 기록한다. 통계창 30초 기준은 시험상 실패 기준이지 Riot SLA가 아니다. 원본 로그·계정·주소를 기본 내보내지 않는다. 실제 재현은 미실행이며 다음 승인된 현장 검증에서 수행한다.

## G1: 구현

- 순수 `health_model.py`: 컴포넌트별 enum, 요청 ID/세대, 관측 시각/TTL, 근거/제한된 원인 코드. 오래된 세대·다른 요청·중복/역전/만료 관측을 거부한다. 실제 command IPC나 supervisor는 아니다.
- `protocol_output.py`: 서비스 검사 오류에 비민감 reason_code를 부여한다. machine component_status는 stdout, 사용자 오류는 stderr로 구분하며 statistics_verified=false를 유지한다.
- Mac: 엔진이 준비된 뒤 단일 외부 검사 실패는 engine=true를 보존하고 경고를 표시한다. 엔진 준비 5단계와 Riot 검증 PASS/FAIL/TIMEOUT/UNKNOWN을 구분한다. 프로브 실패가 실제 Riot 기능 성공으로 바뀌지 않는다. 취소는 기존 정리 흐름에 넘긴다.
- Mac: 진행/컴포넌트 JSON을 사람이 보는 실패 문장에서 제외한다. 관련 request/generation과 TTL을 확인하며 오래된 응답은 UI를 덮어쓰지 못한다.
- Windows: engine READY/route ACTIVE → Riot TIMEOUT/FAIL → 기존 finally 정리 → 실제 STOPPED/RESTORED(또는 cleanup 실패)를 관측 이벤트로 표시한다. 별도 supervisor 없는 지속형 DEGRADED를 만들지 않는다.
- Windows UI: 컴포넌트별 실제 관측과 만료를 표시한다. 전체 수명/종료 정책은 유지한다.
- 경로 분류, Riot 도메인·CIDR, DNS lease/guardian 소유권, full-tunnel fallback은 변경하지 않는다.

## 상태·IPC 경계

Observation 필드: component, status, request_id, generation, observed_at(UTC epoch seconds), ttl_seconds(0~300), evidence, reason_code. game 결과는 실측 없이 생성하지 않는다. 서비스 PASS는 기본 HTTPS 응답 증거일 뿐 로그인·통계 성공이 아니다.

G1은 관측 상관관계/신선도만 구현했다. command request 재전송의 멱등 캐시, privileged peer ACL, 영속 restart generation, lease CAS, supervisor 전환은 **G2 미구현**이다. main.py의 standalone CLI 기본 request_id=cli는 개발 편의값이며 실 IPC 권한 토큰으로 사용하지 않는다.

## 디자인 통합과 보존

- `README_STRATA_PREVIEW.md`와 새 이미지 3장을 신규 경로로 통합. README.md는 ALPHA 1.2.3을 유지한다.
- 실제 ALPHA 출시 배너와 STRATA 시안을 열어 비교했다. 양쪽 모두 **2172×724, 3:1**이다.
- 차이: ALPHA는 둥근 입체 크림색 글자·컬러 3D 광부·여유 있는 동굴 배치, STRATA 제공 시안은 굵은 산세리프·라임 STRATA·선화 캐릭터·화면을 더 채우는 배치다. 스타일이 정확히 같다고 검증하지 않았다.
- 제공 시안은 개발 프리뷰로 보존한다. 폰트/캐릭터의 최종 ALPHA 스타일 정합 조정은 미완료 디자인 검토 항목으로 남긴다. 원본 ALPHA나 제공 시안을 임의로 덮어그리지 않았다.
- artwork_archive의 과거 시안은 업로드 ZIP과 외부 이관 폴더에 그대로 보존했다. 기존 repository archive를 정리하지 않았다.

## 검증

- 로컬: `PYTHONPATH=v5 SCHOOLNET_TEST_ENGINE=<고정 1.12.0 Linux 엔진> python3 -m unittest discover -s v5/tests -v`.
- 신규: enum/TTL/미래 시각/요청·세대/중복/엔진-프로브 분리, 비민감 오류, fixed-Warp 복귀 정책, CLI stdout/stderr, Windows timeout 이후 안전 정리.
- Mac native: STRATA 전용 branch-only CI에서 전체 Swift frontend 컴파일 + StrataHealthSmoke를 실행한다. 실제 WARP·학교망·게임은 호출하지 않는다.
- `.github/workflows/strata-g1.yml`은 읽기 전용 권한의 검사 전용 workflow이며 publisher·release·Homebrew dispatch가 없다.
- Mac/Windows 실기 게임·통계 API·Vanguard, G2 수명 시험은 미검증. CI 성공을 그 증거로 사용하지 않는다.

## G2 진입 판정

**진입하지 않음.** G1 코드와 native CI 결과 리뷰, 디자인 미완 항목 및 별도 Windows 서비스/Job/guardian 소유권 설계가 필요하다. Close/Quit/logout/reboot 정책을 바꾸지 않았다. 실제 현장 반복 시험과 자동 배포는 수행하지 않는다.

## 최종 실행 결과

- 로컬 전체 원본 소스 + 고정 sing-box 1.12.0: **169 tests PASS**, 수집 오류 없음.
- 브랜치 CI: https://github.com/hexagon0401/MINER/actions/runs/45134822839 — Ubuntu / Windows Server 2025 / macOS 26 모두 PASS.
- macOS: 전체 Swift UI 소스 컴파일 및 pure model smoke로 엔진 유지/프로브 FAIL, 요청 불일치 거부, TTL 만료, 진행 JSON 제거 검증 PASS. 네이티브 앱 화면 렌더링·실제 게임 시험을 실행한 것은 아님.
- 보호 대상 SHA-256 및 프리뷰 PNG 링크 확인 PASS. ALPHA 이미지 크기/시안 비교 완료, 스타일 최종 정합은 디자인 미완 항목으로 명시.
- G1 명령 observation 모델의 상태 전환은 요청·세대·시각의 유효성에 한정된다. 서비스 수명 FSM·명령 중복 실행 방지·IPC 권한 검증은 G2다.
- main SHA 유지: 7889545ea4c41301b0f75995f541d9c8164e9d16. 배포·태그·cask 갱신·G2 진입 없음.
