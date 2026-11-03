import QtQuick
import QtQuick.Controls.Basic

Button {
    id: control
    property bool primary: false
    property bool quiet: false
    property bool navigation: false
    implicitHeight: navigation ? 40 : 36
    implicitWidth: Math.max(36, label.implicitWidth + 28)
    hoverEnabled: true
    padding: 12
    opacity: enabled ? 1 : 0.42
    font.pixelSize: 13
    font.weight: primary || checked ? Font.DemiBold : Font.Medium
    contentItem: Text {
        id: label
        text: control.text
        font: control.font
        color: control.primary ? "#ffffff" : control.checked ? control.palette.highlight : control.palette.buttonText
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: control.navigation ? Text.AlignLeft : Text.AlignHCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: control.navigation ? 8 : 9
        color: control.primary ? (control.down ? "#005bbf" : control.hovered ? "#006bd6" : "#0071e3")
             : control.checked ? Qt.rgba(0.04, 0.52, 1, 0.16)
             : control.down ? Qt.rgba(0.5, 0.5, 0.5, 0.2)
             : control.hovered ? Qt.rgba(0.5, 0.5, 0.5, 0.12)
             : control.quiet || control.navigation ? "transparent" : control.palette.button
        border.width: control.activeFocus ? 2 : control.quiet || control.navigation || control.primary ? 0 : 1
        border.color: control.activeFocus ? "#0a84ff" : Qt.rgba(0.5, 0.5, 0.5, 0.18)
        Behavior on color { ColorAnimation { duration: 110 } }
    }
}
