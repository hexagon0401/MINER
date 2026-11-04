# MINER DELTA v2.1 — Codex 이관 패키지

**먼저 `UPGRADE_SPEC.md`를 읽는다.** 이 파일이 최종 요구사항이다. 기존 v2 명세는 `UPGRADE_SPEC_v2_BASE.md`에 비교용으로 남겨뒀고, 두 명세가 충돌하면 v2.1을 우선한다.

이 패키지는 기존 MINER 앱의 UI 변경분만 포함한다. 네트워크 엔진, 실제 5단계 진행 이벤트, 기존 캐릭터, 로컬라이징 데이터는 교체하지 않는다.

### 이번 v2.1 추가분

- 시각적 타이틀바 회색 띠와 중앙 중복 타이틀 제거. macOS 기본 창 제어 버튼과 창 드래그는 유지.
- 동굴과 시스템 반투명 Liquid Glass 소재가 창 맨 위까지 자연스럽게 연결.
- 데스크톱 배경색을 시스템 재질이 은은하게 반영. 화면 픽셀을 직접 읽지 않음.
- 기존 **5칸 진행 막대** 유지. 기존 v2 초록·빨강 파동, 성공 체크·블러, SVG 8종도 모두 유지.

### 최신 시안 및 명세

- `UPGRADE_SPEC.md` — **최종 단일 명세 및 QA 체크리스트**
- `preview/layout-v2-1-concept.png` — 새 무타이틀바 유리 창 시안
- `preview/index.html` — 브라우저용 오프라인 동작 미리보기 (네트워크 변경 없음)
- `assets/motion-tokens.json` — v2.1 수치와 색상
- `UPGRADE_SPEC_v2_BASE.md`, `preview/layout-v2-reference.png` — 이전 v2 참고 자료

### Codex에 전달할 지시문

> 이 MINER DELTA.zip은 기존에 구현 완료된 MINER 프로젝트에 병합하는 UI-only patch이다. 가장 먼저 `UPGRADE_SPEC.md`를 읽고, macOS 네이티브 hidden titlebar/full-size content 기법을 사용하되 신호등 버튼/드래그/창 기능은 유지한다. Liquid Glass의 시스템 소재로 주변색을 은은하게 흡수하게 하며 기존 5칸 실제 이벤트 진행 막대, 승인된 캐릭터, 엔진과 로그, WARP 로직은 그대로 둔다. 기존 v2의 초록 시작·빨강 중지 파동, 광부/흙 파티클, 성공 체크·블러 복원은 모두 보존한다. 프리뷰의 임의 타이머를 실제 진행 로직으로 복사하지 마.

---

이 패키지는 이미 Codex로 구현한 **MINER v1.0의 디자인·애니메이션 업그레이드분만** 포함한다. 기존 v1.0 에셋이나 작동 로직을 이 패키지로 통째로 덮어쓰지 않는다.

## 구성

| 파일 | 역할 |
| --- | --- |
| `UPGRADE_SPEC.md` | **v2.1 우선 명세**: 새 타이틀바/글래스/배치/타이밍/QA |
| `UPGRADE_SPEC_v2_BASE.md` | 참고용 이전 v2.0 명세 |
| `preview/layout-v2-1-concept.png` | **최신** 전체 윈도우 디자인 |
| `preview/layout-v2-reference.png` | 이전 v2 시안 |
| `preview/layout-concept.png` | 업로드한 현재 UI 스크린샷을 기반으로 새 배치를 이미지 편집 도구로 시각화한 시안 |
| `preview/index.html` | 실제 네트워크 조작 **없는** 시뮬레이션. 시작 초록 파동, 중지 빨간 파동, 채굴, 연결 성공 가운데 체크/블러/복원 |
| `preview/approved-mascot-reference.png` | preview 전용 원본 캐릭터의 작은 사본. **production mascot 교체 금지** |
| `preview/school-reference.svg` | preview 전용 기존 학교 에셋 사본. **production 기존 파일 교체 금지** |
| `assets/full-window-strata.svg` | 창 전체 투명 지층 배경 레이어 |
| `assets/shaft-reveal.svg` | 수직 땅굴 파내려가는 전환 |
| `assets/dig-wall-cracks.svg` | 곡괭이 충격 시 균열 |
| `assets/pickaxe-impact.svg` | 타격 순간 작은 스파크 |
| `assets/dirt-particle-cluster.svg` | 사각형 흙 파티클 디자인 가이드/선택적 레이어 |
| `assets/pebble.svg` | 날아가는 작은 바위 |
| `assets/skylight-beam.svg` | 연결 성공 시 빛이 내려오는 효과 |
| `assets/exit-ceiling.svg` | 땅굴 천장 출구 |
| `assets/motion-tokens.json` | 창 치수, 버튼 위치, 타이밍, 성공 체크/블러 수치 |

## Codex 적용 순서

1. **`UPGRADE_SPEC.md`를 먼저 읽는다.** `preview/layout-v2-1-concept.png`로 최종 구도를 이해한다.
2. 기존 `MINER` 뷰의 네이티브 윈도우 프레임, 연결 상태 바인딩, 승인된 광부 원본, 로컬 메시지 JSON을 유지한다.
3. 검은 둥근 개별 애니메이션 패널을 없애고 전체 창 **content**에 `full-window-strata.svg`와 기존 학교·땅굴·광부를 올린다.
4. 시작/중지 버튼을 중앙 세로 정렬하고, `시작` 초록 파동·`중지` 빨간 파동을 일회성으로 실행한다.
5. 전체 엔진 성공 때 새 빛 SVG→**창 중앙 native SF 체크**→배경 블러→정상 복원 시퀀스를 재생한다.
6. 필요한 새 SVG만 기존 프로젝트의 `Assets.xcassets`에 추가한다. 캐릭터나 원본 배경·네트워크 관련 파일은 중복 생성/교체하지 않는다.
7. `preview/index.html`은 압축 해제 후 브라우저에서 실행할 수 있으며, 실제 로직의 진행 타이머로 복제하면 안 된다. UI state 이벤트에 연결한다.

## 색상과 원칙

- 시작 파동 `#0EFB2E`, 중지 파동 `#FF5A61`, 네이비 `#0E131F`
- 전체 창 배경은 macOS Liquid Glass + 반투명 딥네이비, 정확한 글씨 가독성 우선
- 시작/중지 파동은 요청 피드백이며 **성공/정지 완료 판정이 아님**
- 연결 성공 가운데 체크는 **전체 엔진 연결 성공**일 때만 표시. WARP-only 준비 완료와 구별
- 원래 코드의 CLI/Proxy/TLS/Admin/Engine 5단계를 그대로 재사용

## 제작 참고

`layout-v2-1-concept.png`는 이전 v2 시안의 분리된 회색 타이틀바를 제거하고 전체 유리 동굴로 확장한 이미지 편집 시안이다. 정확한 수치와 동작은 이미지보다 `UPGRADE_SPEC.md`/`motion-tokens.json`이 우선이다. 이 패키지에는 실제 macOS 앱 소스가 없으며 기존 프로젝트에 병합할 UI 요구사항·신규 에셋·미리보기를 제공한다.
