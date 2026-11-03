import QtQuick
import QtQuick.Controls.Basic

TextField {
    id: control
    implicitHeight: 36
    leftPadding: 12
    rightPadding: 12
    font.pixelSize: 13
    color: palette.text
    selectByMouse: true
    selectionColor: "#0071e3"
    selectedTextColor: "white"
    background: Rectangle {
        radius: 9
        color: Qt.rgba(0.5, 0.5, 0.5, 0.07)
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? "#0a84ff" : Qt.rgba(0.5, 0.5, 0.5, 0.15)
    }
}
