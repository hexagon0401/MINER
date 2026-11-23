# Preview 2: macOS 시작·설치 위치 보완

사용자 보고: Open Anyway 후 창 없이 Dock 점핑 → 재설치로 점핑은 해소됨. 이후 Applications에 복사했는데도 복사 안내 오류. `ps` 첫 출력은 비어 있어 사용자 기기의 실제 bundle 경로와 최초 점핑 원인은 확정하지 않았습니다.

확인한 코드 문제는 시작 시 `/Applications/MINER.app` 문자열과의 정확한 일치만으로 설치를 판정한 점입니다. Python의 privileged preparation도 resolve 결과를 고정 문자열에 비교했습니다. 파일 identity(볼륨·inode / samefile)로 대조하여 alias를 처리하고, 다른 복사본·존재하지 않는 설치는 거부합니다.

잘못된 위치에서 Start를 누르면 같은 버전/동일 bundle ID의 시스템 설치본을 새 인스턴스로 엽니다. 잘못된 복사본에서 WARP/TUN을 시작하지 않고, 버전 불일치·반복 handoff는 오류로 남깁니다. 오류에는 실제 실행 위치를 표시합니다. 사용자 Applications·다운로드·DMG 복사본은 고정 시스템 설치본으로 무조건 허용하지 않습니다.

앱 delegate를 NSApplication run loop 동안 명시적으로 유지하며, 재열기 이벤트가 창을 다시 표시하게 했습니다. 비민감 시작 로그에 stage·시각·PID·설치 종류만 기록하고 경로·계정·네트워크 데이터는 기록하지 않습니다.

검증: 고정 엔진 포함 Python 186개 PASS, skip 없음. Swift identity fixture는 alias 일치·다른 복사본/없는 경로 거부를 확인했습니다. Mac AS/Intel DMG에서 `/Applications/MINER.app`을 LaunchServices로 **일반 실행**하여 `isFinishedLaunching`, main event loop, 실제 on-screen 창, reopen, 정상 Quit를 모두 확인했습니다. Start·WARP·TUN 활성화는 요청하지 않았습니다. 기존 UI fixture·root helper·선택 DNS/TUN·업데이터 검사도 PASS했습니다.

[Native CI](https://github.com/hexagon0401/MINER/actions/runs/45157421198) · [검증 JSON](PREVIEW2_VALIDATION.json) · [Preview 2 다운로드](https://github.com/hexagon0401/MINER/releases/tag/miner-strata-v2.0.0-preview.2)

실제 MacBook에서 같은 오류가 사라졌다는 확인과 게임·통계창 시험은 아직 미검증입니다. Mac 27.1.1을 CI에서 실행한 것이 아니며, App Translocation이 사용자 기기의 확정 원인이라고 주장하지 않습니다. Windows 바이너리는 Preview 1을 유지합니다. source의 preview revision은 2로 올렸으나 Windows P2 설치본을 배포하지 않았습니다.
