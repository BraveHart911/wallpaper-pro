import QtQuick
import QtQuick.Controls.Basic

ComboBox {
    id: control
    implicitHeight: 36
    implicitWidth: 170
    leftPadding: 12
    rightPadding: 28
    font.pixelSize: 13
    opacity: enabled ? 1 : 0.45
    contentItem: Text {
        text: control.displayText
        textFormat: Text.PlainText
        font: control.font
        color: control.palette.text
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Text {
        x: control.width - 24
        anchors.verticalCenter: parent.verticalCenter
        text: "⌄"
        font.pixelSize: 16
        color: control.palette.text
    }
    background: Rectangle {
        radius: 9
        color: control.palette.button
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? "#0a84ff" : Qt.rgba(0.5,0.5,0.5,0.18)
    }
    delegate: ItemDelegate {
        required property var modelData
        required property int index
        width: ListView.view ? ListView.view.width : control.availableWidth
        implicitHeight: 36
        contentItem: Text { text: parent.modelData; textFormat: Text.PlainText; color: control.palette.text; font: control.font; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
        background: Rectangle { radius: 6; color: control.highlightedIndex === parent.index ? Qt.rgba(0.04,0.52,1,0.2) : "transparent" }
    }
    popup: Popup {
        y: control.height + 6
        width: control.width
        padding: 6
        implicitHeight: contentItem.implicitHeight + 12
        contentItem: ListView {
            clip: true
            implicitHeight: Math.min(contentHeight, 240)
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: Rectangle { color: control.palette.window; radius: 12; border.color: Qt.rgba(0.5,0.5,0.5,0.3) }
    }
}
