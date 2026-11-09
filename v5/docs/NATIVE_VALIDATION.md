# 네이티브 자동 검증과 실기 합격 기준

## ALPHA v1.2.0 배포 검사

macOS Apple Silicon·Intel, Windows Server 2025에서 `selective_smoke.py`로 실제 선택 TUN 경로·OS DNS/HTTPS·연속 TCP의 SOCKS 원격 호스트 이름 전달·정상/엔진 강제 종료 후 DNS 복구를 검사합니다. Windows는 독립 복구 감시 프로세스, 공개 v1.1.1 위 덮어쓰기 설치 및 사용자 데이터 보존도 검사합니다. 네트워크 시험은 실제 WARP 대신 로컬 SOCKS fixture를 사용합니다. 필수 검사 실패 시 배포하지 않으며 플랫폼별 JSON이 해당 실행의 증거입니다.

v1.2.0은 실제 게임 서버/일반 앱 IP가 TUN을 통과하지 않습니다. 아래의 TUN direct/프로세스 매칭 설명과 초기 확인 범위는 이전 alpha의 기록이며, 실제 학교망·개인용 WARP·LoL·Vanguard의 실기 합격 항목은 여전히 별도입니다. CPU·게임 RTT·FPS 수치를 자동 시험으로 만들어내지 않습니다.

## 이전 alpha의 실기 검증 계획 (보관 기록)

대상은 사용자 제공 **macOS 27.1.1 + 개인용 WARP**입니다. 이 환경은 개발 컨테이너에 없으므로 아래 항목의 결과는 아직 비어 있습니다. 학교 연결 조건과 게임 서버는 프로그램의 로컬 테스트로 대체할 수 없습니다.

## 현재 확인한 범위

- Python 제어 프로그램, 설정 유효성, 기존 파일 보호, 단일 실행 잠금.
- 공식 SHA-256을 확인한 sing-box 1.12.0의 실제 macOS/Windows 설정 문법 검사. 이는 Linux 바이너리의 스키마 검사이며 해당 OS에서의 실행 검증은 아님.
- 로컬 SOCKS5 성공·실패, 부분 응답·연결 종료 처리, TCP 측정 결과의 실패 구분.
- 실제 엔진 → 테스트 SOCKS 서버 → 로컬 목적지 TCP 체인. TUN을 만들지 않는 대체 인바운드로 엔진 outbound를 검증함. 실제 WARP 연결 및 OS 프로세스 매칭을 검증한 것은 아님.
- 제어 프로세스에 SIGTERM을 보냈을 때 테스트 자식의 정상 종료와 잠금 해제. 실제 엔진의 OS 라우트 복구 검증은 아님.
- 설치 파일 변조 시 SHA-256 불일치로 거부, 알려진 파일만 추출. macOS Gatekeeper/아키텍처 호환성은 실기 미검증.

## 순서

1. 실행 전 WARP 버전·모드, OS 버전, 실제 Wi-Fi 인터페이스, 기존 VPN/프록시, `route -n get default`, `netstat -rn`, `scutil --dns` 결과를 로컬에 기록합니다. 계정 토큰, lockfile 인증정보, 실행 인수나 전체 패킷 내용을 수집할 필요는 없습니다.
2. 전체 터널을 끄고 Local proxy를 연결합니다. 아직 게임에 들어가지 않은 상태에서 `doctor`를 실행합니다. Mode 출력이 다르면 거부 원인을 확인하고 검사 자체를 생략하지 않습니다.
3. v5를 실행한 뒤 클라이언트를 새로 시작합니다. 로그인·친구 목록·채팅·로비가 유지되는지와 클라이언트 로그의 `warp` 경로를 확인합니다. 연결 실패가 DNS/TCP/TLS/앱 중 어디서 발생했는지 구분합니다.
4. 연습 모드에서 게임 실행 파일의 실제 이름과 `direct` 경로를 확인합니다. 가능하면 `route -n get 실제게임서버IP`와 OS 연결 관찰을 교차 확인합니다. TUN direct outbound는 로컬 중계를 거치므로 단순 기본 라우트 하나만으로 직접 경로 여부를 판정하지 않습니다.
5. 같은 Wi-Fi·동일 조건에서 직접 연결 기준과 v5를 각각 여러 번 비교합니다. 사용자가 이미 직접 게임 접속이 되는 조건을 기준으로 하되, 실게임 중 WARP를 반복 전환하는 실험은 피합니다. 일반 핑, 웹 TCP 측정, DoH 시간과 게임 내 표시 RTT를 혼동하지 않습니다.
6. 게임 종료 후 클라이언트 복귀, 채팅·로비 유지, 재접속을 확인합니다. **WARP 전환 없이 한 번 이상 게임 → 클라이언트 → 다음 게임**을 성공해야 핵심 목표를 통과한 것입니다.
7. Ctrl+C 후 실제 경로·DNS·일반 인터넷 복구를 확인합니다. 이어서 v5 재실행, 프로필 재생성, Wi-Fi 재접속도 확인합니다. WARP 프록시 자체 장애 시 Riot 클라이언트·Riot DNS는 실패할 수 있지만 일반 웹의 DNS·HTTPS는 직접 경로로 유지되어야 하며, 게임 데이터가 전체 터널로 자동 변경되면 안 됩니다.
8. IPv4/IPv6, Apple Silicon/Intel은 테스트한 조합만 따로 기록합니다. Windows는 같은 기준과 관리자/Wintun/Vanguard 호환성을 추가 검증한 뒤 지원 완료로 표시합니다.

## 잠정 성능 기준

아래 수치는 **개발 목표**이며 실측 결과가 아닙니다. 학교망의 변동이 크면 반복 측정으로 차이를 분리합니다.

| 지표 | 잠정 합격 기준 | 측정 대상 |
|---|---|---|
| 게임 RTT 중앙값 | 직접 연결 기준 대비 +5ms 이내 | 동일 조건의 게임 내 RTT |
| 게임 RTT p95 | 직접 연결 기준 대비 +10ms 이내 | 시간별 RTT 표본 |
| 반복 지연 급증 | 기존에 없던 400ms급 반복 급증 없음 | 원시 RTT 표본·이벤트 시각 |
| 연결 유지 | 게임 중 끊김 및 클라이언트 복귀 재시작 불필요 | 연습 세션 반복 |
| CPU | 제어 프로세스가 대기 상태, 엔진 비용을 별도 기록 | Activity Monitor/프로세스 CPU |
| FPS | 같은 그래픽 설정에서 기준 대비 악화 여부 별도 비교 | 게임 FPS 표본 |
| 종료 복구 | v5가 만든 경로 제거, 일반 인터넷과 DNS 정상 | 실행 전후 상태와 기능 검사 |

CPU·메모리·FPS 수치도 아직 측정하지 않았습니다. TUN 직접 전달에서 위 기준을 못 맞추면, 실제 확인한 게임 목적지의 host route 제외를 검토하거나 네이티브 앱별 라우팅으로 구조를 바꿔야 합니다. TCP 벤치마크가 빠르다는 이유로 게임 성능 합격으로 처리하지 않습니다.

## 최소 결과 기록

```json
{
  "os": "macOS 27.1.1 (user-reported; verify locally)",
  "warp_version": null,
  "warp_mode": "Local proxy",
  "engine_version": "1.12.0",
  "client_process_match_verified": false,
  "game_direct_path_verified": false,
  "client_return_without_restart": null,
  "baseline_game_rtt_median_ms": null,
  "v5_game_rtt_median_ms": null,
  "baseline_game_rtt_p95_ms": null,
  "v5_game_rtt_p95_ms": null,
  "engine_cpu_observation": null,
  "route_dns_restoration_verified": false
}
```
