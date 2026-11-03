import QtQuick
import qs.Ui

BarWidget {
    id: root
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "󰸉"
        tooltipText: "Wallpaper Pro"
        onPressed: { if (root.bar && root.bar.shell) root.bar.shell.toggle(root.bar.shell.pluginId, "{}") }
    }
}
