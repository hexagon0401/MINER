# MINER — UI/Animation Handoff v1.0

**MINER** — *Makes Internet Not Eternally Restricted*  
**Tagline:** Dig your way out.

Small, lightweight macOS desktop utility designed around an adorable student-made miner escaping a fictional SchoolNet prison by digging a tunnel. This bundle is intended for direct use by Codex in the existing MINER app. **This bundle contains presentation/UI assets only; it does not implement a proxy, VPN, routing, tunneling, privilege escalation, or network bypass.**

## Start here

1. Read [`DESIGN_SPEC.md`](DESIGN_SPEC.md) completely: screen placement, visual tokens, UX, real state mapping, accessibility, implementation boundaries.
2. Open [`preview/index.html`](preview/index.html) locally in a browser. It is a self-contained functional visual prototype with simulated states (no network side effects).
3. Import [`assets/mascot-approved.png`](assets/mascot-approved.png). **This is the user's exact approved character; DO NOT redraw, recolor, reconstruct, or replace it.** Use `mascot-runtime-256.png` when performance matters.
4. Load [`assets/copy-ko.json`](assets/copy-ko.json) for messages. It includes all four Master Yi parodies, eight other champion lines (including three additional ones), and original Korean jokes.
5. Reuse vector background layers from `assets/*.svg` in SwiftUI or replace with native vector equivalents; keep same flat, lightweight language.

## Deliverables

| Path | Function |
| --- | --- |
| `DESIGN_SPEC.md` | Authoritative visual/interaction specification and Codex task checklist |
| `preview/index.html` | Static offline UI simulation for states and transitions |
| `assets/mascot-approved.png` | **Approved original mascot, unmodified**, 1254×1254 transparent |
| `assets/mascot-runtime-256.png` | 256×256 display-sized downsample, transparent |
| `assets/school.svg` | Minimalist SchoolNet school illustration for idle/start sequence |
| `assets/tunnel.svg` | Tunnel scene background and dark capsule shape |
| `assets/rock.svg` | Error blockage accent |
| `assets/spotlight.svg` | Success light from above |
| `assets/check-fallback.svg` | Preview-only green check; use native macOS checkmark in actual app |
| `assets/copy-ko.json` | Status copy, League of Legends parodies, jokes, display rules |
| `assets/tokens.json` | Color/geometry/animation tokens |
| `assets/app-icon-*.png` | Optional experimental app icon directions from earlier exploration; not mascot assets, not final without review |
| `assets/storyboard-reference.png` | Optional staging reference from earlier exploration; not an implementation requirement |

## Prime directive

The UI must feel like a **round, clunky toy**: tiny pickaxe swings (`뚝딱 뚝딱`), square dirt pixels, mild tunnel shake, small school above, glowing exit check. Flat 2D is correct. Realistic mining, detailed pixel-art scenery, heavy canvas engines, and long sprite/video assets are wrong for this project.

## Constraints

- macOS 27 Liquid Glass: native materials and symbols wherever possible; preserve macOS window behavior.
- Fixed comfortable window ~540×492 pt, minimum ~500×470 pt, no full screen required.
- Ensure actual operation state labels are **truthful**: `WARP 준비 완료` must not be reported as complete engine routing; `연결 완료` means engine is running, not that real game traffic has been externally validated.
- UI does not trigger platform operations in the prototype. The production UI should only drive the app's existing, tested workflow.
- All joke lines are optional rotating secondary copy; never replace critical errors, permission requests, or system status.

## Licensing note

LoL champion references are short, original *parody text* rather than dialogue audio, character artwork, game assets, or a suggestion of Riot sponsorship. If public distribution is planned, perform a separate trademark/copyright review. The user-supplied school/ministry logos or icon explorations should also undergo licensing/branding review before publication.
