pragma ComponentBehavior: Bound
import QtQuick
import QtMultimedia
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Services.UPower

Item {
    id: root
    property var shell
    property var manifest
    property var config: ({})
    readonly property string configPath: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/wallpaper-pro/settings.json"
    FileView {
        id: settings
        path: root.configPath
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: { try { root.config = JSON.parse(text()) } catch (e) { console.warn("Wallpaper Pro: invalid settings", e) } }
    }
    // Also handles first use, when no file exists for FileView to watch yet.
    Timer { interval: 2000; repeat: true; running: true; onTriggered: settings.reload() }
    function mediaFor(name) {
        if (!config.enabled) return null
        const id = config.mode === "individual" ? (config.assignments || {})[name] : config.default
        return (config.library || []).find(item => item.id === id) || null
    }
    readonly property real desktopLeft: Math.min.apply(null, Quickshell.screens.map(s => s.x))
    readonly property real desktopTop: Math.min.apply(null, Quickshell.screens.map(s => s.y))
    readonly property real desktopWidth: Math.max.apply(null, Quickshell.screens.map(s => s.x + s.width)) - desktopLeft
    readonly property real desktopHeight: Math.max.apply(null, Quickshell.screens.map(s => s.y + s.height)) - desktopTop
    Variants {
        model: Quickshell.screens
        PanelWindow {
            id: wall
            required property var modelData
            screen: modelData
            readonly property var media: root.mediaFor(modelData.name)
            readonly property bool spanning: root.config.mode === "span"
            visible: media !== null
            anchors { top: true; bottom: true; left: true; right: true }
            exclusionMode: ExclusionMode.Ignore
            color: "transparent"
            WlrLayershell.layer: WlrLayer.Bottom
            WlrLayershell.namespace: "wallpaper-pro"
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
            mask: Region {}
            Item {
                anchors.fill: parent
                clip: true
                Item {
                    x: wall.spanning ? root.desktopLeft - wall.modelData.x : 0
                    y: wall.spanning ? root.desktopTop - wall.modelData.y : 0
                    width: wall.spanning ? root.desktopWidth : wall.width
                    height: wall.spanning ? root.desktopHeight : wall.height
                    Image {
                        anchors.fill: parent
                        source: wall.media && wall.media.kind === "image" ? wall.media.url : ""
                        asynchronous: true
                        fillMode: Image.PreserveAspectCrop
                    }
                    Video {
                        id: video
                        anchors.fill: parent
                        source: wall.media && wall.media.kind === "video" ? wall.media.url : ""
                        loops: MediaPlayer.Infinite
                        muted: true
                        fillMode: VideoOutput.PreserveAspectCrop
                        readonly property bool paused: root.config.pauseOnBattery !== false && UPower.onBattery
                        onSourceChanged: { if (source.toString() !== "") { play(); if (paused) freeze.restart() } }
                        onPausedChanged: { if (paused) pause(); else if (source.toString() !== "") play() }
                        Timer { id: freeze; interval: 300; onTriggered: video.pause() }
                    }
                }
            }
        }
    }
}
