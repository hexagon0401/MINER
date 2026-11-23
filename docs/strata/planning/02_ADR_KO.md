# MINER 2.0.0 Architectural Decision Records (초안)

| ADR | 제안 결정 | 대안 | 재검토/반증 조건 |
|---|---|---|---|
| 001 | UI 비종속 Connection Supervisor | 현 GUI 소유 세션 | UI 종료 중 DNS/엔진 자동 복구를 보장할 수 없을 때 |
| 002 | 1.12.0 선택 FakeIP/TUN 기반 점진 개선 | 광범위 앱별 TUN/NE/WFP | 실제 미포착 서비스 세션이 P0 원인으로 입증되고 대안의 권한·성능·배포 조건 충족 |
| 003 | Local Proxy는 별도 설치된 개인 WARP 사용 | 자체 VPN 구현/비공식 토큰 | Cloudflare 공식 지원 계약이 바뀌거나 사용 불가능해질 때 |
| 004 | 컴포넌트 상태/관측 근거와 TTL 분리 | 5단계 단일 running | Riot 상태와 엔진 상태 오표시가 완전히 제거되지 않을 때 |
| 005 | 프록시 검사 실패는 국소 DEGRADED | 서비스 검증 실패=전체 Stop | DNS/엔진이 실제로 손상되었다는 추가 증거가 있을 때 |
| 006 | 명시적 Stop/로그아웃에서 안전 복구, 재부팅 자동시작 OFF | 무기한 자동 서비스 | 명시적 사용자 opt-in 및 안전한 부팅 복구 설계 입증 |
| 007 | 2.0 출시 ALPHA 호환 계약 유지 | 즉시 코드명 교체 | 1.2.3 updater에서 새 세대로 이동이 입증된 1.2.x bridge가 있을 때 |
| 008 | 민감한 로그 수집 금지·능동 진단 opt-in | 세션 원문 로그 / MITM | 개인정보/약관/최소 권한 요건을 준수하면서 필요성을 입증한 경우에만 검토 |
| 009 | Riot 경로 직접 fallback 및 강제 full tunnel 전환 금지 | 네트워크 실패 시 자동 우회 | 사용자 명시 동의/합법적 정책과 실기 검증이 별도로 확인된 경우에 한해 다시 논의 |

**후보 비교:** A: Persistent service+Selective TUN = 가장 작은 회귀 위험, 작동 범위 불완전. B: OS-native app capture = 범위 확대 잠재력, Mac MDM/entitlement 및 Windows 서명/호환 제약. C: Official app proxy = 간단한 범위 제어 잠재력, Riot 공식 지원 확인 전까지 불가. 2.0 출시 기준안은 A.

| 010 | WARP 이전 모드 복구는 현행 미구현. 소유권·충돌·복귀 정책을 G2에서 명시 | Warp 고정 복귀 | 실제 사용자 WARP 상태를 안전하게 보존할 수 없을 때 UX 상 경고와 정책 고정 |
