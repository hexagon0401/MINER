# MINER 베타 1 — Windows

macOS 베타 1.1의 공통 엔진과 디자인 에셋을 사용하는 Windows x64 버전입니다. 베타 2 기능은 포함하지 않습니다.

## 설치와 사용

개인용 Cloudflare WARP를 먼저 설치하고 등록합니다. GitHub 프리릴리스의 Windows x64 Setup.exe로 설치합니다. 관리자 권한 승인이 필요하며, Python·Qt·sing-box는 함께 제공됩니다.

시작 버튼은 `warp-cli`를 PATH 또는 `Program Files\Cloudflare\Cloudflare WARP`에서 찾고, Local Proxy 40000 설정과 SOCKS 원격 DNS/TLS 검증 후 TUN 엔진을 시작합니다. 5단계 표시는 실제 확인 결과를 따릅니다. Riot/LoL 클라이언트 TCP는 WARP, 게임 실행 파일의 통신은 직접 경로를 사용합니다. 프록시 실패 시 클라이언트를 직접 경로로 자동 전환하지 않습니다.

중지·종료는 엔진에 CTRL_BREAK를 보내 정상 종료를 기다린 뒤 WARP를 UDP Traffic and DNS로 복귀시킵니다. 실패하면 창에 오류를 남기고 중지 버튼으로 복귀를 재시도할 수 있습니다. 작업 관리자 강제 종료나 전원 차단 후 복구는 보장하지 않습니다.

설정은 Ctrl+,로 열며 한국어/영어와 개발자 소개를 제공합니다. 제거는 MINER에서 중지·종료 후 Windows 설치된 앱에서 진행합니다. 사용자 설정과 로그는 `%LOCALAPPDATA%\MINER\Beta1`에 남깁니다. WARP는 제거하지 않습니다.

## 소스 빌드

Windows x64, Python 3.12, Inno Setup 6에서 저장소의 `v5` 디렉터리를 기준으로 실행합니다.

```powershell
python -m pip install PySide6==6.8.3 pyinstaller==6.22.3 certifi==2026.10.23 Pillow==11.3.0
python windows/build.py
```

빌드는 관리자 권한 환경이 필요합니다. 체크섬으로 공식 엔진을 확인하고, 기본 경로를 변경하지 않는 실제 Windows TUN 생성/종료, 내장 UI 셀프 테스트, 실제 설치·제거를 실행한 뒤 배포 파일과 검증 JSON을 만듭니다. CI는 `.github/workflows/miner-windows.yml`입니다.

실제 WARP 연결·학교망·LoL/Vanguard 호환성·핑과 프레임은 자동 UI 검사의 범위가 아니며 실기 테스트가 필요합니다. 현재 Windows 실행 파일은 Authenticode 서명이 없습니다.

## Windows 현지화와 베타 1 수정

| macOS | Windows |
|---|---|
| SwiftUI·AppKit | PySide6·Qt, Windows 기본 제목 표시줄 |
| ⌘, | Ctrl+, 및 설정 버튼 |
| 앱 번들·DMG | Program Files 설치, Setup.exe·Windows 설치된 앱에서 제거 |
| Unix 권한·신호 | UAC, Windows byte-range lock·CTRL_BREAK·Job Object |
| macOS 지원 폴더 | LocalAppData의 설정·로그·미완료 연결 기록 |
| 시스템 동작 줄이기 | Windows 애니메이션 설정과 앱 동작 줄이기 |

파일 잠금 전에 잠긴 바이트를 읽던 오류를 수정했습니다. 공통 TLS 경로 검사는 Windows 경로 표현도 검증하고, macOS 서비스·공증 계약은 POSIX CI에서 유지합니다. 미완료 세션은 다음 실행에서 WARP 복귀를 재시도하도록 안내합니다. 중복 작업과 종료 중 재연결을 막습니다.

Mac 디자인 에셋을 재사용하되 캐릭터 비율을 유지합니다. 밝은/어두운/시스템 테마, 고대비, 작은 창과 화면 배율에 대응하며 설정창도 언어 변경을 즉시 반영합니다. 채굴 효과는 최대 30fps이고 비활성·최소화·연결 완료 시 멈춥니다. 시작·중지 파동과 성공 체크는 실제 백엔드 상태와 분리되어 진행률을 조작하지 않습니다.

배포 스크린샷과 GIF는 **실제 패키징 EXE의 UI 검증 화면**입니다. 표시한 연결 상태는 테스트 주입 값이며 WARP나 게임 접속 성공의 증거가 아닙니다. Windows Server CI에서 검사하며 Windows 11 실기·학교망·LoL·Vanguard는 미검증입니다.

## Windows UI 엔진 — build 7

화면은 Qt Widgets에서 **Qt Quick RHI + FluentWinUI3 스타일**로 전환했습니다. Mac은 SwiftUI를 유지하고 Windows는 Windows 기본 제목 표시줄과 Fluent 컨트롤, Ctrl+,와 UAC를 사용합니다. FluentWinUI3는 Qt의 Windows 스타일이며 Windows App SDK 자체로 재작성한 앱이라는 뜻은 아닙니다.

Windows 화면은 D3D11 장면 그래프에서 움직입니다. 한국어는 맑은 고딕, 영어는 Segoe UI Variable Text → Segoe UI를 우선합니다. 작은 본문에는 고품질 distance-field 글꼴 렌더링을 적용하고, 도형에는 CurveRenderer를 사용해 배율 변화에 대응합니다. 운영체제의 ClearType 설정을 강제로 변경하지 않습니다. PNG 에셋에는 부드러운 축소와 mipmap을 적용하고, 땅굴과 체크 표시는 벡터로 렌더링합니다.

시작·중지 파동, 단계에 따른 캐릭터 이동, 채굴·입자·빛·성공 전환은 QML 애니메이션 엔진이 처리하며 Python 프레임 타이머는 사용하지 않습니다. 연결 완료·비활성·최소화·동작 줄이기에서는 반복 효과를 정지합니다. 실행 결과는 기존 백엔드 단계만 반영합니다.

네트워크 엔진은 검증된 **sing-box 1.12.0 Windows TUN**을 유지합니다. UI 교체가 게임 통신 경로를 바꾸지 않습니다. 렌더러·스타일·텍스트 모드·실제 선택한 글꼴은 검증 JSON과 렌더러 로그에 기록합니다. Windows Server CI의 그래픽 장치는 실제 Windows 11 PC의 GPU와 다를 수 있으며 하드웨어 가속 성능을 검증했다는 뜻은 아닙니다.

## Pearl White — build 8

첨부 `Pearl White Implementation Assets.zip`의 로고·캐릭터·설정 아이콘과 색상 토큰을 사용합니다. 전체 목업 PNG를 배경으로 붙이지 않고 실제 Qt Quick 컨트롤·그라디언트·벡터 패널로 구현했습니다. 원본 이미지 파일은 변경하지 않고 투명 여백만 화면 표시 영역에서 조정합니다.

기본은 **A안: 둥근 독립형 플로팅 버튼**입니다. 설정의 버튼 스타일에서 **B안: 일체형 컨트롤**로 바꿔 비교할 수 있으며 선택은 저장합니다. Pearl White 단일 테마로 적용하고 Windows 고대비에서는 시스템 색상을 우선합니다. 새 명세에 따라 캐릭터는 정적이며 학교·땅굴·채굴·성공 파동은 표시하지 않습니다. 미세한 버튼 호버·포커스 반응만 유지합니다.

- **START:** WARP Local Proxy 준비·검증 후 기존 분리 라우팅 엔진 실행
- **STOP:** 엔진 정리 후 WARP Traffic and DNS 복귀 확인
- **KILL SWITCH:** 소유한 엔진 정리 후 WARP 연결 해제 확인. **일반 인터넷은 유지하며 방화벽 차단 기능이 아닙니다.**

KILL SWITCH는 시작·STOP 처리 중에도 요청할 수 있습니다. 같은 작업자에서 CLI 명령을 직렬 처리하고, STOP이 완료되는 순간에 들어온 긴급 정지 요청은 별도의 연결 해제로 이어집니다. 실패 시 복구 기록과 오류를 유지하고 성공을 표시하지 않습니다. WARP CLI 작업의 응답을 기다릴 수 있으므로 즉각적인 모든 패킷 차단을 보장하지 않습니다.
