# Release checklist

## Before marketplace submission

- [x] Valid root Omarchy manifest, persistent overlay with an embedded renderer, and bar entry point.
- [x] Python library tests and GitHub Actions workflow.
- [x] QML components load in an isolated Quickshell harness.
- [x] GitHub owner: BraveHart911; plugin namespace: bravehart911.wallpaper-pro; MIT license attributed to Leif.
- [x] Test installation, enable/disable lifecycle, shell restart, and IPC summon inside Omarchy.
- [ ] Test the actual bar-button click with the selected replacement bar.
- [ ] Visually verify local file picker, imports, failure messages, and keyboard flow.
- [x] Test independent image/video assignments, all-monitor video, panoramic video, looping, and off/decoder cleanup on DP-2 and HDMI-A-2. Original settings restored after testing.
- [ ] Test image spanning with negative positions, mixed scale, rotation, and hotplug.
- [ ] Verify battery pause/resume and CPU/GPU use. H.264 video decoding and panoramic playback passed a short smoke test on DP-2 and HDMI-A-2; both players reported 3958 ms at the four-second sample.
- [x] Test HTTP failures, redirects, media size limit, and corrupt media (automated local HTTP server and ffprobe checks).
- [ ] Create a tagged release after integration checks. A cropped screenshot of the actual manager in the two-monitor smoke test is included.
- [x] Publish the public GitHub repository: https://github.com/BraveHart911/wallpaper-pro.
- [ ] Submit its URL at https://plugins.omarchy.org/publish.html.

The marketplace's maintainers approve listings. A valid manifest alone does not mean approval or runtime correctness.

## Next milestones

- Frame-locked panoramic video. A shared timeline with periodic drift correction is implemented; it is not frame locked.
- Saved named monitor profiles and assignment overview.
- Provider adapters for web collections, with provenance and license information.
- Video thumbnails, search, favorites, playlists, scheduled rotation.
- Per-monitor fit, focal point, brightness, mute/pause controls.
- Coexistence controls for other wallpaper plugins without deleting their configuration.
- Expand decoder validation beyond stream inspection. Stream validation at import and visible playback errors are implemented.
