# 버전·디자인·실험 보관함

기존 소스, 바이너리, 빌드 결과와 로그를 삭제하지 않고 분류한 보관함입니다. 파일 내용은 Git blob 해시로 보존 여부를 확인합니다.

## 버전별 소스

| 구분 | 보관 위치 |
|---|---|
| v1 | [원본 코드와 빌드 자료](versions/v1/) |
| v2 | [원본 코드와 빌드 자료](versions/v2/) |
| v3 | [원본 코드와 빌드 자료](versions/v3/) |
| v3.7 | [원본 코드와 빌드 자료](versions/v3.7/) |
| v3.8 | [원본 코드와 빌드 자료](versions/v3.8/) |
| v4 | [원본 코드와 빌드 자료](versions/v4/) |
| 초기 UI 디자인 | [디자인 실험](design/ui-dev/) |
| 루트 실험·로그·메타데이터 | [실험 자료](experiments/root/) |

## v5 · beta · ALPHA

`v5/`는 현재 빌드와 테스트 경로이므로 그대로 유지합니다. 베타 2 학교·제보 소스도 삭제하거나 활성 배포에 섞지 않습니다.

| 단계 | 고정된 이력 |
|---|---|
| ALPHA v1 · 현재 배포 | [정식 릴리스](https://github.com/hexagon0401/MINER/releases/tag/miner-alpha-v1) |
| 통합 Beta 1 | [플랫폼 통합 기록](https://github.com/hexagon0401/MINER/releases/tag/miner-alpha-universal-beta.1) |
| macOS Beta 1.1 | [Mac 배포](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1.1) |
| Windows Beta 1 Pearl White | [build 8](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1.1-windows.8) |
| Beta 2 · 소스 보관 | [보관 당시 전체 소스](https://github.com/hexagon0401/MINER/tree/5608728d1882c20727a8e07ffbbc534c707c71b9) · [기능 코드](../v5/community/) |

기존 alpha·delta·beta 태그와 릴리스도 모두 유지합니다. [전체 릴리스](https://github.com/hexagon0401/MINER/releases)에서 이전 파일을 받을 수 있습니다.

## 브랜치 보관

사용이 끝난 CI 기록과 병합된 통합 브랜치는 `archive/branches/<원래 브랜치 이름>` 보관 태그로 옮깁니다. 태그는 원래 브랜치의 마지막 커밋을 그대로 가리킵니다. 열린 PR의 브랜치와 개발·배포·재시도 상태 브랜치는 유지합니다.

[브랜치별 보관 위치](branches.md)와 [파일 해시·원본 경로](inventory.json)에 원래 경로·브랜치·커밋을 기록했습니다.

### 원래 폴더 구조로 복구

```bash
git switch -c restore/legacy archive/snapshots/pre-organization-2026-11-05
```

보관 브랜치를 다시 작업하려면 다음과 같이 복원합니다.

```bash
git switch -c restore/example archive/branches/보관된-원래-브랜치-이름
```

예전 빌드 자료에는 작성 당시 컴퓨터의 절대 경로가 들어 있을 수 있습니다. 이는 원본 보존을 위해 수정하지 않았으며 현재 빌드에 사용하지 않습니다.

## 전체 배포 이력

| 이름 | 구분 |
|---|---|
| [MINER BETA 1 — Windows](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1.1-windows.8) | 과거 프리릴리스 |
| [MINER BETA 1 — Windows](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1.1-windows.7) | 과거 프리릴리스 |
| [MINER BETA 1 — Windows](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1.1-windows.6) | 과거 프리릴리스 |
| [MINER BETA 1 — Windows](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1.1-windows.5) | 과거 프리릴리스 |
| [MINER BETA 1 — Windows](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1.1-windows.4) | 과거 프리릴리스 |
| [MINER BETA 1 — Windows](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1.1-windows.3) | 과거 프리릴리스 |
| [MINER ALPHA v1](https://github.com/hexagon0401/MINER/releases/tag/miner-alpha-v1) | 정식 릴리스 |
| [MINER ALPHA universial Beta 1](https://github.com/hexagon0401/MINER/releases/tag/miner-alpha-universal-beta.1) | 과거 프리릴리스 |
| [MINER BETA 1.1](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1.1) | 과거 프리릴리스 |
| [MINER BETA](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-beta.1) | 과거 프리릴리스 |
| [MINER Alpha](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-alpha.5-dmg.6) | 과거 프리릴리스 |
| [SchoolNet v5.0.0-alpha.4](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-alpha.4) | 과거 프리릴리스 |
| [SchoolNet v5.0.0-alpha.3](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-alpha.3) | 과거 프리릴리스 |
| [SchoolNet v5.0.0-alpha.2](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-alpha.2) | 과거 프리릴리스 |
| [SchoolNet v5.0.0-alpha.1](https://github.com/hexagon0401/MINER/releases/tag/v5.0.0-alpha.1) | 과거 프리릴리스 |

Beta 소스는 `archive/betas/beta2-source`, `archive/betas/macos-beta1.1`, `archive/betas/windows-beta1-pearl-white` 태그로도 확인할 수 있습니다.
