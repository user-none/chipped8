import QtQuick
import QtQuick.Controls
import Qt.labs.platform

ApplicationWindow {
    id: win
    title: "Chipped8"
    width: 640;
    height: 320;
    minimumWidth: 64
    minimumHeight: 32
    visible: true

    signal windowFocusChanged(bool active)
    signal keyEvent(int key, bool pressed, int modifiers)
    signal loadRom(url filename)

    MenuBar {
        id: menuBar

        Menu {
            id: fileMenu
            title: "File"

            MenuItem {
                id: menuItemOpen
                text: "Open..."
                shortcut: "Ctrl+O"

                onTriggered: (event) => {
                    fileDialog.open()
                }
            }
        }
    }

    Image {
        id: scene
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        cache: false
        source: "image://SceneProvider/scene"
        focus: true

        Keys.onPressed: (event) => {
            keyEvent(event.key, true, event.modifiers)
        }

        Keys.onReleased: (event) => {
            keyEvent(event.key, false, event.modifiers)
        }

    }

    FileDialog {
        id: fileDialog
        nameFilters: ["Chip-8 (*.ch8)", "BIN (*.bin)"]

        onAccepted: {
            loadRom(currentFile)
        }
    }

    onActiveChanged: {
        windowFocusChanged(active)
    }

    Connections {
        target: SceneProvider

        function onBlitReady() {
            scene.source = ""
            scene.source = "image://SceneProvider/scene"
        }
    }
}
