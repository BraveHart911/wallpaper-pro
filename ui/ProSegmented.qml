import QtQuick

Rectangle {
    id: control
    property var options: []
    property int selectedIndex: 0
    property color accent: "#0a84ff"
    property color foreground: "white"
    property color secondary: "#9aa0a6"
    signal activated(int index)

    implicitWidth: 280
    implicitHeight: 42
    radius: 12
    color: Qt.rgba(0.5, 0.5, 0.5, 0.10)
    border.color: Qt.rgba(0.5, 0.5, 0.5, 0.18)
    Accessible.role: Accessible.Grouping
    Accessible.name: "Live wallpaper display filter"

    readonly property real segmentWidth: (width - 8) / Math.max(1, options.length)

    Rectangle {
        x: 4 + control.selectedIndex * control.segmentWidth
        y: 4
        width: control.segmentWidth
        height: control.height - 8
        radius: 9
        color: Qt.rgba(control.accent.r, control.accent.g, control.accent.b, 0.17)
        border.color: Qt.rgba(control.accent.r, control.accent.g, control.accent.b, 0.38)
        Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
    }

    Repeater {
        id: optionRepeater
        model: control.options
        delegate: Item {
            id: option
            required property int index
            required property string modelData
            x: 4 + index * control.segmentWidth
            y: 4
            width: control.segmentWidth
            height: control.height - 8
            Accessible.role: Accessible.RadioButton
            Accessible.name: modelData
            Accessible.checked: control.selectedIndex === index
            Accessible.onPressAction: control.activated(index)
            activeFocusOnTab: index === control.selectedIndex
            Keys.onLeftPressed: {
                const next = Math.max(0, index - 1)
                control.activated(next)
                optionRepeater.itemAt(next).forceActiveFocus()
            }
            Keys.onRightPressed: {
                const next = Math.min(control.options.length - 1, index + 1)
                control.activated(next)
                optionRepeater.itemAt(next).forceActiveFocus()
            }
            Text {
                anchors.centerIn: parent
                text: option.modelData
                color: control.selectedIndex === option.index ? control.foreground : (hover.hovered ? control.foreground : control.secondary)
                font.pixelSize: 12
                font.weight: control.selectedIndex === option.index ? Font.DemiBold : Font.Medium
            }
            HoverHandler { id: hover }
            TapHandler {
                onTapped: {
                    control.activated(option.index)
                    option.forceActiveFocus()
                }
            }
        }
    }
}
