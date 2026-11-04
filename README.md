# MINER

**Dig your way out. — 학교 네트워크의 벽을 넘어.**

## 개요

학교에서는 리그 오브 레전드(LoL)를 비롯한 게임의 접속과 플레이를 네트워크에서 제한합니다. MINER는 이러한 제한을 기술적으로 파훼하고, 대한민국 교육청을 통해 학교에 제공되는 **스쿨넷 환경의 게임 접속 차단을 회피·돌파하는 것**을 목표로 시작한 프로젝트입니다.

단순히 접속만 되는 것으로는 충분하지 않습니다. 클라이언트 로그인·다운로드는 되지만 게임 중 지연이 커지거나, 게임이 끝난 뒤 클라이언트를 다시 실행해야 하는 불편함도 해결하려 합니다. 이를 위해 클라이언트 통신은 WARP로 보내고 게임 플레이 통신은 직접 연결하는 분리 라우팅을 사용합니다. **접속 가능성과 함께 게임 지연 및 컴퓨터 성능에 주는 영향을 줄이는 것**이 개발의 핵심입니다.

현재는 macOS와 개인용 Cloudflare WARP를 중심으로 개발합니다. 전국 모든 학교에서의 작동을 보장하는 단계는 아니며, 학교별 네트워크 설정에 따라 결과가 달라질 수 있습니다.

## 배포 버전

| 버전 | 상태 |
|---|---|
| **베타 1.1** | [Apple Silicon DMG 다운로드](https://github.com/hexagon0401/MINER/releases/download/v5.0.0-beta.1.1/MINER-v5.0.0-beta.1.1-macOS-AppleSilicon.dmg) · 베타 1 기반, 땅굴 모양 개선 · UI·서명 무결성·설치 복사 검증 완료 |
| **베타 1 유지 보수** | [`beta1-maintenance` 브랜치](https://github.com/hexagon0401/MINER/tree/beta1-maintenance)에서 개발을 이어갑니다. |
| **베타 2** | 학교 현황·로컬 진단·제보 기능의 소스만 보관합니다. 현재 배포용 DMG에는 포함되지 않습니다. |
| 공유 제보 서버 | 아직 개방하지 않았습니다. |
| Homebrew | 배포 준비 단계입니다. 현재는 위 DMG로 설치해 주세요. |

[프리릴리스 페이지](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1.1)에서 배포 파일과 검증 정보를 확인할 수 있습니다.

## 설치

### macOS

1. 개인용 [Cloudflare WARP](https://one.one.one.one/)를 설치하고 최초 등록을 마칩니다.
2. 위의 **Apple Silicon DMG**를 다운로드해 엽니다.
3. 왼쪽의 `MINER.app`을 오른쪽의 **Applications(응용 프로그램)** 폴더로 드래그합니다.
4. 응용 프로그램 폴더에서 `MINER.app`을 실행합니다.

#### 처음 실행할 때 macOS에서 차단되는 경우

현재 배포본은 **ad-hoc 서명이며 Apple 공증이 적용되지 않았습니다.** 처음 실행하면 아래 순서로 앱 실행을 허용해야 할 수 있습니다. MINER 공식 릴리스에서 받은 파일인지 확인한 뒤 진행해 주세요.

**1. 실행 차단 창 닫기**

`“MINER.app” Not Opened`(MINER.app을 열지 못함) 창이 나타나면 **Done(완료)**을 누릅니다. **Move to Trash(휴지통으로 이동)**는 누르지 않습니다.

<img src="docs/images/macos-install/01-app-blocked.png" alt="macOS에서 MINER.app의 첫 실행을 차단한 창" width="460" />

**2. 시스템 설정에서 실행 허용**

**시스템 설정 → 개인정보 보호 및 보안 → 보안**으로 이동합니다. `“MINER.app” was blocked to protect your Mac` 안내 옆의 **Open Anyway(확인 없이 열기)**를 누릅니다. 항목이 보이지 않으면 응용 프로그램 폴더에서 MINER를 한 번 실행한 뒤 설정을 다시 확인합니다.

<img src="docs/images/macos-install/02-privacy-security.png" alt="개인정보 보호 및 보안 설정의 Open Anyway 버튼" width="760" />

**3. 최종 확인 창에서도 실행 허용**

`Open “MINER.app”?` 확인 창이 나타나면 여기서도 **Open Anyway(확인 없이 열기)**를 누릅니다. macOS에서 암호나 Touch ID 인증을 요구하면 인증합니다. 이후 MINER 창이 열립니다.

<img src="docs/images/macos-install/03-open-anyway.png" alt="최종 실행 확인 창의 Open Anyway 버튼" width="460" />

macOS 버전과 표시 언어에 따라 버튼 이름이나 화면 구성은 조금 다를 수 있습니다. `앱이 손상되어 열 수 없습니다`처럼 다른 오류가 표시되는 경우에는 이 안내와 다른 문제일 수 있으므로 오류 문구를 확인해 주세요.

## 사용 방법

1. 기존 SchoolNet 또는 MINER가 실행 중이면 먼저 중지하고 종료합니다.
2. MINER에서 **시작**을 누릅니다. 앱이 WARP CLI로 Local Proxy 모드를 준비하고 `127.0.0.1:40000` 연결을 확인한 뒤 분리 라우팅을 시작합니다.
3. 클라이언트의 TCP 통신은 WARP 경로로, 게임 실행 파일과 나머지 트래픽은 직접 경로로 보냅니다. 진행 막대는 실제 백엔드 상태에 따라 표시됩니다.
4. **중지** 또는 앱 종료 시 엔진을 정리하고 WARP를 **UDP — Traffic and DNS** 모드로 복귀시킵니다. 실패하면 앱에 표시되는 오류를 확인합니다.
5. **⌘,**로 설정을 열어 한국어·영어 변경, 개발자 소개, 제거 기능을 사용할 수 있습니다.

## 현재 검증 범위

베타 1.1은 자동 테스트 59개, macOS 네이티브 UI 검사 22개, DMG 설치 복사 후 앱 서명 무결성 검증을 통과했습니다. 학교망에서의 실제 게임 지연·프레임·클라이언트 영상 재생과 WARP 복귀는 사용자 환경에서 별도로 확인해야 합니다. 프록시 HTTPS 진단 성공이 실제 게임 플레이나 특정 학교에서의 작동을 증명하지는 않습니다.

베타 2 소스의 초록 깃발은 과거 성공 기록이 있음을, 빨강 깃발은 성공이 아직 확인되지 않았음을 뜻합니다. 내 기기의 기록과 운영자가 승인한 공유 기록은 구분하며, 전국 학교 통계와 공유 제보 서비스는 현재 제공하지 않습니다.

## 개발 안내

- [v5 설치·기술 안내](v5/README.md)
- [학교 데이터·진단·제보 시스템](v5/community/README.md)
- [베타 2 인계 및 남은 작업](v5/docs/BETA2_HANDOFF.md)
- [Homebrew 배포 준비](packaging/homebrew/README.md)
- [Apple 서명·공증 설정](v5/docs/SIGNING.md)
- [개인 Mac 빌드 러너 준비](v5/docs/SELF_HOSTED_MAC.md)

개발자: [Punkthats*it · @hexagon0401](https://github.com/hexagon0401)

이전 v1~v4는 개발 이력으로 보존합니다. v5 설치·제거는 WARP나 이전 버전을 삭제하지 않습니다.
