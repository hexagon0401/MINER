# SchoolNet v5 — 분리 연결 실험판

**macOS 우선, CLI 중심의 `5.0.0-alpha.1`입니다.** 개인용 WARP의 Local proxy와 sing-box TUN을 연결해, Riot/LoL **클라이언트 TCP는 WARP**, **게임 실행 파일과 나머지 트래픽은 직접 경로**로 보냅니다. 게임 시작/종료 때 WARP를 전환하지 않습니다. UI는 만들지 않았습니다.

사용자가 제공한 환경은 **개인용 WARP / macOS 27.1.1**입니다. 개발·자동 검증 환경은 Linux이므로 해당 macOS 버전의 실제 호환성, 학교에서의 연결 성공, 게임 핑 개선은 **아직 검증되지 않았습니다**. Windows용 설정도 생성하지만 Windows 네이티브 동작은 미검증입니다. 기존 v1~v4는 변경하지 않습니다.

## DMG 앱 설치·제거

GitHub의 `v5.0.0-alpha.*` **사전 릴리스**에서 Apple Silicon 또는 Intel DMG를 선택합니다. 앱을 **Applications로 드래그**한 뒤 실행하면 됩니다. Python과 엔진이 포함되어 있습니다. 개인용 WARP는 별도로 설치하고 Local proxy·포트 40000으로 연결하세요.

앱의 **사전 점검 → 시작**으로 실행하고 **중지**로 종료합니다. 시작·중지·제거 때 macOS 관리자 인증을 사용합니다. **제거** 버튼은 실행을 중지하고 v5 지원 파일·사용자 설정·로그를 삭제한 뒤 앱을 휴지통으로 옮깁니다. WARP와 기존 v1~v4는 유지합니다. 제거 전에 필요한 로그를 복사하세요. 부팅 자동 시작 항목은 설치하지 않습니다.

이 alpha 앱은 **ad-hoc 서명이고 Apple Developer ID 서명·공증은 없습니다**. macOS가 실행을 제한할 수 있으며, 출처를 확인한 뒤 시스템 설정의 해당 앱 열기 절차가 필요할 수 있습니다. Gatekeeper를 전역 해제하는 절차는 사용하지 않습니다.

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

2. WARP 앱의 **Preferences → Advanced → Configure Proxy**에서 포트를 **40000**으로 정하고 **Local proxy** 모드로 연결합니다. Cloudflare 문서상 데스크톱 지원 기능입니다. 실제 설치 버전에서 메뉴가 없거나 CLI가 다르면 그 상태를 먼저 확인해야 합니다. 일반 **Traffic and DNS 전체 터널 모드와 함께 실행하지 않습니다**. 이 초기 전환 뒤 클라이언트는 한 번 새로 시작해야 합니다.

3. 사전 검사를 실행합니다.

   ```bash
   python3 main.py doctor --directory local/mac --engine "$PWD/local/bin/sing-box"
   ```

   `warp-cli`를 못 찾으면 `--warp-cli /실제/warp-cli/경로`를 추가합니다. macOS 앱 내부의 일반 경로와 PATH를 자동으로 확인합니다. 검사는 엔진 버전·설정, OS, CLI의 `Mode: WarpProxy`, SOCKS5 응답을 확인합니다. **사전 검사 성공은 학교 접속 성공이나 게임 직접 연결의 증명이 아닙니다.** 알 수 없는 CLI 출력은 통과시키지 않습니다.

4. 관리자 권한으로 전경 실행합니다. CLI를 실행한 터미널은 유지합니다.

   ```bash
   sudo "$(command -v python3)" main.py run \
     --directory "$PWD/local/mac" \
     --engine "$PWD/local/bin/sing-box"
   ```

   WARP를 켜고 끄는 자동화는 없습니다. 엔진 로그에서 Riot/League 클라이언트 연결은 `outbound/socks[warp]`, 게임 연결은 `outbound/direct[direct]`인지 확인한 뒤 연습 모드에서 시험합니다. 프로세스 이름이 매칭되지 않으면 기본 직접 경로로 갑니다. 접속 실패를 무조건 DPI 차단으로 해석하지 마세요.

5. 종료는 **Ctrl+C**입니다. v5는 자신이 실행한 엔진만 종료하고 WARP Local proxy는 유지합니다. sing-box가 자신의 임시 라우트를 정리하도록 정상 종료를 전달하며, 10초 내 종료되지 않으면 강제 종료 후 경로 점검을 안내합니다. **macOS 27.1.1의 실제 복구 결과는 실기 확인이 필요합니다.** 강제 종료·전원 차단 후 자동 복구까지 검증된 제품은 아닙니다.

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
