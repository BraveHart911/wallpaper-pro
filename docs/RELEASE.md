# Release checklist

## GitHub release

1. Run the [checks in the README](../README.md) and review the manual checks below. Use the [Omarchy Shell Plugins manual](https://omarchy.org/manual/shell-plugins/) for the host contract.
2. Merge the release changes and verify that GitHub Actions passes on the commit you intend to tag.
3. From the release commit, create a draft GitHub release with the version from `manifest.json`.

   ```sh
   version=$(jq -r .version manifest.json)
   gh release create "v$version" --target "$(git rev-parse HEAD)" --draft \
     --title "Wallpaper Pro $version" --notes-file docs/RELEASE-NOTES.md
   ```

4. Review the target commit and rendered notes in GitHub, then publish the draft. GitHub provides source archives for the tag.

## Before marketplace submission

- [x] Valid root Omarchy manifest, persistent panel hosting a native application window with an embedded renderer, and bar entry point.
- [x] Python library tests and GitHub Actions workflow.
- [x] QML components load in an isolated Quickshell harness.
- [x] GitHub owner: BraveHart911; plugin namespace: bravehart911.wallpaper-pro; MIT license attributed to Leif.
- [x] Test installation, enable/disable lifecycle, shell restart, and IPC summon inside Omarchy.
- [x] Test primary-click open and close on both the built-in Omarchy bar and Island Bar. Verify Super+W and the absence of Super+Q on the test desktop.
- [x] Add, fast-forward update, and remove a disposable Git checkout of the release tree using Omarchy’s CLI.
- [x] Verify native tiled client registration (`floating: false`), absence of a manager layer-shell surface, and compositor close/bar-toggle reopen using `tests/window_session.py`.
- [ ] Visually verify local file picker, imports, failure messages, and keyboard flow.
- [x] Test independent image/video assignments, all-monitor video, panoramic video, looping, and off/decoder cleanup on DP-2 and HDMI-A-2. Original settings restored after testing.
- [x] Test empty, negative-position, mixed logical dimensions, and portrait layout calculations.
- [x] Apply and restore the current live monitor layout. Verify profile save, list, apply, restore, and delete against a temporary monitor configuration. Verify automatic rollback and prompt cleanup while the panel instance stays loaded.
- [x] Write and read back hardware brightness on HDMI-A-2, then restore its original value. DP-2 did not expose DDC/CI brightness.
- [x] Read the live theme catalog and current background, cycle and restore the live background, and apply a stock theme in an isolated Omarchy home.
- [x] Verify automatic monitor rollback after the Quickshell process exits during confirmation.
- [ ] Verify physical mixed-scale/rotated monitor seams, hotplug, and DPMS sleep/resume.
- [x] Verify per-monitor fullscreen video pause/resume using a temporary Hyprland window; restore original wallpaper settings and focus.
- [x] Verify Omarchy palette parsing and read-only competing-renderer diagnostics.
- [ ] Verify battery pause/resume and CPU/GPU use. H.264 video decoding and panoramic playback passed a short smoke test on DP-2 and HDMI-A-2; both players reported 3958 ms at the four-second sample.
- [x] Test HTTP failures, redirects, media size limit, and corrupt media (automated local HTTP server and ffprobe checks).
- [ ] Create a tagged release after integration checks.
- [x] Refresh the public README screenshots for the current gallery and full-page theme picker.
- [x] Publish the public GitHub repository: https://github.com/BraveHart911/wallpaper-pro.
- [x] Submit the repository URL, category, and tags using the marketplace issue form. [Wallpaper Pro submission](https://github.com/omacom/omarchy-plugin-marketplace/issues/13818)
- [ ] Receive listing approval from the marketplace maintainers.

The marketplace's maintainers approve listings. A valid manifest alone does not mean approval or runtime correctness.

## Theme discovery verification

- [x] Scan stock themes, user themes, additional theme backgrounds, nested folders, and linked theme directories.
- [x] Deduplicate identical media, generate thumbnails, and reuse unchanged metadata without decoding or rewriting checkpoints.
- [x] Merge against the latest settings to preserve active wallpapers, assignments, and personal imports.
- [x] Verify startup discovery and a newly installed theme appearing in the Themes category through the actual QML/background-process pipeline.
- [x] Development-machine scan: 1,023 files, 1,020 unique theme wallpapers, no failures. Cached follow-up scan: approximately 0.15 seconds.

## Visual context verification

- [x] Run actual local CLIP inference on the library; 1,081 wallpaper records received image-derived subject labels.
- [x] Verify whole-image/detail views and panorama edge crops; review forest and workstation examples against their previews.
- [x] Test color-family priority, subject grouping, visually similar neighbors, precise thumbnail fingerprints, and cached runs without model reloads.
- [x] Keep model/runtime downloads outside the plugin checkout, use pinned npm dependencies, and disable remote model access during normal analysis.
- [x] Preserve imports and active assignments; context analysis runs outside the settings lock and failures do not block theme discovery.

## Next milestones

- Frame-locked panoramic video. A shared timeline with periodic drift correction is implemented; it is not frame locked.
- Provider adapters for web collections, with provenance and license information.
- Video thumbnails, search, favorites, playlists, scheduled rotation.
- Per-monitor fit, focal point, and mute/pause controls.
- Coexistence controls for other wallpaper plugins without deleting their configuration.
- Expand decoder validation beyond stream inspection. Stream validation at import and visible playback errors are implemented.
