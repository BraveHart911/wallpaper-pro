# Release checklist

## Before publishing 0.1

- [x] Valid root Omarchy manifest and separate service/overlay/bar entry points.
- [x] Python library tests and GitHub Actions workflow.
- [x] QML components load in an isolated Quickshell harness.
- [x] GitHub owner: BraveHart911; plugin namespace: bravehart911.wallpaper-pro; MIT license attributed to Leif.
- [ ] Test full bar launch and enable/disable lifecycle inside Omarchy.
- [ ] Visually verify local file picker, imports, failure messages, and keyboard flow.
- [ ] Test independent image/video assignments on both physical monitors.
- [ ] Test image spanning with negative positions, mixed scale, rotation, and hotplug.
- [ ] Verify video decoding, battery pause/resume, and CPU/GPU use.
- [ ] Test HTTP failures, redirects, media size limit, and corrupt media.
- [ ] Add actual plugin screenshots and a tagged release.
- [x] Publish the public GitHub repository: https://github.com/BraveHart911/wallpaper-pro.
- [ ] Submit its URL at https://plugins.omarchy.org/publish.html.

The marketplace's maintainers approve listings. A valid manifest alone does not mean approval or runtime correctness.

## Next milestones

- Shared playback clock and synchronized panoramic video.
- Saved named monitor profiles and assignment overview.
- Provider adapters for web collections, with provenance and license information.
- Video thumbnails, search, favorites, playlists, scheduled rotation.
- Per-monitor fit, focal point, brightness, mute/pause controls.
- Coexistence controls for other wallpaper plugins without deleting their configuration.
- Media decoder validation at import and visible renderer error reporting.
