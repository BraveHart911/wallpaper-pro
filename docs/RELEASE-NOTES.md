# Wallpaper Pro 0.9.0-alpha.21

Wallpaper Pro brings image and looping video wallpapers to Omarchy, with a local library, per-monitor assignments, panoramic playback, and controls for themes and monitor layouts.

## In this prerelease

- Browse 15 bundled wallpapers, discover installed theme wallpapers, and import images or videos from files, folders, or direct media links.
- Use one wallpaper per display, repeat a wallpaper across displays, or span a panorama across the desktop. Videos loop silently, with options to pause on battery power or behind fullscreen apps.
- Arrange displays, change resolution and scale, save layouts, and adjust hardware brightness on supported DDC/CI displays.
- Switch away from Themes & appearance in narrow windows. The theme picker now distinguishes loading, empty results, and an unavailable current background.
- The active-theme highlight and checkmark follow the applied theme. Gallery tooltips use the active palette, and automatic theme discovery preserves the gallery’s scroll position.
- The bar launcher responds to primary clicks, and the gallery selects a wallpaper on first load when one is available.
- Paste a web link as soon as the import dialog opens. Enter and the Import wallpaper button use the same submission rules.
- Monitor layout edits skip commented-out examples in `monitors.lua`. The manager allows one layout change at a time while a layout is being applied or awaits confirmation.
- Monitor rollback clears the confirmation prompt after restoring the previous layout. Background theme discovery preserves import errors and folder summaries.

## Install

Run `omarchy plugin add https://github.com/BraveHart911/wallpaper-pro`, enable `bravehart911.wallpaper-pro` in Omarchy’s plugin settings, and open it from the bar. See the [README](https://github.com/BraveHart911/wallpaper-pro/blob/v0.9.0-alpha.21/README.md) for dependencies and usage.

## Known limitations

- Panoramic video uses separate players and periodic drift correction. Motion may show timing differences at monitor seams.
- Hardware brightness depends on DDC/CI support and access to the display’s I²C bus.
- Keep Omarchy Shell running until you confirm a new monitor layout or the 15-second rollback completes. Restarting or unloading the shell during that countdown can leave the unconfirmed layout active. The recovery copy of `monitors.lua` remains on disk.
- Physical mixed-scale and rotated display seams, hotplug, display sleep, and battery behavior are still on the [release checklist](https://github.com/BraveHart911/wallpaper-pro/blob/v0.9.0-alpha.21/docs/RELEASE.md).
