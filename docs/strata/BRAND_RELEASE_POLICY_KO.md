# Naming and Release Contract — MINER STRATA

## 제품명

- **Product:** MINER
- **Generation II:** STRATA
- **Display brand:** MINER STRATA
- **Target version:** 2.0.0
- **Suggested concise title:** `MINER / STRATA`
- **Meaning:** 지층/레이어. Riot 서비스와 인게임 트래픽이 서로 다른 경로에 고정되고, 상태/복구가 계층별로 분리되는 구조.
- **Tagline proposal:** `Stay connected. Stay divided.`

이것은 새 제품/세대의 브랜딩 제안이지 현행 코드를 이미 바꾼 내역이 아니다. 상표/도메인 독점 사용 가능 여부는 조사하지 않았다.

## 배포 시 특히 주의할 변경 불변식

`MINER STRATA` 브랜딩을 2.0에서 사용자에게 보여주는 것과 release manifest의 `codename=ALPHA` 교체는 **별도 변경**이다. 기존 updater는 ALPHA를 고정 검사한다.

권장 경로: 
1. 기존 코드로 동작하는 ALPHA 계열 bridge 업데이트를 설계하고 안전한 마이그레이션 지원을 검증. (태그·버전 미확정, `1.2.4`는 가능 예시일 뿐)
2. 실제 1.2.3→bridge→2.0 업데이트/롤백 성공 입증 후 STRATA codename/명명 규칙 릴리스.
3. 검증 전에는 `ALPHA` 배포 계약 유지 가능. 사용자 가시 브랜드/메타데이터의 불일치를 릴리스 안내에 명확히 설명.

첫 릴리스에서 macOS bundle identifier, Windows Inno AppId, root helper label, Homebrew `miner` cask name, 기존 DNS journal 경로를 통째로 변경하지 않음.
