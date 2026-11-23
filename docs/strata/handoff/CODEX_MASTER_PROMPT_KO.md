# CODEX MASTER PROMPT — MINER STRATA 2.0.0

You are working with a complete Git checkout of `hexagon0401/MINER`, not the partial source snapshot inside this ZIP. Do not treat the handoff ZIP as a standalone source of truth. Before editing:

1. Confirm `git rev-parse HEAD`, `git status --short`, `git branch --show-current` and compare to `REPOSITORY_ANCHOR.json`.
2. If HEAD changed from SHA `7889545ea4c41301b0f75995f541d9c8164e9d16`, summarize differences before using older architecture assumptions.
3. Read `START_HERE_KO.md`, `AUDIT_AND_CORRECTIONS_KO.md`, `BRAND_RELEASE_POLICY_KO.md`, `planning/01_BLUEPRINT_KO.md`, `planning/04_TEST_MATRIX_KO.md`, and `CODEX_G0_G1_PROMPT_KO.md`.
4. Import proposed README preview and artwork into a new feature branch using `python3 tools/prepare_codex_checkout.py --repo . --apply`; skip when the same proposal is already staged, and never replace current `README.md` or existing release assets.
5. Implement only **G0/G1** initially. Preserve Windows cleanup and DNS journal behavior until G2 has a verified service owner. Show source diff, tests, and unverified conditions.
6. Distinguish observed source behavior, reported local diagnostics, and design proposals. Never claim STRATA is already released. Do not expand Riot domains/CIDRs on guesses. Test only on networks where use is authorized.
7. Preserve historical archive, ALPHA updater protocol, identifiers, helper IDs, installation GUID and user state unless a separately tested migration is approved.
8. Later phases G2–G6 each need their own commits, tests and operator review. Do not auto-deploy.

**Readme policy:** `README_STRATA_PREVIEW.md` is a preview; leave `README.md` representing the actually released ALPHA 1.2.3 until STRATA release eligibility is proven. New banner files are under `docs/assets/`.

**Done criteria for first task:** branch created; all files validated; preview README renders both images; G0/G1 work implemented with focused test results; unresolved items documented; `main` untouched; no release published.


### STRATA 이미지 작업 및 ALPHA 원본 보존 (필수)

- 기존 GitHub ALPHA 이미지 `docs/assets/miner-readme-banner.png`, `docs/assets/miner-alpha-v1-release-banner.png`는 절대 덮어쓰거나 삭제하지 말 것. 나머지 과거 이미지를 임의로 일괄 정리하지 말 것.
- 새 `docs/assets/miner-strata-release-preview-banner.png`를 STRATA README 프리뷰에만 반영. `docs/assets/miner-strata-readme-banner.png` 및 `docs/assets/miner-strata-system-banner.png`도 함께 보존.
- ALPHA 축하 배너를 실제로 검사해 **이미지 가로·세로 비율, 폰트, 그림체, 캐릭터 크기, 주변 여백**을 확인하고 STRATA 이미지가 명백히 다른 부분만 수정해라. 원본 ALPHA 바이너리는 ZIP에 없으므로 GitHub 체크아웃에서 불러와야 한다.
- `artwork_archive/` 과거 시안은 이관 ZIP에 보존된 참고자료다. 모두 삭제하지 않는다. GitHub에 별도로 모두 보관하려면 신규 archive 경로에 커밋하는 PR을 제안한다.
- `2.0.0 PREVIEW`는 배포 전 개발 프리뷰로 유지한다. 정식 릴리스 아님.
