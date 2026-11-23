# MINER 2.0.0 — Product & Engineering Blueprint

> 문서 상태: **설계 제안 v0.1 / 미구현**  
> 작성 기준: 2026-11-23 KST  
> 출처: 첨부 1.2.3 소스 스냅샷과 2026-11-04 스쿨넷 연구 원문, 1.2.2 현장 진단 요약, 당시 공식 제품 문서  
> 코드 기준: release payload `b8af912e42366c39edacdea39289332f23f57921`, main `7889545ea4c41301b0f75995f541d9c8164e9d16`  
> 범위: 제품 기획·기술 설계·구현 작업 명세. **2.0.0을 구현/배포하거나 사용자 컴퓨터의 DNS·WARP 설정을 변경하지 않았다.**

## 0. 한 문장 목표

Riot/LoL의 서비스 TCP는 개인용 WARP Local Proxy 경로에, 실제 인게임 트래픽은 OS 원래 경로에 **동시에 유지**하면서, 게임/클라이언트 단계마다 연결 방식을 바꾸지 않고 UI 종료 및 개별 검사 실패에도 정상 경로를 안전하게 유지하는 Mac/Windows 앱.

학교 네트워크에서 무엇이 실제로 허용되는지는 학교/정책별로 다르며, 차단을 우회할 권한이 있다는 의미가 아니다. 학교 시설망에서의 시험·배포는 해당 망의 이용 규정과 허용 범위에 따라 수행한다.

## 1. 현재 확인된 사실과 미확정 가설

| ID | 사실/관측/가설 | 상태 | 근거 |
|---|---|---|---|
| F01 | 1.2.3은 **게임 중 WARP ON/OFF 토글을 하지 않는다**. WARP Local Proxy와 직접 경로를 실행 중 병행한다. | [코드] | `v5/schoolnet/config.py`, `v5/macos/App.swift`, `v5/windows/controller.py` |
| F02 | 분류의 주축은 `RIOT_DOMAINS`의 A/AAAA FakeIP + 선택 TUN; 전 프로세스의 실제 목적지를 포착하는 앱별 VPN이 아니다. | [코드] | `v5/schoolnet/config.py` |
| F03 | 해당 TUN TCP는 SOCKS5 TCP, 실제 게임 IP는 OS 경로; 전체 0/0 TUN 라우트는 설치하지 않는다. | [코드] | `v5/schoolnet/config.py` |
| F04 | 1.2.2 진단의 통계창 무한 로딩 시점에는 WARP/SOCKS/엔진이 살아 있었다. | [현장 관측] | 이관서 7장; 원본 진단 ZIP은 이번 패키지에 없음 |
| F05 | 1.2.3 Mac: 검증 실패 후 엔진이 남을 수 있고 전체 `phase=error`; Windows: 검증 예외 후 세션 finally 정리. | [코드] | `v5/macos/App.swift`, `v5/windows/controller.py` |
| F06 | 시작 전 존재하던 클라이언트 DNS/소켓 캐시, 미포함 목적지, 실제 서비스 세션 문제가 통계창과 연관될 수 있다. | [가설] | 이관서 6장; 특정 통계 요청 미관측 |
| F07 | WARP OFF 즉시 끊김은 세션 경로 변화(A), 직접 경로 정책(B), 혹은 복합 효과로 설명 가능하다. | [연구] | `reference/schoolnet_warp_riot_network_research_2026-11-04.md` |
| F08 | 특정 학교의 DPI 제품, 실제 IP/UDP 허용 규칙, Riot 현행 통계 API 목적지는 확인되지 않았다. | [미확정] | 연구 범위의 한계 |
| F09 | 서명·공증 없는 Mac ad-hoc 빌드와 미서명 Windows 빌드는 배포 신뢰 제약이다. | [배포 상태] | 이관서 3·10장 |

**버릴 가정:** DNS만 바꾸면 전부 해결된다; WARP OFF 직후 실패는 반드시 DPI다; Riot.exe 전부 직접/우회 중 하나로 보내면 된다; `auth.riotgames.com` 단일 HEAD 성공은 통계창 성공이다; Windows Server CI 통과는 Win11 실기 성공이다; WARP가 모든 UDP를 SOCKS로 보낼 수 있다; 개인용 WARP에 Cloudflare One 조직별 split tunnel 설정을 그대로 적용할 수 있다.

## 2. 권장안과 대체안

### A. 권장 — Durable Service + 현재 선택 TUN 단계적 개선

```
[MINER UI / tray / menu]
       | 로컬 인증 IPC (Status/Connect/Stop/Diagnose/UpdatePrepare)
       v
[MINER Connection Supervisor]  <- 사용자 소유 상태/요청 ID/세대 번호
       |-- WARP Controller (개인용 warp-cli, local SOCKS5h)
       |-- Route Engine Owner (sing-box, 선택 TUN)
       |-- DNS Lease Controller (원본 보존, 소유권 검증, 저널)
       |-- Health Evaluator (엔진/프록시/Riot 서비스/게임 관측 별도)
       |-- Recovery Guardian (UI와 별개, 부팅 후 고아 lease 복구)
       +-- Diagnostics (동의 기반, 최소 수집, 자동 업로드 없음)

Riot 지정 서비스 TCP --> FakeIP 선택 TUN --> WARP SOCKS5 TCP
실제 게임 서버 패킷 --> 기존 OS 경로 (단, 학교 정책이 허용한 경우)
일반 앱 --> 기존 OS 경로 (현행 글로벌 DNS 변경은 예외 위험)
```

장점: 기존 1.2.3 경로·CI·릴리스 자산 재사용; 전 시스템 트래픽의 TUN 재포착 없음; 문제를 격리해 시험 가능. 한계: OS DNS를 사용하지 않는 앱, 클라이언트의 기존 TCP 연결, 새로운 Riot 종단점, 일부 UDP 기능은 자동 포착하지 못함.

### B. 미래 PoC — OS 네이티브 앱/흐름 선택

macOS Network Extension 앱 프록시/packet tunnel, Windows WFP 기반 프로세스/흐름 식별을 **별도 실험**한다. Mac에서 per-app VPN의 앱 규칙은 MDM 관리 요건이 있어 일반 개인 사용자에게 배포할 수 있다고 전제하지 않는다. Windows는 드라이버/서명/Vanguard 호환성 부담이 크다. 2.0.0 출시 기본안으로 채택하지 않음.

### C. 보조 후보 — 앱의 공식 프록시 설정

Riot/LoL이 공식적으로 해당 기능을 제공한다면 TUN·전역 DNS 변경을 더 줄일 수 있으나, 지원 여부 미확인. 임의 Chromium 플래그나 실행파일 수정에 의존하지 않는다.

**전환 조건:** A로 실제 10회 연속 사후 통계창 성공·일반 앱 안정성 확보에 실패하고, 실패한 실제 통신이 FakeIP/DNS 간극에 기인한다는 검증이 확보되며, B 또는 C가 공식 권한/배포/성능 조건을 충족하면 대안을 재평가한다. 단순 가설만으로 전체 경로를 넓히지 않는다.

## 3. 제품 기본 정책 (제안 결정)

| 상황 | 기본 동작 |
|---|---|
| UI 창 닫기 | 백그라운드 서비스 유지, 트레이/메뉴 상태 아이콘 표시 |
| 사용자 명시적 Stop | DNS 원본 복구 확인 → 엔진 종료 → WARP 복귀 정책 검증(현재 1.2.3은 고정 Warp 복귀이며 이전 사용자 모드 복원은 미구현). 실패 시 Recovery Required |
| OS 로그아웃 | 기본적으로 세션을 안전 종료·DNS 복원. 재부팅 후 자동 연결 OFF |
| 사용자 로그인 | 서비스 상태·잔류 lease 확인. 이전 미완료 세션 자동 실행하지 않음 |
| UI 강제 종료/충돌 | 통신 서비스 유지, UI 재실행 시 상태 재동기화 |
| 네트워크 전환/절전 복귀 | 소유권·인터페이스·경로 검증. 게임 중 자동 WARP 모드 전환 금지. 필요한 경우 경고·사용자 재시도 |
| 프록시/단일 Riot 확인 실패 | 해당 기능만 Degraded. 건강한 게임/일반 경로 유지. 직접 Riot 우회 fallback 금지 |
| 엔진/DNS 손상 | 원본 DNS 복구 우선. 오류 유지, 명시적 재시도/복구 가능. 정상으로 위장 금지 |
| 게임 연결 중 재설정 요청 | 사전 경고 또는 안전한 거부. TCP/UDP 기존 세션을 무중단 이전할 수 있다고 약속하지 않음 |
| 개인정보 | DNS 조회 원문, 계정 토큰, 쿠키, 패킷 내용 저장 금지. 진단 업로드 OFF |

본 제품은 공인 게임 서버에 연결하는 사용자 프로그램이다. 학교 운영 규정을 무시하는 회피·은닉 기능이나 공격 트래픽 기능을 추가하지 않는다.

## 4. 연결 경로 계약 (Routing Contract)

| 흐름 | 조건 | 허용 경로 | 실패 시 |
|---|---|---|---|
| Riot 서비스 TCP | 인식된 도메인의 FakeIP 주소로 유입된 TCP | WARP Local Proxy SOCKS5 원격 호스트 연결 | 국소 실패, 직접 fallback 하지 않음 |
| 실제 게임 IPv4/IPv6 | 실제 목적지 IP가 기존 OS 경로로 향함 | 원래 네트워크 직접 경로 | 연결 불가 관측, 임의 경로 추가 금지 |
| 서비스/게임 UDP | 명시적 관측과 지원 범위에 한함 | 기존 실제 목적지는 직접 | FakeIP UDP는 기존 안전 규칙 유지, 미검증 우회 금지 |
| 일반 앱 | Riot 관련 인식 도메인 아닌 일반 IP | 원래 OS 경로 | 기존 DNS 충돌 시 lease 복원 |
| Riot 도메인을 방문하는 브라우저 | 인식된 Riot FakeIP 도메인 | WARP 영향 받을 수 있음 | 전역 도메인 분류의 알려진 한계로 UI/문서에 고지 |
| 캐시된 실제 주소/독립 DoH | 현행 선택 TUN 밖 | 자동 제어 불가능 | 인식 범위 미확보 상태 표시. 캐시 일괄 삭제 금지 |
| WARP 불가 | Riot FakeIP TCP 유입 | 재시도 보류 또는 명시적 오류 | 학교망에 직접 Riot 연결을 몰래 누출하지 않음 |

**핵심 규칙:** 도메인 분류, 프로세스 분류, 게임 패킷 분류는 동일하지 않다. 현재 `extra_clients` 설정값을 늘려도 FakeIP 선택 범위가 늘지 않는다. 실제 게임 UDP 직접 경로가 학교 정책상 차단된 경우, 2.0의 원하는 품질을 보장할 수 없다.

## 5. 상태/IPC 계약

단일 `running=true`와 숫자 0~5 대신 컴포넌트별 상태를 가진다.

```
ServiceState = STOPPED | PREFLIGHT | STARTING | READY | DEGRADED |
               STOPPING | RECOVERY_REQUIRED
RouteState   = UNKNOWN | PREPARING | ACTIVE | FAILED | RESTORED
ProxyState   = UNKNOWN | CONNECTING | CONNECTED | DEGRADED | FAILED
RiotProbe    = NOT_RUN | PASS | FAIL | TIMEOUT | NOT_APPLICABLE
GamePath     = NOT_OBSERVED | DIRECT_OBSERVED | BLOCKED_OR_UNREACHABLE | UNKNOWN
```

상태에는 항상 `observed_at`, `evidence` (`CODE_TEST`/`LIVE_PROBE`/`PASSIVE_OBSERVATION`/`USER_REPORT`), `ttl_seconds`, `reason_code`를 포함한다. `READY`는 인프라 준비이지 실제 게임·통계 API 성공을 의미하지 않는다. 사용자 언어로 `분리 경로 준비됨 / Riot 서비스 검사 실패 / 실제 통계 기능 미검증` 표시 가능해야 한다.

IPC는 버전 붙인 JSON/로컬 소켓(맥: 기존 root helper 기반) 또는 보호된 Named Pipe(윈도우 서비스)를 사용한다.

```
commands: status, connect, stop, retry_probe, diagnose, prepare_update
fields: api_version, request_id, expected_generation, operation, options
```

요청은 멱등(idempotent) 처리, 중복 방지, 세대번호 CAS, 경합 직렬화, 제한시간/취소, 권한된 단일 소유 사용자 검증. root 명령·임의 shell·임의 경로/바이너리 지정 금지. 성공 응답은 실제 lease/엔진 상태 확인 후에만 생성. 진행 이벤트 JSON과 오류 메시지 채널을 분리한다.

**Mac:** 현 `macos_helper.py`의 피어 UID 인증, root 소유 고정 런타임, launchd helper를 재사용하되 **engine owner와 lease guardian의 책임을 UI에서 분리**. `App.swift` 앱 종료 시 `stop()`으로 이어지는 기본 정책을 변경하되 실제 Stop/로그아웃/업데이트는 복구 보장을 유지.

**Windows:** 현 GUI worker 수명에 결합된 Job Object 소유를 장기 실행 서비스로 이전. 보호된 서비스/Named Pipe, 적절한 서비스 계정/토큰과 ACL, 재부팅 후 복구 guardian, UAC 경계 설계. 아무 관리되지 않는 고아 sing-box 프로세스를 만들지 않는다. Windows Service의 실제 관리 방식, 서명 및 Riot Vanguard 호환은 Win11 실기에서 검증한다.

## 6. 장애 모델과 복구 우선순위

```
WARP 단일 검사 FAIL
   -> service/probe DEGRADED, 엔진 정상 유지, 재검사 제한 backoff
WARP 연결 소실
   -> Riot 연결 DEGRADED, 게임 직접 경로 보존, 자동 full-tunnel 전환 금지
Engine process exited
   -> DNS lease 오염 여부 검사 -> 원본 DNS 복구 -> RECOVERY_REQUIRED
UI process exited
   -> 백엔드 유지, IPC 재접속 대기
DNS 소유권/설정 충돌
   -> 다른 사용자의 DNS 설정을 강제 덮어쓰지 않음; 수동 안내
OS sleep/wake or NIC swap
   -> 변경된 인터페이스와 세션 상태 검사; 게임 중 무리한 재설정 금지
Crash/reboot
   -> journal+owner+generation 비교, 안전한 원상 복구; 자동 재연결 OFF
```

복구 순서에서 DNS를 먼저 정상화하고 엔진을 내리는 기존 보수적인 원칙 유지. 임의 프로세스를 PID 파일만으로 종료하지 말 것. 동일 요청 반복은 끊김을 유발하지 않는 멱등 동작으로 구현.

## 7. P0 원인 조사: 통계창 무한 로딩

**반드시 분리해서 검증할 가설**

- H1: MINER 시작 전에 생성된 Riot Client 소켓/이름 캐시가 계속 유지됨.
- H2: 통계/런처 호출이 `RIOT_DOMAINS` 바깥의 이름·직접 IP·별도 프로토콜을 사용함.
- H3: SOCKS에 들어간 특정 요청의 실제 TCP/TLS 세션 실패·응답 시간초과.
- H4: Riot 클라이언트 내부 렌더러/애플리케이션 계층 오류(네트워크 통과와 무관할 수 있음).
- H5: 무선 손실/재전송 또는 학교 정책에 의해 직접 게임/다른 흐름이 실패함.

**진단 디자인:** 로그를 현장에서 자동 전송하거나 복호화하지 않는다. 사용자가 단계 버튼(시작 전/연결/인게임/종료/통계)을 눌러 시간 구간을 표시하면, 최소한의 메타데이터만 수집: 경로 방식(실제 주소 값 제외), DNS 오류 유형, SOCKS CONNECT 결과 유형, TLS 핸드셰이크 성공 여부, 프로세스 존재·수명, OS 연결 오류 클래스, 클라이언트 로그의 개인식별정보 없는 오류 타입. 1.2.3의 단일 `auth.riotgames.com` HEAD 결과를 통계 성공의 대리 지표로 사용하지 말 것.

**실험:** [baseline WARP 단독], [baseline MINER 1.2.3], [MINER 2.0 PoC]를 가능한 동일한 장치/네트워크/리전/사용 패턴에서 비교. 시작 전 완전 종료 여부를 기록. 각 시험은 클라이언트 로딩→매칭→연습게임→통계창을 실제로 수행. 실패한 최초 정확한 시각과 재현성을 기록. 장비·학교 차단 추정은 검증 가능한 증거를 확보한 경우만 적기.

## 8. UI/UX — 브랜드 유지, 상태 정확도 우선

기존 MINER 광부·흙굴·5단계·Mac 네이티브 감성을 유지한다. Windows Pearl White/Fluent 및 정적 캐릭터 자산을 바꾸기 위한 대규모 UI 재개발은 본 버전 범위 밖.

주 화면은 `CONNECT`/`STOP`과 **SERVICE, WARP, ROUTE, RIOT, GAME** 상태를 단순하게 표시. `Connected`를 네트워크·게임 전체 성공으로 오인하지 않도록 상세 창에서 근거와 마지막 검증 시각을 제공. 통계창 성공 확인은 사용자 또는 실제 응용단 기능 관측 증거만으로 판정.

별도 `Diagnostics` 화면에 수동 단계 기록, `ACTIVE PROBE ON/OFF`, 로컬 리포트 내보내기, 개인정보 제외 목록. 서비스가 살아 있는 상태에서 UI 창만 닫으면 메뉴/트레이에서 열기·중지·오류 확인 가능. 네트워크 변경/업데이트는 경기 중 차단하거나 사용자에게 경고한다.

## 9. 단계별 개발 로드맵 (각 단계 통과 후 다음 단계)

| Gate | 구현 범위 | 반드시 확보할 증거 | 종료 조건 |
|---|---|---|---|
| G0 BASELINE | 소스·프로필·CI 고정, 현장 진단 설계 | 원본 SHA, 재현 시험 결과/불확실성 | 1.2.3 실패 상황과 4/5 표시를 재현하거나 미재현 기록 |
| G1 P0 HEALTH | 인프라 준비와 Riot 외부 검사 분리, Mac/Windows 동일 의미 | `service_verify` 실패 주입 fixture | 검사 실패가 전체 엔진을 잘못 정상/고장으로 표시하지 않음 |
| G2 SERVICE | Mac 지속 연결 supervisor; Windows 서비스·IPC 수명 분리 | UI 강제 종료/복원, Stop/로그아웃/충돌 | GUI 없이 복구 책임 있는 소유 프로세스 지속 |
| G3 DIAG | opt-in 비활성/능동 진단, 통계창 실패 도메인·종단점 분류 | 프라이버시 감사, 재현 가능한 실패 증거 | 확인/미확인 원인을 구분해 출력 |
| G4 ROUTING PoC | 선택 FakeIP의 분류 간극 보완, IPv6/DoH/캐시 경계 | fixture와 실기 경로 회귀 비교 | 일반 트래픽·게임 직접 경로 손상 없음 |
| G5 HARDEN | 절전/기본 NIC 변경, race/lease, updater 2.0 마이그레이션 | 장애 주입·업그레이드/롤백 | 원본 DNS 복구 및 데이터 보존 검증 |
| G6 RELEASE | Mac AS/Intel, Windows x64 네이티브 빌드·서명 검토 | 실제 게임·Win11·지원 환경 결과 | 기능 수용·안전성·배포 게이트 모두 통과 |

G1은 G2에 앞서 독립적으로 안정화 가능. **통계창 현장 증거(G3)가 없으면 G4의 앱 분류 알고리즘을 임의로 확장하지 않는다.**

## 10. 수용 기준 (계획 목표이며 아직 달성 아님)

- 동일한 실행 중 로비/게임/통계 복귀를 **10회 연속** 성공(연습·사용 조건 기록). 통계 화면 30초 이상 멈춤을 실험상 실패로 표시; Riot의 공식 SLA로 주장하지 않음.
- UI 창 닫기, 다시 열기, UI 프로세스 강제 종료 후에도 테스트용 연결이 끊기지 않음; 실제 Stop은 DNS/엔진/WARP의 정리 완료를 확인.
- 30분 이상 장기 세션 최소 1회 및 잠자기/깨우기, Wi-Fi 변경, WARP Connecting/Disconnected, 업데이트 중단, 동시 Start·Stop 등 주입 시험.
- 브라우저·카카오톡·일반 OS DNS/HTTPS의 정상 기능 유지. Riot 관련 웹 사이트는 현행 도메인 기반 규칙 영향 예외로 기록.
- 게임의 FPS/클릭 지연과 네트워크 RTT/패킷 손실, CPU/RAM을 **서로 다른 지표**로 측정. 서로 다른 시점의 1회 HUD 값을 유의미한 인과 효과로 취급하지 않음.
- Mac Apple Silicon 실기 우선, Intel 네이티브 CI, Windows 11 x64 실기(Windows Server 2025 CI만으로 대체 금지).
- 최소 권한, 사용자 데이터 보존, uninstall/recovery/upgrade rollback, signing/notarization 조건을 별도 체크리스트로 증명.
- 학교 네트워크·게임 연결의 실제 허용 여부는 환경별로 다름을 표기. 미검증 기능을 완료로 표시하지 않음.

## 11. 배포·마이그레이션

**2.0.0 최초 출시에서는 `ALPHA` 코드명/태그/파일명 계약을 유지하는 방식 권장.** `v5/schoolnet/updates.py`는 `miner-alpha-v{version}`, `MINER-ALPHA-v{version}-…`, `codename=ALPHA`를 명시적으로 검사한다. 새 세대명으로 바꾸려면 먼저 1.2.x bridge updater를 배포하고 실제 업그레이드를 입증해야 한다.

- 첫 버전에서는 Mac bundle ID, root helper label, Windows AppId, brew cask `miner`, 기존 데이터 경로와 DNS journal 레이아웃을 한 번에 바꾸지 않는다.
- 설치 전 실행 중 엔진/경기 상태 검사; explicit Stop→사용자 데이터·journal 스냅샷→원자적 교체→정상 상태 확인→구 캐시 정리.
- 기존의 `network-dns-v1.json`이 미복구이면 마이그레이션 전에 복구하고 실패 상태를 노출; 무단 삭제 금지.
- 신규 supervisor 스키마에 버전/ownership/generation 추가, 구 1.2.3 파일을 신버전이라고 해석하지 말 것.
- Apple Developer 등록만으로 서명 인증서·공증 자동 생성 아님. Windows Authenticode·Win11/Vanguard는 실제 확인해야 함.
- release manifest SHA, source commit, platform verification JSON, Homebrew cask hash 및 CI 입력 SHA 연결 유지.

## 12. 새 코드 모듈 제안 (세부는 단계별 구현에서 결정)

```
v5/schoolnet/supervisor.py         # 순수 상태기계 + 명령 직렬화 (OS 비의존)
v5/schoolnet/health_model.py       # 경로·프록시·서비스 결과 분리, TTL
v5/schoolnet/route_evidence.py     # 개인정보 최소화 관측 이벤트
v5/schoolnet/lease_owner.py        # journal owner / generation / CAS
v5/schoolnet/ipc_protocol.py       # 버전/요청 ID/오류 구조
v5/macos/...                       # 기존 helper/service와 launchd 수명 확장
v5/windows/...                     # Windows Service 호스트, 제한된 Named Pipe
v5/tests/test_supervisor.py
v5/tests/test_health_model.py
v5/tests/test_lease_owner.py
v5/tests/test_lifecycle_integration.py
```

이 경로는 **구현 후보**이지 지금 존재하는 파일이 아니다. 현행 `v5/schoolnet/runtime.py`, `network_dns.py`, `macos_service.py`, `macos_helper.py`, `windows/controller.py`와 책임을 추출·통합해야 한다. 일괄 재작성 대신 TDD/회귀 테스트에서 점진 이전.

## 13. 검증과 근거 추적

**현장 사용자 진단**: 2026-11-23 1.2.2의 `active_probes=false`; 통계창 순간 WARP/엔진 살아 있음. 1.2.3의 새로운 서비스 검사 4/5 오류는 화면 보고이며 원문 오류 유형 미확정. 위 사실은 독립 검증의 종류가 다름.

**기존 자동 검증**: 보고된 1.2.3 공통 161 tests, Mac/Windows 배포 CI. 그러나 local SOCKS fixture이며 실제 WARP/game 성공 증명 아님. 해당 수치를 2.0 성능이나 완성도 증명으로 재사용 금지.

**예비 성능**: 2026-11-05 WARP 단독 vs MINER 게임 HUD Ping 평균 143.90ms vs 24.28ms (각 5분·1회). 연구로 참고하되 2.0.0의 예상 개선치로 취급하지 않음.

**학교망 연구**: [V] 특정 교육청 자료, [G] 표준 일반 원리, [H] 사용자 상황 해석, [U] 미확인이라는 원문 등급 그대로 유지. AP/SSID/VLAN/DNS/L4/TLS/DPI를 단일 원인으로 뭉뚱그리지 않음.

### 공식 자료 (기획 시 검토)

- Cloudflare WARP modes: https://developers.cloudflare.com/warp-client/warp-modes/
- Cloudflare One modes(관리형과 개인용 구분): https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/configure/modes/
- Apple Network Extension routing: https://developer.apple.com/documentation/networkextension/routing-your-vpn-network-traffic
- Apple MDM-managed per-app VPN limitation: https://developer.apple.com/documentation/networkextension/netunnelprovidermanager
- sing-box TUN/FakeIP documentation: https://sing-box.sagernet.org/configuration/inbound/tun/ 및 https://sing-box.sagernet.org/configuration/dns/fakeip/
- Riot 고객지원 VPN FAQ: https://support-leagueoflegends.riotgames.com/hc/ko/articles/27902920799763

참고: 최신 sing-box 문서는 1.12.0 이후 변경을 포함할 수 있다. 현재 소스의 1.12.0 문법 변경 검토에는 고정 버전 소스·테스트를 우선한다. 과거 연구 원문의 URL은 원문 레지스트리에 포함되어 있다.

## 14. 기획의 명시적 한계와 남은 선택

- Riot 내부 통계 API를 모른다. 서버 목록, DPI 벤더, 특정 학교 포트/ACL, 게임 세션의 실제 UDP 목적지는 추측해 채우지 않는다.
- 진단 원본 ZIP이 이 패키지에 없으므로 통계 실패 당시 실제 서버/소켓 유형을 확정하지 않는다.
- 추후 필요할 사용자 선택은 자동시작(기본 OFF), 로그아웃 후 연결 유지(기본 OFF), 능동 진단 허용(기본 OFF). 초기에 안전한 기본값으로 개발 가능하므로 질문 때문에 설계를 멈추지 않는다.
- 사용자 환경의 게임·스쿨넷·Riot 약관과 학교 네트워크 규칙 준수를 확인한다. 본 기획은 타인 장치 침입/로그 탈취/보안 차단 비밀 우회를 위한 도구를 설계하지 않는다.
