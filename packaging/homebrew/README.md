# Homebrew 준비 상태

`Casks/miner-beta.rb`는 **실제로 게시된 베타 1 Apple Silicon DMG**의 검증 JSON과 SHA-256으로 생성했습니다. 베타 2 소스가 추가되어도 설치 가능한 파일이 없는 베타 2로 cask 버전을 올리지 않습니다.

현재 MINER는 비공개이므로 익명 Homebrew 설치·다운로드는 제공되지 않습니다. 이 디렉터리는 아직 공개 tap이 아닙니다. 토큰을 cask에 넣거나 GitHub 저장소를 자동 공개하지 않습니다.

공개 배포할 때 사용자가 할 작업:

1. MINER 릴리스와 `hexagon0401/homebrew-miner` tap을 공개합니다. tap에 이 디렉터리의 `Casks/`를 복사합니다.
2. 토큰 없는 환경에서 DMG 다운로드와 SHA-256을 확인합니다.
3. tap을 설치한 뒤 `brew style --cask hexagon0401/miner/miner-beta`, `brew audit --cask --online hexagon0401/miner/miner-beta`를 실행합니다.
4. 새 Mac에서 설치·중지·업데이트·제거를 확인합니다.
5. 공개 전 Gatekeeper 제한을 피하려면 Developer ID와 Apple 공증을 구성합니다. 현재 베타 1은 ad-hoc이며 공증이 없습니다.

공개 후 설치 명령:

```bash
brew tap hexagon0401/miner
brew install --cask miner-beta
```

새 버전 DMG 검증 후 cask 재생성:

```bash
python3 packaging/homebrew/generate.py path/to/verified.dmg.verification.json
```

실행 중인 MINER/네트워크 작업이 있으면 설치·업데이트·제거를 중단하고 먼저 앱의 중지·종료를 요구합니다. WARP를 자동 설치·삭제하거나 전체 보안을 해제하지 않습니다. 완전 제거는 앱 설정의 제거 기능으로 서비스·데이터·키체인 키를 정리한 뒤 Homebrew에서 제거하세요. `--zap`은 사용자 설정·학교 기록을 선택적으로 삭제하며 시스템 지원 파일을 임의로 지우지 않습니다.
