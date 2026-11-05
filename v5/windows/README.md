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
