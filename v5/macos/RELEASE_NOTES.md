macOS 우선의 **SchoolNet v5 Alpha** 테스트 배포입니다.

- Apple Silicon / Intel DMG를 각각 제공합니다. 앱을 Applications로 드래그해 설치합니다.
- Python과 sing-box 엔진을 포함합니다. 개인용 Cloudflare WARP는 별도 설치가 필요합니다.
- 앱에서 사전 점검, 시작, 중지, 로그 확인, 제거를 할 수 있습니다.
- WARP Local proxy(포트 40000)로 Riot/LoL 클라이언트 TCP를 전달하고 게임 데이터는 직접 연결합니다.
- macOS 관리자 인증은 시작/중지/제거에 사용합니다. 자동 부팅 항목은 설치하지 않습니다.
- 제거는 앱의 '제거' 버튼으로 진행하세요. WARP와 기존 v1~v4는 유지합니다.

**이 alpha는 Apple Developer ID 서명·공증이 없습니다.** macOS가 실행을 제한할 수 있습니다.
학교에서의 연결 성공, macOS 27.1.1의 실제 라우팅·복구, 게임 RTT/FPS 개선은 아직 검증 전입니다.
클라이언트 UDP(음성 등)는 지원하지 않을 수 있습니다. 로컬 TUN 처리 비용도 남습니다.

DMG의 `.sha256` 파일도 함께 제공합니다. 빌드 테스트는 설정·패키지·로컬 통신 검증이며,
실제 WARP/학교/LoL 테스트를 대신하지 않습니다. 상세 안내는 저장소 `v5/README.md`에 있습니다.
