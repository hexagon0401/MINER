# MINER BETA — v5 분리 연결 실험판

**현재 소스는 macOS 우선의 `5.0.0-beta.2` 개발본입니다. 설치 가능한 최신 DMG는 [베타 1](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1)입니다.** 개인용 WARP의 Local proxy와 sing-box TUN을 연결해, Riot/LoL **클라이언트·웹 Helper의 TCP는 WARP**, **게임 실행 파일과 나머지 트래픽은 직접 경로**로 보냅니다. 게임 시작/종료 때 WARP를 전환하지 않습니다. DMG 앱은 제공된 MINER 디자인·캐릭터를 사용하며 `⌘,` 설정 창에서 한국어/English를 선택할 수 있습니다.

사용자가 제공한 환경은 **개인용 WARP / macOS 27.1.1**입니다. 개발·자동 검증 환경은 Linux이므로 해당 macOS 버전의 실제 호환성, 학교에서의 연결 성공, 게임 핑 개선은 **아직 검증되지 않았습니다**. Windows용 설정도 생성하지만 Windows 네이티브 동작은 미검증입니다. 기존 v1~v4는 변경하지 않습니다.

## DMG 앱 설치·제거

GitHub의 `v5.0.0-beta.*` **사전 릴리스**는 Apple Silicon DMG를 우선 빌드합니다. DMG가 첨부되지 않은 릴리스는 소스 배포이며 설치 파일은 아직 제공되지 않습니다. 이전 Alpha는 Apple Silicon 또는 Intel DMG를 선택할 수 있습니다. 앱을 **Applications로 드래그**한 뒤 실행하면 됩니다. Python과 엔진이 포함되어 있습니다. 개인용 WARP는 별도로 설치·등록해두세요.

앱의 **시작**은 WARP CLI로 Local Proxy·기본 포트 40000 연결과 검증을 수행한 뒤 v5를 실행합니다. **WARP 자동 연결**은 WARP 설정·검증만 실행하고, **WARP 연결 확인**은 설정을 바꾸지 않습니다. **중지·앱 종료**는 엔진을 먼저 중지하고 `warp-cli mode warp`로 UDP Traffic and DNS에 복귀합니다. 설정·연결 확인에 실패하면 오류를 표시하며, 종료 복귀 실패 시 앱을 유지합니다. **WARP 끄기**는 v5를 먼저 중지한 뒤 WARP 연결을 해제합니다. 최초 전체 터널 → 프록시 전환은 게임 밖에서 진행하세요.

시작·중지·제거 때 macOS 관리자 인증을 사용합니다. **제거** 버튼은 실행을 중지하고 v5 지원 파일·사용자 설정·로그를 삭제한 뒤 앱을 휴지통으로 옮깁니다. WARP와 기존 v1~v4는 유지합니다. 새 alpha는 관리 중인 런타임을 검증 후 교체하며 사용자 프로필과 로그를 유지합니다. 제거 전에 필요한 로그를 복사하세요. 부팅 자동 시작 항목은 설치하지 않습니다.

인증서를 설정하지 않은 빌드는 **ad-hoc 서명이며 Apple 공증이 없습니다**. macOS가 실행을 제한할 수 있습니다. Developer ID 자격 증명을 설정하면 별도 서명·공증 검증을 거치며, 실제 상태는 DMG 옆의 `.verification.json`에 기록합니다. [인증서 발급·서명 설정 안내](docs/SIGNING.md)를 참고하세요. Gatekeeper를 전역 해제하는 절차는 사용하지 않습니다.

alpha.3은 한글 안내 파일명이 정규화되며 `a sealed resource is missing or invalid`가 발생한 문제를 수정합니다. 앱 내부 파일명을 ASCII로 제한하고 DMG에서 복사한 뒤의 서명까지 검사합니다. 이 패키징 수정과 Developer ID 공증은 별개의 검증입니다.

[앱 사용 안내](macos/사용%20안내.txt) · [릴리스 안내](macos/RELEASE_NOTES.md)

macOS 빌드는 `.github/workflows/v5-alpha-macos.yml`에서 Apple Silicon/Intel을 각각 빌드하고, 코드 서명 무결성·DMG 검사·실제 마운트 후 내장 CLI 실행을 검증합니다. 태그 빌드가 모두 통과해야 DMG와 SHA-256 파일을 GitHub 사전 릴리스에 게시합니다. 아래 CLI 설치 절차는 소스에서 실행할 때 사용합니다.

## 연결 구조

```text
RiotClientServices / LeagueClient / LeagueClientUx 등 TCP
  → 로컬 sing-box TUN → WARP SOCKS5 → Cloudflare → 클라이언트 서버

LeagueofLegends / League of Legends.exe (TCP·UDP)
  → 로컬 sing-box TUN → direct → 기존 인터넷 경로 → 게임 서버

OS의 일반 DNS(port 53)
  → sing-box → DoH(TLS 검증) → WARP SOCKS5 → Cloudflare DNS
```

Python은 설정 생성·실행·검증만 담당합니다. 게임 패킷을 Python으로 중계하거나 프레임/메모리/게임 프로세스를 조작하지 않습니다. 게임 데이터의 원격 WARP 우회를 없애는 설계지만 **로컬 TUN 처리 비용은 남습니다**. 따라서 CPU·핑 무영향 또는 0ms 추가 지연을 보장하지 않습니다.

DNS를 WARP로 보내는 이유는 macOS의 `mDNSResponder` 때문에 원래 앱을 DNS 프로세스 이름만으로 신뢰성 있게 구분하기 어렵기 때문입니다. DNS만 터널로 간다고 게임 데이터도 터널로 가는 것은 아닙니다. 반대로 WARP 장애 시 새로운 일반 DNS 조회도 실패할 수 있습니다. 사설 DNS·분할 DNS가 필요한 회사/학교 내부 서비스에는 이 기본 프로필이 적합하지 않을 수 있습니다. 앱 자체 DoH는 port 53 규칙에 해당하지 않으며 앱의 TCP 규칙을 따릅니다.

## macOS 설치·실행

필요한 것은 Python **3.10+**, 설치·연결된 **개인용 Cloudflare WARP**, 네트워크 엔진 **sing-box 1.12.0**입니다. Python 외부 패키지는 필요 없습니다. 먼저 실행 중인 게임과 Riot/LoL 클라이언트를 종료하고 설정합니다.

1. 저장소의 `v5` 디렉터리에서 실행합니다.

   ```bash
   cd /path/to/MINER/v5
   python3 install_engine.py
   python3 main.py init --directory local/mac --platform macos
   ```

   설치기는 CPU 아키텍처를 감지하고 공식 GitHub 릴리스의 SHA-256을 확인합니다. 엔진은 `local/bin/sing-box`에 설치되며 재실행해도 다른 기존 바이너리를 덮어쓰지 않습니다. Homebrew 등으로 설치한 **다른 엔진 버전은 이 alpha의 검증 대상이 아닙니다**.

2. WARP의 최신 GUI에서 Configure Proxy 메뉴가 없어도 CLI로 연결할 수 있습니다.

   ```bash
   python3 main.py warp connect --proxy-port 40000
   python3 main.py warp status --proxy-port 40000
   ```

   버전과 `mode --help` / `proxy --help`로 지원 여부를 먼저 확인하고, 필요한 경우 `disconnect → mode proxy → proxy port 40000 → connect`를 실행합니다. 이미 같은 프록시로 연결되고 HTTPS 검증을 통과하면 연결을 끊지 않습니다. 전체 터널과 동시 사용하지 않습니다. 최초 전환 뒤 기존 클라이언트는 한 번 새로 시작해야 할 수 있습니다.

   검증은 `www.cloudflare.com/cdn-cgi/trace`에 **SOCKS5 원격 DNS → TLS 검증 → warp=on/plus** 순서로 진행합니다. 검증 실패 시 오류를 반환하고 직접 연결로 재시도하지 않습니다. 실제 학교에서의 CLI 동작은 해당 WARP 버전으로 확인해야 합니다.

3. 사전 검사를 실행합니다.

   ```bash
   python3 main.py doctor --directory local/mac --engine "$PWD/local/bin/sing-box"
   ```

   `warp-cli`를 못 찾으면 `--warp-cli /실제/warp-cli/경로`를 추가합니다. macOS 앱 내부의 일반 경로와 PATH를 자동으로 확인합니다. 검사는 엔진 버전·설정, OS, CLI의 `Mode: WarpProxy`, SOCKS5 응답과 WARP HTTPS를 확인합니다. **사전 검사 성공은 Riot 영상 재생이나 게임 직접 연결의 증명이 아닙니다.** 알 수 없는 CLI 출력은 통과시키지 않습니다.

4. 관리자 권한으로 전경 실행합니다. CLI를 실행한 터미널은 유지합니다.

   ```bash
   sudo "$(command -v python3)" main.py run \
     --directory "$PWD/local/mac" \
     --engine "$PWD/local/bin/sing-box"
   ```

   CLI의 `run`은 이미 연결된 프록시를 사용하며, 앱의 `시작`은 그 전에 `warp connect`를 자동 실행합니다. 게임 시작/종료에 따른 WARP 전환은 없습니다. 엔진 로그에서 Riot/League 클라이언트와 웹 Helper는 `outbound/socks[warp]`, 게임은 `outbound/direct[direct]`인지 확인합니다. 프로세스 이름과 클라이언트 번들 경로 모두 매칭되지 않으면 기본 직접 경로로 갑니다.

5. 종료는 **Ctrl+C**입니다. CLI의 `run`을 Ctrl+C로 종료하면 엔진만 중지합니다. GUI의 중지·종료는 추가로 `warp restore`를 호출해 WARP UDP 모드에 복귀합니다. sing-box가 자신의 임시 라우트를 정리하도록 정상 종료를 전달하며, 10초 내 종료되지 않으면 강제 종료 후 경로 점검을 안내합니다. **macOS 27.1.1의 실제 복구 결과는 실기 확인이 필요합니다.** 강제 종료·전원 차단 후 자동 복구까지 검증된 제품은 아닙니다.

   ```bash
   route -n get default
   netstat -rn
   scutil --dns
   ```

   실행 전후 결과와 실제 인터넷 연결을 비교합니다. 다른 VPN/네트워크 서비스나 방화벽 전체를 초기화하지 않습니다. 현재 프로필이 실행 중이면 설정 재생성을 거부합니다.

## 설정 변경

`local/mac/profile.json`을 편집한 뒤, 종료된 상태에서 다음을 실행합니다.

```bash
python3 main.py render --directory local/mac
python3 main.py doctor --directory local/mac --engine "$PWD/local/bin/sing-box"
```

| 필드 | 의미 |
|---|---|
| `proxy_port` | WARP 앱과 일치하는 로컬 SOCKS 포트 |
| `physical_interface` | 기본은 자동 감지. 필요하면 실측한 물리 인터페이스 지정. `en0`이라고 가정하지 않음 |
| `mtu` | 기본 1500, 허용 1280~1500. TUN MTU이며 WARP 외부 터널 MTU가 아님 |
| `extra_clients` | 추가할 **정확한 실행 파일 이름**. 게임 실행 파일은 추가 불가 |
| `game_cidrs` | 기본 빈 목록. 실제 게임 연결에서 확인한 공개 IP의 `/32` 또는 `/128`만 허용 |

실행 파일 경로를 확인하려면 `ps -axo comm`을 사용합니다. 전체 실행 인수에는 인증 정보가 포함될 수 있으므로 수집하지 않습니다. 프로세스 이름 규칙은 프로그램의 서명/신원을 검증하는 보안 경계가 아닙니다.

`game_cidrs`는 선택 기능입니다. 정확한 게임 IP가 확인됐을 때 그 목적지는 TUN 자체에서 제외할 수 있습니다. **고정 Riot IP나 포트 표로 서버 주소를 만들어 넣지 않습니다.** 해당 IP를 클라이언트와 공유하면 클라이언트 연결도 직접 경로가 되므로, 기본값을 유지하는 편이 낫습니다. 새 게임의 서버 IP가 달라지면 기존 제외 항목은 그 서버에 적용되지 않습니다. CIDR 허용 예시의 주소는 실제 Riot 서버 목록이 아닙니다.

## 제한 사항

alpha.4는 빈 클라이언트 홈/영상의 원인 후보인 **누락된 CEF Helper 경로**를 추가했습니다. 클라이언트 번들의 웹/렌더러/네트워크 Helper TCP를 WARP로 보내고, 해당 Helper의 QUIC/UDP는 즉시 거부해 HTTPS/TCP 폴백을 유도합니다. Safari 등 일반 브라우저는 일괄 터널링하지 않습니다. 콘텐츠가 여전히 비면 로그의 Helper 실제 경로와 `warp` 매칭을 확인해야 하며, CDN·코덱·DRM 등 다른 원인은 별도 진단이 필요합니다. Linux 테스트로 실제 Riot 영상 재생 성공을 확인한 것은 아닙니다.

- WARP SOCKS의 UDP 지원을 가정하지 않습니다. 지정된 **클라이언트의 UDP는 명시적으로 거부**합니다. QUIC은 TCP로 폴백할 수 있지만 보장할 수 없고, 음성 등 UDP 기능은 동작하지 않을 수 있습니다. 게임 실행 파일의 UDP에는 이 규칙이 적용되지 않습니다.
- 게임이 직접 연결에서도 막히는 학교라면 이 구조로 게임 접속을 해결할 수 없습니다. 전체 터널로 자동 전환해서 숨기지 않습니다.
- Windows 게임의 Vanguard 호환성, macOS 권한/네트워크 확장 충돌, Riot 실행 파일 이름 변경, IPv6 및 실제 종료 복구는 실기 검증 항목입니다.
- 다른 전체 터널 VPN, v4 DNS/방화벽 변경, 기존 프록시가 남아 있으면 경로가 충돌할 수 있습니다. v5는 기존 v4 설정을 임의로 복구하거나 덮어쓰지 않습니다.
- 일반 트래픽도 TUN을 통과하므로 로컬 오버헤드는 실측해야 합니다. 프로세스 분류 실패 시 기본 직접 경로이고, 항상 클라이언트 터널을 보장하는 정책은 아닙니다.

## 검증·지연 측정

```bash
python3 -m unittest discover -s tests -v

# 실제 엔진 설정 검사와 로컬 SOCKS 체인 검사도 실행하려면:
SCHOOLNET_TEST_ENGINE="$PWD/local/bin/sing-box" \
  python3 -m unittest discover -s tests -v

# 직접/프록시의 같은 IP까지 TCP 연결 시간을 비교 (사용할 공개 호스트를 지정):
python3 main.py benchmark --host example.com --port 443 --samples 5
```

벤치마크는 로컬 DNS로 목적지를 한 번 정한 후 같은 IP에 교대로 연결합니다. `median_ms`, `p95_ms`, 연속 측정값 차이와 연결 실패율을 기록합니다. **게임 RTT·UDP 손실률·FPS 측정이 아닙니다.** `direct`도 일반 OS 소켓이라는 뜻이므로 다른 VPN이 켜져 있으면 실제 물리 직접 경로라고 단정할 수 없습니다. DNS 조회 자체의 시간은 제외합니다.

학교에서의 성공 판정과 성능 기준은 [실기 검증 계획](docs/NATIVE_VALIDATION.md), 원리와 출처는 [설계 판단](docs/DESIGN.md)을 확인하세요. Linux에서 통과한 자동 테스트로 학교 접속 성공을 대신하지 않습니다.

## Windows

Python과 개인용 WARP 설치 후 `python install_engine.py`, `python main.py init --directory local/windows --platform windows`를 실행합니다. `doctor`에 `--engine`으로 `local/bin/sing-box.exe`를 지정하고, 관리자 터미널에서 `run`을 실행합니다. macOS와 같은 Local proxy 구성이 필요합니다. 이는 설정·CLI 지원이며 **Windows 실행 검증 완료를 의미하지 않습니다**.

sing-box는 별도 설치되는 GPL-3.0 프로젝트입니다. upstream의 라이선스와 릴리스 조건은 [공식 저장소](https://github.com/SagerNet/sing-box)를 따릅니다. 이 저장소에는 엔진 바이너리를 포함하지 않습니다.

## MINER DELTA UI (Delta v2.1)

원본 계획서와 확정 자산은 `macos/design/DESIGN_SPEC.md`, `macos/design/README.md`, `macos/design/assets/`에 보존했습니다. `preview/index.html`의 가상 연결 타이머는 사용하지 않습니다. UI의 다섯 노드는 실제 CLI 지원 확인·프록시 준비·TLS 확인·관리자 승인·엔진 프로세스 실행 결과로만 진행합니다. 엔진 실행은 실제 게임 접속 성공을 뜻하지 않습니다.

Delta의 최우선 명세는 `macos/delta/UPGRADE_SPEC.md`입니다. 전체 창 560×610pt, 최소 520×570pt이며 네이티브 신호등·드래그·크기 조절은 유지하고 제목 표시줄 표면만 숨깁니다. 시스템 소재 위에 투명 지층을 올리고 시작·중지를 세로로 배치했습니다. 기존 캐릭터·학교·아이콘·한국어 문구와 실제 다섯 개의 얇은 진행 막대를 보존했습니다.

초록 시작·빨강 중지 파동은 요청 피드백입니다. 성공 빛·중앙 SF 체크·배경 블러는 실제 전체 엔진 실행 상태에서 한 번 재생하고 복원하며, WARP-only 준비에는 재생하지 않습니다. 중지·오류·비활성화는 성공 연출을 취소합니다. 동작 줄이기에서는 입자·흔들림·블러를 제거하고 투명도 줄이기에서는 불투명 네이비를 사용합니다. 로그·설정·제거·도움말은 기존 도구에 유지합니다.

macOS CI는 네트워크를 실행하지 않는 네이티브 UI fixture로 기본/최소 크기, 영문, WARP-only, 전체 성공/복원, 중지·오류 취소와 접근성 모드를 검증합니다. 앱 자체 뷰의 PNG와 결과는 빌드 진단에 보관합니다. 이는 학교·WARP·게임의 실제 연결 검증을 대신하지 않습니다.

앱 파일·실행 파일·Dock 이름은 **MINER**입니다. 기존 설치를 중지·종료한 뒤 `/Applications/MINER.app`으로 설치하세요. 이전 SchoolNet 앱을 동시에 실행하지 마세요. 사용자 프로필·지원 파일·서비스 식별자는 기존 데이터 호환성을 위해 유지합니다.

명시적인 UDP 복귀 명령: `python3 main.py warp restore`. 설치된 CLI가 `mode warp`를 지원하고 실제 settings가 `Mode: Warp`, status가 Connected인 경우에만 복귀 성공으로 표시합니다. 다른 이름을 쓰는 WARP 버전은 설정을 확인해야 합니다. 지원 파일 경로와 서비스 식별자는 구버전 호환성을 위해 유지합니다.

## BETA 아이콘 · 개발자 소개

`macos/design/MINER-BETA.icon/`에 제공된 원본을 보존하고, 밝은 기본 배경과 원본 레이어 크기·이동 값을 반영한 1024px ICNS 호환 PNG를 사용합니다. 기존 앱 내부 캐릭터는 변경하지 않습니다.

설정(⌘,)의 개발자 소개에는 GitHub 공개 프로필의 **Punkthats*it · @hexagon0401**, 이미지와 프로필 링크를 표시합니다. `macos/design/assets/developer-profile.json`이 프로필 정보의 원본이며, 빌드 시 이미지를 앱에 포함하고 해시를 검증 JSON에 기록합니다. 앱 실행 중에는 프로필 이미지를 요청하지 않습니다.

BETA 릴리스는 실제 DMG 첨부 여부를 확인하세요. 베타 1은 별도 지속 재시도 작업에서 고정 소스·정상 실행 작업을 보존하며, 검증된 DMG 게시 후 새 빌드를 중단합니다.

## 베타 2 학교 현황

설정의 학교 현황에서 내 기기/전국 공유를 구분하고, 별도 상세 창에서 지역·학교명·학교급·초록/빨강 깃발을 검색합니다. 개인 성공은 즉시 반영하지만 전국 공유는 검토 승인 후 반영합니다. 90일이 지나도 누적 성공은 유지하며 오래된 기록과 마지막 확인일을 보여줍니다.

공식 전체 학교 명부는 아직 필요합니다. API 키 없이 받은 샘플은 사용하지 않았으며 전체 수를 임의로 채우지 않습니다. 공유 서버도 미개방입니다. [데이터·인증·로컬 서버 안내](community/README.md), [남은 사용자 작업](docs/BETA2_HANDOFF.md)을 참고하세요.

개발용 네이티브 검증은 `python3 macos/build.py --arch arm64 --validation-only`입니다. 배포용 DMG는 기본적으로 전체 공식 명부를 요구합니다. 명시적인 `--allow-incomplete-catalog`은 로컬 개발용이며 전국 현황 완성본으로 게시하지 않습니다.

베타 1 지속 재시도는 별도 workflow에서 고정 소스만 사용합니다. 이미 검증된 베타 1 DMG가 있으면 재시도하지 않습니다. 베타 2 명부·공유 서버 준비가 베타 1 배포를 막지 않습니다.
