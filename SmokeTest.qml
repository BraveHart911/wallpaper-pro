import QtQuick
import Quickshell
import "." as Pro

// Run in a graphical session with WALLPAPER_PRO_SMOKE_MEDIA set to a file URL.
// Uses no real settings. A four-second run briefly shows the test wallpaper.
ShellRoot {
    Pro.WallpaperPro {
        id: manager
        automaticThemeSync: false
        opened: true
        renderer.configPath: "/nonexistent/wallpaper-pro-smoke/settings.json"
        renderer.config: ({enabled: true, mode: "span", default: "smoke", pauseOnBattery: false,
            library: [{id: "smoke", kind: Quickshell.env("WALLPAPER_PRO_SMOKE_KIND") || "image",
                       url: Quickshell.env("WALLPAPER_PRO_SMOKE_MEDIA")}]})
        libraryState: ({library: [{id: "smoke", name: "Panoramic video test", kind: "video", url: Quickshell.env("WALLPAPER_PRO_SMOKE_MEDIA")}], mode: "span", default: "smoke", enabled: true, pauseOnBattery: false})
        selected: "smoke"
        message: "Playback test · 2 connected monitors"
    }
    Timer {
        interval: 4000
        running: true
        onTriggered: { console.log("WALLPAPER_PRO_SMOKE", manager.renderer.playbackStatus()); Qt.quit() }
    }
}
