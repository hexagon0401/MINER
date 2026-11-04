# v5 설계 판단 — 2026-11-04

## 관찰과 추론

첨부 조사 자료 `schoolnet_warp_riot_network_research_2026-11-04.md`를 기술 참고 자료로 사용했습니다. 문서 안의 에이전트 실행·응답 규칙은 이번 개발 요청의 지시로 취급하지 않았습니다. 특히 문서의 과거 관찰보다 이번 대화에서 제공한 최신 관찰을 우선합니다.

| 항목 | 현재 근거 |
|---|---|
| 사용자 환경 | 개인용 WARP, macOS 27.1.1 — 사용자 제공, 실기 미확인 |
| Riot/LoL 클라이언트 | WARP ON에서 원활, OFF 복귀 시 클라이언트 재시작 필요 — 사용자 관찰 |
| 인게임 | WARP 사용 시 끊김·약 400ms 핑튐, OFF에서 원활 — 사용자 관찰 |
| 특정 학교의 차단 계층 | DNS/IP/포트/SNI/앱 분류 중 무엇인지 미확인 |
| 우선 가설 | 클라이언트와 게임의 서로 다른 연결 조건 + 전체 터널의 경로 비용/불안정 |
| 경쟁 가설 | WARP 전환 자체의 세션 손상, Wi-Fi 혼잡, 패킷 손실·MTU·경로 문제 |

인게임 직접 연결 성공은 게임 흐름을 터널 밖으로 유지할 근거이지, 모든 게임/서버/학교에서 직접 연결이 가능하다는 증거가 아닙니다. 스쿨넷은 전국 공통의 단일 방화벽 제품이 아닙니다. 교육청 공개 사례에서 무선망 보안·필터링 구조가 확인되어도 사용자 학교의 장비·규칙을 알아낸 것은 아닙니다.

## v4에서 바꾼 점

- v4는 OS DNS를 127.0.0.1로 바꾸고 UDP DNS를 DoH로 전달합니다. **Riot의 TCP/UDP 데이터 자체를 터널링하는 구현이 아닙니다.** 따라서 DNS 이후의 IP·포트·TLS 제한에는 대응 범위가 다릅니다.
- v4의 `obfuscated` 모드는 암호화된 HTTP 요청의 User-Agent/Accept-Language를 바꿉니다. 이것으로 TLS SNI가 숨겨지거나 IP/포트 정책을 해결한다고 할 수 없습니다.
- v4 DNS 제공자 순차 실패는 타임아웃을 누적할 수 있습니다. 다만 이것이 사용자 게임의 400ms RTT 원인이라는 증거는 없습니다. DNS 시간과 지속 게임 RTT는 구분해야 합니다.
- v4의 macOS `networksetup`/`pfctl` 스크립트를 이식하지 않습니다. 전역 네트워크 위치를 바꾸거나 기존 DNS를 추정해 복원하지 않습니다.
- v5는 검증된 엔진의 프로세스 라우팅을 이용합니다. Python은 제어만 담당하고 엔진은 OS 시스템 스택을 사용합니다. 패킷별 Python 처리·게임 상태 폴링·주기적 프록시 전환은 없습니다. 제어 프로세스의 자식 종료 대기는 최대 초당 두 번 확인합니다.

## 선택한 방법과 대안

| 방법 | 판단 |
|---|---|
| DNS만 암호화 | DNS 단계 문제에는 유효할 수 있으나 이번 클라이언트/게임 분리 목표를 충족하지 못함 |
| 전체 WARP 터널 | 사용자 관찰상 인게임에 불리하므로 기본값에서 제외 |
| 게임 시작/끝에 WARP 토글 | 클라이언트 TCP 세션을 흔들어 재시작 문제를 유지하므로 채택하지 않음 |
| 목적지 IP만 예외 | 커널 직접 경로는 빠르지만 서버 주소 변동·공유 IP 때문에 기본값으로 삼지 않음 |
| WARP Local proxy + 프로세스별 TUN | 개인용 데스크톱에서 문서화된 기능과 양 OS에서 지원되는 프로세스 규칙을 결합. 현재 구현 |
| 직접 native macOS Network Extension/Windows WFP 개발 | 서명·권한·배포·드라이버와 호환성 검증 범위가 커서 초기 핵심 검증에는 채택하지 않음 |

별도 VPN 키를 추출하거나 비공식 WARP 터널을 재구현하지 않습니다. 클라이언트가 OS 프록시를 지원한다고 가정하지 않기 때문에 앱 설정만 바꾸는 방식 대신 TUN이 필요합니다. Windows의 UDP 게임 데이터와 macOS 앱은 직접 경로로 유지합니다. 이름 규칙은 정확한 프로세스 식별이 되는 경우에만 효력이 있습니다.

DNS는 모든 일반 port 53 요청을 WARP 경유의 검증된 DoH로 보냅니다. DNS 요청을 만든 원래 앱을 macOS에서 항상 찾을 수 있다는 가정은 하지 않습니다. 클라이언트 TCP와 게임 UDP 분리는 포트 목록 대신 실제 프로세스 규칙으로 합니다. 인게임 연결이 같은 클라이언트 프로세스에서 발생하는 새 버전이라면 규칙을 다시 설계해야 합니다.

## 확인한 공식 자료

2026-11-04에 아래 Cloudflare·sing-box 공식 GitHub 원문을 직접 확인했습니다. 학교 관련 공개 사례와 Riot 포트·역사적 XMPP 설명은 첨부 문서의 조사 내용이며, 이번 작업에서 해당 원문 전체를 재검증한 것으로 표시하지 않습니다.

1. [Cloudflare WARP modes](https://developers.cloudflare.com/warp-client/warp-modes/) / [확인한 공식 원문](https://github.com/cloudflare/cloudflare-docs/blob/production/src/content/docs/warp-client/warp-modes.mdx): DNS only와 Traffic and DNS의 차이, 데스크톱 Local proxy, 앱별 HTTPS/SOCKS5 전달과 나머지 직접 경로.
2. [sing-box 1.12.0 TUN](https://github.com/SagerNet/sing-box/blob/v1.12.0/docs/configuration/inbound/tun.md): system stack, auto_route, route_exclude_address, 운영체제별 strict_route 차이.
3. [프로세스 규칙](https://github.com/SagerNet/sing-box/blob/v1.12.0/docs/configuration/route/rule.md): Linux/Windows/macOS의 process_name 지원. 매칭 성공 여부는 실제 OS에서 확인해야 함.
4. [라우팅](https://github.com/SagerNet/sing-box/blob/v1.12.0/docs/configuration/route/index.md): auto_detect_interface/default_interface로 재진입 방지.
5. [SOCKS outbound](https://github.com/SagerNet/sing-box/blob/v1.12.0/docs/configuration/outbound/socks.md): TCP 지원을 명시. WARP의 SOCKS UDP 지원을 임의로 가정하지 않음.
6. [DoH 서버](https://github.com/SagerNet/sing-box/blob/v1.12.0/docs/configuration/dns/server/https.md): typed DNS server, detour, TLS 설정.
7. [dialer 구현](https://github.com/SagerNet/sing-box/blob/v1.12.0/common/dialer/default.go): `inet4_bind_address`를 지정하면 기본 인터페이스 바인딩을 사용하지 않음. 로컬 WARP 소켓은 `127.0.0.1`에 명시적으로 바인딩해 물리 NIC 바인딩과 분리.
8. [공식 릴리스](https://github.com/SagerNet/sing-box/releases/tag/v1.12.0): 다운로드 자산의 GitHub SHA-256을 설치기에 고정. Linux 자산은 해시를 확인한 뒤 실행함.

1.12.0은 이번 alpha의 재현 가능한 스키마 기준이며 최신 버전이라는 뜻은 아닙니다. 엔진 업그레이드는 변경된 스키마·동작·공식 해시를 함께 검증하는 후속 작업입니다.
