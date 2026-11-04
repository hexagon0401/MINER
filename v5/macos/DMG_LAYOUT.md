# Alpha.5 DMG installer layout

The user's supplied two-cavern artwork is the background. Its original PNG/JPG
must be provided as a build input; a chat preview is not substituted with newly
generated art. Save the original as `design/dmg-background.png` to select it
automatically, or pass `--dmg-background /path/to/background.png` explicitly.

Use the latest revision containing the MINER heading. If the chat client exposes
images only as inline previews, attach the original PNG inside a ZIP so the build
can consume its real bytes. Do not substitute regenerated mascot artwork.
The requested GitHub publication is a prerelease titled **MINER Alpha**.

- Finder content: 805 × 488 points (the supplied 1611 × 976 artwork at approximately 2×).
- App icon center: (201, 247), in the left cavern.
- Applications center: (603, 247), in the right cavern.
- Icon size: 112 points; labels underneath.
- Manual icon layout, no automatic sorting/sidebar/toolbar/status bar.
- Only the real app and a real symlink to `/Applications` are visible.
- Background is embedded in the DMG; positions/background are stored in `.DS_Store`.

On macOS:

```bash
python3 -m pip install 'pyinstaller==6.22.3' 'certifi==2026.10.23' 'dmgbuild==1.6.7'
python3 macos/build.py --arch arm64 --dmg-background /path/to/background.png
```

The native build mounts the finished image, verifies Finder icon positions and
embedded background, verifies the actual Applications target, checks app code
signatures, copies the app out and runs its embedded CLI. Signing/notarization
remain available through the existing Developer ID flags. The app stays alpha.5;
an existing Git tag/release is not silently overwritten.

The original image is now included at `design/dmg-background.png` (SHA-256
`235ed09ba1d9acf88e4db0ee371be2a8b16339a4c67fef38a3ea34106ba6190e`).
The optional plain-layout code path remains available for existing builds. Linux tests check
the settings contract, not Finder rendering or DMG creation.
