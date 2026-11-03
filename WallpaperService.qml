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
    property bool hasSettings: false
    property var players: []
    function playbackStatus() {
        return JSON.stringify({ monitors: Quickshell.screens.map(screen => screen.name), enabled: !!config.enabled, mode: config.mode || "individual", paused: paused,
            players: players.map(player => ({ monitor: player.monitorName, position: player.position,
                duration: player.duration, mediaStatus: player.mediaStatus, loops: player.loops, state: player.playbackState, error: player.errorString })) })
    }
    IpcHandler {
        target: "wallpaper-pro"
        function status(): string { return root.playbackStatus() }
    }
    property string configPath: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/wallpaper-pro/settings.json"
    FileView {
        id: settings
        path: root.configPath
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoadFailed: if (root.hasSettings) root.config = ({})
        onLoaded: { root.hasSettings = true; try { root.config = JSON.parse(text()) } catch (e) { console.warn("Wallpaper Pro: invalid settings", e) } }
    }
    // Also handles first use, when no file exists for FileView to watch yet.
    Timer { interval: 2000; repeat: true; running: true; onTriggered: settings.reload() }
    function mediaFor(name) {
        if (!config.enabled) return null
        const id = config.mode === "individual" ? (config.assignments || {})[name] : config.default
        return (config.library || []).find(item => item.id === id) || null
    }
    readonly property bool paused: config.pauseOnBattery !== false && UPower.onBattery
    readonly property string groupId: config.enabled && config.mode !== "individual" ? String(config.default || "") : ""
    property real elapsed: 0
    property real lastTick: Date.now()
    onGroupIdChanged: { elapsed = 0; lastTick = Date.now() }
    Timer {
        interval: 100
        repeat: true
        running: root.groupId !== ""
        onTriggered: {
            const now = Date.now()
            if (!root.paused) root.elapsed += Math.max(0, now - root.lastTick)
            root.lastTick = now
        }
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
                    VideoOutput {
                        id: output
                        anchors.fill: parent
                        fillMode: VideoOutput.PreserveAspectCrop
                    }
                    Loader {
                        active: wall.media !== null && wall.media.kind === "video"
                        sourceComponent: Component {
                            MediaPlayer {
                                id: player
                                readonly property string monitorName: wall.modelData.name
                                readonly property bool batteryPaused: root.paused
                                Component.onCompleted: { root.players = root.players.concat([player]); loadMedia() }
                                Component.onDestruction: root.players = root.players.filter(item => item !== player)
                                function loadMedia() {
                                    const next = wall.media && wall.media.kind === "video" ? wall.media.url : ""
                                    if (source.toString() === next) return
                                    // Stop the old stream while it is still attached, then replace it.
                                    stop()
                                    source = next
                                }
                                property Connections mediaConnection: Connections {
                                    target: wall
                                    function onMediaChanged() { player.loadMedia() }
                                }
                                loops: MediaPlayer.Infinite
                                videoOutput: output
                                audioOutput: AudioOutput { muted: true }
                                function applyPlayback() {
                                    if (source.toString() === "") { stop(); return }
                                    if (batteryPaused) {
                                        // Decode the first frame before pausing a newly selected video.
                                        if (position === 0) { play(); freeze.restart() }
                                        else pause()
                                    } else {
                                        freeze.stop()
                                        play()
                                    }
                                }
                                function align() {

                                    if (playbackState !== MediaPlayer.PlayingState) return
                                    if (wall.media && root.groupId === wall.media.id && seekable && duration > 0) {
                                        const desired = root.elapsed % duration
                                        const delta = Math.abs(position - desired)
                                        if (Math.min(delta, duration - delta) > 150) position = desired
                                    }
                                }
                                onSourceChanged: Qt.callLater(applyPlayback)
                                onMediaStatusChanged: {
                                    if (mediaStatus === MediaPlayer.LoadedMedia) applyPlayback()
                                }
                                onBatteryPausedChanged: applyPlayback()
                                property Timer syncTimer: Timer {
                                    interval: 500
                                    repeat: true
                                    running: player.source.toString() !== "" && !player.batteryPaused && root.groupId !== ""
                                    onTriggered: player.align()
                                }
                                property Timer freezeTimer: Timer { id: freeze; interval: 300; onTriggered: if (player.batteryPaused) player.pause() }
                            }
                        }
                    }
                }
            }
        }
    }
}
