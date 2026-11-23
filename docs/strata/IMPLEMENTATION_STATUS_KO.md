# STRATA 2.0.0 Preview 1 구현 및 검증 경계

이 문서는 G0/G1 완료 시점의 기록인 `G0_G1_IMPLEMENTATION_KO.md` 이후 상태입니다. 사용자가 남은 단계 개발과 배포를 요청했으며, 실기 시험은 사용자 MacBook에서 수행합니다. 이번 산출물은 정식 승격 없는 프리뷰입니다.

## 구현

| 단계 | 반영 내용 | 남은 증거 |
|---|---|---|
| G2 | 요청 ID 멱등 캐시(최근 128개), 소유 사용자 인증, 영속 세대, 시작 전 ownership 기록, GUI 재부착 | 아래 실기 수명·다중 사용자 시험 |
| Mac 수명 | 기존 root helper·launchd 엔진·DNS journal 유지. 메뉴 막대 열기/중지/종료. 창 Close는 연결 유지, Quit는 명시적 복구. helper가 console owner 변경 시 엔진/DNS 정리 | 실제 강제 종료/로그아웃/재부팅. 로그아웃 시 사용자 WARP 복귀는 미완전하며 다음 로그인 후 Stop으로 확인 |
| Windows 수명 | SCM demand-start 서비스가 worker/Job/guardian 소유. SID ACL·커널 피어 토큰·서버 PID 확인, bounded IPC. 서비스 재시작 시 unfinished 세션은 복구 필요 | native CI의 별도 fixture와 실제 WARP 서비스 계정 호환성 구분 |
| G3 | post_game 결과(USER_REPORT)·회차·시각, H1~H5 가설을 관측/미확인/추가 조사로 분리. 실제 통계 endpoint는 NOT_IDENTIFIED | 현장 실패 요청 식별. HEAD PASS는 로그인/통계 성공 아님 |
| G4 | IPv4/IPv6 FakeIP→SOCKS hostname fixture 확장, 기존 real-IP·일반 HTTPS·연속 TCP 및 DNS 복구 회귀 | DoH·앱 내부 DNS/cache로 선택 DNS를 우회하면 포착하지 못함. 증거 없는 도메인 확장은 보류 |
| G5 | 원문 대신 category-only 엔진 오류 로그 약 1MiB×2, 경고 중복 억제. NIC/DNS 변경 read-only 감시. Mac wake 즉시 재검사 및 15초 주기. 외부 WARP 모드 변경 시 지속형 worker를 종료/덮어쓰기하지 않고 경고 | 24시간 자원 증가율·실기 절전/네트워크 전환 |
| 업데이트 | ALPHA와 동일한 앱/설치 ID·지원 경로 보전. Windows는 STOPPED인 SCM만 설치/제거 전에 정지. 기존 updater 교체/캐시 정리 fixture 유지 | 실제 ALPHA 1.2.3→STRATA→ALPHA 게임 세션 migration, 정식 bridge |
| G6 | native DMG 2종·Setup.exe·진단 도구·SHA·검증 JSON을 모아 prerelease gate 적용 | Mac 10회/Win11 Vanguard/성능·서명 공증 gate 미통과 |

Windows CI는 실제 SCM과 별도 fixture 자식의 Job 소유권, 제어 클라이언트 종료 후 유지, SCM 강제 종료 후 자식 종료, 재시작 시 복구 필요 상태, 다른 사용자 토큰의 pipe 접근 거부를 시험합니다. fixture는 제품 EXE에 넣지 않으며 WARP/DNS/게임을 실행하지 않습니다. 설치된 제품 서비스의 시작·status·재부착·정지 검사는 별도로 수행합니다. 이 결과도 Windows 11/Vanguard 실기 성공으로 표현하지 않습니다.

기존 DNS journal schema 1을 다시 쓰지 않고 별도 `strata-owner.json`으로 소유자/세대를 기록합니다. 기존 lease의 DNS restore는 여전히 임시 DNS가 남아 있으면 기록을 보존하고, 외부 DNS를 무단 덮어쓰지 않습니다. 관리자가 직접 호출하는 legacy CLI까지 새 IPC actor로 통일한 것은 아닙니다.

## WARP 정책과 경로 경계

- 실행 중 WARP Local Proxy를 유지하고 Riot 선택 TCP만 SOCKS5h로 보냅니다. 게임 real IP와 일반 브라우저 real IP는 OS 직접 경로입니다.
- Stop의 복귀 정책은 이전 설정 그대로가 아니라 **Warp / Traffic and DNS 연결**로 고정합니다. KILL SWITCH는 엔진/DNS 정리 후 WARP disconnect입니다. 실패 시 success를 표시하지 않습니다.
- WARP 외부 모드 변경을 감지하면 자동 mode 재설정 루프를 돌리지 않습니다. 사용자 Stop은 고정 복귀 정책을 실행합니다.
- WARP Connecting 때 connect를 반복 발행하지 않습니다. Disconnected는 기존 최대 15초 주기의 제한된 재시도입니다. 지수 backoff나 24h 실측 완료로 표현하지 않습니다.
- DoH·캐시·알 수 없는 Riot 도메인·실제 게임 UDP 품질은 아직 현장 증거가 필요합니다. NetworkExtension/WFP는 entitlement·서명·배포 부담과 추가 회귀를 고려해 2.0 preview에 도입하지 않습니다. 현재 경계가 실제 실패 원인으로 확인되면 후속 PoC를 평가합니다.

## 배포·보존

- main·ALPHA README/배너·Cask·기존 릴리스는 보존합니다. STRATA 소스는 개발 브랜치에, 프리뷰 설치본은 `miner-strata-v2.0.0-preview.1` 별도 태그에 둡니다.
- 프리뷰는 beta 아이콘을 사용합니다. 서명 상태는 native receipt를 기준으로 하며, ad-hoc을 Apple 공증으로 표현하지 않습니다.
- 프리뷰 내 자동 설치와 stable Homebrew 승격은 비활성입니다. 정식 ALPHA 1.2.3 사용자를 프리뷰로 자동 이동시키지 않습니다.
- 실제 ALPHA 배너와 제공 STRATA 시안의 폰트/캐릭터 스타일 정합은 디자인 미완 항목입니다. 원본 이미지를 덮어쓰지 않았습니다.

## 재현 명령과 결과

```bash
PYTHONPATH=v5 python -m unittest discover -s v5/tests -v
```

현재 로컬: 고정 sing-box 1.12.0까지 지정하여 **183개 전부 PASS, skip 없음**. Windows persistent controller의 Riot timeout 후 명시적 Stop까지 엔진 유지 및 DNS/WARP 복구도 별도 mock 장애 주입으로 확인했습니다. 최종 native CI는 각 OS의 고정 sing-box 1.12.0을 설치하여 실행하며 결과는 release receipt와 CI run에서 확인합니다. CI 패키지·TUN·가짜 SOCKS·서비스 시험은 게임 성공 증거가 아닙니다.

Mac CI에서 `getaddrinfo(AF_INET6)`의 시스템 AAAA 응답이 FakeIP가 아닌 경계를 관측했습니다. 실제 선택 DNS listener의 AAAA 응답과 합성 IPv6 TCP→SOCKS 경로는 별도로 검사하며, receipt의 `os_resolver_aaaa_synthetic`와 `os_resolver_aaaa_boundary`에 OS 결과도 보존합니다. 시스템 scope/cache/IPv6 정책의 원인은 아직 미확인입니다. 이를 통계창의 확정 원인으로 처리하거나 Mac의 모든 IPv6 경로가 포착된다고 주장하지 않습니다.

실기 기록: [MacBook 시험 안내](MACBOOK_TEST_KO.md), [10회 결과 CSV](STRATA_TEST_RESULTS.csv). G6 미검증 항목을 완료로 채우지 않습니다.
