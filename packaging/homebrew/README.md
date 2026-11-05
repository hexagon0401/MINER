# MINER Homebrew 배포 준비

현재 정식 배포 대상은 **MINER ALPHA v1**입니다. ALPHA는 세대 코드명이며 테스트 단계 표시가 아닙니다. 저장소 루트의 [Casks/miner.rb](../../Casks/miner.rb)는 Apple Silicon·Intel을 자동으로 구분해 ALPHA v1의 검증된 DMG와 SHA-256을 사용합니다. 이 디렉터리의 이전 `Casks/miner-beta.rb`와 생성기는 과거 이력으로 유지합니다.

## 배포 경로

기존 공개 저장소 `hexagon0401/MINER`를 그대로 tap으로 사용합니다. 별도 저장소는 필요하지 않습니다. Homebrew가 루트 `Casks/`에서 앱 정의를 찾도록 구성했습니다. Mac에서의 Homebrew 검사와 설치·실행 검증은 아직 남아 있으므로 아래는 검증용 설치 명령입니다.

```bash
brew tap hexagon0401/miner https://github.com/hexagon0401/MINER.git
brew install --cask hexagon0401/miner/miner
```

첫 번째 명령의 저장소 URL을 생략하면 Homebrew가 기본 규칙에 따라 `hexagon0401/homebrew-miner`를 찾습니다. 기존 MINER 저장소를 사용할 때는 처음 등록할 때 위 URL을 반드시 지정합니다. 등록 이후에는 `brew install --cask hexagon0401/miner/miner`만 사용하면 됩니다. 최소 macOS는 앱 빌드 대상과 같은 Ventura(13)입니다. 개인용 Cloudflare WARP는 별도로 설치·등록합니다.

## 사용자 준비

새 저장소 생성이나 추가 인증 토큰은 필요하지 않습니다. Homebrew가 설치된 Mac에서 위 명령으로 검증할 수 있습니다. DMG를 직접 설치한 MINER가 이미 있다면 먼저 중지·종료하고, Homebrew가 같은 앱의 존재로 설치를 중단하면 기존 앱의 데이터와 제거 안내를 확인한 뒤 전환합니다.

## 배포 전 확인

1. **tap 등록:** 위의 명시적 URL로 기존 MINER 저장소를 등록합니다. 앱 소스·DMG를 복사할 필요 없이 기존 ALPHA v1 릴리스 파일을 다운로드합니다. tap을 복제할 때는 프로젝트 소스와 보관 이력도 함께 내려받으므로, 규모가 커지면 별도 tap을 선택할 수 있습니다.
2. **익명 다운로드 검사:** 토큰 없이 두 DMG를 다운로드해 각각 아래 해시와 일치하는지 확인합니다. Apple Silicon URL의 익명 접근은 개발 환경에서 HTTP 200을 확인했습니다. 실제 전체 파일 검사는 별도로 수행합니다.
3. **Homebrew 검사:** Mac에서 tap 설치 후 `brew style --cask hexagon0401/miner/miner`와 `brew audit --cask --online hexagon0401/miner/miner`를 실행합니다. 검사 오류는 보안 우회로 숨기지 않고 수정합니다.
4. **설치·업데이트·제거 검증:** Apple Silicon과 Intel에서 실제 앱 설치·실행, 중지 후 WARP 복귀, 업데이트·제거를 확인합니다. 실행 중 설치·제거가 중단되는지도 확인합니다.
5. **공개 안내:** 검사가 통과한 뒤 루트 README에 실제 brew 설치 명령을 추가합니다. 공식 `homebrew/cask` 등재는 별도 후속 단계입니다.

| Mac | SHA-256 |
|---|---|
| Apple Silicon | `8b430e5d4fac61d6e3c0e3a42f6058d22dc5ad0532df6b85672bc474a0eb40e4` |
| Intel | `51012a4dd35bf7b3042c80df645fe40115ae1f69c56cc06580e37b748abb23f5` |

출처는 `alpha-v1.verification.json`과 [ALPHA v1 정식 릴리스](https://github.com/hexagon0401/MINER/releases/tag/miner-alpha-v1)입니다. cask 버전 `1`은 배포 버전이며 앱 내부의 기존 빌드 번호는 검증 기록에 유지합니다.

## 서명·실행 허용

현재 DMG 앱은 ad-hoc 서명이며 Apple 공증이 없습니다. Homebrew로 설치해도 macOS 최초 실행 경고가 없어지는 것은 아닙니다. Developer ID 서명·Apple 공증을 준비하면 배포 경험을 개선할 수 있습니다. tap 준비와 서명 준비는 별도로 진행할 수 있습니다.

Apple 자격 증명은 채팅이나 cask에 넣지 않고 저장소 Secrets에 등록합니다. [서명·공증 안내](../../v5/docs/SIGNING.md)를 따릅니다. Gatekeeper 전역 해제나 quarantine 제거를 cask에서 자동 실행하지 않습니다.

## 업데이트와 제거

MINER에서 중지한 뒤 종료하고 `brew upgrade --cask miner` 또는 `brew uninstall --cask miner`를 사용합니다. 전체 서비스·지원 파일 정리는 앱 설정의 제거 기능을 먼저 사용합니다. WARP는 cask가 설치하거나 삭제하지 않습니다. `--zap`은 사용자 설정의 선택적 정리입니다.

과거 `miner-beta`를 Homebrew로 설치했다면 앱을 중지·종료하고 기존 cask를 제거한 뒤 새 `miner`를 설치합니다. 두 cask가 같은 `MINER.app`을 동시에 소유하지 않도록 충돌 설정을 둡니다.

## 정식 릴리스 → cask 자동 갱신

[MINER Homebrew cask update](../../.github/workflows/miner-homebrew.yml)가 GitHub의 최신 정식 릴리스를 확인하고, 두 Mac DMG를 실제로 다운로드해 SHA-256을 검사한 뒤 기본 브랜치의 cask와 `latest.verification.json`을 커밋합니다. 별도 저장소·PAT는 필요하지 않으며 GitHub Actions의 `GITHUB_TOKEN`을 사용합니다. 저장소 규칙에서 봇의 기본 브랜치 쓰기를 막으면 커밋 단계가 실패하므로 Actions 결과를 확인해야 합니다. 강제 push는 하지 않습니다.

- **실행 시점:** 정식 릴리스 게시·수정, 6시간 간격 확인, Actions의 수동 실행. 자동화 파일 변경 시에도 한 번 확인합니다. GitHub 스케줄 실행은 지연될 수 있습니다.
- **GITHUB_TOKEN으로 만든 릴리스:** 다른 워크플로의 즉시 실행을 유발하지 않으므로 정기 확인에서 반영됩니다. 바로 반영하려면 Actions에서 이 워크플로를 수동 실행합니다.
- **지원 버전:** `miner-alpha-v2`, `miner-alpha-v2.1`과 같은 숫자 버전. ALPHA는 세대 코드명이며 프리릴리스 여부는 GitHub의 별도 표시로 판단합니다. 다른 세대 코드명이나 파일명 체계로 전환할 때는 updater도 함께 수정합니다.
- **필수 첨부 파일:** `release-manifest.json`, `MINER-ALPHA-v<버전>-macOS-AppleSilicon.dmg`, `MINER-ALPHA-v<버전>-macOS-Intel.dmg`. 기존 ALPHA v1과 같은 manifest 구조를 유지하고 각 플랫폼의 `filename`, `architecture`, `sha256`을 기록합니다. 기존 `alpha-v1.verification.json`은 역사 기록으로 보존합니다.
- **갱신 조건:** 최신 정식 릴리스만 처리하며 프리릴리스·초안·낮은 버전은 제외합니다. 두 DMG 중 하나라도 없거나 해시가 틀리면 기존 cask를 유지합니다. 같은 버전의 DMG 내용 교체는 거부하므로 새 버전을 발행합니다. 실패 로그는 Actions artifact에 남고 다음 확인 때 재시도합니다.

이 자동화는 릴리스에 게시한 파일을 검증·연결합니다. 앱 빌드·Apple 공증·Mac 실기 검증을 대신하거나 사용자의 앱을 백그라운드에서 교체하지 않습니다. cask가 반영된 후 사용자는 MINER를 중지·종료하고 다음 명령을 실행합니다.

```bash
brew update
brew upgrade --cask miner
```
