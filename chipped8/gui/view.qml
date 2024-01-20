import QtQuick
import QtQuick.Controls
import QtQuick.Scene2D
import Qt3D.Render

ApplicationWindow {
    width: 640;
    height: 320;
    visible: true

    Image {
        id: scene
        width: parent.width
        height: parent.height
        fillMode: Image.PreserveAspectFit
        cache: false
        source: "image://SceneProvider/scene"
    }

    Connections {
        target: SceneProvider

        function onBlitImage() {
            scene.source = ""
            scene.source = "image://SceneProvider/scene"
        }
    }
}
