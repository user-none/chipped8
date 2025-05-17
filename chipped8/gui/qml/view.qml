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
    signal platformChanged(string platfrom, string interpreter)
    signal interpreterChanged(string platfrom, string interpreter)
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

        Menu {
            id: menuPlatform
            title: "Platform"

            MenuItemGroup {
                id: platformsGroup
                items: menuPlatform.items

                onTriggered: (item) => {
                    platformChanged(item.text, "")
                }
            }

            MenuItem { id: platOriginalChip8; text: "originalChip8"; checkable: true; checked: true }
            MenuItem { id: platHybridVIP; text: "hybridVIP"; checkable: true }
            MenuItem { id: platModernChip8; text: "modernChip8"; checkable: true }
            MenuItem { id: platChip48; text: "chip48"; checkable: true }
            MenuItem { id: platSuperchip1; text: "superchip1"; checkable: true }
            MenuItem { id: platSuperchip; text: "superchip"; checkable: true }
            MenuItem { id: platXochip; text: "xochip"; checkable: true }
        }

        Menu {
            id: menuInterpreter
            title: "Interpreter"

            MenuItemGroup {
                id: interpreterGroup
                items: menuInterpreter.items

                onTriggered: (item) => {
                    interpreterChanged("", item.text)
                }
            }

            MenuItem { id: interpreterCached; text: "cached"; checkable: true; checked: true }
            MenuItem { id: interpreterPure; text: "pure"; checkable: true }
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
