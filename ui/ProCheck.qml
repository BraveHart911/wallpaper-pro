import QtQuick
import QtQuick.Controls.Basic

CheckBox {
    id: control
    implicitHeight: 40
    implicitWidth: label.implicitWidth + 38
    font.pixelSize: 13
    spacing: 10
    opacity: enabled ? 1 : 0.45
    indicator: Rectangle {
        implicitWidth: 18
        implicitHeight: 18
        x: 0
        y: (control.height - height) / 2
        radius: 5
        color: control.checked ? "#0a84ff" : "transparent"
        border.color: control.activeFocus ? "#0a84ff" : control.checked ? "#0a84ff" : Qt.rgba(0.5,0.5,0.5,0.6)
        border.width: control.activeFocus ? 2 : 1
        Text { anchors.centerIn: parent; text: "✓"; color: "white"; font.pixelSize: 13; visible: control.checked }
    }
    contentItem: Text {
        id: label
        text: control.text
        font: control.font
        color: control.palette.text
        leftPadding: 28
        verticalAlignment: Text.AlignVCenter
    }
}
