# MINER 릴리스 아이콘

정식 릴리스는 `v5/macos/design/icons/stable/`, 베타·개발 빌드는 `icons/beta/AppIcon.png`를 사용합니다. 기본 아이콘의 원본은 사용자가 제공한 `MINER.icon`이며 이전 아이콘 원본도 기존 위치에 보존합니다. `ALPHA`는 제품 세대 코드명으로, 정식 릴리스에서도 기본 아이콘을 사용합니다.

두 플랫폼은 `v5/icon_assets.py`의 선택 규칙을 공유합니다. 정식 배포 작업에는 `MINER_RELEASE_CHANNEL=stable`, 베타에는 `MINER_RELEASE_CHANNEL=beta`를 명시합니다. 지정이 없으면 `miner-alpha-v1.0.1` 형태의 정식 태그 또는 숫자 버전은 기본 아이콘을, 기존 alpha/beta/delta 개발 버전은 베타 아이콘을 선택합니다. 선택한 아이콘이 없으면 반대 채널로 대체하지 않고 빌드를 실패시킵니다.

Apple `.icon`은 `Compile official MINER icon` 워크플로에서 `actool`로 컴파일합니다. `Assets.car`는 최신 macOS용 네이티브 아이콘, `AppIcon.icns`는 이전 macOS용 호환 아이콘입니다. `iconutil`이 내보낸 PNG는 Windows ICO와 앱 창 아이콘에도 사용합니다. Apple이 제공하는 호환 출력은 256px이며 이를 임의로 확대하지 않습니다. 원본 고해상도 자산은 `.icon`과 `Assets.car`에 유지합니다.

ALPHA v1.0.1 수정판은 `MINER ALPHA v1.0.1 official icon` 워크플로로 빌드합니다. 기존 ALPHA v1에 사용한 macOS·Windows 소스 SHA를 각각 고정하고 아이콘 선택과 배포 메타데이터만 적용합니다. 두 Mac DMG와 Windows 설치 검증이 모두 성공해야 게시하며, 기존 v1 파일은 교체하지 않습니다. 게시 후 Homebrew 자동 갱신 워크플로도 실행합니다.
