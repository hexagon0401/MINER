# MINER BETA 1 — Windows

베타 1.1 기반 Windows x64 첫 프리릴리스입니다. 베타 2 학교 기능은 포함하지 않습니다.

- 기존 베타 아이콘·학교·캐릭터와 곡선 땅굴 UI, 실제 상태에 연결한 5단계 표시
- 시작 → WARP Local Proxy 40000 → SOCKS 원격 DNS/TLS 검증 → Windows TUN 분리 라우팅
- 중지·종료 → 엔진 정상 정리 → WARP UDP Traffic and DNS 복귀 확인. 복귀 실패 시 창을 유지하고 재시도 가능
- 관리자 권한(UAC), 중복 실행 방지, 한국어/영어 설정(Ctrl+,), 개발자 About
- 설치·제거 프로그램 및 SHA-256·자동 검증 기록 제공

## 설치

Windows 10 1809 이상 / Windows 11의 x64 PC용입니다. 개인용 Cloudflare WARP를 별도로 설치·등록한 뒤 Setup.exe로 설치하세요. 실행 시 관리자 권한이 필요합니다. 제거 전 MINER에서 중지 후 종료하세요. Windows 설정의 설치된 앱에서 제거할 수 있습니다. 사용자 설정·로그는 `%LOCALAPPDATA%\MINER\Beta1`에 보존합니다. WARP와 기존 버전은 삭제하지 않습니다.

실제 Windows TUN 생성/정상 종료, 패키지 UI, 설치·제거는 CI에서 검증합니다. 실제 WARP 연결·학교망·게임·Vanguard 호환성은 사용자 환경 테스트가 필요합니다. 게임 성능이나 모든 학교에서의 작동은 보장하지 않습니다. 이 배포본은 Authenticode 서명이 없어 Windows SmartScreen 경고가 나타날 수 있습니다. 보안 기능을 전역 해제하지 마세요.

## Windows build 4

- Windows 파일 잠금의 권한 오류와 TLS 경로 테스트 수정
- 비정상 종료 시 엔진 정리를 위한 Job Object, 미완료 세션 복구 안내
- Windows 기본 창 조작, Ctrl+, 설정, 실시간 한/영 전환, 테마·고대비·동작 줄이기
- 비율을 유지하는 캐릭터·곡선 땅굴, 시작·중지 파동·채굴·성공 표시
- 100/125/150/200% 배율 UI 검사, 한글·공백 설치 경로, 재설치·제거 검사
- Setup.exe 외에 UI 검증 PNG·GIF·스크린샷 ZIP 제공

스크린샷과 GIF는 실제 EXE 렌더링이지만 연결 상태는 **검사용 주입 값**입니다. 실제 WARP나 LoL 연결 성공을 의미하지 않습니다. Windows Server CI 검사와 Windows 11 실기 검증을 구분해 제공하며 Windows 11·학교망·게임·Vanguard 실기 테스트는 수행하지 않았습니다.

진행률은 실제 완료 단계만 반영하는 5개 막대로 표시합니다. Windows 어두운 테마에서는 지원되는 시스템의 제목 표시줄 색상도 맞춥니다. UI 검증 PNG·GIF에는 테스트용 연결 상태임을 화면에 표시합니다.

## Windows build 7 — Qt Quick / Fluent

- Qt Widgets 화면을 Qt Quick RHI 장면 그래프와 FluentWinUI3 스타일 컨트롤로 전환
- Windows 기본 창·UAC·단축키 유지, 시스템/밝은/어두운 테마 적용
- Segoe UI 계열 글꼴, 배율 독립적인 윤곽선 기반 글꼴 안티앨리어싱, 벡터 도형과 부드러운 이미지 축소
- Python 프레임 타이머를 제거하고 QML에서 채굴·파동·성공 효과를 처리
- 비활성·최소화·동작 줄이기에서 반복 효과 중단
- 네트워크 엔진과 연결·복구 계약 유지

실제 렌더러와 글꼴·스타일은 검증 JSON에 기록합니다. Windows Server CI 검사이며 Windows 11 실기·실제 게임과 GPU 성능은 미검증입니다. UI 캡처의 연결 상태는 검사용 값입니다.

CI에서는 Microsoft Direct3D 소프트웨어 어댑터를 우선하도록 요청합니다. 이는 Cloudflare WARP와 별개의 그래픽 기능이며, 실제 하드웨어 GPU 성능 측정이 아닙니다. GIF 캡처에서는 테스트 객체의 동작 줄이기 값만 잠시 해제해 애니메이션을 검증하며 Windows 전역 설정은 변경하지 않습니다.

작은 본문은 고품질 distance-field 글꼴 안티앨리어싱을 사용하고, 한국어는 맑은 고딕·영어는 Segoe UI 계열을 우선합니다. 땅굴과 체크 표시는 CurveRenderer 벡터 경로를 사용합니다. 캡처는 동기식 단일 렌더 루프에서 수행하고 실제 앱은 Qt 기본 렌더 루프를 유지합니다.

## Windows build 8 — Pearl White

사용자가 제공한 Pearl White 로고·캐릭터·아이콘을 적용했습니다. 기본은 A안의 둥근 플로팅 버튼이며 설정에서 B안 일체형 버튼으로 전환할 수 있습니다. 원본 에셋은 유지하고 실제 컨트롤·그라디언트·그림자로 화면을 구현합니다. Windows 기본 창 조작과 고대비 대응은 유지합니다.

새 명세에 따라 Pearl White 단일 테마, 정적인 캐릭터 패널, 실제 상태를 따르는 5단계 진행 표시를 사용합니다. 학교·땅굴·채굴 애니메이션은 제거하고 버튼의 작은 반응만 유지했습니다.

- START: 기존 WARP 프록시 연결·검증과 엔진 시작
- STOP: 엔진 정리 후 WARP 원래 Traffic and DNS 모드 복귀
- KILL SWITCH: 엔진 정리 후 WARP 연결 해제. **일반 인터넷 유지; 방화벽 차단 아님**

긴급 정지를 연결·복귀 처리 중 요청해도 CLI 명령을 동시에 실행하지 않습니다. 실패하면 오류와 복구 상태를 유지합니다. Preview GIF는 정적인 UI의 상태 전환 안내이며 실제 연결 성공이나 새 채굴 애니메이션이 아닙니다. 실제 Windows 11·학교망·WARP·게임·Vanguard는 미검증이고 EXE는 미서명입니다.
