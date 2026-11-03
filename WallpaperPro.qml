pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

Item {
    id: root
    property var shell
    property var manifest
    property bool opened: false
    property var state: ({library: []})
    property string selected: ""
    property string message: "Add an image or video to get started."
    readonly property string script: decodeURIComponent(Qt.resolvedUrl("scripts/wallpaper-pro.py").toString().replace(/^file:\/\//, ""))
    function open(payload) { opened = true; run(["status"]) }
    function close() { opened = false }
    function run(args) {
        if (worker.running) return
        message = "Working…"
        worker.command = ["python3", script].concat(args)
        worker.running = true
    }
    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.state = JSON.parse(text); root.message = "Library ready · " + root.state.library.length + " wallpapers" }
                catch (e) { }
            }
        }
        stderr: StdioCollector { onStreamFinished: { if (text.trim()) root.message = text.trim() } }
        onExited: function(code, status) { if (code !== 0 && root.message === "Working…") root.message = "Operation failed (" + code + ")" }
    }
    FileDialog {
        id: picker
        title: "Add wallpaper"
        nameFilters: ["Wallpaper media (*.jpg *.jpeg *.png *.webp *.bmp *.avif *.mp4 *.webm *.mkv *.mov *.m4v)"]
        onAccepted: root.run(["import", selectedFile.toString()])
    }
    PanelWindow {
        id: panel
        visible: root.opened
        implicitWidth: 940
        implicitHeight: 690
        color: "#111820"
        WlrLayershell.namespace: "wallpaper-pro-manager"
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
        exclusionMode: ExclusionMode.Ignore
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 28
            spacing: 16
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Label { text: "WALLPAPER PRO"; color: "#f1f5f9"; font.pixelSize: 28; font.bold: true }
                    Label { text: "Your collection. Every screen."; color: "#a4b4c4" }
                }
                Item { Layout.fillWidth: true }
                Button { text: "Turn off"; enabled: !worker.running; onClicked: root.run(["off"]) }
                Button { text: "Close"; onClicked: root.close() }
            }
            RowLayout {
                Button { text: "Add local file"; enabled: !worker.running; onClicked: picker.open() }
                TextField { id: link; Layout.fillWidth: true; placeholderText: "Paste a direct image or video URL"; onAccepted: if (text.trim()) root.run(["import", text.trim()]) }
                Button { text: "Import link"; enabled: !worker.running && link.text.trim() !== ""; onClicked: root.run(["import", link.text.trim()]) }
            }
            Label { text: root.message; color: "#bcd0dd"; Layout.fillWidth: true; wrapMode: Text.Wrap }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                GridView {
                    id: gallery
                    model: root.state.library || []
                    cellWidth: Math.max(200, width / 3)
                    cellHeight: 174
                    delegate: Item {
                        id: card
                        required property var modelData
                        width: gallery.cellWidth - 12
                        height: gallery.cellHeight - 12
                        Rectangle {
                            anchors.fill: parent
                            radius: 10
                            color: "#1d2935"
                            border.width: root.selected === card.modelData.id ? 2 : 1
                            border.color: root.selected === card.modelData.id ? "#7ce2c0" : "#344452"
                            Image { anchors { top: parent.top; left: parent.left; right: parent.right; margins: 8 } height: 100; source: card.modelData.kind === "image" ? card.modelData.url : ""; fillMode: Image.PreserveAspectFit; asynchronous: true }
                            Label { anchors.centerIn: parent; visible: card.modelData.kind === "video"; text: "▶  LIVE VIDEO"; color: "#7ce2c0" }
                            Label { anchors { bottom: parent.bottom; left: parent.left; right: parent.right; margins: 12 } text: card.modelData.name; elide: Text.ElideRight; color: "#f1f5f9" }
                            MouseArea { anchors.fill: parent; onClicked: root.selected = card.modelData.id }
                        }
                    }
                }
            }
            RowLayout {
                ComboBox { id: mode; model: ["Individual monitor", "All monitors", "Panoramic image"] }
                ComboBox { id: monitor; model: Quickshell.screens.map(s => s.name); enabled: mode.currentIndex === 0; Layout.fillWidth: true }
                Button {
                    text: "Apply wallpaper"
                    enabled: root.selected !== "" && !worker.running
                    onClicked: root.run(["apply", root.selected, "--mode", ["individual", "all", "span"][mode.currentIndex], "--monitor", monitor.currentText])
                }
            }
            Label { text: "Videos loop silently. All monitors repeats the video on each screen; panoramic mode spans images. Turn off restores the wallpaper underneath."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: "#a4b4c4" }
        }
    }
}
