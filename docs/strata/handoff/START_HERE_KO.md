# MINER STRATA 2.0.0 — 통합 Codex 이관 패키지

**현재 제품:** MINER ALPHA v1.2.3. **STRATA 2.0.0:** 개발 계획 + README 이미지 시안, 아직 구현·배포되지 않음.

## 0. 무결성과 범위 (중요)

본 ZIP에는 **기존에 제공받은 88개 핵심 소스 파일의 부분 스냅샷 + 모든 최신 기획/감사/연구자료 + 새 README 이미지 세 장 및 미리보기 + Codex 스크립트**가 있다.

그러나 GitHub `main`의 **전체 1,228개 blob 파일(과거 바이너리 기록 포함)**을 단일 ZIP으로 내려받지는 못했다. 따라서 이 ZIP은 전체 저장소 그 자체가 아니다. 누락 파일을 가짜로 채우지 않는다.

정확한 전체 코드는 반드시 GitHub `hexagon0401/MINER` commit `7889545ea4c41301b0f75995f541d9c8164e9d16`을 Codex에서 clone/fetch해야 한다. Codex의 GitHub 환경에서 체크아웃하면 모든 파일을 이용할 수 있다. 자체 복구 스크립트는 원격 저장소를 다운로드하지 않는다.

## 1. 권장 흐름

1. Codex에서 `https://github.com/hexagon0401/MINER`를 복제하거나 이미 연결된 저장소를 연다.
2. 기준 SHA와 `git status`를 확인한다. 새 브랜치 `codex/strata-2.0`을 만든다.
3. 이 ZIP을 해제하고 저장소 바깥의 참조 위치에 둔다. 처음 복제하는 Codex 환경에서는 `python3 tools/bootstrap_codex.py --destination /workspace/MINER`로 전체 저장소 복제+제안 파일 적용을 한 번에 처리할 수도 있다.
4. `python3 tools/prepare_codex_checkout.py --repo /path/to/MINER`를 실행하여 적용 계획을 보고, 문제가 없으면 `--apply`로 신규 파일만 추가한다. `main`에서 apply 금지, 기존 파일 덮어쓰기 금지.
5. 루트 `README_STRATA_PREVIEW.md`를 미리보기 한다. 새 이미지 세 개는 `docs/assets/miner-strata-*.png`다. 이관 패키지에 기존 시안도 `artwork_archive/`로 보관했다.
6. `CODEX_MASTER_PROMPT_KO.md`를 Codex에 제공하여 **G0/G1** 먼저 수행한다.
7. 전체 소스까지 하나의 ZIP이 필요하다면 전체 체크아웃 안에서 스크립트 `tools/create_full_source_zip.py --repo /path/to/MINER --out /path/to/FINAL.zip`를 사용한다. 새 proposal 파일이 저장소에 존재해야 한다.

## 2. 포함 내용

- `proposal/`: README 시안과 이미지 세 장, `docs/strata/` 기획 문서 (원본 안정판 README를 덮어쓰지 않음)
- `planning/`: 기존 설계/ADR/상태 스키마/백로그/테스트 매트릭스
- `research/`: 스쿨넷 원문과 전체 1.2.3→2.0 이관서
- `reference_partial_source_snapshot/`: 기존 이관 패키지의 88개 파일 (전체 소스 아님)
- `reference_release_proof/`: 현재 ALPHA 배포 검증 메타데이터
- `tools/`: 전체 소스 저장소 복제/제안파일 적용/완전 소스 ZIP 생성/체크섬 검증
- `SHA256SUMS.txt`, `HANDOFF_MANIFEST.json`: 파일 무결성 자료

## 3. 중요한 제한

STRATA 이미지는 UI 시연이나 실제 통계 API 성공 증명이 아니며, 릴리스 자료가 아니라 README 초안이다. 전체 학교망 차단 정책을 추정하지 않는다. 사용자 학교망에서 실제 게임 연결 허용 여부를 확인하지 않았다. 실제 배포를 하지 않는다.

## 4. ALPHA 이미지 보존 및 새 배너

원본 ALPHA README/릴리스 배너는 이 패키지에 바이너리가 포함되지 않았으나 실제 전체 GitHub 체크아웃에는 존재한다. **절대 교체하거나 삭제하지 말 것.** 이번 최신 `proposal/docs/assets/miner-strata-release-preview-banner.png`는 예전 ALPHA 축하 배너와 비슷한 디자인의 새 시안이다. `proposal/docs/strata/ALPHA_ARTWORK_PRESERVATION_KO.md` 및 `ALPHA_AND_STRATA_ARTWORK_MANIFEST.json`에서 원본 blob 식별자와 저장 규칙을 확인한다.

Codex에서 GitHub ALPHA 배너를 열고 실제 해상도·폰트·그림체를 비교한 다음 수정할 필요가 있으면 STRATA 이미지만 변경하라. **정확한 일치 여부는 아직 검증되지 않았다.**
