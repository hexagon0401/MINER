# macOS 서명 오류와 Developer ID 공증

## 이번에 확인한 문제

alpha.2의 실제 macOS 검사에서 `a sealed resource is missing or invalid`와 함께
같은 한글 안내 파일이 `file added` / `file missing`으로 나타났습니다.
이는 한글 파일명의 NFC/NFD 정규화가 배포·복사 과정에서 달라진 경우와 맞습니다.
단순히 Apple Developer 가입 여부로 해결되는 오류가 아닙니다.

alpha.3부터 앱 내부 안내 파일은 **UserGuide.txt**로 바꿉니다. 내용은 한국어입니다.
서명 전 앱 내부의 비 ASCII 경로를 거부하고, DMG 마운트 검사에 더해 **DMG에서 새 폴더로
앱을 복사한 후** 서명 무결성과 내장 CLI를 다시 검사합니다.

이 수정이 Developer ID 서명·공증을 대신하지는 않습니다. 인증서가 없는 빌드는
명시적인 ad-hoc 배포이며 Gatekeeper가 추가로 제한할 수 있습니다.
보안 경고를 없애려고 Gatekeeper를 전역으로 끄거나 손상된 서명 검사를 생략하지 않습니다.

## 현재 맥의 인증서

사용자가 실행한 `security find-identity -v -p codesigning` 결과는 **0 valid identities found**였습니다.
따라서 그 키체인에서 사용할 수 있는 서명 인증서+개인 키 조합은 확인되지 않았습니다.
Developer Program 신청/가입과 Developer ID 인증서 발급은 별개입니다.

1. 유료 Apple Developer Program 멤버십이 활성화되어 있는지 확인합니다.
2. Mac의 **키체인 접근 → 인증서 지원 → 인증 기관에서 인증서 요청**으로 CSR을 디스크에 저장합니다.
3. Apple Developer의 [Certificates](https://developer.apple.com/account/resources/certificates/list)에서
   **Developer ID Application** 인증서를 생성하고 CSR을 제출합니다.
   `Apple Development`, `Apple Distribution`, `Developer ID Installer`는 이 앱 서명용 인증서와 다릅니다.
   계정 역할에 따라 Account Holder의 작업이 필요할 수 있습니다.
4. 발급받은 인증서를 CSR을 만든 같은 Mac의 키체인에 설치합니다. 인증서를 펼쳤을 때
   개인 키가 연결되어 있어야 합니다. 기존 인증서가 있다면 새로 만들기 전에 올바른 키체인에
   인증서와 개인 키가 설치되어 있는지 확인합니다.
5. 다음 명령에 유효한 `Developer ID Application: 이름 (TEAMID)`가 나오는지 확인합니다.

   ```bash
   security find-identity -v -p codesigning
   ```

인증서/개인 키·p12·p8·비밀번호를 채팅이나 Git에 올리지 않습니다.

## GitHub에서 자동 서명·공증하기

저장소 **Settings → Secrets and variables → Actions**에 다음 Repository secrets를 설정합니다.
이미 같은 용도의 값이 있다면 중복 생성하기 전에 이름과 사용 범위를 확인하세요.
이 작업 환경에서는 GitHub API 네트워크 차단으로 저장소의 secret 이름을 조회하지 못했습니다.

| 이름 | 입력 내용 |
|---|---|
| `APPLE_CERTIFICATE_P12_BASE64` | 키체인에서 인증서+개인 키를 내보낸 `.p12`의 base64 |
| `APPLE_CERTIFICATE_PASSWORD` | 해당 `.p12` 내보내기 암호 |
| `APPLE_TEAM_ID` | 인증서에 대응하는 Apple Developer Team ID |
| `APPLE_NOTARY_KEY_P8_BASE64` | 공증용 App Store Connect API `.p8` 키의 base64 |
| `APPLE_NOTARY_KEY_ID` | 그 API Key ID |
| `APPLE_NOTARY_ISSUER_ID` | 그 API 키의 Issuer ID |

base64는 암호화가 아닙니다. 예를 들어 Mac에서 `base64 -i /로컬/인증서.p12 | pbcopy`로
변환해 GitHub Secret 값에 직접 붙여넣습니다. p8도 같은 방식입니다. 원본 파일은 업로드하지 않습니다.
공증 API 키는 Apple의 App Store Connect **Users and Access → Integrations**에서 관리하며
Apple notarization에 사용할 수 있는 팀 키와 권한이 필요합니다.

빌드는 인증서를 임시 키체인으로 가져와 지정한 Team의 유효한 Developer ID인지 확인합니다.
PyInstaller 런타임·라이브러리·엔진을 안쪽부터 동일한 ID로 서명하고 Hardened Runtime과
timestamp를 사용합니다. 앱 ZIP을 Apple에 제출해 **Accepted**를 확인한 뒤 앱에 티켓을 부착하고,
DMG도 서명·공증·티켓 검증합니다. 복사한 앱에는 `spctl` 평가도 실행합니다.

인증서 설정이 전혀 없으면 기존처럼 **ad-hoc임을 명시한** 테스트 빌드를 만듭니다.
설정을 일부만 넣었거나 Developer ID/공증이 실패하면 ad-hoc으로 몰래 전환하지 않고 빌드를 실패시킵니다.
각 DMG의 `.verification.json`에 실제 signing 모드와 앱/DMG 공증 결과가 기록됩니다.
키체인과 임시 키 파일은 빌드 후 제거합니다. 학교 연결·게임 성능 검증은 별도입니다.

## Mac에서 직접 서명해 빌드하기

GitHub에 키를 넣지 않는 대안입니다. 유효한 Developer ID 인증서가 설치된 Mac에서
Apple ID와 앱 전용 암호를 **로컬 키체인에** 저장할 수 있습니다. 아래 명령은 대화형으로
자격 증명을 요청합니다. 일반 Apple 로그인 암호를 코드나 스크립트에 적지 않습니다.

```bash
xcrun notarytool store-credentials SchoolNetNotary
cd /path/to/MINER/v5
python3 -m pip install 'pyinstaller==6.22.3' 'certifi==2026.10.23'
python3 macos/build.py --arch arm64 --signing developer-id \
  --identity 'Developer ID Application: 인증서의 실제 이름 (TEAMID)' \
  --notary-profile SchoolNetNotary
```

Intel Mac은 `--arch x86_64`를 사용합니다. 결과는 `v5/dist`에 생성됩니다.
서명·공증의 실제 수행에는 macOS, 인증서+개인 키, Apple 공증 자격 증명과 네트워크가 필요합니다.
Linux 자동 테스트는 이 Apple 절차의 성공을 보장하지 않습니다.

## 수정본 확인

기존 앱의 데이터는 필요하면 백업하고 실행 중이면 중지한 뒤 새 DMG의 앱으로 교체합니다.
다음 검사를 통과해야 기존의 파일 봉인 오류가 해결됐다고 볼 수 있습니다.

```bash
codesign --verify --deep --strict --verbose=2 '/Applications/MINER.app'
```

Developer ID로 공증한 배포라면 아래도 통과해야 합니다. ad-hoc 빌드에는 공증 성공을 기대하지 않습니다.

```bash
spctl --assess --type execute --verbose=2 '/Applications/MINER.app'
xcrun stapler validate '/Applications/MINER.app'
```
