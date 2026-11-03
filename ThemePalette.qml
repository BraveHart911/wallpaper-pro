import QtQuick
import Quickshell
import Quickshell.Io
import "js/Desktop.js" as Desktop

Item {
    id: root
    property var colors: Desktop.colors("")
    // Theme "muted" tokens can be too dim for body copy, especially on cards.
    readonly property color secondary: Qt.tint(colors.background, Qt.rgba(Qt.color(colors.foreground).r, Qt.color(colors.foreground).g, Qt.color(colors.foreground).b, 0.78))
    function refresh() { themeFile.reload() }
    FileView {
        id: themeFile
        path: Quickshell.env("HOME") + "/.local/state/omarchy/current/theme/colors.toml"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: root.colors = Desktop.colors(text())
    }
}
