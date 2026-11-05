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
