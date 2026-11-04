# MINER

**Dig your way out.** macOS 우선의 WARP Local Proxy·분리 라우팅 실험 앱입니다.

| 버전 | 제공 상태 |
|---|---|
| **베타 1** | [Apple Silicon DMG](https://github.com/hexagon0401/MINER/releases/download/v5.0.0-beta.1/MINER-v5.0.0-beta.1-macOS-AppleSilicon.dmg) · 네이티브 UI/서명/설치 복사 검증 완료 |
| **베타 2** | `v5/`의 학교 현황·로컬 인증·제보 시스템 개발본. 전체 공식 학교 명부 확보 전에는 전국 통계를 완성했다고 표시하지 않으며 배포용 DMG도 게시하지 않음 |
| 공유 제보 서버 | **미개방**. 로컬 Workers/D1 코드와 검토 도구만 준비 |
| Homebrew | 실제 베타 1 DMG 해시로 cask 준비. 저장소와 tap 공개 전에는 공개 설치 제공 안 함 |

저장소와 릴리스는 비공개로 유지합니다. 공개 전환은 소유자가 직접 합니다.

## 설치와 사용

1. 개인용 Cloudflare WARP를 별도로 설치·등록합니다.
2. 베타 1 DMG에서 `MINER.app`을 Applications로 옮깁니다.
3. 앱의 시작은 WARP Local Proxy 포트 40000을 준비하고 분리 라우팅을 시작합니다.
4. 중지·종료는 엔진을 중지하고 WARP UDP Traffic and DNS 복귀를 확인합니다.
5. ⌘, 에서 한국어/English, 개발자 소개, 제거 기능을 사용할 수 있습니다.

기존 SchoolNet 앱은 먼저 중지·종료하세요. **현재 베타 1은 ad-hoc 서명이며 Apple 공증이 없습니다.** macOS 실행 허용을 보장하는 배포는 아닙니다. Gatekeeper를 전역 해제하거나 보안 설정을 자동 변경하지 않습니다.

## 연결 범위와 검증 범위

Riot/LoL 클라이언트·웹 Helper의 TCP는 WARP, 게임 실행 파일과 나머지 트래픽은 직접 경로로 보내는 구성입니다. 실제 학교망·게임 RTT/FPS·영상·종료 복귀는 사용자 환경에서 확인해야 합니다. 프록시 HTTPS 진단 성공이 실제 게임 플레이나 학교 위치를 증명하지는 않습니다.

베타 2의 초록 깃발은 해당 범위에서 **과거 성공 기록이 있음**, 빨강은 **성공 미확인**입니다. 빨강을 작동 불가능으로 해석하지 않습니다. 내 기기의 기록과 운영자가 승인한 전국 공유 기록을 구분합니다.

## 개발·배포 안내

- [v5 설치·기술 안내](v5/README.md)
- [학교 데이터·인증·제보 계약과 로컬 서버](v5/community/README.md)
- [배포 상태와 사용자가 남겨둘 작업](v5/docs/BETA2_HANDOFF.md)
- [Homebrew 준비와 공개 전 확인](packaging/homebrew/README.md)
- [Apple 서명·공증 설정](v5/docs/SIGNING.md)
- [개인 Mac 러너 등록 준비](v5/docs/SELF_HOSTED_MAC.md)

개발자: [Punkthats*it · @hexagon0401](https://github.com/hexagon0401). 이전 v1~v4는 이력으로 보존하며 v5 설치·제거가 WARP나 이전 버전을 삭제하지 않습니다.
