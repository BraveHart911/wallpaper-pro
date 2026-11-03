import QtQuick
import QtTest
import "../../ui"

Item {
    width: 220
    height: 420
    ColorRail {
        id: rail
        x: 180; y: 10; width: 30; height: 400
        pageSize: 0.1
    }
    TestCase {
    name: "ColorRail"
    when: windowShown
    SignalSpy { id: jump; target: rail; signalName: "jumpRequested" }
    SignalSpy { id: scroll; target: rail; signalName: "scrollRequested" }
    function init() {
        rail.items = [{dominantColor:"#ff0000",colorName:"Red"}, {dominantColor:"#0000ff",colorName:"Blue"}, {dominantColor:"#ffffff",colorName:"White"}]
        jump.clear(); scroll.clear()
    }
    function test_clicks_map_to_color_positions() {
        mouseClick(rail, 15, 1)
        verify(jump.signalArguments[0][0] < 0.01)
        mouseClick(rail, 15, 200)
        compare(jump.signalArguments[jump.count-1][0], 0.5)
        mouseClick(rail, 15, 399)
        verify(jump.signalArguments[jump.count-1][0] > 0.99)
    }
    function test_drag_scrubs_through_collection() {
        mousePress(rail, 15, 40)
        mouseMove(rail, 15, 320, 10, Qt.LeftButton)
        mouseRelease(rail, 15, 320)
        verify(jump.count >= 2)
        verify(Math.abs(jump.signalArguments[jump.count-1][0] - 0.8) < 0.01)
    }
    function test_keyboard_and_wheel_navigation() {
        rail.forceActiveFocus()
        keyClick(Qt.Key_End)
        compare(jump.signalArguments[0][0], 1)
        keyClick(Qt.Key_Home)
        compare(jump.signalArguments[1][0], 0)
        mouseWheel(rail, 15, 200, 0, -120)
        compare(scroll.count, 1)
        verify(scroll.signalArguments[0][0] > 0)
    }
    function test_empty_collection_does_not_jump() {
        rail.items = []
        mouseClick(rail, 15, 200)
        compare(jump.count, 0)
    }
}
}
