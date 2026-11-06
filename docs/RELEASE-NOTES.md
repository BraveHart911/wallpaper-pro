# Wallpaper Pro 0.9.0

Wallpaper Pro’s first regular GitHub release for Omarchy and Hyprland. Browse image and video wallpapers, assign them to your displays, and manage themes and monitor layouts from one window.

## Features

- Browse 15 bundled wallpapers and backgrounds from installed Omarchy themes. Import images and videos from files, folders, or direct links.
- Assign a different wallpaper to each display, repeat one across all displays, or span a panorama across your desktop. Videos loop silently and can pause on battery power or behind fullscreen apps.
- Apply Omarchy themes, cycle theme backgrounds, save monitor layouts, and adjust resolution, scale, and brightness on supported DDC/CI displays.

## Changes since alpha.21

- A separate process restores an unconfirmed monitor layout after 15 seconds, even if Omarchy Shell exits during confirmation. The recovery copy stays on disk. Edits made outside Wallpaper Pro during the countdown are preserved.
- Added a root gallery preview for the Omarchy Marketplace submission.

## Install

Run `omarchy plugin add https://github.com/BraveHart911/wallpaper-pro`, enable `bravehart911.wallpaper-pro` in Omarchy’s plugin settings, and open it from the bar. Existing Git-managed installations can run `omarchy plugin update bravehart911.wallpaper-pro`. See the [README](https://github.com/BraveHart911/wallpaper-pro/blob/v0.9.0/README.md) for dependencies and usage.

## Known limitations

- Panoramic video uses separate players and drift correction. Motion can briefly differ across monitor seams.
- Hardware brightness requires a DDC/CI-capable display and user access to its I²C device.
- Physical mixed-scale and rotated display seams, hotplug, display sleep, and battery behavior are still on the [release checklist](https://github.com/BraveHart911/wallpaper-pro/blob/v0.9.0/docs/RELEASE.md).
