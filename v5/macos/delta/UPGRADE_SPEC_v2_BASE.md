# MINER — UI Delta v2: Full-Bleed Cave + Motion Upgrade

**Purpose:** Update an already built MINER v1.0 app. **Apply only the differences in this folder.** Do not replace the original character, rewrite the networking engine, recreate earlier sprites, or overwrite the old handoff documentation/assets.

## 0. What stays unchanged

- App name `MINER`, expansion `Makes Internet Not Eternally Restricted`, slogan `Dig your way out.`
- Exact original approved toy miner PNG and existing gameplay/network status events.
- Existing five real connection stages and the separate WARP-only 1–3 stage workflow.
- Existing Korean copy / LoL parodies, technical status truth rules, tools, logs, help, WARP and engine statuses.
- macOS window controls and native material, no fake custom traffic lights in production.

## 1. The requested changes — strictly a delta

| Before | After | Implementation scope |
| --- | --- | --- |
| Separate MINER header above isolated dark rounded animation card | **One full-bleed cavern scene** spans whole native window content; brand, illustration, progress, buttons overlay the same backdrop | Recompose existing view hierarchy and material layers |
| Mostly opaque rectangular background | Semi-transparent Liquid Glass material, softly layered blue-gray underground shapes and restrained deep navy vignette | Visual only, keep contrast/readability |
| Start/Stop side by side, asymmetric | Large centered green **시작** button; smaller centered gray **중지** directly below | Move actions; keep actual action handlers |
| Start immediately changes textual status | **Green radial color wave** spreads from start button across whole content during process entry | 520ms overlay independent of backend timing |
| Stop simple state update | **Red radial color wave** spreads from stop button; then stop UI follows backend result | 480ms overlay; do not fake engine stop |
| Check appears inside scene without cinematic hierarchy | As miner turns toward ceiling light, **native green check at entire window center**, background UI smoothly blurs and then restores | Success transition overlay, 1.55s total |
| Limited environment motion | New shaft reveal, wall cracks, impact spark, individual pebble, square soil motes, soft strata, beam and skylight | SVG layers + a few cheap SwiftUI transforms |

### Meaning of “full-screen” for this delta

Interpret this as **full-window background artwork**, not automatically entering native macOS fullscreen mode. Keep the app a small desktop utility. Suggested nominal window **560×610 pt**, minimum 520×570. Content is edge-to-edge beneath the native title bar. The animated scene is NOT another rounded rectangle within the window. If the user later explicitly asks for fullscreen OS behavior, implement separately.

## 2. Updated layout coordinates (logical pt)

Content canvas: width **560**, height **578** excluding ~32pt system titlebar. All positions scale vertically with size; do not pin to screen pixels. Grid is center aligned.

| Component | Suggested position / geometry | Visual treatment |
| --- | --- | --- |
| Background | Full `ZStack` content, x0–560, y0–578 | `.ultraThinMaterial` exterior + matte navy cave art, layered translucency |
| MINER header | x26, y18; title 25pt, tagline 11pt | Floats above landscape, NO separate card |
| State chip | top trailing x≈470, y23 | 10–11pt, very thin frosted capsule |
| School | centered x280, visual y96–180 | Small flat school, existing `school.svg` |
| Descending shaft | from under school at y165 toward y258 | `shaft-reveal.svg`, reveal using animated mask on start |
| Tunnel/miner | x45–515, main activity around y220–367 | Existing approved miner PNG; cavity is part of full background, not an inset pane |
| Status overlay | centered x40–520, y369, height58 | Small floating translucent text strip, never dark opaque panel; true status/title on top |
| Five progress ticks | bottom of status overlay | Native rounded slim bars; only completed callback fills green |
| **시작** | center x280, y436, width340, height48 | Primary green button; radius15; subtly luminous, no constant glow animation |
| **중지** | center x280, y493, width166, height36 | Quiet neutral glass/gray button; red only during stop wave |
| WARP/tools footer | y544–573, horizontal edges x26–534 | Secondary typography/menus, actual engine and WARP statuses distinct |

Use 15–18pt spacing where possible. If a diagnostic message wraps, move status up slightly or grow window; never let text overlap buttons. Preserve native keyboard access and minimum target 34×34pt for secondary controls.

## 3. Whole-window glass treatment

Place `full-window-strata.svg` behind **all** header and action content. Its SVG has transparent layers; it is not a flat PNG with baked UI. Production compositing concept:

1. Native `NSVisualEffectView` / SwiftUI `.ultraThinMaterial` fills content under window chrome.
2. A deep-navy translucent tint ~0.84 opacity gives sufficient white-text contrast; cave is darker in lower half.
3. `full-window-strata.svg` drawn at entire content size; softly fades behind header and under status buttons.
4. Existing SchoolNet building, shaft, horizontal mine, original miner and particles are independent animatable layers.
5. Status overlay uses a *small* `.regularMaterial` capsule; controls sit over the scene without a boxed section.

Avoid two nested competing glass panels or over-blurring the animation by default. The user should perceive one environment extending from the title to buttons.

## 4. Start and stop: expanding green/red wave

Use a circular **radial clip/mask wave**, anchored at the actual clicked button center. The wave crosses the ENTIRE content, including header, tunnel and footer. It is a translucent color wash, not an opaque takeover.

### Start green wave

- User presses **시작** once. Immediately disable repeat start and call the pre-existing start action exactly once.
- Create one green circle at button center (global content coordinate approximately x280/y460). Radius 8pt → `maxDistanceToContentCorner + 30pt` over **520ms**, easeOut.
- Fill `#0EFB2E`; alpha peaks around **0.32** before fading to 0. Effect should be visible but text and miner remain readable.
- The reveal of school shaft begins at ~180ms, followed by existing five-stage dig animation; status is updated by backend events only.
- Remove the wave layer entirely on completion of visual animation. No looping or continuous green overlay.

### Stop red wave

- User presses **중지**. Immediately stop local particle emission and trigger existing stop/cancel backend action once.
- Red wave `#FF5A61` originates from centered small Stop button x280/y511, expands over **480ms** with ~0.30 peak alpha. Then fade out, leaving normally colored UI.
- If backend is still stopping, display actual `중지 중…`; display `중지됨` only after stop success. WARP state must not falsely flip off when engine stops.
- Do not reuse red full-wave for a random network error: errors instead use their own subtle rock/chip bounce, unchanged from base spec.

### SwiftUI implementation hint (conceptual)

```swift
// Overlay sits above scene/header/status/buttons, but below an active alert.
// `origin` is measured in content coordinates via anchor preferences or GeometryReader.
ZStack {
    existingContent
    if let wave = transientWave {
        Circle()
            .fill(wave.kind == .start ? Color(red: 0.055, green: 0.984, blue: 0.18) : Color(red: 1, green: 0.353, blue: 0.38))
            .opacity(wave.opacity)
            .frame(width: wave.diameter, height: wave.diameter)
            .position(wave.origin)
            .allowsHitTesting(false)
    }
}
// Animate diameter from 16pt to 2 × farthest-corner-distance.
// Animate alpha from 0→0.32→0 independently; clean layer afterward.
```

This snippet illustrates drawing only; it intentionally omits backend action calls.

## 5. Connection success: miner looks at light, centered check, blurred background, recovery

**Only** trigger when the existing backend reports the full engine `running`/verified state. A successful WARP-only request is `WARP 준비 완료` and must not show the full success celebration.

| Relative time | Visual |
| ---: | --- |
| 0–260ms | `exit-ceiling.svg` appears above miner, `skylight-beam.svg` fades in. Miner tilts slightly upward (whole original PNG −6° to −8°) |
| 230–450ms | All regular screen content behind celebration (school, scene, header, status, buttons) blurs smoothly 0→10pt; dark translucent scrim increases to ~0.12 alpha |
| 350–610ms | Native macOS `checkmark.circle.fill` in **system green** scales 0.76→1 at **center of entire window content** (x=280, y≈289), size ~64pt; short subtitle `연결 완료` may appear below |
| 610–1120ms | Hold icon clear and motionless, background remains elegantly softened. No false sound, no confetti spam |
| 1120–1550ms | Check fades and lifts 6pt; scrim and background blur return smoothly to zero; spotlight can remain faint for another moment; view returns to normal running UI |

The check must float **outside** the blurred content group so it stays crisp. On interruption or user stop, cancel the success timeline and restore blur to zero in ≤180ms. Do not leave interaction blocked by an invisible overlay.

Prefer an actual SF Symbol `checkmark.circle.fill` and native semantic `Color.green` in production; no third-party Apple symbol PNG. An optional simple green circle/check is fine only in the web preview.

## 6. Added animation assets and motions

These assets are NEW and do not replace the existing `mascot-approved.png`, `school.svg`, `tunnel.svg`, `rock.svg`, `spotlight.svg`, `copy-ko.json` or base UI icons.

| Asset | When visible | How to animate |
| --- | --- | --- |
| `full-window-strata.svg` | always | background parallax y 0→3pt during mining, never constant fast motion |
| `shaft-reveal.svg` | idle→start | vertical 0→100% clipping mask 300–500ms |
| `dig-wall-cracks.svg` | strong pickaxe impact | opacity 0→0.75→0 and tiny scale 0.97→1.0; 240ms |
| `pickaxe-impact.svg` | actual toy strike | pop 0.8→1.05→0 with 150ms, located near existing pickaxe tip |
| `dirt-particle-cluster.svg` | 1–2 impacts / occasional cue | optional still-frame reference; production individual squares 3–6pt and 380–670ms fall |
| `pebble.svg` | one out of every ~4 hits | falls 9–24pt and fades 500ms; must not flood scene |
| `exit-ceiling.svg` | success intro | slide down 5pt + fade in |
| `skylight-beam.svg` | success | opacity to 0.75, fade gently; clip within scene |

Combine existing miner bob/rotation 570ms, 1–2pt scene jolt 88ms, and 3–5 little square particles per hit. Max 14 particles on screen. No separate animation engine or high-resolution sprite video. Restart timers when view becomes active; cancel promptly when hidden or stopped.

## 7. Interaction states and actual logic boundaries

Keep original backend statuses `cli_check`, `proxy_connect`, `tls_verify`, `admin_auth`, `routing`, `warp_ready`, `running`, `stopped`, `error`. **Do not duplicate or refactor network engine** just for animations.

- The green wave expresses **start requested**, not connection verified.
- Progress 0/5 → 5/5 advances only via real callbacks, never by an animation timer.
- `WARP 자동 연결` remains stages 1–3 and should not show full-engine success.
- The red wave expresses **stop requested**, not stop confirmed.
- The green check expresses **full-engine reported ready**, not proof that a League game has been launched successfully.
- Keep existing original humor lines but never substitute jokes for actionable technical failure.
- Native admin authorization must appear above visual waves, not underneath a custom mock prompt.

## 8. Accessibility, resource discipline, quality checks

Respect Reduce Motion: replace spreading waves with brief 120ms color-tint crossfade; no particle spray, no scene jolt or heavy blur; centered check still appears. VoiceOver should announce actual stages and errors only once. Maintain legible controls on vibrant waves, good contrast in both system themes.

QA checklist:

1. Confirm **no separate animation panel** remains, the same cave fills behind header and buttons.
2. Verify both buttons have same horizontal center, Start visually dominant, Stop directly beneath.
3. Confirm green wave covers window content and fades completely. Fast double-click cannot issue duplicate backend requests.
4. Confirm red wave during stop also fades; stop failure leaves honest engine status.
5. Confirm successful **WARP-only** mode has no full-screen check celebration.
6. Confirm full success beam + background blur + centered check + unblur sequence runs once and cleans up after cancellation.
7. Confirm original approved miner/old comedy copy and all alpha functions remain available.
8. Check 560×610 and min 520×570 pt, macOS light/dark, VoiceOver, Reduce Motion, menu/log window sheet, system authorization, engine errors.

## 9. Handoff instruction to Codex

> This is an additive UI-only update to the already working MINER v1 app. Read UPGRADE_SPEC.md, view preview/layout-concept.png and preview/index.html, import only NEW files under assets/, and recompose the existing window background and action placements. Preserve the networking engine, the existing approved mascot image and original messages; bind animations to actual existing state events. Implement start green wave, stop red wave, full-engine success blur/check recovery, and new lightweight impact assets. Do not copy the prototype's simulated stage timing into production. Validate against the included QA checklist.
