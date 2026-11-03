# Wallpaper Pro

An Omarchy shell plugin for a personal image and live wallpaper collection.

**Early development · 0.2.0-alpha.1.** This is a working foundation, not a marketplace release yet.

## Current features

- Import local images and videos through a file picker.
- Download direct HTTP/HTTPS media links into a private local collection.
- Assign a different image or looping, muted video to each monitor.
- Repeat one image or video on all connected monitors.
- Span a panoramic image or video across the desktop's logical monitor layout.
- Pause video on battery power.
- Turn off Wallpaper Pro to reveal the wallpaper underneath.
- Keep library and assignments across shell restarts; reconnecting displays use their connector assignments.

Multi-monitor videos use separate players and a shared playback timeline, checking for drift every 500 ms and seeking when drift exceeds 150 ms. Panoramic video is **experimental and not frame locked**; monitor seams may show timing differences. Web imports require a direct media URL with a supported file extension; YouTube, Steam Workshop, Wallpaper Engine projects, HTML pages, and provider galleries are not supported.

![Wallpaper Pro manager in a two-monitor playback smoke test](docs/images/manager.png)

## Requirements

Omarchy with its Quickshell plugin system, Python 3, ffmpeg (including ffprobe), Qt Quick Controls, Qt Quick Dialogs, and Qt Multimedia with codecs for your videos. No swww, awww, or mpvpaper dependency. Codec availability varies by system.

## Development install

From this checkout:

```sh
omarchy plugin validate .
```

Install this development version with `omarchy plugin add https://github.com/BraveHart911/wallpaper-pro` and enable `bravehart911.wallpaper-pro` from Omarchy's plugin settings. For a local test, copy this checkout into `~/.config/omarchy/plugins/bravehart911.wallpaper-pro`, rescan with `omarchy-shell shell rescanPlugins`, then enable with `omarchy plugin enable bravehart911.wallpaper-pro`. Do not copy over an existing plugin checkout.

Open Wallpaper Pro from its bar icon. Add media, select a library card, select the display mode and monitor, then choose **Apply wallpaper**. Applying an individual assignment switches to individual mode; other saved individual assignments remain available.

Wallpaper Pro adds click-through bottom-layer windows and does not rewrite Omarchy's theme, wallpaper, Hyprland startup, or other plugins' settings. Other live wallpaper plugins may compete for the same desktop layer; turn those off through their own controls while using Wallpaper Pro. Stock backgrounds remain underneath.

The manager stays loaded when closed so wallpapers continue playing. Disabling the plugin removes its renderer; turning wallpapers off destroys its video players. Plugin updates may require `omarchy restart shell` to replace already loaded QML components.

## Command line

```sh
python3 scripts/wallpaper-pro.py import '/path/to/image.png'
python3 scripts/wallpaper-pro.py import 'https://example.org/wallpaper.mp4'
python3 scripts/wallpaper-pro.py status
python3 scripts/wallpaper-pro.py apply MEDIA_ID --mode individual --monitor DP-2
python3 scripts/wallpaper-pro.py apply MEDIA_ID --mode all
python3 scripts/wallpaper-pro.py apply MEDIA_ID --mode span
python3 scripts/wallpaper-pro.py off
```

`MEDIA_ID` comes from `status`. `unassign MONITOR` clears one saved monitor assignment; `battery on` and `battery off` control battery pausing. `omarchy-shell wallpaper-pro status` reports renderer state, per-monitor playback positions, and decoder errors while the plugin is enabled. `remove MEDIA_ID` forgets an unassigned library entry; it retains the cached media file. Imports copy local files, leaving the originals untouched. Downloads have a 512 MiB limit and a 30-second socket timeout. Imports use ffprobe to reject files without a readable video/image stream. This checks stream metadata, not every frame; playback errors can still occur.

Settings: `$XDG_CONFIG_HOME/wallpaper-pro/settings.json` (default `~/.config/wallpaper-pro/settings.json`). Media: `$XDG_DATA_HOME/wallpaper-pro/library` (default `~/.local/share/wallpaper-pro/library`). Settings include source URLs, so avoid sharing them if URLs contain private access tokens. Nothing uploads your media or sends analytics.

## Remove

Turn off Wallpaper Pro, then run `omarchy plugin remove bravehart911.wallpaper-pro`. Your collection and settings remain for reinstalling. Delete those two Wallpaper Pro data directories manually if you want to remove them permanently.

## Checks

```sh
python3 -m unittest discover -s tests -v
omarchy plugin validate .
```

A graphical playback smoke test (briefly shows test media, without saving settings):

```sh
WALLPAPER_PRO_SMOKE_KIND=video WALLPAPER_PRO_SMOKE_MEDIA=file:///absolute/path/test.mp4 quickshell -p SmokeTest.qml
```

A full installed-plugin session test is available with `python3 tests/integration_session.py`. It requires two monitors, temporarily switches wallpapers, generates its own fixtures, and restores the exact original settings in a `finally` block. It is a manual graphical-session test, separate from CI.

See [release checklist](docs/RELEASE.md) for remaining integration testing and marketplace steps. No wallpaper assets are bundled. Import only media you have permission to use.
