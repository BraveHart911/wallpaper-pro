import QtQuick
import Quickshell
import Quickshell.Io
import "js/Desktop.js" as Desktop

Item {
    id: root
    property var colors: Desktop.colors("")
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
