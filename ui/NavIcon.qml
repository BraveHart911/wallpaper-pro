import QtQuick

Canvas {
    id: icon
    property string name: ""
    property color color: "white"
    property color backgroundColor: "transparent"
    antialiasing: true

    onPaint: {
        const ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        ctx.strokeStyle = color
        ctx.fillStyle = color
        ctx.lineWidth = 1.7
        ctx.lineCap = "round"
        ctx.lineJoin = "round"

        if (name === "library") {
            ctx.strokeRect(3.5, 3.5, 17, 17)
            ctx.beginPath(); ctx.moveTo(9.2, 4); ctx.lineTo(9.2, 20); ctx.moveTo(15, 4); ctx.lineTo(15, 20)
            ctx.moveTo(4, 9.2); ctx.lineTo(20, 9.2); ctx.moveTo(4, 15); ctx.lineTo(20, 15); ctx.stroke()
        } else if (name === "live") {
            ctx.strokeRect(3, 5, 18, 14)
            ctx.beginPath(); ctx.moveTo(9, 8.2); ctx.lineTo(15, 12); ctx.lineTo(9, 15.8); ctx.closePath(); ctx.fill()
        } else if (name === "monitor") {
            ctx.strokeRect(3, 4, 18, 12)
            ctx.beginPath(); ctx.moveTo(12, 16); ctx.lineTo(12, 20); ctx.moveTo(8.5, 20); ctx.lineTo(15.5, 20); ctx.stroke()
        } else if (name === "panorama") {
            ctx.strokeRect(2.5, 6, 19, 12)
            ctx.beginPath(); ctx.moveTo(4.5, 15.5); ctx.lineTo(9, 10.5); ctx.lineTo(12, 13.3); ctx.lineTo(15.7, 9.7); ctx.lineTo(19.5, 15.5); ctx.stroke()
        } else if (name === "imports") {
            ctx.beginPath(); ctx.moveTo(4, 7); ctx.lineTo(9.5, 7); ctx.lineTo(11.5, 9); ctx.lineTo(20, 9); ctx.lineTo(20, 18); ctx.lineTo(4, 18); ctx.closePath(); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(12, 3); ctx.lineTo(12, 13); ctx.moveTo(8.5, 9.5); ctx.lineTo(12, 13); ctx.lineTo(15.5, 9.5); ctx.stroke()
        } else if (name === "themes") {
            ctx.beginPath(); ctx.moveTo(4, 8); ctx.lineTo(12, 3.5); ctx.lineTo(20, 8); ctx.lineTo(12, 12.5); ctx.closePath(); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(4, 12); ctx.lineTo(12, 16.5); ctx.lineTo(20, 12); ctx.moveTo(4, 16); ctx.lineTo(12, 20.5); ctx.lineTo(20, 16); ctx.stroke()
        } else if (name === "appearance") {
            ctx.beginPath(); ctx.moveTo(4, 6); ctx.lineTo(20, 6); ctx.moveTo(4, 12); ctx.lineTo(20, 12); ctx.moveTo(4, 18); ctx.lineTo(20, 18); ctx.stroke()
            ctx.fillStyle = backgroundColor
            ctx.beginPath(); ctx.arc(9, 6, 2.4, 0, Math.PI * 2); ctx.fill()
            ctx.beginPath(); ctx.arc(15, 12, 2.4, 0, Math.PI * 2); ctx.fill()
            ctx.beginPath(); ctx.arc(7, 18, 2.4, 0, Math.PI * 2); ctx.fill()
            ctx.strokeStyle = color
            ctx.beginPath(); ctx.arc(9, 6, 2.4, 0, Math.PI * 2); ctx.stroke()
            ctx.beginPath(); ctx.arc(15, 12, 2.4, 0, Math.PI * 2); ctx.stroke()
            ctx.beginPath(); ctx.arc(7, 18, 2.4, 0, Math.PI * 2); ctx.stroke()
        }
    }

    onNameChanged: requestPaint()
    onColorChanged: requestPaint()
    onBackgroundColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
}
