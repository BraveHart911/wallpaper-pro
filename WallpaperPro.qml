pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtMultimedia
import Quickshell
import Quickshell.Io
import "ui"
import "js/Library.js" as Library

Item {
    id: root
    ThemePalette { id: theme }
    Timer { interval: 3000; repeat: true; running: root.opened; onTriggered: theme.refresh() }
    property string compatibilityWarning: ""
    property string themeSyncMessage: ""
    property string themeSyncError: ""
    property bool automaticThemeSync: true
    property bool libraryInitialized: false
    property bool refreshAfterThemeSync: false
    Component.onCompleted: if (automaticThemeSync) startThemeSync()
    function startThemeSync() {
        if (!themeSync.running) {
            themeSyncError = ""
            themeSyncMessage = "Discovering Omarchy theme wallpapers…"
            themeSync.running = true
        }
    }
    Timer { interval: 60000; repeat: true; running: root.automaticThemeSync; onTriggered: root.startThemeSync() }
    Timer {
        interval: 100
        running: root.refreshAfterThemeSync && root.opened && !worker.running
        onTriggered: { root.refreshAfterThemeSync = false; root.run(["status"]) }
    }
    Process {
        id: themeSync
        command: ["python3", root.script, "sync-themes", "--progress"]
        stdout: SplitParser {
            onRead: function(line) {
                try {
                    const result = JSON.parse(line)
                    if (result.event === "context-progress") root.themeSyncMessage = result.message || "Learning image context · " + result.done + " of " + result.total
                    if (result.event === "color-progress") root.themeSyncMessage = "Analyzing wallpaper colors · " + result.done + " of " + result.total
                    if (result.event === "theme-progress") root.themeSyncMessage = "Discovering theme wallpapers · " + result.done + " of " + result.total
                } catch (e) { }
            }
        }
        onExited: function(code, status) {
            if (code === 0) root.refreshAfterThemeSync = true
            else root.themeSyncError = "Theme discovery could not finish. Try syncing again in Settings."
        }
    }
    Process {
        id: desktopCheck
        command: ["python3", root.script, "doctor"]
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.compatibilityWarning = JSON.parse(text).warnings.join("\n") }
                catch (e) { root.compatibilityWarning = "Desktop compatibility check was unavailable." }
            }
        }
    }
    Process {
        id: themeListProcess
        command: ["python3", root.script, "theme-catalog"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const catalog = JSON.parse(text)
                    root.currentThemeName = catalog.current
                    root.availableThemes = catalog.themes
                    const current = catalog.themes.find(item => item.current)
                    root.currentThemeMode = current ? current.mode : "unknown"
                } catch (e) { root.operationError = "Could not read Omarchy's theme colors." }
            }
        }
    }
    Process {
        id: currentThemeProcess
        command: ["omarchy", "theme", "current"]
        stdout: StdioCollector { onStreamFinished: root.currentThemeName = text.trim() }
    }
    Process {
        id: currentBackgroundProcess
        command: ["omarchy", "theme", "bg", "current"]
        stdout: StdioCollector { onStreamFinished: root.currentBackground = text.trim() }
    }
    Process {
        id: applyThemeProcess
        command: ["omarchy", "theme", "set", root.pendingTheme]
        stderr: StdioCollector { onStreamFinished: if (text.trim()) root.operationError = text.trim() }
        onExited: function(code, status) {
            root.themeApplying = false
            if (code !== 0) root.operationError = "Could not apply " + root.pendingTheme + "."
            else {
                root.currentThemeName = root.pendingTheme
                const appliedTheme = root.availableThemes.find(item => item.name === root.pendingTheme)
                root.currentThemeMode = appliedTheme ? appliedTheme.mode : "unknown"
                root.currentBackground = ""
                root.message = root.pendingTheme + " is now active. Refreshing wallpapers and colors…"
                theme.refresh()
                currentBackgroundProcess.running = true
                if (root.automaticThemeSync) root.startThemeSync()
                else root.run(["status"])
            }
        }
    }
    Process {
        id: nextBackgroundProcess
        command: ["omarchy", "theme", "bg", "next"]
        onExited: function(code, status) {
            if (code === 0) currentBackgroundProcess.running = true
            else root.operationError = "Could not change the Omarchy theme background."
        }
    }
    property var shell
    property alias renderer: rendererService
    WallpaperService { id: rendererService }
    property var manifest
    property bool opened: false
    property string appWindowTitle: "Wallpaper Pro"
    property var availableThemes: []
    property string currentThemeName: ""
    property string currentThemeMode: "unknown"
    property string currentBackground: ""
    property string themeSearch: ""
    property string pendingTheme: ""
    property bool themeApplying: false
    property string previewId: ""
    property var previewOutput: null
    readonly property bool compact: panel.width < 900
    readonly property bool dark: (Qt.color(theme.colors.background).r + Qt.color(theme.colors.background).g + Qt.color(theme.colors.background).b) < 1.5
    readonly property color surface: Qt.tint(theme.colors.background, Qt.rgba(0.5, 0.5, 0.5, 0.07))
    readonly property color divider: Qt.rgba(0.5, 0.5, 0.5, 0.15)
    readonly property var sections: ["All wallpapers", "Live wallpapers", "Single monitor", "Dual panorama", "My imports", "Favorites", "Themes"]
    function displayName(media) {
        if (!media) return "Choose a wallpaper"
        const title = String(media.name || "").replace(/\.(jpg|jpeg|png|webp|bmp|avif|mp4|webm|mkv|mov|m4v|gif)$/i, "").replace(/[._ -]+\d{3,5}[x×]\d{3,5}$/i, "").replace(/[-_]+/g, " ")
        return title.charAt(0).toUpperCase() + title.slice(1)
    }
    function mediaSubtitle(media) { return media ? (media.contextGroup ? media.contextGroup + " · " : "") + (media.themes && media.themes.length ? media.themes[0] + " · " : "") + (media.layout === "panoramic" ? "Dual panorama" : "Single monitor") + (media.width ? " · " + media.width + " × " + media.height : "") : "Select a preview from your collection" }
    property var state: ({library: []})
    property string selected: ""
    property int librarySection: 0
    property bool liveDualOnly: false
    property string searchQuery: ""
    readonly property string sortOrder: state.sortOrder || "original"
    readonly property var favoriteIds: state.favorites || []
    readonly property var sortKeys: ["original", "name", "color"]
    readonly property var filteredThemes: availableThemes.filter(item => (item.name + " " + item.group).toLowerCase().indexOf(themeSearch.trim().toLowerCase()) !== -1)
    function matchesSearch(item) {
        const terms = searchQuery.trim().toLowerCase().split(/\s+/).filter(term => term !== "")
        if (!terms.length) return true
        const haystack = [item.name || "", (item.themes || []).join(" "), item.contextGroup || "", item.colorName || ""].join(" ").toLowerCase()
        return terms.every(term => haystack.indexOf(term) !== -1)
    }
    onLibrarySectionChanged: { selected = ""; stopPreview(previewId) }
    onLiveDualOnlyChanged: stopPreview(previewId)
    readonly property var filteredLibrary: Library.ordered((state.library || []).filter(item => {
        const layout = item.layout || ((item.width || 0) / (item.height || 1) >= 2.7 ? "panoramic" : "single")
        const matchesSection = librarySection === 0 || (librarySection === 1 && item.kind === "video" && (!liveDualOnly || layout === "panoramic")) || (librarySection === 2 && layout === "single") || (librarySection === 3 && layout === "panoramic") || (librarySection === 4 && !item.bundled && !item.themeManaged) || (librarySection === 5 && favoriteIds.indexOf(item.id) !== -1) || (librarySection === 6 && (item.themes || []).length > 0)
        return matchesSection && matchesSearch(item)
    }), sortOrder, state.contextEnabled === true)
    readonly property var selectedMedia: (state.library || []).find(item => item.id === selected) || null
    function selectMedia(item) {
        selected = item.id
        mode.currentIndex = item.layout === "panoramic" ? 2 : 0
    }
    function startPreview(media, output) {
        if (librarySection !== 1 || media.kind !== "video") return
        previewId = media.id
        previewOutput = output
        previewPlayer.videoOutput = output
        if (previewPlayer.source.toString() !== media.url) {
            previewPlayer.stop()
            previewPlayer.source = media.url
        }
        previewPlayer.play()
    }
    function stopPreview(id) {
        if (!id || previewId !== id) return
        previewPlayer.stop()
        previewPlayer.source = ""
        previewPlayer.videoOutput = null
        previewOutput = null
        previewId = ""
    }
    MediaPlayer {
        id: previewPlayer
        loops: MediaPlayer.Infinite
        audioOutput: AudioOutput { muted: true; volume: 0 }
    }
    readonly property string playbackErrors: rendererService.players.map(player => player.errorString ? player.monitorName + ": " + player.errorString : "").filter(text => text !== "").join(" · ")
    property string pendingCommand: ""
    property string folderErrors: ""
    property string operationError: ""
    property string message: "Add an image or video to get started."
    readonly property string script: decodeURIComponent(Qt.resolvedUrl("scripts/wallpaper-pro.py").toString().replace(/^file:\/\//, ""))
    onStateChanged: {
        if (!libraryInitialized || ["apply", "off", "unassign"].indexOf(pendingCommand) !== -1)
            mode.currentIndex = Math.max(0, ["individual", "all", "span"].indexOf(state.mode || "individual"))
        libraryInitialized = true
        if (!(state.library || []).some(item => item.id === selected)) {
            const preferred = filteredLibrary.find(item => item.id === state.default) || filteredLibrary[0]
            selected = preferred ? preferred.id : ""
        }
    }
    function open(payload) {
        if (!Quickshell.screens.length) return
        opened = true
        libraryInitialized = false
        theme.refresh()
        if (automaticThemeSync) startThemeSync()
        if (!desktopCheck.running) desktopCheck.running = true
        refreshThemeControls()
        run(["status"])
    }
    function refreshThemeControls() {
        if (!themeListProcess.running) themeListProcess.running = true
        if (!currentThemeProcess.running) currentThemeProcess.running = true
        if (!currentBackgroundProcess.running) currentBackgroundProcess.running = true
    }
    function applyTheme(name) {
        if (themeApplying || !name) return
        pendingTheme = name
        operationError = ""
        themeApplying = true
        applyThemeProcess.running = true
    }
    function nextThemeBackground() {
        if (!nextBackgroundProcess.running) nextBackgroundProcess.running = true
    }
    function showImportOptions() { importPopup.open() }
    function showPlaybackSettings() { settingsPopup.open() }
    function close() {
        if (!opened) return
        opened = false
        stopPreview(previewId)
        if (shell && typeof shell.hide === "function") shell.hide("bravehart911.wallpaper-pro")
    }
    function assignment(name) {
        if (!state.enabled) return "Omarchy wallpaper"
        const id = state.mode === "individual" ? (state.assignments || {})[name] : state.default
        const media = (state.library || []).find(item => item.id === id)
        return media ? displayName(media) : "Omarchy wallpaper"
    }
    function run(args) {
        if (worker.running) return
        pendingCommand = args[0]
        folderErrors = ""
        operationError = ""
        message = pendingCommand === "import-folder" ? "Scanning folder and subfolders…" : "Working…"
        worker.command = ["python3", script].concat(args)
        worker.running = true
    }
    Process {
        id: worker
        stdout: SplitParser {
            onRead: function(line) {
                try {
                    const result = JSON.parse(line)
                    if (result.event === "setup-progress" || result.event === "context-progress") {
                        root.message = result.message || "Preparing local visual analysis…"
                        return
                    }
                    if (result.event === "context-ready") return
                    if (result.event === "progress") {
                        root.message = "Importing " + (result.done + 1) + " of " + result.total + " · " + result.file
                        return
                    }
                    if (root.pendingCommand === "favorite" && root.librarySection === 5 && (result.favorites || []).indexOf(root.selected) === -1) root.selected = ""
                    root.state = result
                    if (root.pendingCommand === "import-folder" && result.lastFolderImport) {
                        const report = result.lastFolderImport
                        root.message = "Folder imported · " + report.added + " added · " + report.duplicates + " duplicates · " + report.failed + " failed · " + report.skipped + " unsupported files skipped"
                        root.folderErrors = report.errors.slice(0, 3).map(error => error.file + ": " + error.error).join("\n")
                    } else {
                        root.message = "Library ready · " + root.state.library.length + " wallpapers"
                    }
                } catch (e) { root.operationError = "Could not read the library response." }
            }
        }
        stderr: StdioCollector { onStreamFinished: { if (text.trim()) root.operationError = text.trim() } }
        onExited: function(code, status) {
            if (code !== 0 && !root.operationError) root.operationError = "Operation failed (" + code + ")"
            if (code === 0 && root.state.contextEnabled && ["import", "import-folder", "thumbnails", "install-context", "context"].indexOf(root.pendingCommand) !== -1) root.startThemeSync()
        }
    }
    FileDialog {
        id: picker
        title: "Add wallpaper"
        nameFilters: ["Wallpaper media (*.jpg *.jpeg *.png *.webp *.bmp *.avif *.mp4 *.webm *.mkv *.mov *.m4v *.gif)"]
        onAccepted: root.run(["import", selectedFile.toString()])
    }
    FolderDialog {
        id: folderPicker
        title: "Add wallpaper folder (includes all subfolders)"
        onAccepted: root.run(["import-folder", selectedFolder.toString(), "--progress"])
    }
    FloatingWindow {
        id: panel
        title: root.appWindowTitle
        minimumSize: Qt.size(540, 560)
        implicitWidth: 1160
        implicitHeight: 800
        visible: root.opened
        color: theme.colors.background
        onClosed: root.close()
        Pane {
            id: frame
            anchors.fill: parent
            padding: 0
            background: null
            font.family: "Inter"
            palette.window: theme.colors.background
            palette.windowText: theme.colors.foreground
            palette.text: theme.colors.foreground
            palette.base: theme.colors.background
            palette.button: root.surface
            palette.buttonText: theme.colors.foreground
            palette.highlight: root.dark ? "#4da3ff" : "#0065cc"
            palette.highlightedText: "white"
            palette.placeholderText: theme.secondary
            focus: true
            Keys.onEscapePressed: root.close()

            ColumnLayout {
                anchors.fill: parent
                spacing: 0
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 66
                    color: root.surface
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: root.divider }
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 20
                        anchors.rightMargin: 20
                        spacing: 12
                        Label { visible: panel.width > 620; text: "Wallpaper Pro"; font.pixelSize: 14; font.weight: Font.DemiBold; color: theme.colors.foreground }
                        Item { Layout.fillWidth: true }
                        ProField {
                            visible: !root.compact && root.librarySection !== 7
                            Layout.preferredWidth: 230
                            placeholderText: "Search wallpapers"
                            text: root.searchQuery
                            onTextEdited: root.searchQuery = text
                        }
                        ProButton { id: addButton; visible: root.librarySection !== 7; text: "+  Add wallpapers"; primary: true; onClicked: importPopup.open() }
                        ProButton { text: "⚙"; quiet: true; onClicked: settingsPopup.open(); Accessible.name: "Wallpaper settings" }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0
                    Rectangle {
                        visible: !root.compact
                        Layout.preferredWidth: 218
                        Layout.fillHeight: true
                        color: root.surface
                        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: root.divider }
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 6
                            Label { text: "LIBRARY"; color: theme.secondary; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.4; Layout.topMargin: 12; Layout.bottomMargin: 10; Layout.leftMargin: 12 }
                            Repeater {
                                model: root.sections
                                delegate: ProButton {
                                    required property int index
                                    required property string modelData
                                    Layout.fillWidth: true
                                    text: modelData
                                    navigation: true
                                    iconName: ["library", "live", "monitor", "panorama", "imports", "favorite", "themes"][index]
                                    checked: root.librarySection === index
                                    onClicked: root.librarySection = index
                                }
                            }
                            ProButton {
                                Layout.fillWidth: true
                                text: "Themes & appearance"
                                navigation: true
                                iconName: "appearance"
                                checked: root.librarySection === 7
                                onClicked: { root.librarySection = 7; root.refreshThemeControls() }
                                Accessible.name: "Open themes and appearance controls"
                            }
                            Item { Layout.fillHeight: true }
                            Label { text: "YOUR DISPLAYS"; color: theme.secondary; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.3; Layout.leftMargin: 12; Layout.bottomMargin: 10 }
                            Repeater {
                                model: Quickshell.screens
                                delegate: Rectangle {
                                    id: displayCard
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: 80
                                    radius: 10
                                    color: Qt.rgba(0.5,0.5,0.5,0.07)
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 5
                                        RowLayout {
                                            Rectangle { width: 18; height: 12; radius: 2; color: "transparent"; border.color: theme.secondary; border.width: 1 }
                                            Label { text: displayCard.modelData.name; font.pixelSize: 12; font.weight: Font.Medium; color: theme.colors.foreground }
                                            Item { Layout.fillWidth: true }
                                            Rectangle { width: 5; height: 5; radius: 3; color: "#30c783" }
                                        }
                                        Label { text: root.assignment(displayCard.modelData.name); font.pixelSize: 11; color: theme.secondary; elide: Text.ElideRight; Layout.fillWidth: true }
                                    }
                                }
                            }
                    ProButton { text: "Use Omarchy wallpaper"; quiet: true; Layout.fillWidth: true; Layout.topMargin: 14; enabled: !worker.running; onClicked: root.run(["off"]) }
                        }
                    }
                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: root.compact ? 20 : 28
                            spacing: 18
                            RowLayout {
                                visible: root.librarySection !== 7
                                Layout.fillWidth: true
                                ColumnLayout {
                                    Layout.preferredWidth: 220
                                    spacing: 7
                                    Label { text: root.librarySection === 0 ? "Your collection" : root.sections[root.librarySection]; font.pixelSize: 27; font.weight: Font.DemiBold; color: theme.colors.foreground; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: root.filteredLibrary.length + " wallpapers. A fresh perspective for every screen."; font.pixelSize: 12; color: theme.secondary; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                                Item { Layout.fillWidth: true }
                                ProSegmented {
                                    visible: root.librarySection === 1 && !root.compact
                                    Layout.preferredWidth: 264
                                    options: ["All live", "Dual monitor"]
                                    selectedIndex: root.liveDualOnly ? 1 : 0
                                    accent: theme.colors.accent || "#0a84ff"
                                    foreground: theme.colors.foreground
                                    secondary: theme.secondary
                                    onActivated: function(index) { root.liveDualOnly = index === 1 }
                                }
                                Item { Layout.fillWidth: true }
                                ProCombo {
                                    Layout.preferredWidth: 150
                                    model: ["Sort: original", "Sort: name", root.state.contextEnabled ? "Color + context" : "Sort: color"]
                                    currentIndex: Math.max(0, root.sortKeys.indexOf(root.sortOrder))
                                    enabled: !worker.running
                                    onActivated: root.run(["sort", root.sortKeys[currentIndex]])
                                    Accessible.name: "Sort wallpapers"
                                }
                            }
                            RowLayout {
                                visible: root.compact && root.librarySection !== 7
                                Layout.fillWidth: true
                                ProCombo { Layout.fillWidth: true; model: root.sections; currentIndex: root.librarySection; onActivated: root.librarySection = currentIndex }
                                ProField { Layout.fillWidth: true; placeholderText: "Search"; text: root.searchQuery
                            onTextEdited: root.searchQuery = text }
                            }
                            RowLayout {
                                visible: root.librarySection === 1 && root.compact
                                Layout.fillWidth: true
                                ProSegmented {
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.preferredWidth: Math.min(280, parent.width)
                                    options: ["All live", "Dual monitor"]
                                    selectedIndex: root.liveDualOnly ? 1 : 0
                                    accent: theme.colors.accent || "#0a84ff"
                                    foreground: theme.colors.foreground
                                    secondary: theme.secondary
                                    onActivated: function(index) { root.liveDualOnly = index === 1 }
                                }
                            }
                            Rectangle {
                                visible: root.operationError !== "" || !!root.state.contextError || root.themeSyncError !== "" || themeSync.running || worker.running || root.folderErrors !== "" || root.playbackErrors !== "" || root.compatibilityWarning !== "" || root.pendingCommand === "import-folder"
                                Layout.fillWidth: true
                                implicitHeight: notice.implicitHeight + 24
                                radius: 10
                                color: Qt.rgba(0.04,0.52,1,0.08)
                                Label {
                                    id: notice
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    text: root.operationError || root.state.contextError || root.folderErrors || root.playbackErrors || root.compatibilityWarning || root.themeSyncError || (themeSync.running && !worker.running ? root.themeSyncMessage : root.message)
                                    color: root.operationError || root.folderErrors || root.playbackErrors ? theme.colors.red : theme.secondary
                                    wrapMode: Text.Wrap
                                    maximumLineCount: 3
                                    elide: Text.ElideRight
                                    font.pixelSize: 12
                                }
                            }
                            RowLayout {
                                visible: root.librarySection !== 7
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 8
                            ScrollView {
                                id: collectionScroll
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                ScrollBar.vertical.policy: root.sortOrder === "color" ? ScrollBar.AlwaysOff : ScrollBar.AsNeeded
                                GridView {
                                    id: gallery
                                    model: root.filteredLibrary
                                    keyNavigationEnabled: true
                                    Keys.onReturnPressed: if (currentItem) root.selectMedia(currentItem.modelData)
                                    Keys.onSpacePressed: if (currentItem) root.selectMedia(currentItem.modelData)
                                    cellWidth: width / Math.max(1, Math.floor(width / 240))
                                    cellHeight: (cellWidth - 18) * 9 / 16 + 74
                                    delegate: Item {
                                        id: card
                                        required property var modelData
                                        required property int index
                                        readonly property bool favorite: root.favoriteIds.indexOf(modelData.id) !== -1
                                        Accessible.role: Accessible.Button
                                        Accessible.name: root.displayName(modelData) + ", " + root.mediaSubtitle(modelData)
                                        Accessible.selected: root.selected === modelData.id
                                        Accessible.onPressAction: root.selectMedia(modelData)
                                        width: gallery.cellWidth - 18
                                        height: gallery.cellHeight - 18
                                        Rectangle {
                                            anchors.fill: parent
                                            anchors.topMargin: 2
                                            anchors.bottomMargin: -2
                                            radius: 13
                                            color: Qt.rgba(0,0,0,root.dark ? 0.22 : 0.05)
                                        }
                                        Rectangle {
                                            anchors.fill: parent
                                            radius: 13
                                            color: root.selected === card.modelData.id ? Qt.tint(theme.colors.background, Qt.rgba(0.04,0.52,1,0.12)) : root.surface
                                            border.width: root.selected === card.modelData.id ? 2 : 1
                                            border.color: root.selected === card.modelData.id ? "#0a84ff" : root.divider
                                            Rectangle {
                                                id: picture
                                                anchors.top: parent.top
                                                anchors.left: parent.left
                                                anchors.right: parent.right
                                                anchors.margins: 7
                                                height: width * 9 / 16
                                                color: Qt.rgba(0.5,0.5,0.5,0.08)
                                                radius: 8
                                                clip: true
                                                Image {
                                                    id: preview
                                                    anchors.fill: parent
                                                    visible: root.previewId !== card.modelData.id
                                                    source: card.modelData.thumbnailUrl || (card.modelData.kind === "image" ? card.modelData.url : "")
                                                    fillMode: Image.PreserveAspectCrop
                                                    asynchronous: true
                                                    sourceSize.width: 600
                                                }
                                                VideoOutput {
                                                    id: livePreview
                                                    anchors.fill: parent
                                                    visible: root.previewId === card.modelData.id
                                                    fillMode: VideoOutput.PreserveAspectCrop
                                                }
                                                Label { anchors.centerIn: parent; visible: preview.source.toString() === "" || preview.status === Image.Error; text: "Preview unavailable"; color: theme.secondary; font.pixelSize: 12 }
                                                Rectangle {
                                                    visible: card.modelData.kind === "video" || (card.modelData.themes || []).length > 0
                                                    x: 8; y: 8; width: root.previewId === card.modelData.id ? 76 : 49; height: 22; radius: 6
                                                    color: "#a0101318"
                                                    Text { anchors.centerIn: parent; text: card.modelData.kind === "video" ? (root.previewId === card.modelData.id ? "▶ PREVIEW" : "▶ LIVE") : "THEME"; color: "white"; font.pixelSize: 9; font.weight: Font.DemiBold }
                                                }
                                            }
                                            ColumnLayout {
                                                anchors { left: parent.left; right: parent.right; top: picture.bottom; margins: 10; topMargin: 9; rightMargin: 24 }
                                                spacing: 3
                                                Label { text: root.displayName(card.modelData); font.pixelSize: 12; font.weight: Font.Medium; color: theme.colors.foreground; elide: Text.ElideRight; Layout.fillWidth: true }
                                                Label { text: root.mediaSubtitle(card.modelData); font.pixelSize: 10; color: theme.secondary; elide: Text.ElideRight; Layout.fillWidth: true }
                                            }
                                            Rectangle {
                                                anchors { right: parent.right; bottom: parent.bottom; margins: 12 }
                                                width: 7; height: 7; radius: 4
                                                visible: !!card.modelData.dominantColor
                                                color: card.modelData.dominantColor || "transparent"
                                                border.color: Qt.rgba(0.5,0.5,0.5,0.35)
                                            }
                                            MouseArea {
                                                id: cardMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onEntered: if (root.librarySection === 1 && card.modelData.kind === "video") root.startPreview(card.modelData, livePreview)
                                                onExited: root.stopPreview(card.modelData.id)
                                                onClicked: { gallery.currentIndex = card.index; gallery.forceActiveFocus(); root.selectMedia(card.modelData) }
                                                onDoubleClicked: if (!worker.running) root.run(["apply", card.modelData.id, "--mode", card.modelData.layout === "panoramic" ? "span" : "individual", "--monitor", monitor.currentText])
                                            }
                                            Rectangle {
                                                id: favoriteButton
                                                anchors { top: parent.top; right: parent.right; margins: 12 }
                                                width: 30
                                                height: 30
                                                radius: 15
                                                z: 2
                                                visible: card.favorite || cardMouse.containsMouse
                                                color: card.favorite ? Qt.rgba(0.70, 0.15, 0.25, 0.92) : Qt.rgba(0.03, 0.05, 0.07, 0.72)
                                                border.color: Qt.rgba(1, 1, 1, 0.28)
                                                Accessible.role: Accessible.Button
                                                Accessible.name: card.favorite ? "Remove from favorites" : "Add to favorites"
                                                Accessible.onPressAction: root.run(["favorite", card.modelData.id, card.favorite ? "off" : "on"])
                                                NavIcon { anchors.centerIn: parent; width: 17; height: 17; name: "favorite"; color: "white"; filled: card.favorite }
                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: root.run(["favorite", card.modelData.id, card.favorite ? "off" : "on"])
                                                }
                                            }
                                            ToolTip.visible: cardMouse.containsMouse
                                            ToolTip.delay: 700
                                            ToolTip.text: card.modelData.name + (card.modelData.contextGroup ? " · Suggested subject: " + card.modelData.contextGroup + (card.modelData.contextUncertain ? " (uncertain)" : "") : "") + (card.modelData.colorName ? " · " + card.modelData.colorName : "")
                                        }
                                    }
                                    Label { anchors.centerIn: parent; visible: !root.filteredLibrary.length; text: root.librarySection === 1 && root.liveDualOnly ? "No dual-monitor live wallpapers found.\nTurn off the filter to see all live wallpapers." : root.librarySection === 5 ? "No favorites yet.\nTap the heart on a wallpaper to save it here." : "No wallpapers here yet.\nAdd a file, folder, or web link to get started."; color: theme.secondary; horizontalAlignment: Text.AlignHCenter; lineHeight: 1.6; font.pixelSize: 13 }
                                }
                            }
                                ColorRail {
                                    visible: root.sortOrder === "color"
                                    Layout.preferredWidth: 30
                                    Layout.fillHeight: true
                                    items: root.filteredLibrary
                                    foreground: theme.colors.foreground
                                    background: theme.colors.background
                                    position: gallery.contentHeight > gallery.height ? Math.max(0, gallery.contentY) / (gallery.contentHeight - gallery.height) : 0
                                    pageSize: Math.min(1, gallery.height / Math.max(1, gallery.contentHeight))
                                    rowStep: gallery.cellHeight * 0.75
                                    onJumpRequested: function(fraction) {
                                        const index = Library.spectrumIndex(root.filteredLibrary.length, fraction)
                                        if (index >= 0) gallery.positionViewAtIndex(index, GridView.Beginning)
                                    }
                                    onScrollRequested: function(pixels) {
                                        gallery.contentY = Math.max(0, Math.min(Math.max(0, gallery.contentHeight - gallery.height), gallery.contentY + pixels))
                                    }
                                }
                            }
                            Item {
                                visible: root.librarySection === 7
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 16
                                    RowLayout {
                                        Layout.fillWidth: true
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: "Themes & appearance"; color: theme.colors.foreground; font.pixelSize: 27; font.weight: Font.DemiBold }
                                            Label { text: root.currentThemeName ? "Current theme · " + root.currentThemeName + " · " + (root.currentThemeMode === "unknown" ? "Mode unknown" : root.currentThemeMode.charAt(0).toUpperCase() + root.currentThemeMode.slice(1) + " mode") : "Choose an Omarchy theme"; color: theme.secondary; font.pixelSize: 12 }
                                        }
                                        ProButton { text: "Refresh list"; quiet: true; onClicked: root.refreshThemeControls() }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: 88
                                        radius: 12
                                        color: root.surface
                                        border.color: root.divider
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 14
                                            spacing: 12
                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 4
                                                Label { text: "Desktop background"; color: theme.colors.foreground; font.pixelSize: 13; font.weight: Font.DemiBold }
                                                Label { text: root.currentBackground || "Loading current background…"; color: theme.secondary; font.pixelSize: 11; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                            }
                                            ProButton { text: "Next background"; quiet: true; enabled: !nextBackgroundProcess.running; onClicked: root.nextThemeBackground() }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        ProField { Layout.fillWidth: true; placeholderText: "Search installed themes"; text: root.themeSearch; onTextEdited: root.themeSearch = text }
                                        Label { text: root.filteredThemes.length + " themes"; color: theme.secondary; font.pixelSize: 11 }
                                    }
                                    ScrollView {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        clip: true
                                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                        GridView {
                                            id: themeGrid
                                            model: root.filteredThemes
                                            cellWidth: width / Math.max(1, Math.floor(width / 250))
                                            cellHeight: 86
                                            delegate: Item {
                                                id: themeCard
                                                required property var modelData
                                                width: themeGrid.cellWidth - 12
                                                height: themeGrid.cellHeight - 12
                                                Rectangle {
                                                    anchors.fill: parent
                                                    radius: 12
                                                    color: themeCard.modelData.current ? Qt.tint(root.surface, Qt.rgba(0.04,0.52,1,0.16)) : root.surface
                                                    border.width: themeCard.modelData.current ? 2 : 1
                                                    border.color: themeCard.modelData.current ? themeCard.modelData.accent : root.divider
                                                    RowLayout {
                                                        anchors.fill: parent
                                                        anchors.margins: 13
                                                        spacing: 9
                                                        Rectangle {
                                                            width: 34; height: 34; radius: 10
                                                            color: themeCard.modelData.accent
                                                            border.color: Qt.rgba(0,0,0,.22)
                                                            Text { anchors.centerIn: parent; text: themeCard.modelData.current ? "✓" : ""; color: "white"; font.pixelSize: 15; font.weight: Font.Bold }
                                                        }
                                                        ColumnLayout {
                                                            Layout.fillWidth: true
                                                            spacing: 2
                                                            Label { Layout.fillWidth: true; text: themeCard.modelData.name; color: theme.colors.foreground; font.pixelSize: 12; font.weight: Font.Medium; elide: Text.ElideRight }
                                                            RowLayout {
                                                                spacing: 7
                                                                Label { text: themeCard.modelData.group; color: theme.secondary; font.pixelSize: 10 }
                                                                Rectangle {
                                                                    implicitWidth: modeLabel.implicitWidth + 12
                                                                    implicitHeight: 18
                                                                    radius: 5
                                                                    color: themeCard.modelData.mode === "light" ? "#f0e8d7" : themeCard.modelData.mode === "dark" ? "#303944" : root.surface
                                                                    Label { id: modeLabel; anchors.centerIn: parent; text: themeCard.modelData.mode === "unknown" ? "Mode ?" : themeCard.modelData.mode === "light" ? "Light" : "Dark"; color: themeCard.modelData.mode === "light" ? "#49443a" : theme.colors.foreground; font.pixelSize: 9; font.weight: Font.DemiBold }
                                                                }
                                                            }
                                                        }
                                                        ProButton {
                                                            text: themeCard.modelData.current ? "Current" : "Apply"
                                                            quiet: themeCard.modelData.current
                                                            enabled: !root.themeApplying && !themeCard.modelData.current
                                                            onClicked: root.applyTheme(themeCard.modelData.name)
                                                        }
                                                    }
                                                }
                                            }
                                            Label { anchors.centerIn: parent; visible: root.filteredThemes.length === 0; text: root.themeSearch ? "No matching themes." : "Loading installed themes…"; color: theme.secondary }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Rectangle {
                    visible: root.librarySection !== 7
                    Layout.fillWidth: true
                    implicitHeight: root.compact ? 120 : 88
                    color: root.surface
                    Rectangle { width: parent.width; height: 1; color: root.divider }
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: root.compact ? 16 : 20
                        spacing: 10
                        Label { visible: root.compact; text: root.displayName(root.selectedMedia); color: theme.colors.foreground; font.pixelSize: 13; font.weight: Font.Medium; elide: Text.ElideRight; Layout.fillWidth: true }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Image { visible: !root.compact; Layout.preferredWidth: 68; Layout.preferredHeight: 42; source: root.selectedMedia ? root.selectedMedia.thumbnailUrl || (root.selectedMedia.kind === "image" ? root.selectedMedia.url : "") : ""; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                            ColumnLayout {
                                visible: !root.compact
                                Layout.fillWidth: true
                                spacing: 5
                                Label { text: root.displayName(root.selectedMedia); color: theme.colors.foreground; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                                Label { text: root.mediaSubtitle(root.selectedMedia); color: theme.secondary; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                            }
                            ProCombo { id: mode; Layout.preferredWidth: root.compact ? 162 : 172; model: ["Individual monitor", "All monitors", "Panoramic (experimental)"] }
                            ProCombo { id: monitor; Layout.fillWidth: root.compact; Layout.preferredWidth: 130; model: Quickshell.screens.map(s => s.name); enabled: mode.currentIndex === 0 }
                            ProButton { text: root.compact ? "Apply" : "Apply wallpaper"; primary: true; enabled: root.selectedMedia !== null && !worker.running; onClicked: root.run(["apply", root.selected, "--mode", ["individual", "all", "span"][mode.currentIndex], "--monitor", monitor.currentText]) }
                        }
                    }
                }
            }

            Popup {
                id: importPopup
                x: frame.width - width - 20
                y: 58
                width: 228
                padding: 8
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { color: theme.colors.background; radius: 13; border.color: root.divider }
                ColumnLayout {
                    width: parent.width
                    spacing: 3
                    ProButton { text: "Add a file…"; quiet: true; navigation: true; Layout.fillWidth: true; enabled: !worker.running; onClicked: { importPopup.close(); picker.open() } }
                    ProButton { text: "Add folder & subfolders…"; quiet: true; navigation: true; Layout.fillWidth: true; enabled: !worker.running; onClicked: { importPopup.close(); folderPicker.open() } }
                    ProButton { text: "Add from web link…"; quiet: true; navigation: true; Layout.fillWidth: true; enabled: !worker.running; onClicked: { importPopup.close(); urlDialog.open() } }
                }
            }
            Dialog {
                id: urlDialog
                anchors.centerIn: parent
                width: Math.min(440, frame.width - 40)
                modal: true
                title: "Add from web link"
                background: Rectangle { color: theme.colors.background; radius: 15; border.color: root.divider }
                ColumnLayout {
                    width: parent.width
                    spacing: 16
                    Label { text: "Paste a direct image or video URL."; color: theme.secondary; font.pixelSize: 13 }
                    ProField { id: link; Layout.fillWidth: true; placeholderText: "https://…"; onAccepted: if (text.trim()) { root.run(["import", text.trim()]); urlDialog.close() } }
                    RowLayout {
                        Item { Layout.fillWidth: true }
                        ProButton { text: "Cancel"; quiet: true; onClicked: urlDialog.close() }
                        ProButton { text: "Import wallpaper"; primary: true; enabled: !worker.running && link.text.trim() !== ""; onClicked: { root.run(["import", link.text.trim()]); urlDialog.close() } }
                    }
                }
            }
            Popup {
                id: settingsPopup
                x: Math.max(16, frame.width - width - 20)
                y: 58
                width: Math.min(330, frame.width - 32)
                padding: 20
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                background: Rectangle { color: theme.colors.background; radius: 14; border.color: root.divider }
                height: Math.min(settingsColumn.implicitHeight + 40, Math.max(120, frame.height - 80))
                contentItem: ScrollView {
                    id: settingsScroll
                    clip: true
                    contentWidth: availableWidth
                    contentHeight: settingsColumn.implicitHeight
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    id: settingsColumn
                    width: settingsScroll.availableWidth
                    spacing: 8
                    Label { text: "Playback & library"; color: theme.colors.foreground; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.bottomMargin: 8 }
                    ProButton {
                        visible: !root.state.contextAvailable
                        text: "Enable smart grouping"
                        primary: true
                        enabled: !worker.running
                        Layout.fillWidth: true
                        onClicked: root.run(["install-context"])
                    }
                    Label {
                        visible: !root.state.contextAvailable
                        text: "Downloads a local image model and tools (about 530 MB on disk). Images stay on this device."
                        color: theme.secondary
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    ProCheck {
                        visible: !!root.state.contextAvailable
                        text: "Group by color, then image context"
                        checked: !!root.state.contextEnabled
                        enabled: !worker.running
                        onClicked: root.run(["context", checked ? "on" : "off"])
                    }
                    Label {
                        visible: !!root.state.contextEnabled
                        text: (root.state.contextReport ? root.state.contextReport.analyzed + " wallpapers analyzed. " : "") + "Subject labels are automatic suggestions."
                        color: theme.secondary
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    ProCheck { text: "Pause video on battery"; checked: root.state.pauseOnBattery !== false; enabled: !worker.running; onClicked: root.run(["battery", checked ? "on" : "off"]) }
                    ProCheck { text: "Pause behind fullscreen apps"; checked: root.state.pauseOnFullscreen !== false; enabled: !worker.running; onClicked: root.run(["fullscreen", checked ? "on" : "off"]) }
                    Label { text: "Videos loop silently. Panoramic video uses drift correction and is not frame locked."; color: theme.secondary; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true; Layout.bottomMargin: 10 }
                    Rectangle { Layout.fillWidth: true; height: 1; color: root.divider }
                    ProButton { text: "Sync theme wallpapers"; quiet: true; Layout.fillWidth: true; enabled: !themeSync.running; onClicked: root.startThemeSync() }
                    ProButton { text: "Use Omarchy wallpaper"; quiet: true; Layout.fillWidth: true; enabled: !worker.running; onClicked: root.run(["off"]) }
                    ProButton { text: "Clear this monitor"; quiet: true; Layout.fillWidth: true; enabled: mode.currentIndex === 0 && !worker.running; onClicked: root.run(["unassign", monitor.currentText]) }
                    ProButton { text: "Remove selected wallpaper"; quiet: true; Layout.fillWidth: true; enabled: root.selectedMedia !== null && !root.selectedMedia.bundled && !root.selectedMedia.themeManaged && !worker.running; onClicked: root.run(["remove", root.selected]) }
                }
                }
            }
        }
    }
}
