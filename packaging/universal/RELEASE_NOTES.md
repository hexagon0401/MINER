# MINER ALPHA universial Beta 1

macOS와 Windows 베타 1을 한곳에서 받는 통합 프리릴리스입니다. **플랫폼별 설치 파일 3개**를 제공하며, 하나의 파일에서 모든 CPU/OS를 실행하는 형식은 아닙니다.

| 컴퓨터 | 다운로드 파일 |
|---|---|
| Mac · Apple Silicon (M 시리즈) | `MINER-Alpha-Universal-Beta1-macOS-AppleSilicon.dmg` |
| Mac · Intel | `MINER-Alpha-Universal-Beta1-macOS-Intel.dmg` |
| Windows · x64 | `MINER-Alpha-Universal-Beta1-Windows-x64-Setup.exe` |

Mac은 DMG에서 MINER.app을 Applications로 옮기고, Windows는 Setup.exe로 설치합니다. 개인용 Cloudflare WARP는 별도로 설치·등록해야 합니다.

- macOS: 검증된 베타 1.1 SwiftUI 앱. 학교·땅굴 UI와 기존 연결·복구 동작을 유지합니다. Intel DMG도 동일한 macOS 소스로 네이티브 빌드합니다.
- Windows: 검증된 베타 1 Pearl White build 8. 기본 A안 플로팅 버튼, 설정에서 B안 일체형 버튼, 한/영 설정을 제공합니다. STOP은 WARP 원래 모드로 복귀하고 KILL SWITCH는 엔진 정리 후 WARP 연결을 해제합니다. 일반 인터넷은 유지합니다.
- 베타 2 학교·제보 기능은 이번 설치 파일에 포함하지 않습니다.

앱 내부 버전은 macOS `5.0.0-beta.1.1`, Windows `5.0.0-beta.1.1-windows.8`입니다. 통합 릴리스로 묶으면서 검증된 Apple Silicon·Windows 바이너리는 변경하지 않았습니다. 플랫폼 버전과 출처는 `release-manifest.json`, 검증 결과는 각 `.verification.json`, 체크섬은 `SHA256SUMS.txt`에서 확인할 수 있습니다.

현재 macOS 빌드는 ad-hoc 서명·미공증이고 Windows EXE는 Authenticode 미서명입니다. 실제 학교망·게임·Vanguard와 Windows 11 GPU 성능은 미검증입니다. UI 캡처에 표시한 연결 상태는 검사용 값이며 실제 접속 성공의 증거가 아닙니다.
