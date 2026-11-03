import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

Button {
    id: control
    property bool primary: false
    property bool quiet: false
    property bool navigation: false
    property string iconName: ""
    implicitHeight: navigation ? 40 : 36
    implicitWidth: Math.max(36, label.implicitWidth + 28)
    hoverEnabled: true
    padding: 12
    opacity: enabled ? 1 : 0.42
    font.pixelSize: 13
    font.weight: primary || checked ? Font.DemiBold : Font.Medium
    contentItem: RowLayout {
        spacing: 10
        NavIcon {
            visible: control.navigation && control.iconName !== ""
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            name: control.iconName
            color: control.checked ? control.palette.highlight : control.palette.buttonText
            backgroundColor: control.palette.button
        }
        Text {
            id: label
            text: control.text
            font: control.font
            color: control.primary ? "#ffffff" : control.checked ? control.palette.highlight : control.palette.buttonText
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: control.navigation ? Text.AlignLeft : Text.AlignHCenter
            elide: Text.ElideRight
            Layout.fillWidth: control.navigation
        }
    }
    background: Rectangle {
        radius: control.navigation ? 8 : 9
        color: control.primary ? (control.down ? "#005bbf" : control.hovered ? "#006bd6" : "#0071e3")
             : control.checked ? Qt.rgba(0.04, 0.52, 1, 0.13)
             : control.down ? Qt.rgba(0.5, 0.5, 0.5, 0.2)
             : control.hovered ? Qt.rgba(0.5, 0.5, 0.5, 0.12)
             : control.quiet || control.navigation ? "transparent" : control.palette.button
        border.width: control.activeFocus ? 1 : control.quiet || control.navigation || control.primary ? 0 : 1
        border.color: control.activeFocus ? "#0a84ff" : Qt.rgba(0.5, 0.5, 0.5, 0.18)
        Behavior on color { ColorAnimation { duration: 110 } }
        Rectangle {
            visible: control.navigation && control.checked
            anchors.left: parent.left
            anchors.leftMargin: 3
            anchors.verticalCenter: parent.verticalCenter
            width: 3
            height: 18
            radius: 2
            color: control.palette.highlight
        }
    }
}
