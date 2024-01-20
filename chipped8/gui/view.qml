import QtQuick
import QtQuick.Controls
import QtQuick.Scene2D
import Qt3D.Render

ApplicationWindow {
    id: win
    width: 640;
    height: 320;
    minimumWidth: 64
    minimumHeight: 32
    visible: true

    signal windowFocusChanged(bool active)
    signal keyEvent(int key, bool pressed)

    Image {
        id: scene
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        cache: false
        source: "image://SceneProvider/scene"
        focus: true

        Keys.onPressed: (event) => {
            keyEvent(event.key, true)
        }

        Keys.onReleased: (event) => {
            keyEvent(event.key, false)
        }

    }

    onActiveChanged: {
        windowFocusChanged(active)
    }

    Connections {
        target: SceneProvider

        function onBlitImage() {
            scene.source = ""
            scene.source = "image://SceneProvider/scene"
        }
    }
}
