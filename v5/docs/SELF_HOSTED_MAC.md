# 개인 Mac 러너 준비

이 안내만 준비했으며 계정 로그인·러너 등록·유료 서버 구매는 하지 않았습니다. 현재 베타 1 DMG는 GitHub 호스팅 Mac에서 빌드·게시됐습니다.

호스팅 Mac이 다시 배정되지 않을 때의 대안:

1. 신뢰하는 개인 Mac에서 GitHub 저장소 Settings → Actions → Runners → New self-hosted runner를 엽니다.
2. macOS/ARM64 등록 명령은 GitHub가 표시하는 일회성 토큰으로 **본인이 해당 Mac에서** 실행합니다. 토큰·키체인·Apple 개인 키를 채팅이나 Git에 올리지 않습니다.
3. Xcode 명령줄 도구, Python 3.12, 저장소 접근 권한을 준비합니다. Mac은 깨어 있고 네트워크에 연결돼 있어야 합니다.
4. 러너를 해당 비공개 저장소에만 제한하고 `miner-trusted-mac` 라벨을 붙입니다. 자동 부팅 서비스 설치 여부는 본인이 정합니다.
5. 소유자가 고정한 소스 태그를 빌드하는 수동 작업에만 연결합니다. 외부 PR·fork 코드를 이 러너에서 실행하지 않습니다.
6. Apple 인증서는 키체인에, CI 공증 키는 GitHub Secrets에 넣습니다. 키를 소스·로그·캐시에 저장하지 않습니다.

현재 자동 재시도는 무료 GitHub `macos-26`/`macos-15`만 사용합니다. self-hosted 라벨을 기본값으로 자동 선택하지 않습니다. 등록이 끝나면 workflow 입력의 허용 러너 목록에 이 라벨을 추가하고 동일한 네이티브 검증을 유지해야 합니다.

로컬 수동 빌드도 가능합니다. `v5`에서:

```bash
python3.12 -m pip install pyinstaller==6.22.3 certifi==2026.10.23 dmgbuild==1.6.7
python3.12 macos/build.py --arch arm64 --validation-only
```

베타 2의 배포용 DMG는 공식 전체 학교 명부가 필요합니다. 로컬 개발 화면만 확인하려면 `--allow-incomplete-catalog`을 명시할 수 있으나, 이 파일을 전국 현황 완성본으로 게시하지 않습니다. 베타 1은 고정 태그를 별도 체크아웃해 빌드합니다.
