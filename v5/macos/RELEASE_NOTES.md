macOS 우선의 **SchoolNet v5 Alpha** 테스트 배포입니다.

alpha.4:
- 'WARP 자동 연결'과 '시작'이 warp-cli로 Local Proxy/포트 40000을 설정하고 SOCKS5 원격 DNS·TLS·warp=on을 검증합니다.
- 정상 프록시에는 재연결하지 않으며, 오류 시 직접 연결로 재시도하지 않습니다. 'WARP 끄기'는 v5를 먼저 중지합니다.
- 빈 웹/영상의 원인 후보인 Riot/League CEF Helper 경로를 추가하고 QUIC 거부로 HTTPS/TCP 폴백을 유도합니다. 실제 Riot 영상 재생은 사용자 환경에서 확인해야 합니다.
- 관리 중인 구버전 런타임은 검증 후 교체하며 사용자 설정과 로그를 보존합니다.

alpha.3: 앱 내부 한글 안내 파일을 `UserGuide.txt`로 바꿔 파일명 정규화에 따른 resource seal 오류를 방지합니다. DMG 마운트뿐 아니라 다른 폴더로 앱을 복사한 뒤에도 서명을 검사합니다.

- Apple Silicon / Intel DMG를 각각 제공합니다. 앱을 Applications로 드래그해 설치합니다.
- Python과 sing-box 엔진을 포함합니다. 개인용 Cloudflare WARP는 별도 설치가 필요합니다.
- 앱에서 사전 점검, 시작, 중지, 로그 확인, 제거를 할 수 있습니다.
- WARP Local proxy(포트 40000)로 Riot/LoL 클라이언트 TCP를 전달하고 게임 데이터는 직접 연결합니다.
- macOS 관리자 인증은 시작/중지/제거에 사용합니다. 자동 부팅 항목은 설치하지 않습니다.
- 제거는 앱의 '제거' 버튼으로 진행하세요. WARP와 기존 v1~v4는 유지합니다.

Apple 인증서를 설정하지 않은 빌드는 **ad-hoc이며 공증이 없습니다**. macOS가 실행을 제한할 수 있습니다.
Developer ID 인증서와 공증 키가 설정되면 앱·DMG의 서명/공증을 검증하며, 실패 시 ad-hoc으로 대체하지 않습니다.
실제 signing 모드와 공증 결과는 각 DMG의 `.verification.json`에서 확인하세요. 인증서 발급은 `v5/docs/SIGNING.md`를 참고하세요.
학교에서의 연결 성공, macOS 27.1.1의 실제 라우팅·복구, 게임 RTT/FPS 개선은 아직 검증 전입니다.
클라이언트 UDP(음성 등)는 지원하지 않을 수 있습니다. 로컬 TUN 처리 비용도 남습니다.

DMG의 `.sha256` 파일도 함께 제공합니다. 빌드 테스트는 설정·패키지·로컬 통신 검증이며,
실제 WARP/학교/LoL 테스트를 대신하지 않습니다. 상세 안내는 저장소 `v5/README.md`에 있습니다.
