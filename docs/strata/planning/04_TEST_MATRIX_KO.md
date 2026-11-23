# Verification & Failure-Injection Matrix (proposal)

| Test | Layer | Stimulus/Setup | Expected | Gate |
|---|---|---|---|---|
| T001 | unit | Riot 서비스 HEAD TLS 타임아웃 | 엔진 ready/서비스 degraded 상태 분리, 오류 코드 보존 | G1 |
| T002 | unit | 진행 JSON 후 최종 명령 실패 | JSON 진행 항목 오류 제목에 노출되지 않음 | G1 |
| T003 | integration | Windows service_verify 실패 | G1에서는 상태·원인 분리와 기존 finally 안전 복구 유지. G2 소유 서비스 완성 전 임의 엔진 지속 금지 | G1 |
| T004 | integration | Mac helper 띄운 뒤 UI 강제 종료 | 지속 상태/경로 유지, 재접속 UI 상태 동기화 | G2 |
| T005 | integration | Windows UI 종료 | 서비스/Job Object owner 유지, 고아 엔진 없음 | G2 |
| T006 | integration | 실제 Stop 명령 반복 | 원본 DNS 및 WARP 복구 멱등; journal 정합 | G2 |
| T007 | integration | 두 UI 창/프로세스의 동시 Connect, Stop | generation/lock에 의한 직렬화 | G2 |
| T008 | integration | DB/lease journal 중간 손상, 엔진 종료 | 원래 DNS 복구 또는 Recovery Required, 성공 위장 없음 | G2/G5 |
| T009 | integration | 일반 DNS 트래픽·브라우저·메신저 fixture | 일반 OS 연결 경로 보전 | G4 |
| T010 | integration | Riot FakeIP TCP | WARP SOCKS domain name 전송 / no direct fallback | G4 |
| T011 | integration | 실제 게임 IP TCP/UDP fixture | 기본 경로가 TUN으로 들어가지 않음 | G4 |
| T012 | integration | IPv6와 앱 DoH | 현행 지원/미포착 경계 가시화, 자동 확장 금지 | G4 |
| T013 | integration | WARP status Connecting/Disconnected | 모드 반복 변경·접속 폭주 없이 degraded 표시 | G5 |
| T014 | integration | sleep/wake, NIC/SSID 변경 | lease/route 재검증, 게임 중 자동 full tunnel 전환 금지 | G5 |
| T015 | security | 비소유 사용자/위조 IPC/임의 바이너리·경로 | 명령 거부/감사 로그(비민감) | G2/G5 |
| T016 | privacy | 진단 기본 모드 | IP/SSID/계정·패킷/쿠키·원문 로그 없음; 자동 업로드 없음 | G3 |
| T017 | real Mac | 반복 LoL 시작→게임→통계 | 10회 연속 성공; 실패 시 30s 기준/로그 시간 구분 | G6 |
| T018 | real Windows 11 | Riot/Vanguard와 설치·서비스/게임 | 실제 디바이스 및 호환성 확인; Server CI 대체 금지 | G6 |
| T019 | release | 1.2.3→2.0 업데이트·취소·rollback·uninstall | user data/lease/AppId/cask 보존·정확한 복구 | G6 |
| T020 | performance | WARP, 1.2.3, 2.0 실기 비교 | ping/packet loss/FPS/click delay/CPU/RAM 분리 측정, 조건 기록 | G6 |

실제 연결을 확인하는 테스트는 사용자 권한과 네트워크 규칙이 허용한 환경에서만 수행한다. 모든 수치는 **목표**이며 완료/측정된 결과가 아니다.

> 추가 시험 T021~T030, Windows T003 수정 이유는 `AUDIT_AND_CORRECTIONS_KO.md`에서 확인한다.
