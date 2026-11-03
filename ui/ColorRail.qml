import QtQuick
import QtQuick.Controls.Basic
import "../js/Library.js" as Library

FocusScope {
    id: root
    property var items: []
    property real position: 0
    property real pageSize: 1
    property real rowStep: 120
    property color foreground: "#f1f5f9"
    property color background: "#111820"
    readonly property var stops: Library.spectrumStops(items, 96)
    readonly property real pointerFraction: Math.max(0, Math.min(1, pointer.mouseY / Math.max(1, height)))
    readonly property int pointerIndex: Library.spectrumIndex(items.length, pointerFraction)
    readonly property var pointerItem: pointerIndex >= 0 ? items[pointerIndex] : null
    signal jumpRequested(real fraction)
    signal scrollRequested(real pixels)
    implicitWidth: 30
    activeFocusOnTab: true
    Accessible.role: Accessible.Slider
    Accessible.name: "Wallpaper color spectrum"
    Accessible.description: "Click or drag a color to browse matching wallpapers. Arrow keys and Page Up or Down also scroll."
    Accessible.onIncreaseAction: jumpRequested(Math.min(1, position + 0.02))
    Accessible.onDecreaseAction: jumpRequested(Math.max(0, position - 0.02))
    Keys.onPressed: function(event) {
        let target = root.position
        if (event.key === Qt.Key_Up) target -= 0.02
        else if (event.key === Qt.Key_Down) target += 0.02
        else if (event.key === Qt.Key_PageUp) target -= root.pageSize
        else if (event.key === Qt.Key_PageDown) target += root.pageSize
        else if (event.key === Qt.Key_Home) target = 0
        else if (event.key === Qt.Key_End) target = 1
        else { event.accepted = false; return }
        root.jumpRequested(Math.max(0, Math.min(1, target)))
        event.accepted = true
    }
    onStopsChanged: if (spectrum) spectrum.requestPaint()
    onHeightChanged: if (spectrum) spectrum.requestPaint()

    Canvas {
        id: spectrum
        anchors { top: parent.top; bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; margins: 1 }
        width: 12
        onPaint: {
            const ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            const gradient = ctx.createLinearGradient(0, 0, 0, height)
            root.stops.forEach(stop => gradient.addColorStop(stop.position, stop.color))
            const r = 6
            ctx.beginPath()
            ctx.moveTo(r, 0)
            ctx.lineTo(width-r, 0)
            ctx.quadraticCurveTo(width, 0, width, r)
            ctx.lineTo(width, height-r)
            ctx.quadraticCurveTo(width, height, width-r, height)
            ctx.lineTo(r, height)
            ctx.quadraticCurveTo(0, height, 0, height-r)
            ctx.lineTo(0, r)
            ctx.quadraticCurveTo(0, 0, r, 0)
            ctx.closePath()
            ctx.fillStyle = gradient
            ctx.fill()
        }
    }
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: Math.max(0, Math.min(1, root.position)) * (root.height - height)
        width: 22
        height: Math.max(24, Math.min(root.height, root.pageSize * root.height))
        radius: 8
        color: pointer.pressed ? "#55333333" : "#33000000"
        border.width: root.activeFocus || pointer.pressed ? 2 : 1.5
        border.color: "#eeeeee"
    }
    Rectangle {
        visible: (pointer.containsMouse || pointer.pressed) && root.pointerItem !== null
        x: -width - 6
        y: Math.max(0, Math.min(root.height - height, pointer.mouseY - height / 2))
        width: tip.implicitWidth + 38
        height: 30
        radius: 8
        color: root.background
        border.color: Qt.rgba(0.5,0.5,0.5,0.3)
        Rectangle { x: 10; anchors.verticalCenter: parent.verticalCenter; width: 9; height: 9; radius: 5; color: root.pointerItem ? root.pointerItem.dominantColor || "#777777" : "#777777" }
        Text { id: tip; x: 26; anchors.verticalCenter: parent.verticalCenter; text: root.pointerItem ? (root.pointerItem.colorName || "Unclassified") + " · " + (root.pointerIndex + 1) + "/" + root.items.length : ""; color: root.foreground; font.pixelSize: 11 }
    }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        preventStealing: true
        cursorShape: Qt.PointingHandCursor
        enabled: root.items.length > 0
        onPressed: function(mouse) { root.forceActiveFocus(); root.jumpRequested(Math.max(0, Math.min(1, mouse.y / Math.max(1, root.height)))) }
        onPositionChanged: function(mouse) { if (pressed) root.jumpRequested(Math.max(0, Math.min(1, mouse.y / Math.max(1, root.height)))) }
        onWheel: function(wheel) {
            root.scrollRequested(wheel.pixelDelta.y ? -wheel.pixelDelta.y : -wheel.angleDelta.y / 120 * root.rowStep)
            wheel.accepted = true
        }
    }
}
