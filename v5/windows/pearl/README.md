# MINER — Windows 11 Pearl White UI assets

Static concept assets and implementation specifications for the Windows MINER UI.
Only the pearl-white theme is included. There are two alternative button layouts.

## File index

| File | Purpose |
| --- | --- |
| `mockups/PearlWhite-Soft-Red-Kill.png` | A: Rounded buttons; pale pink/red Kill Switch gradient |
| `mockups/PearlWhite-Flush-Controls.png` | B: Three buttons in one flat, rectangular, integrated control plate |
| `mascot/miner-transparent.png` | Static chibi miner image with transparent background |
| `mascot/MINER-wordmark-transparent.png` | Rounded charcoal MINER title image; use if matching font is unavailable |
| `icons/settings.svg` | Settings outline icon |
| `icons/minimize.svg`, `maximize.svg`, `close.svg` | Window control outlines; use native Windows controls when possible |
| `styles/theme.css` | Theme tokens, background, hero, status bar, typography |
| `styles/controls.css` | CSS for rounded and flush control layouts |
| `ui-spec.json` | Machine-readable asset names and layout requirements |

## Design requirements

1. Windows 11-inspired pearl-white acrylic with ice-blue and pale lilac gradients. Keep the window visually soft, with no elaborate animation.
2. Round, heavy, playful `MINER` wordmark centered at the top. Subtitle: `Dig your way out.`. Prefer the included transparent wordmark image for pixel-consistent appearance. Other text should remain actual selectable text.
3. One non-animated miner centered in a wide frosted hero panel. No tunnel or school backdrop.
4. Below the hero, center `탈옥 준비` and `개인용 WARP를 먼저 설치하고 등록해 주세요.`.
5. Exactly five segmented progress bars and `0/5` when idle.
6. Controls: `START` in green, `STOP` in cool pearl grey, `KILL SWITCH` in a very faint red/blush gradient. These are **functional button elements** in the eventual app, not background images.
7. Footer text: `WARP Local Proxy · 127.0.0.1:40000`; settings button at far right. The displayed address is a prototype value, not verification of a live proxy.
8. The supplied PNG mockups are visual references, not sliced UI layers. Build gradients, buttons, borders, shadows, type, and progress from native controls/CSS/XAML; don't use a whole mockup screenshot as app background.

## Layout choice

- **A / rounded**: Separate soft raised buttons. Green full-width START above half-width STOP and KILL SWITCH.
- **B / flush**: One rectangular inset panel with START as a full-width upper row and STOP/KILL SWITCH side by side in the lower row, separated by 1px hairlines. No floating button shadows. Use this if native Windows font/layout rendering makes the rounded controls look inconsistent.

The mockups are `1137 × 1383` pixels; target approximately `560 × 680` device-independent pixels and allow the layout to resize. Asset positioning is illustrative; don't read fixed coordinates from the image.

## Suggested colors

CSS tokens in `styles/theme.css` provide a reproducible approximation to the image-generation reference; they are not sampled, exact colors.

| Role | Color |
| --- | --- |
| Text | `#353A45` |
| Background base | `#F6F8FF` |
| Soft lavender | `#EEEBFF` |
| Soft ice blue | `#E7F0FF` |
| START | `#22DE42` / `#08C82E` |
| STOP | `#F4F6FD` |
| KILL pale | `#FFFAFB` → `#F9E4E9` |
| KILL outline | `#E9C3CD` |
| KILL text | `#733D48` |

## Typography

- Prefer included `MINER-wordmark-transparent.png` for the distinctive heading when the exact bubbly font isn't available.
- For UI/Korean text on Windows: `Segoe UI Variable`, `Malgun Gothic`, then system sans-serif.
- Keep Korean status copy as text; do not rasterize it into the app.

## Implementation reminders

- Button availability, error handling and Kill Switch behavior must be wired to the app's real connection state; this package is visual only.
- Never treat changing the button color as equivalent to enforcing a network kill switch.
- Use Windows-native window controls and accessibility semantics in the final application.
- Do not add digging/progress animation unless a future specification explicitly requests it.
