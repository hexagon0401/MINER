# ALPHA / STRATA 시각 자료 보관 및 비교 원칙

## ALPHA 원본 파일 (GitHub 저장소에 존재 확인)

GitHub `hexagon0401/MINER`의 기준 커밋 `7889545ea4c41301b0f75995f541d9c8164e9d16`:

- `docs/assets/miner-readme-banner.png` (Git blob `793f44568c5a97be783e7535df751e03321f8a6f`)
- `docs/assets/miner-alpha-v1-release-banner.png` (Git blob `ba41d762effb1e0ce6f26f70f530b61816698045`)

**원본 PNG 바이너리는 이 이관 ZIP에 포함되지 않는다.** 이유는 현재 환경에서 전체 GitHub 소스를 내려받을 수 없기 때문이다. 위 두 원본은 Git 저장소에는 포함되어 있다. Codex에서 체크아웃한 뒤 원본을 열어 픽셀 크기·타이포·이미지 비율을 직접 비교해야 한다. 현재 이 패키지는 원본 ALPHA의 정확한 폰트 이름/크기를 검증한 상태가 아니다.

## STRATA 새 배너

- `docs/assets/miner-strata-readme-banner.png`: 기존 제안한 README용 긴 배너 (보존)
- `docs/assets/miner-strata-system-banner.png`: 시스템 분리 개념 배너 (보존)
- `docs/assets/miner-strata-release-preview-banner.png`: 이번 요청에 따라 최신 **ALPHA 릴리스 축하 배너와 비슷한 방향**으로 제작한 STRATA 2.0.0 개발 프리뷰 (PNG 원본 2172×724)
- `artwork_archive/`는 이전 생성안 4개를 보관하는 **이관 패키지 전용** 디렉터리다. 저장소에 자동으로 전부 복사하지 않는다.

## 안전한 이관 규칙

1. `docs/assets/miner-alpha-v1-release-banner.png` 및 `docs/assets/miner-readme-banner.png`를 **절대 지우거나 덮어쓰지 않는다.** 과거 로고, 캐릭터, 베타 에셋, 릴리스 포스터도 보존한다.
2. STRATA는 별도 파일명으로 추가하고, README 미리보기 문서만 새 이미지를 참조한다. 안정판 루트 `README.md`는 변경하지 않는다.
3. 원본 ALPHA 배너를 실제로 열어 **해상도·비율·여백·색·폰트/글자굵기·선 두께·캐릭터 비율**이 충분히 비슷한지 확인한다. 일치하지 않으면 STRATA 디자인만 수정한다.
4. 이미지 보관을 GitHub에 영속화하려면 새 이미지 파일을 작업 브랜치에 커밋하고, 필요한 경우 이전 초안은 별도 보관용 `docs/assets/archive/`에 명시적으로 추가한다. **이 패키지를 생성했다고 GitHub에 자동 저장되지는 않는다.**
5. 지금은 `2.0.0 PREVIEW`이며 **정식 릴리스 축하 배너라고 표시하거나 가짜 다운로드 링크를 만들지 않는다.**
6. 이전 디자인을 제거해야 하는 경우에도 사용자에게 보여준 뒤, 별도 archive 경로와 Git 추적 여부를 확인하고 처리한다.
