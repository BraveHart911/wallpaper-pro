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
    property alias renderer: rendererService
    WallpaperService { id: rendererService }
    property var manifest
    property bool opened: false
    property var state: ({library: []})
    property string selected: ""
    property int librarySection: 0
    property string searchQuery: ""
    onLibrarySectionChanged: selected = ""
    readonly property var filteredLibrary: (state.library || []).filter(item => {
        const layout = item.layout || ((item.width || 0) / (item.height || 1) >= 2.7 ? "panoramic" : "single")
        const matchesSection = librarySection === 0 || (librarySection === 1 && item.kind === "video") || (librarySection === 2 && layout === "single") || (librarySection === 3 && layout === "panoramic") || (librarySection === 4 && !item.bundled)
        return matchesSection && String(item.name || "").toLowerCase().indexOf(searchQuery.toLowerCase()) !== -1
    })
    readonly property var selectedMedia: (state.library || []).find(item => item.id === selected) || null
    function selectMedia(item) {
        selected = item.id
        mode.currentIndex = item.layout === "panoramic" ? 2 : 0
    }
    readonly property string playbackErrors: rendererService.players.map(player => player.errorString ? player.monitorName + ": " + player.errorString : "").filter(text => text !== "").join(" · ")
    property string message: "Add an image or video to get started."
    readonly property string script: decodeURIComponent(Qt.resolvedUrl("scripts/wallpaper-pro.py").toString().replace(/^file:\/\//, ""))
    onStateChanged: {
        mode.currentIndex = Math.max(0, ["individual", "all", "span"].indexOf(state.mode || "individual"))
        if (!(state.library || []).some(item => item.id === selected))
            selected = state.default || ((state.library || [])[0] || {}).id || ""
    }
    function open(payload) { opened = true; run(["status"]) }
    function close() { opened = false }
    function assignment(name) {
        const id = state.mode === "individual" ? (state.assignments || {})[name] : state.default
        const media = (state.library || []).find(item => item.id === id)
        return media ? media.name : "Desktop default"
    }
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
        implicitWidth: Math.min(1040, screen.width - 48)
        implicitHeight: Math.min(800, screen.height - 64)
        color: "#111820"
        WlrLayershell.namespace: "wallpaper-pro-manager"
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
        exclusionMode: ExclusionMode.Ignore
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 28
            spacing: 16
            focus: true
            Keys.onEscapePressed: root.close()
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
            Label {
                text: "Playback issue: " + root.playbackErrors
                visible: root.playbackErrors !== ""
                color: "#ffb4a9"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            RowLayout {
                Repeater {
                    model: Quickshell.screens
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: 62
                        radius: 8
                        color: "#1d2935"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Label { text: parent.parent.modelData.name; color: "#7ce2c0"; font.bold: true }
                            Label { text: root.assignment(parent.parent.modelData.name); color: "#a4b4c4"; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Repeater {
                    model: ["All wallpapers", "Videos", "Single monitor", "Dual panorama", "My imports"]
                    delegate: Button {
                        required property int index
                        required property string modelData
                        text: modelData
                        checkable: true
                        checked: root.librarySection === index
                        onClicked: root.librarySection = index
                    }
                }
                Item { Layout.fillWidth: true }
                TextField { Layout.preferredWidth: 180; placeholderText: "Search wallpapers"; onTextChanged: root.searchQuery = text }
            }
            Label {
                text: root.filteredLibrary.length + " wallpapers · Select a card, then apply to your screen or both monitors."
                color: "#a4b4c4"
            }
            Label {
                visible: !root.filteredLibrary.length
                text: "No matching wallpapers. Add a local file or direct web link, or try another category."
                color: "#a4b4c4"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                GridView {
                    id: gallery
                    model: root.filteredLibrary
                    cellWidth: Math.max(200, width / 3)
                    cellHeight: 192
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
                            Image { anchors { top: parent.top; left: parent.left; right: parent.right; margins: 8 } height: 100; source: card.modelData.thumbnailUrl || (card.modelData.kind === "image" ? card.modelData.url : ""); fillMode: Image.PreserveAspectFit; asynchronous: true }
                            Label { anchors.centerIn: parent; visible: card.modelData.kind === "video" && !card.modelData.thumbnailUrl; text: "▶  LIVE VIDEO"; color: "#7ce2c0" }
                            Label { anchors { bottom: parent.bottom; left: parent.left; right: parent.right; margins: 12; bottomMargin: 30 } text: card.modelData.name; elide: Text.ElideRight; color: "#f1f5f9" }
                            Label {
                                anchors { bottom: parent.bottom; left: parent.left; right: parent.right; margins: 12 }
                                text: (card.modelData.kind === "video" ? "VIDEO · " : "") + (card.modelData.layout === "panoramic" ? "DUAL PANORAMA" : "SINGLE MONITOR") + (card.modelData.width ? " · " + card.modelData.width + " × " + card.modelData.height : "")
                                color: "#7ce2c0"
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                            MouseArea { anchors.fill: parent; onClicked: root.selectMedia(card.modelData) }
                        }
                    }
                }
            }
            RowLayout {
                ComboBox { id: mode; implicitWidth: 210; model: ["Individual monitor", "All monitors", "Panoramic (experimental)"] }
                ComboBox { id: monitor; model: Quickshell.screens.map(s => s.name); enabled: mode.currentIndex === 0; Layout.fillWidth: true }
                Button {
                    text: "Apply wallpaper"
                    enabled: root.selected !== "" && !worker.running
                    onClicked: root.run(["apply", root.selected, "--mode", ["individual", "all", "span"][mode.currentIndex], "--monitor", monitor.currentText])
                }
            }
            RowLayout {
                CheckBox {
                    text: "Pause video on battery"
                    checked: root.state.pauseOnBattery !== false
                    enabled: !worker.running
                    onClicked: root.run(["battery", checked ? "on" : "off"])
                }
                Item { Layout.fillWidth: true }
                Button { text: "Clear monitor"; enabled: mode.currentIndex === 0 && !worker.running; onClicked: root.run(["unassign", monitor.currentText]) }
                Button { text: "Remove selected"; enabled: root.selectedMedia !== null && !root.selectedMedia.bundled && !worker.running; onClicked: root.run(["remove", root.selected]) }
            }
            Label { text: "Videos loop silently. Panoramic mode spans images or video. Video timing is drift-corrected, not frame locked. Turn off restores the wallpaper underneath."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: "#a4b4c4" }
        }
    }
}
