import QtQuick
import qs.Ui

BarWidget {
    id: root
    property var shell: null
    moduleName: "bravehart911.wallpaper-pro"
    readonly property var hostShell: shell || (bar && bar.shell ? bar.shell : null)
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "󰸉"
        tooltipText: "Wallpaper Pro"
        onPressed: { if (root.hostShell) root.hostShell.toggle(root.moduleName, "{}") }
    }
}
