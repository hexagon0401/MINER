# MINER — Production UI & Motion Design Specification

Version 1.0 · 2026-11-04 · macOS utility · Korean primary UI

## 1. Objective and visual direction

**MINER — Makes Internet Not Eternally Restricted**  
**Dig your way out.**

The app symbolizes an escape from school network restrictions: a tiny school building above ground, a toy-like miner, a dark tunnel that is simultaneously a **loading track**. The miner hits a wall with a pickaxe, square dirt particles fall, and the loading track jolts with each hit. On successful startup a skylight opens, the miner looks up, a native Apple green check appears, and the words **연결 완료** are shown. Humor is Korean student black comedy; the engineering status remains sober and precise.

Design pillars:

1. **Unmodified approved mascot.** Use the exact user-provided transparent PNG (`mascot-approved.png`) as the master. He has a butter-yellow helmet, white helmet stripe, small black square eyes, a simple brown mouth, round peach head, navy body, two dark boots, wooden brown pickaxe handle and softly curved silver head. No aesthetic reconstruction or new eyes/face/gear.
2. **Toy-like motion.** A few CSS/SwiftUI transforms and 3–5 falling square particles. Do not use realistic character animation, complex terrain rendering, frame-by-frame 3D, or large video/Lottie bundles.
3. **Modern native shell.** macOS Liquid Glass material and recognizable traffic lights; use frosted transparent panels, small spacing, SF typography, understated hairline separators. **Scene only** is matte navy for readability.
4. **Progress is truthful.** The technical phase, not a joke or fake percentage, governs the loader. A long verification may hold on the current phase with a gently repeating pickaxe; never fake completion. Gray milestone ticks fill on actual success callbacks.
5. **Humor is a secondary channel.** Nerd messages are tucked underneath status; errors, administrator permission instructions, and accessibility labels take precedence.

## 2. Window — exact recommended geometry

Use a single floating, non-fullscreen native macOS window. Initial size **540 × 492 pt** (not image pixels). Minimum **500 × 470 pt**; optional expansion to 580×540 for larger text. Native titlebar height is OS controlled (~28–38 pt), so the following positions are **content-relative**, not a requirement to fake the actual macOS traffic lights.

Suggested layout with left/right 24pt inset and 14pt gaps, intrinsic heights rather than absolute y values:

| Block | Approx. height | Contents and alignment |
| --- | ---: | --- |
| Titlebar | System-managed | Native close/minimize/zoom (allow zoom to be disabled for small utility); title `MINER` |
| Header | 64pt | Left `MINER` 24pt semibold; slogan `Dig your way out.` 11pt; right tiny capsule state chip (`대기`, `연결 중`, `실행 중`, `오류`) |
| Main stage | 184pt | Dark navy rounded capsule/scene, radius 24pt; stage art and miner centered in a **single horizontally scrolling visual**, no decorative fullscreen background |
| Status panel | 80pt | Title 16pt semibold; exact technical subline 12pt; quiet 5-tick progress at bottom; optional witty line in muted 12pt, never same prominence as title |
| Primary actions | 52pt | One dominant `시작` button (around 308pt wide), and 124pt secondary `중지` button; two buttons share height 44pt and 12pt gap. Disable unavailable action, never swap both into confusing identical-primary style |
| Tool row | 42pt | `WARP 자동 연결` at left (secondary); `사전 점검`, `상태·로그`, `도움말` tucked into a `⋯ 도구` menu at right. Settings also includes `제거`, with confirmation |
| Bottom inset | 12–16pt | Optionally tiny connection badge `WARP: 연결됨/연결 안 됨/검증 중` and note of proxy type. Avoid an always-open raw logs pane |

Spacing is responsive: content frame is ~492pt wide. At smaller height, reduce **vertical gaps**, not character readability; status explanation wraps to max 2 lines. Do **not** reintroduce the alpha's 8 equal-weight gray buttons or full-height console. The `status/log` window should be a sheet or collapsible diagnostics, including copy button and privacy-conscious redaction.

### Suggested in-scene composition

Background: #080D15 / #141C2B soft vertical gradient, **not** translucent (the container glass outside already provides depth). Rounded rectangle radius 24pt; hairline stroke low-opacity white.

- **Idle:** small simplified gray SchoolNet building from `school.svg`, roof near upper center. A tiny light-cream ground line runs along middle. Approved mascot small (~74pt) sits to lower right with pickaxe. Atmosphere is dark but cute, not dystopian realism.
- **Start transition:** school shifts up and shrinks while the composition pans down ~20pt within **600ms**; no separate screen or page jump. A short vertical shaft grows from school down to tunnel. Then the view becomes a **horizontal tunnel capsule**.
- **Mining:** near-black tunnel spans x=25 to x=width−25, y approximately 65–156. An earth-colored unmined wall stands just in front of the miner; revealed dark tunnel expands left-to-right. The mascot stands at boundary, face still consistent with approved PNG; his whole body bobs 1pt and pivots 4–6° as a single cutout. This is intentional toy puppet movement.
- **Success:** near rightmost end, opening above tunnel grows; very soft light shaft (from `spotlight.svg`) descends, approved mascot rotates −8° as if looking up, then native `checkmark.circle.fill` green icon appears above. `연결 완료` crossfades in. Do not show an unjustified 100% while still waiting for engine callback.
- **Error:** a one-piece flat rock (from `rock.svg`) blocks the front. Pickaxe bounces *once*, scene jolts twice ≤2pt, a few pixels settle. Error chip red and reason shown in normal UI. No alarming screen-wide flash.
- **Stop:** digging ceases immediately; `연결 중`/`실행 중` updates to `중지 중...` where relevant and finally `중지됨`. Character sits back or returns to tiny school. Never imply WARP was disconnected if only engine stopped.

## 3. Color, type, materials

Canonical tokens in `assets/tokens.json`:

| Element | Hex / native equivalent | Application |
| --- | --- | --- |
| Shell base | SwiftUI `.ultraThinMaterial` or `.regularMaterial` | Liquid Glass frosted window and small tool plates |
| Primary navy | `#0E131F` | Titles on light shell; navy backgrounds |
| Cave black | `#080D15` | Loading tunnel / stage |
| Cavern blue | `#141C2B` | Depth behind miner; no noisy texture |
| Frosted white | `#E6E8E6` | Soft contrasts / borders / labels |
| Signature electric green | `#0EFB2E` | Brand accents, not Apple semantic check substitute |
| Native success | macOS semantic green, fallback `#29C85E` | `checkmark.circle.fill`, `연결 완료` |
| Soil beige | `#D0A579` | 3–6pt dirt squares at impact |
| Failure | semantic red, fallback `#FF5A61` | Failure badge and small rock indication |
| Character yellow | PNG native yellow | Do not recolor mascot |

Typography native `.system`: MINER 24pt semibold; primary status 16pt semibold; details 12pt regular; button 14pt semibold; slogan 11pt medium. Button corners 13pt, tool chip 11pt, scene 24pt. Avoid excessive blur behind dark scene and avoid glass overlays on top of the mascot (preserve the transparent alpha / bright yellow).

### Light/dark

Prefer system appearance, with material dynamic and semantic text colors. The dark cave scene remains navy in both appearances. On light material dark text; on dark material frosted-white text. Ensure sufficient contrast at 13pt; check text at 100%, 125%, 150% scaling. Do not rely on the green accent alone for status.

## 4. Actual workflow, labels and stage logic

These are **UI mappings of the existing described pipeline**, not an instruction to change connection implementation.

| Step | Existing pipeline event | Display | Motion | Mark completed only when |
| ---: | --- | --- | --- | --- |
| 0 | Idle | `탈옥 준비` / “시작하면 연결 경로를 점검합니다.” | Small school, miner idle | No operation |
| 1 | WARP CLI check | `곡괭이 챙기는 중...` / “WARP CLI와 명령 지원 여부 확인” | School shrink, shaft appears | CLI present and required commands supported |
| 2 | WARP local proxy setup/reuse at 40000 | `40000번 굴 입구 확보 중...` / “WARP Local Proxy 연결 확인” | Tunnel extends, pickaxe repeats | Local Proxy verified/reused; no conflicted full tunnel |
| 3 | HTTPS over proxy, TLS validation, `warp=on` check | `가짜 출구인지 확인 중...` / “TLS 인증 및 warp=on 검증” | More dirt pixels, no premature success | TLS and WARP-on request both genuinely pass |
| 4 | OS authorization | `관리자님, 땅 좀 파겠습니다...` / “macOS 관리자 인증 대기” | Pause pickaxe; quiet idle bob | Admin authorization accepted |
| 5 | Start split routing engine | `클라는 땅굴로, 게임은 정문으로.` / “클라이언트/WARP · 게임/직접 경로 분리” | Push to final tunnel segment | Engine/process ready and expected routing configuration applied |
| Success | Engine operational | `연결 완료` / “분리 라우팅 엔진 실행 중” | Ceiling skylight, looks up, **native** green check | State machine actually reports running; not synthetic timer |
| WARP-only success | User clicked `WARP 자동 연결` | `WARP 준비 완료` / “WARP 검증 완료 · 분리 라우팅 미시작” | Small green WARP chip; **do not play full escape success** | Steps 1–3 complete |
| Stop | Stopping/engine stopped | `중지 중...` then `오늘은 모범생 모드.` | Mine motion stops, scene settles | Engine shutdown confirmed |
| Failure | Any stage fails | `돌덩이 억까 실화냐.` + **real error** | Rock, single bounce, red badge, retry available | Actual error handled |

Progress track: five small nodes representing 1–5, each only fills when the underlying step completes. For WARP-only 1–3 nodes may fill and the last two remain dim; place a `WARP 준비 완료` label, **not** `연결 완료`. Do not show numeric percent unless grounded in actual measurable progress. `start` performs 1–5; `WARP 자동 연결` only 1–3. On retry keep prior check results only if the underlying engine validates they are still current.

The underlying traffic separation summary may be shown under `도움말 → 작동 방식`: LoL client/web helper over local WARP proxy, actual game direct path, DNS encrypted via WARP. Do not state all application traffic is tunneled; do not promise latency improvement or success.

### Real state API shape (adapt to project)

```swift
enum MinerUIPhase: String {
    case idle, cliCheck, proxyConnect, tlsVerify, adminAuth, routing
    case warpReady, running, stopping, stopped, error
}

struct MinerViewState {
    var phase: MinerUIPhase
    var mode: OperationMode // .warpOnly / .fullStart
    var verifiedStepCount: Int // 0...5, driven by real callbacks
    var warpConnected: Bool? // tri-state unknown/false/true
    var engineRunning: Bool
    var failureCode: String?
    var failureMessage: String?
}
```

Never infer state from UI animation duration; UI observes the existing backend's result. On retry, clear transient error and take latest backend state.

## 5. Lightweight animation implementation

Preferred production SwiftUI: one `ZStack` stage, `Image` mascot, native shapes for path/soil, `rotationEffect`, `offset`, `opacity`, `TimelineView` only if actually needed; animations can be driven by phase and a cancellable repeating timer. If app uses AppKit, `NSView` with CALayer transforms is sufficient. **No game engine.**

| Trigger | Duration/repetition | Motion |
| --- | --- | --- |
| `시작` pressed | 600ms once | School zooms away / shaft reveals tunnel, easeInOut |
| Active mining | 570ms repeating only in active phase | Approved PNG moves down 1pt, rotates +5° and returns −4°; exaggerated tiny toy pickaxe impression |
| Pickaxe contact | 95ms max | Stage/track lateral jolt 1–2pt; not full window |
| Contact particles | 420–720ms | Spawn **3–5** flat squares (3–6pt), brown/beige at wall, drift 8–20pt down / fade |
| Phase completed | 190ms | Next milestone node illuminates; content title crossfades |
| Success | 550ms once | Beam fades in; miner −8° look up; native green check scales 0.82→1.0 |
| Error | 370ms once | Wall rock appears; bounce backward 2–4pt; no continuous shake |
| Stop | ≤240ms | Stop timer/particle emission, freeze stable pose |
| Witty subtitle | every ≥5s only while waiting | Simple crossfade; preserve primary status + technical detail |

Implementation notes:

1. `mascot-approved.png` alpha image contains a pickaxe attached to the character. Do **not** split and independently animate the pickaxe unless a clean mask can be created without altering the face. Whole-character bob/rotation is the intended MVP.
2. Tunnel scene is drawn vectorially. Track filling maps to verified phase progress; do not translate the mascot faster than milestones. For a slow step, mine the **same current wall** in a tiny repetitive loop until backend reports completion.
3. Avoid timers when window is hidden / app inactive. Particle objects must be removed when their transition ends. Keep ≤15 particles onscreen at once. 30–60 FPS should be trivial on MacBook Air M2.
4. Follow `accessibilityReduceMotion`: no jitter, no particle spam, no rotating character; static mascot + 150ms phase fades + accurate text updates. Maintain VoiceOver descriptions (`연결 중, 단계 2/5, WARP 로컬 프록시 확인`), announce success/error once, not repeating jokes.
5. `시작` is disabled if running or an operation is ongoing; `중지` enabled if appropriate; `WARP 자동 연결` disabled during full startup. Avoid double-click starting two backend operations.

## 6. UI control behaviors, no missing alpha functions

| Alpha function | Production position | Expected UI contract |
| --- | --- | --- |
| `WARP 열기` | `⋯ 도구` | Open installed WARP; if unavailable, show actionable installation guidance |
| `사전 점검` | `⋯ 도구` | Run checks; report results in sheet; no unexpected start |
| `시작` | Large primary button | Full existing 1–5 workflow; once initiated swap to busy/disable as appropriate |
| `중지` | Adjacent secondary button | Stop engine; keep WARP state independently accurate |
| `상태 확인` | Header state chip click or `상태·로그` | Read-only diagnostics, last transitions, connection mode |
| `로그 열기` | `상태·로그` sheet | Show/open log path, copy redacted log; default UI avoids raw JSON |
| `사용 안내` | `⋯ 도구 → 도움말` | How-to, “what happens” routing legend, caveat |
| `제거` | `설정 → 제거` (danger zone) | Explicit confirmation of actual targets, no accidental destructive action |

Small status indicators: `WARP` and `ENGINE` separate; `WARP CONNECTED` by itself does not imply `ENGINE RUNNING`. Admin authorization should use native macOS authentication UI, not a whimsical fake password prompt.

## 7. Korean jokes & LoL parody data

Authoritative user-visible strings are in `assets/copy-ko.json`. **All four previously confirmed Master Yi parodies are included exactly** (punctuation preserved):

1. `쉿, 굴착 중이오...`
2. `우회로는 내 안에 살아 있소.`
3. `방화벽 같은 장난은 그만하지!`
4. `일굴 필살!`

Three **added** LoL-inspired parodies:

- 카직스: `우회란 좋은 거야.`
- 럭스: `땅굴 속에도 빛이 있답니다.`
- 바이: `곡괭이는 하나인데 벽은 왜 이렇게 많냐.`

Other champion jokes retained: 티모, 블리츠크랭크, 잭스, 야스오, 말파이트. Together **12** champion-parody lines + original Korean jokes. These are **creative rewrites**, not claims that Riot champions actually said the altered text; asset JSON keeps a provenance/source field where known, or labels a skill-name parody. Do not quote/copy full original dialogue into UI.

#### Display policy

Main panel always shows title and actual technical subline. Only the third, visually light line rotates through eligible gags at least every 5 sec. In `adminAuth`, hide the gag and show plain permission explanation. In `error`, hide rotating gags and show actionable error code, missing tool, failed test stage, and `자세히`/`다시 시도`; error-themed LoL phrases may be used **only** in decorative tooltip after the error is understood. In `running` show a single celebratory line but not incessant cycling.

Good original Korean subtitle examples: `검열의 제왕과 숨바꼭질 중...`, `흙먹 중... 쌀먹 아님.`, `오늘의 수행평가: 땅굴 파기`, `이건 우회가 아니라 지질조사입니다.` Avoid offensive personal insults or a false claim of government affiliation. Korean localization should feel student-made and slightly irreverent; English UI if added later should be separately written, not literal translated Korean slang.

## 8. Asset usage and layering

Production scene Z-order (back to front):

1. Rounded clipping container, matte dark fill + subtle stroke.
2. `school.svg` only during idle/start; fades/zooms out.
3. `tunnel.svg` at active stage; dynamic revealed segment/soil wall native shape overlay.
4. `spotlight.svg` success only, opacity 0→1 and position above miner.
5. `rock.svg` failure only, at the digging boundary.
6. `mascot-runtime-256.png` (source master `mascot-approved.png`) at ~88–110pt display width, keep transparent padding as appropriate; anchor bottom align.
7. Contact dirt particles ephemeral (tiny rounded=0 square Rectangles), 3–5 per hit.
8. Success `Image(systemName: "checkmark.circle.fill")` semantic green; `check-fallback.svg` only for HTML offline demonstration.

Master asset is 1254×1254; square transparent canvas contains all of mascot and pickaxe. Never crop the raised pickaxe or cut off boots. Downsample using high-quality Lanczos for 256pt runtime when feasible; retain original in archive. If app targets 1x/2x/3x retina, build optimized `Assets.xcassets` entries using source PNG, preserving transparency and relative proportions.

Optional `app-icon-ministry.png` and `app-icon-ministry-sejong.png` are *old experimental* icon mockups, separate from loading scene. They are supplied only for context and should not be assumed approved production icons; do not confuse them with the confirmed miner mascot.

## 9. Error designs

Never merely show `에러`. Preserve the stage and useful cause:

| Failure case | Accurate display example | Primary recovery affordance |
| --- | --- | --- |
| CLI missing/unsupported | `곡괭이가 없어요` · “WARP CLI를 찾지 못했습니다.” | `설치 안내` |
| Wrong proxy mode/port | `굴 입구가 막혔어요` · “Local Proxy: 40000 설정을 확인하세요.” | `WARP 설정 확인` |
| TLS or `warp=on` fails | `가짜 출구 발견` · “TLS/warp=on 검증에 실패했습니다.” | `진단 보기` |
| Admin denied | `허가 없이 땅 파기 실패` · “관리자 인증이 취소되었습니다.” | `다시 시도` |
| Engine fails | `착공 후 붕괴` · “분리 라우팅 엔진 시작 실패.” | `로그 보기` / `다시 시도` |

The display detail must come from actual backend errors. Do not claim a specific step failed unless verified. Show `오류 코드 복사`, `자세히` in the diagnostics sheet. Avoid loading indefinite animation after a fatal condition.

## 10. Code migration plan for Codex

1. Keep existing real networking logic intact; extract into current app's observable backend state if not already structured.
2. Add `MinerUIPhase` adapter mapping real callbacks to status keys in `copy-ko.json`. No fake completion timer.
3. Build compact SwiftUI host window using `NSVisualEffectView`/material/SwiftUI native controls compatible with the app's deployment target; use `windowStyle` consistent with native traffic lights and titlebar.
4. Import mascot asset and SVG vector layers (SwiftUI Paths or NSImage SVG handling as supported). Center composition and test at 540×492pt.
5. Implement scene transitions and phase-driven 5-step milestone loader with no percentage fiction; WARP-only distinct success.
6. Add capped, cancellable particle emitter and character bob + success/error poses, respecting reduce motion and app inactive state.
7. Implement Korean copy rotation, top-level status always readable, error and auth suppression.
8. Convert alpha's functions to primary buttons and `⋯ 도구` menus; put logs in a sheet and destructive remove under explicit confirmation.
9. Test manual scenarios: WARP absent, already connected, bad proxy port, TLS failure, admin cancel, engine fail, retry, rapid start/stop, WARP-only mode, full success, menu dismiss, light/dark, VoiceOver, reduced motion.

**Acceptance criteria:** user can immediately tell if WARP is ready versus full engine running; app fits a small desktop window; mascot remains exactly the approved character; miner+pixels stay charming and lightweight; success shows light + Apple native green check; every error is actionable; all alpha functions remain reachable.

## 11. Prototype boundary

`preview/index.html` is for checking layout, mascot scale, transitions, witty text, and error animation. Its buttons cycle **fake/simulated UI states only**; it does not connect to WARP or change network routes. Codex must wire visual states to the app's verified backend, not copy any fake simulator timers into production.
