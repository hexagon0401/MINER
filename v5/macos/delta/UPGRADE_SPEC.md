# MINER UI DELTA v2.1 — Final Codex Upgrade Specification

**Priority 1, authoritative.** This file supersedes `UPGRADE_SPEC_v2_BASE.md` wherever they conflict. **Update the existing functional MINER app in-place; do not rewrite its routing engine, network checks, assets or diagnostics.**

## 0. Immutable elements

- Product: **MINER**, *Makes Internet Not Eternally Restricted*, “Dig your way out.”
- The user-approved toy miner character and original school artwork, all Korean humor/LoL lines, existing app icon, settings, tools, logs, help, errors, privileges and original back-end state bindings.
- Existing five real connection stages and **exact five thin progress ticks**. Advance a tick only after a real stage callback. Do not replace the tick strip or simulate progress using time.
- WARP-only 1–3 stages remain distinct from complete engine 1–5 stages. WARP success is not complete engine success.
- Retain all Delta v2 effects: full-window cave, vertical school-to-tunnel reveal, the toy pickaxe rocking, square falling soil particles, crack/spark/pebble layers, green Start wave, red Stop wave, and complete success skylight + sharp centered check + background blur + restoration.
- **Only the window chrome/material, layout offsets and associated visual polish differ in v2.1.**

## 1. Updated outcome

| Component | v2 | **v2.1 final** |
| --- | --- | --- |
| Titlebar | Separate gray/silver horizontal stripe, duplicate centered MINER | **No visible titlebar surface or duplicate title**. Cave extends to rounded top edge |
| Traffic lights | macOS native controls in titlebar | **Keep native controls**, visually float over cave at upper left |
| Window | Compact app with 32pt chrome + full-bleed inner content | Same **compact desktop window**, but now art/material fills **entire window bounds**, not macOS fullscreen |
| Header | At inner content top | Move lower beneath traffic-light safe space |
| Material | Deep navy translucent background | Native **Liquid Glass / system material** with very subtle automatic environmental color reaction |
| Progress | Five thin rounded ticks | **Exactly unchanged** in visual form and backend semantics |
| Animations | V2 motion timeline | All retained; shift layers vertically to new full-window coordinate system |

## 2. macOS native titlebar-less window (do not fake)

Meaning of “타이틀바 제거”: hide the *visible titlebar strip*, title text and divider. Retain normal `NSWindow`: traffic lights, focus, dragging, resizing, window menus, title accessibility and keyboard behavior. **Do not use a custom borderless/pseudo-window. Do not force native fullscreen.**

Preferred SwiftUI window configuration when supported by the real deployment target:

```swift
WindowGroup("MINER") {
    ExistingMinerRootView()
}
.windowStyle(.hiddenTitleBar)
```

Equivalent AppKit approach if current code uses or customizes an `NSWindow`:

```swift
window.titleVisibility = .hidden
window.titlebarAppearsTransparent = true
window.styleMask.insert(.fullSizeContentView)
window.isMovableByWindowBackground = true
```

These snippets describe **alternative patterns**, not four calls that must be duplicated in the SwiftUI entry point. Inspect the actual project first; use supported APIs under correct availability checks. Keep original traffic lights positioned by the system, approximately x16–78/y15–29pt. Top y0–47pt should be an unobstructed drag area except for traffic lights. Do not intercept button clicks with window drag; ensure space for dialogs, sheet attachments and accessibility.

Apple APIs: [HiddenTitleBarWindowStyle](https://developer.apple.com/documentation/swiftui/hiddentitlebarwindowstyle), [titlebarAppearsTransparent](https://developer.apple.com/documentation/appkit/nswindow/titlebarappearstransparent), [isMovableByWindowBackground](https://developer.apple.com/documentation/appkit/nswindow/ismovablebywindowbackground).

## 3. Liquid Glass with environmental reaction

**Goal:** a polished deep-navy frosted cavern cutout where a cool blue, warm peach or purple desktop only *subtly* colors the top and outer rounded edges. Header, character and steps stay clearly readable; there is no giant opaque illustration panel.

Recommended rear-to-front stack:

1. Native `.ultraThinMaterial` / `NSVisualEffectView` filling entire content behind window controls. Ambient color comes from the OS material interacting with the actual desktop/window background.
2. Matte deep-navy tint on top: target alpha approximately **0.60–0.72 near header and edges**, **0.78–0.88 around dark tunnel**. Adjust for contrast rather than bake in an entirely opaque #0E131F rectangle.
3. Transparent `full-window-strata.svg` and original school, shaft, tunnel, mascot, particles. Modest gradient/vignette is allowed; avoid extra black rounded subpanel.
4. Small status chip + quiet status material capsule + neutral Stop + tools use system glass where appropriate. Use SwiftUI `.glassEffect()` with `GlassEffectContainer` **only when available**; otherwise `.regularMaterial` / native AppKit material. **Primary Start keeps its green brand fill**.
5. Real controls, text and the existing five progress ticks on top; transient waves/check/success overlay above those when active.

Do **not** sample/poll the user's wallpaper pixels, run full-screen pixel-read filters, or create a perpetual shader just to react to colors. Native backdrop materials do this without the app needing wallpaper access. Preserve high legibility with dark and light wallpapers and active/inactive windows. **Reduce Transparency:** fall back to stable opaque deep navy with stronger outlines. **Reduce Motion:** particles/waves/blur can be simplified as specified below.

Apple APIs: [glassEffect](https://developer.apple.com/documentation/swiftui/view/glasseffect(_:in:)), [GlassEffectContainer](https://developer.apple.com/documentation/swiftui/glasseffectcontainer).

## 4. Geometry — 560×610pt entire-window canvas

**Coordinate origin is the top-left corner of the ENTIRE window content, including the previously separate titlebar.** Do not subtract an additional 32pt. Typical size 560×610pt, minimum 520×570pt. Use adaptive layout, not screen-absolute positions.

| Layer / control | Coordinates and dimensions | Rules |
| --- | --- | --- |
| System rounded window | 560×610pt | Native resizing/drag; not OS fullscreen |
| Upper quiet/drag zone | y0–47 | System red/yellow/green controls at upper-left; no text underneath |
| Brand MINER | x26, top~64; 25pt | Only in-content MINER, no duplicate centered title |
| Slogan | x26, y~96; 11pt | “Dig your way out.” |
| Right state chip | right x26, top~70 | Small thin translucent dot + status |
| School | center x280, top~129, height~110 | Original existing `school.svg` |
| Shaft reveal | center x280, top~204, height~100 | Connect school to excavated tunnel |
| Cave & miner | y~271–385; mascot around x370/top~258 | Existing approved mascot, no realistic dirt textures |
| Status glass capsule | x40–520, **top389**, height58 | Real status + error subtext; 5 ticks at bottom |
| **Start** | center x280, **top459**, 340×48, radius15 | Bright green; dominant |
| **Stop** | center x280, **top515**, 166×36, radius12 | Neutral translucent glass, directly below Start |
| Footer | x26 to534, top~564–602 | Existing WARP auto connect, tools, WARP/engine state |

UI is a single connected cave scene; no separate animation card. At small width adapt the central vertical rhythm, keep all actions visible and native click targets accessible. Avoid overlap during long Korean status messages; truncate or expand status capsule conservatively.

## 5. Retain Delta v2 motion logic, with whole-window coordinates

### Start: green pulse and digging

- `시작` invokes **existing start action exactly once**, and independently emits one 520ms radial green wave `#0EFB2E`, maximum alpha 0.32, from measured global center of Start button to farthest window corner; fades back to transparent.
- Animation means *request accepted*, **not** actual connection verified. After ~180ms reveal `shaft-reveal.svg` with a clipped vertical mask; animate existing miner toy rocking/pickaxe around 570ms. Each hit: 3–5 **square** soil bits sized 3–6pt falling 380–670ms, brief 88ms ≤2pt cave jolt, low-weight crack/spark, occasional pebble. At most 14 active particles.
- The five progress ticks advance **only** from actual backend stages: CLI check, proxy Local Proxy connection, TLS validation, admin auth, engine routing. No UI timer auto-completes these in production.

### Stop: red pulse

- `중지` invokes existing cancel/stop exactly once; one 480ms translucent red radial wave `#FF5A61`, max alpha 0.30, from measured Stop center across window.
- Immediately remove local dirt particles and stop success overlay. Show `중지 중…` until backend confirms; do not claim WARP is off merely because engine stopped. Red wave is **not** an error overlay.

### Running success: light → blur → center check → restore

Only at verified **full-engine running** state (not WARP-only).

| Relative time | Visual |
| ---: | --- |
| 0–260ms | `exit-ceiling.svg` appears, `skylight-beam.svg` fades in. Original miner tilts ~−7° upward |
| 230–450ms | All regular content (including buttons/header) blurs 0→10pt; slight dim scrim ≤0.12 alpha |
| 350–610ms | Native SF Symbol **`checkmark.circle.fill`**, system green, ~64pt, scales .76→1 at exact **entire window center** x280/y305; `연결 완료` below |
| 610–1120ms | Sharp check stays over the blurred content (check itself not blurred) |
| 1120–1550ms | Check fades/lifts ~6pt, content blur returns to 0, normal running UI restored |

If stop/error interrupts the sequence, cancel all scheduled animation and restore blur and hit testing within ≤180ms. Do not show full-engine check for `warp_ready` or simulated timers.

### Error

Short 180–250ms miner flinch, a falling pebble and red status chip; **show real actionable log/error reason**. No continuous red window takeover. Error has its own accessible status announcement.

### Resource/accessibility

Lightweight SwiftUI opacity, scale, transform, masking and supplied SVG layers only. No costly 3D particles or perpetual animations while idle. Reduce Motion: replace radial wave by 120ms color tint; no debris, scene jolt or background blur; centered check still visible. Respect Reduce Transparency, VoiceOver, keyboard focus, high contrast, locale and system font scaling. Cancel timers when window disappears.

## 6. Included incremental assets (do not replace originals)

- `assets/full-window-strata.svg`: transparent cave silhouettes full window.
- `assets/shaft-reveal.svg`: vertical tunnel reveal beneath school.
- `assets/dig-wall-cracks.svg`: pickaxe impact cracks.
- `assets/pickaxe-impact.svg`: small impact sparkle.
- `assets/dirt-particle-cluster.svg`: square particle shape reference.
- `assets/pebble.svg`: small single rock.
- `assets/skylight-beam.svg`: success opening beam.
- `assets/exit-ceiling.svg`: exit cutout.

Do not replace `mascot-approved.png`, `school.svg`, `tunnel.svg`, `rock.svg`, original status/locale data, backend engine or app icon. The `preview/approved-mascot-reference.png` is a demo-only copy.

## 7. Safe Codex implementation order

1. Inspect existing MINER window root and state manager; identify native `NSWindow` customization.
2. Hide only titlebar's visible strip; retain native traffic lights, dragging, sizing, modal behavior and accessibility; extend root view to whole window bounds.
3. Adjust header/scene/status/button/footer geometry to the table. **Keep original five ticks unchanged**.
4. Add native material + soft navy tint and native environmental response, with accessible opaque fallback.
5. Retain existing v2 start/stop waves, center check/blur and eight SVG details; update coordinates only as needed.
6. Wire visual states to the app's existing real event publisher, not HTML preview timers. Preserve all tools, admin prompts, WARP-only and full-engine cases.
7. Run visual tests on 560×610 and minimum, light/dark desktop colors, high contrast, Reduce Motion/Transparency; test stop/error, success cleanup, traffic lights, drag, 5-stage progress and WARP-only no-check state.

## 8. Acceptance criteria

- [ ] No dedicated gray titlebar, divider or second MINER text; cave extends to window's upper rounded edge.
- [ ] **Native** red/yellow/green macOS traffic lights remain; regular window dragging, resizing and focus still work.
- [ ] Window remains a compact utility, not automatically OS fullscreen.
- [ ] Native material picks up desktop colors subtly; no wallpaper/screen-reading or per-frame shaders.
- [ ] Status is legible; **original five progress bars** remain identical and reflect real events only.
- [ ] Approved miner original preserved; simple toy style intact.
- [ ] Start big centered; Stop smaller centered directly below; back-end handlers unchanged, invoked once.
- [ ] Full-window green start and red stop waves fade back to zero.
- [ ] Success shows sky beam → miner looks up → blur → centrally crisp green native check → restore, once; only full-engine ready.
- [ ] WARP-only success has no full-engine check; real errors and diagnostics available.
- [ ] Accessibility, reduced motion/transparency, dark/light, min window, controls and native authorization pass.

## 9. Source precedence

1. `UPGRADE_SPEC.md` (this final v2.1 spec).
2. `assets/motion-tokens.json` (machine-readable v2.1 values).
3. `preview/index.html` (visual **simulation only**; fake network progress timing is deliberately not production logic).
4. `preview/layout-v2-1-concept.png` (mood reference; exact placement from this spec).
5. `UPGRADE_SPEC_v2_BASE.md` and `preview/layout-v2-reference.png` (historical material only).
