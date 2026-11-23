# MINER STRATA 2.0.0 Preview 2 — macOS 시작·설치 위치 보완

macOS 전용 수정 프리릴리스입니다. Windows 설치본은 [Preview 1](https://github.com/hexagon0401/MINER/releases/tag/miner-strata-v2.0.0-preview.1)을 유지합니다. main·ALPHA·Homebrew·기존 릴리스는 변경하지 않습니다.

- 앱 delegate를 run loop가 종료될 때까지 명시적으로 유지하고 Dock/Finder 재열기 시 창을 다시 표시합니다.
- `/Applications/MINER.app` 문자열 비교를 실제 파일 identity 비교로 바꿔 볼륨 alias·대소문자 경로 차이를 처리합니다. 다른 앱 복사본을 설치본으로 오인하지 않습니다.
- 다른 위치에서 실행했어도 같은 버전의 설치본이 Applications에 있으면, Start에서 그 설치본을 새 인스턴스로 엽니다. 임시/DMG 복사본에서는 WARP·TUN을 시작하지 않습니다. 반복 전환은 제한합니다.
- 설치본이 없거나 버전이 다르면 실제 실행 위치와 필요한 조치를 표시합니다. root helper도 설치 위치의 파일 identity를 확인합니다.
- 비민감 시작 단계는 `~/Library/Logs/MINER/startup.jsonl`에 최대 64KB로 기록합니다. 계정·주소·실제 경로를 기록하지 않습니다.

## 검증 범위

이전의 직접 실행 UI fixture에 더해, `/Applications/MINER.app`을 LaunchServices(`open`)로 **일반 실행**한 뒤 실행 완료·실제 창 표시·main event loop·Dock/Finder 재열기·정상 종료를 확인합니다. 이 시험에서는 Start를 누르지 않으며 WARP나 TUN을 활성화하지 않습니다. 결과는 DMG 검증 JSON의 `updater.normal_launch`에 포함됩니다.

사용자의 Dock 점핑 현상은 재설치로 해소됐다는 보고를 받았습니다. 해당 현상의 확정 원인은 아직 확인되지 않았습니다. 설치 위치 오류의 실제 경로도 사용자 기기에서 추가 확인이 필요합니다. CI를 통과한 것과 같은 기기의 증상이 해결됐다는 것은 구분합니다.

## 설치

현재 MINER를 종료하고 DMG의 MINER.app을 **시스템 `/Applications`**에 교체한 뒤 그 앱을 다시 엽니다. Dock의 이전 항목이나 DMG에서 실행했던 창 대신 설치본을 열어주세요. 이 버전의 helper를 처음 사용할 때 한 번 관리자 승인이 필요할 수 있습니다. Mac 앱은 별도 Developer ID 설정이 없다면 ad-hoc 서명·미공증입니다.

연결 엔진·선택 라우팅 원리는 유지합니다. 실제 LoL 통계창·장시간 게임 및 Windows 11/Vanguard 합격 여부는 미검증입니다.
