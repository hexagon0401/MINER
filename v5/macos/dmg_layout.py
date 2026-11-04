"""Finder installer layout for the supplied two-cavern MINER background."""
from pathlib import Path

WINDOW_SIZE = (805, 488)
APP_POSITION = (201, 247)
APPLICATIONS_POSITION = (603, 247)
ICON_SIZE = 112


def settings(app, background):
    app, background = Path(app).resolve(), Path(background).resolve()
    if not app.is_dir() or app.suffix != ".app":
        raise ValueError("installer layout requires an existing .app bundle")
    if not background.is_file():
        raise ValueError("installer background image is missing; supply the original PNG/JPG")
    return {
        "format": "UDZO", "filesystem": "HFS+",
        "files": [str(app)], "symlinks": {"Applications": "/Applications"},
        "background": str(background), "icon": str(app / "Contents/Resources/AppIcon.icns"),
        "window_rect": ((160, 160), WINDOW_SIZE), "default_view": "icon-view",
        "icon_locations": {app.name: APP_POSITION, "Applications": APPLICATIONS_POSITION},
        "icon_size": ICON_SIZE, "text_size": 13, "label_pos": "bottom",
        "arrange_by": None, "show_icon_preview": False,
        "show_status_bar": False, "show_tab_view": False, "show_toolbar": False,
        "show_pathbar": False, "show_sidebar": False,
        "include_icon_view_settings": True, "include_list_view_settings": False,
        # SetFile -a E adds FinderInfo to the signed .app and invalidates strict
        # verification. Keep the app untouched; only the volume owns metadata.
        "hide_extensions": [],
    }


def create(dmg, app, background, work, execute):
    """Raster conversion only; retain artwork proportions and draw no fake icons."""
    import dmgbuild
    settings(app, background)  # Validate inputs before invoking image tools.
    prepared = Path(work) / "installer-background.png"
    execute("sips", "-s", "format", "png", "-z", WINDOW_SIZE[1], WINDOW_SIZE[0], background, "--out", prepared)
    config = settings(app, prepared)
    dmgbuild.build_dmg(str(dmg), "MINER Alpha", settings=config, lookForHiDPI=False)


def verify(mount, app_name):
    """Inspect the stored Finder positions/background, not only a mounted PID."""
    from ds_store import DSStore
    mount = Path(mount)
    with DSStore.open(str(mount / ".DS_Store"), "r") as store:
        if tuple(store[app_name]["Iloc"]) != APP_POSITION:
            raise ValueError("DMG app icon is not in the left cavern")
        if tuple(store["Applications"]["Iloc"]) != APPLICATIONS_POSITION:
            raise ValueError("DMG Applications icon is not in the right cavern")
        options = store["."]["icvp"]
        if options["backgroundType"] != 2 or options["arrangeBy"] != "none":
            raise ValueError("DMG Finder background/manual placement was not preserved")
    if not any(mount.glob(".background*")):
        raise ValueError("DMG background resource was not embedded")
    if not (mount / "Applications").is_symlink() or (mount / "Applications").readlink() != Path("/Applications"):
        raise ValueError("DMG Applications item is not the real Applications shortcut")
