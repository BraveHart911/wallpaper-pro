import QtQuick
import qs.Ui

BarWidget {
    id: root
    property var shell: null
    moduleName: "bravehart911.wallpaper-pro"
    readonly property var hostShell: shell || (bar ? bar.shell : null)
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "󰸉"
        tooltipText: "Wallpaper Pro"
        onPressed: function(buttonCode) {
            if (buttonCode === Qt.LeftButton && root.hostShell && typeof root.hostShell.toggle === "function")
                root.hostShell.toggle(root.moduleName, "{}")
        }
    }
}
