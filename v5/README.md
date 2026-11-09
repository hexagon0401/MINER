# MINER ALPHA v1.2.1 — 소스·연결 구조

[설치 파일·한국어 설치 안내](../README.md#다운로드) · [릴리스](https://github.com/hexagon0401/MINER/releases/tag/miner-alpha-v1.2.1) · [서명 설정](docs/SIGNING.md)

macOS는 SwiftUI·AppKit, Windows는 Qt Quick·Fluent/Pearl White UI를 유지합니다. 개인용 Cloudflare WARP는 별도 설치·등록해야 합니다. ALPHA는 제품 세대의 코드명입니다. 기존 버전·베타 소스와 릴리스는 보존합니다.

## v1.2.0 연결 구조

```text
지정된 Riot 도메인 A/AAAA 질의
  → 로컬 DNS → 영속 매핑된 가상 주소
  → Riot TCP → 선택 TUN → SOCKS5 원격 호스트 이름 → WARP → 목적지

일반 웹·카카오톡·실제 게임 서버 IP
  → OS의 원래 물리 네트워크 경로 (TUN 우회)

일반 DNS
  → 로컬 엔진 → DNS 전용 bounded relay → 원래 연결의 DNS 서버
```

전체 기본 경로를 TUN으로 보내지 않습니다. `198.18.0.0/15`, `fdfe:dcba:9876:1000::/64`의 가상 주소만 선택 경로로 등록하고, TUN 자체 DNS 주소는 `172.30.255.2`, `fdfe:dcba:9876::2`입니다. 지정된 Riot 도메인은 `schoolnet/config.py`의 `RIOT_DOMAINS`에서 관리합니다. 실제 게임 IP와 일반 앱의 패킷은 Python이나 TUN을 통과하지 않습니다. Python은 구성·감시·DNS 전달을 담당하며 게임 프로세스·메모리를 조작하지 않습니다.

로그인부터 인게임·종료 후 통계창까지 **MINER와 WARP를 켜 두세요.** 게임 단계에 따라 WARP를 전환하지 않습니다. 건강한 프록시는 재설정하지 않고, 같은 프록시 모드에서 연결이 끊기면 `connect`만 재시도합니다. 다른 모드로 외부 변경되면 오류를 표시합니다. 모든 지연·Wi-Fi 손실의 해결을 보장하지 않습니다.

Riot 가상 주소 TCP는 실행 파일명에 의존하지 않고 WARP로 보냅니다. 게임 프로세스의 직접 경로 예외가 먼저 적용되고, 가상 주소 UDP는 거부합니다. 이름이 지정 범위 밖인 클라이언트 서비스나 브라우저 자체 DoH는 이 도메인 경로에 해당하지 않을 수 있습니다. SOCKS 대상의 DNS는 WARP에 맡기며 실패 시 직접 연결로 자동 전환하지 않습니다. 일반 DNS는 기존 연결의 신뢰·암호화 수준을 유지하며 새 공개 DNS로 대체하지 않습니다.

## DNS 변경과 복구

macOS의 활성 네트워크 서비스와 Windows의 활성 어댑터를 찾아 **원래 DNS·DHCP/수동 여부를 먼저 기록**합니다. DNS 전용 전달기와 엔진의 준비 확인 후 활성 연결의 DNS만 변경합니다. 중지할 때는 DNS를 복구한 뒤 엔진을 종료합니다. 다른 어댑터·VPN·방화벽 전체를 초기화하지 않습니다. 사용자가 외부에서 DNS를 완전히 바꿨으면 해당 설정을 덮어쓰지 않습니다. 일부 임시 값만 남은 모호한 상태는 오류와 복구 기록을 유지합니다.

- macOS: root 소유 프로필의 `network-dns-v1.json`. 승인 재사용 여부와 관계없이 복구 도우미를 설치하며, 엔진 비정상 종료 후 확인·복구합니다. 부팅 후 대기하지만 엔진/WARP 자동 연결은 하지 않습니다. 재사용 시 mutable 앱 번들 대신 root 소유의 설치된 런타임만 실행합니다.
- Windows: 관리자/SYSTEM 전용 `%ProgramData%\MINER-Privileged-Recovery\network-dns-v1.json`. 별도 프로세스가 부모/엔진 종료를 감시합니다. Job Object는 잔류 엔진을 정리하고 감시 프로세스는 DNS를 복구합니다.
- 복구 실패 시 기록을 지우지 않습니다. 다음 실행에서 재시도하며 성공 여부를 임의로 표시하지 않습니다. 재부팅·네트워크 변경·외부 VPN 충돌은 별도 복구가 필요할 수 있습니다.

macOS에서는 설정의 **관리자 승인 항상 허용 · 도우미 재사용**을 켜면 설치·도우미 업데이트 시 한 번 승인하고 시작·중지에 재사용합니다. 비밀번호를 저장하지 않습니다. 해제하면 매 연결을 인증합니다. 앱 제거는 관리 중인 도우미·설정·로그도 삭제하며 WARP와 이전 v1~v4는 보존합니다.

## 빌드·검증

배포 워크플로는 [miner-alpha-v121.yml](../.github/workflows/miner-alpha-v121.yml)입니다. Mac Apple Silicon·Intel과 Windows의 필수 검사가 모두 통과해야 새 정식 태그로 게시합니다. 서명·공증 설정이 있으면 그 검증도 필수입니다. 미설정 Mac은 ad-hoc, Windows는 Authenticode 미서명입니다.

```bash
cd v5
python3 install_engine.py
PYTHONPATH=. SCHOOLNET_TEST_ENGINE="$PWD/local/bin/sing-box" python3 -m unittest discover -s tests -v
```

Python 3.10+의 공통 로직은 표준 라이브러리, 앱 업데이트는 certifi를 사용합니다. 패키징은 Python 3.12이며 GUI/패키징 의존성은 각 워크플로에 고정합니다. 엔진은 SHA-256을 확인한 **sing-box 1.12.0**만 사용합니다. 임의 최신 엔진으로 바꾸지 마세요.

`selective_smoke.py`는 **일회용 네이티브 CI 호스트 전용 관리자 검사**입니다. 실제 선택 경로·OS DNS/HTTPS·동일 Riot TCP의 원격 이름 전달·DNS 정상/엔진 강제 종료 복구를 확인합니다. SOCKS는 로컬 시험 서버이며 실제 WARP가 아닙니다. Windows는 이전 공개 v1.1.1 설치 파일의 체크섬을 확인하고 같은 위치에 덮어써 사용자 데이터 보존을 검사합니다. Mac은 DMG 마운트→복사 후 서명 무결성과 네이티브 UI·도우미 root 피어 인증을 확인합니다.

Windows 자동 검증은 **Windows Server 2025**입니다. 실제 Windows 11·학교망·개인용 WARP·LoL·Vanguard·macOS 27.1.1 Arc/게임 호환성은 미검증입니다. UI PNG는 검사용 상태 주입이며 네트워크 성공 증거가 아닙니다. 검증 JSON과 SHA-256을 릴리스에 첨부합니다.

## 프로필과 CLI

`profile.json`의 `proxy_port`, `mtu`(1280~1500), `physical_interface`를 검증합니다. `dns_forward_port`는 시작 시 로컬 임시 포트로 갱신합니다. `extra_clients`는 구버전 파일 호환을 위해 읽지만 **v1.2.0의 선택 범위를 확장하지 않습니다.** 추가 대상은 검증된 도메인 규칙으로 개발해야 합니다. `game_cidrs`는 실측한 공개 호스트 `/32`·`/128`만 허용하며 일반 실제 IP는 이미 TUN 밖이므로 보통 불필요합니다.

```bash
python3 main.py init --directory local/mac --platform macos
python3 main.py warp connect --proxy-port 40000
python3 main.py doctor --directory local/mac --engine "$PWD/local/bin/sing-box"
```

`doctor`는 엔진 구성·플랫폼·WARP 프록시·TLS를 확인하지만 게임/미디어 성공을 증명하지 않습니다. 앱 실행을 권장합니다. 고급 CLI `run`도 임시 DNS를 바꾸므로 강제 종료하지 말고 Ctrl+C로 정상 종료하세요. GUI의 중지/종료는 추가로 `warp restore`를 호출해 UDP Traffic and DNS를 확인합니다. 다른 전체 VPN과 동시에 사용하지 마세요.

## 업데이트·이력

설정에서 업데이트를 확인하고 연결 중지 후 설치합니다. v1.2.0은 실행 후 및 6시간마다 확인해 앱에 알리며 설정에서 끌 수 있습니다. 이전 v1.1.1에는 자동 확인 기능이 없어 최초 수동 업데이트가 필요합니다. 삭제하지 않고 Windows Setup.exe 덮어쓰기·Mac 앱 교체·Homebrew 업그레이드를 사용할 수 있습니다.

[앱 사용 안내](macos/사용%20안내.txt) · [Windows 빌드·UI](windows/README.md) · [네이티브 검증 안내](docs/NATIVE_VALIDATION.md) · [서명 안내](docs/SIGNING.md)

개발자 소개는 번들에 포함한 GitHub 공개 프로필·이미지를 사용합니다. 정식/베타 아이콘 원본과 선택 규칙은 [아이콘 패키징 안내](../packaging/icons/README.md)에 보존합니다.

베타 2 학교 현황·진단·제보 기능은 [보관 태그](https://github.com/hexagon0401/MINER/tree/archive/betas/beta2-ui-before-1.1.1)의 소스입니다. 현재 정식 UI·DMG에는 포함되지 않습니다. [커뮤니티 보관 안내](community/README.md) · [남은 사용자 작업](docs/BETA2_HANDOFF.md). 기존 릴리스와 태그는 덮어쓰지 않습니다.

## v1.2.1 업데이트 설치·정리

설정의 Check for Updates로 확인하고 연결 중지 후 설치합니다. Mac 직접 설치는 앱 바깥에 준비한 검증 작업자가 부모 종료를 기다린 뒤 DMG의 식별자·버전·서명 무결성을 확인하고 교체합니다. 새 창 시작 확인 후 이전 앱/설치 캐시를 제거합니다. Windows는 기존 등록 설치 경로에서 런타임을 임시 보관하고 깨끗한 새 런타임을 설치하며 실패 시 복구합니다. 성공 후 설치 파일을 정리하고 재실행합니다. 사용자 설정·로그는 보존합니다. 전용 캐시는 현재 버전 이하의 알려진 설치 파일만 정리합니다. 네트워크 엔진은 v1.2.0과 같습니다.
