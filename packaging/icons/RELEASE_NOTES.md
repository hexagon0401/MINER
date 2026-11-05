## MINER ALPHA v1.0.1

정식 릴리스에 남아 있던 BETA 아이콘을 기본 MINER 아이콘으로 교체했습니다. ALPHA는 제품 세대의 코드명이며 이번 배포는 정식 릴리스입니다.

- macOS Apple Silicon·Intel: 제공된 Icon Composer 원본을 Apple 도구로 컴파일한 기본 아이콘을 적용했습니다. 이전 macOS를 위한 ICNS도 포함합니다.
- Windows x64: 같은 기본 아이콘을 앱·작업 표시줄·설치 프로그램·바로 가기에 적용했습니다.
- 이후 베타 빌드는 기존 BETA 아이콘, 정식 빌드는 기본 아이콘을 사용합니다.
- 기존 ALPHA v1과 베타 배포는 보존합니다. 베타 2 기능을 추가하지 않고, ALPHA v1의 각 플랫폼 소스를 기반으로 아이콘과 배포 메타데이터를 변경했습니다.

두 Mac DMG의 서명 무결성·네이티브 UI·복사 설치와 Windows EXE의 UI·설치·재설치·제거를 자동 검사한 뒤 게시합니다. Windows 검사는 Windows Server 환경이며 Windows 11 실기·학교망·WARP·게임·Vanguard의 실제 호환성 검사를 대신하지 않습니다. 서명·공증 여부는 각 파일의 `.verification.json`을 확인하세요.

Homebrew 사용자는 MINER를 중지·종료한 후 `brew update`와 `brew upgrade --cask miner`로 업데이트할 수 있습니다.
