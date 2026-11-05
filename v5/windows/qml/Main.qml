import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes
import QtQuick.Effects
import QtQuick.Window

ApplicationWindow {
    id: win
    objectName: "mainWindow"
    visible: true
    title: "MINER"
    width: Math.min(584, Screen.desktopAvailableWidth)
    height: Math.min(704, Screen.desktopAvailableHeight)
    minimumWidth: 480; minimumHeight: 440
    property var s: backend.state
    property color ink: s.contrast ? palette.windowText : s.dark ? "#eef4f8" : "#172b3a"
    property color muted: s.contrast ? palette.windowText : s.dark ? "#a6b6c8" : "#546b7c"
    property color accent: s.contrast ? palette.highlight : "#16d84c"
    property bool motionAllowed: active && visibility !== Window.Minimized && !s.reduced
    property int nativeTextMode: statusText.renderType
    property bool successActive: false
    color: s.contrast ? palette.window : s.dark ? "#111c2b" : "#f3f6fb"
    font.family: s.fontFamily
    font.pixelSize: 14
    SystemPalette { id: systemPalette }
    palette.highlight: s.contrast ? systemPalette.highlight : "#13bb46"
    palette.accent: s.contrast ? systemPalette.highlight : "#13bb46"
    onClosing: function(close) { close.accepted = backend.requestClose() }
    onMotionAllowedChanged: if (!motionAllowed) { waveAnim.stop(); successAnim.stop(); successActive = false }
    Shortcut { sequence: "Ctrl+,"; onActivated: backend.settings(true) }
    Connections {
        target: backend
        function onCloseRequested() { win.close() }
        function onEffect(kind) {
            if (kind === "cancel" || kind === "stop") { successAnim.stop(); win.successActive = false }
            if (!win.motionAllowed) return
            if (kind === "success") { win.successActive = true; successAnim.restart() }
            if (kind === "start" || kind === "stop") {
                wave.color = kind === "start" ? "#16e151" : "#ff6470"
                var button = kind === "start" ? startButton : stopButton
                var pos = button.mapToItem(overlay, button.width/2, button.height/2)
                wave.x = pos.x - wave.width/2; wave.y = pos.y - wave.height/2
                waveAnim.restart()
            }
        }
    }
    Image { anchors.fill: parent; source: s.art+"full-window-strata.png"; fillMode: Image.PreserveAspectCrop; smooth: true; mipmap: true; opacity: s.dark ? 0.24 : 0.08 }
    Item {
        id: page
        anchors.fill: parent
        layer.enabled: win.successActive && win.motionAllowed
        layer.effect: MultiEffect { blurEnabled: true; blurMax: 12; blur: 0.3 }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 28; spacing: 14
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width; spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "MINER"; color: win.ink; font.pixelSize: 30; font.weight: Font.DemiBold }
                        Item { Layout.fillWidth: true }
                        Rectangle { width: 7; height: 7; radius: 3.5; color: s.phase === "error" ? "#e95065" : s.phase === "running" ? win.accent : win.muted }
                        Label { text: s.phase === "running" || s.phase === "idle" || s.phase === "error" ? s.text[s.phase] : s.completed + "/5"; color: win.muted; font.pixelSize: 12 }
                    }
                    Label { text: "Dig your way out."; color: win.muted; font.pixelSize: 13 }
                    Item {
                        id: scene
                        objectName: "caveScene"
                        Layout.fillWidth: true; Layout.preferredHeight: win.height < 560 ? 145 : 292
                        property bool digging: s.busy && win.motionAllowed
                        Item {
                            id: artwork
                            width: 560; height: 280
                            anchors.centerIn: parent
                            scale: Math.min(scene.width/width, scene.height/height)
                            Shape {
                                anchors.fill: parent; antialiasing: true; preferredRendererType: Shape.CurveRenderer
                                ShapePath {
                                    strokeWidth: 1; strokeColor: "#344353"; fillColor: "#080f19"
                                    startX: 268; startY: 74
                                    PathCubic { x: 265; y: 151; control1X: 287; control1Y: 112; control2X: 226; control2Y: 119 }
                                    PathCubic { x: 460; y: 193; control1X: 354; control1Y: 132; control2X: 446; control2Y: 126 }
                                    PathCubic { x: 330; y: 242; control1X: 474; control1Y: 238; control2X: 414; control2Y: 245 }
                                    PathCubic { x: 155; y: 200; control1X: 236; control1Y: 247; control2X: 148; control2Y: 247 }
                                    PathCubic { x: 241; y: 152; control1X: 159; control1Y: 163; control2X: 191; control2Y: 142 }
                                    PathCubic { x: 249; y: 74; control1X: 216; control1Y: 120; control2X: 263; control2Y: 106 }
                                    PathLine { x: 268; y: 74 }
                                }
                            }
                            Image { source: s.art + "school.png"; x: 192; y: -3; width: 176; height: 101; fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true }
                            Rectangle { x: 182; y: 235; width: 250; height: 2; radius: 1; color: "#896e4b"; opacity: 0.32 }
                            Image {
                                source: s.art + "skylight-beam.png"; x: miner.x-12; y: 140; width: 140; height: 108
                                fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
                                opacity: s.phase === "running" ? 0.75 : 0
                                Behavior on opacity { NumberAnimation { duration: s.reduced ? 0 : 260 } }
                            }
                            Image {
                                id: miner
                                source: s.art + "mascot-runtime-256.png"; x: 288 + s.completed*9; y: 133; width: 114; height: 114
                                fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true; transformOrigin: Item.Bottom
                                rotation: s.phase === "running" ? -6 : 0
                                Behavior on x { NumberAnimation { duration: s.reduced ? 0 : 360; easing.type: Easing.InOutCubic } }
                                SequentialAnimation on rotation {
                                    running: scene.digging; loops: Animation.Infinite
                                    NumberAnimation { to: 4; duration: 285; easing.type: Easing.InOutSine }
                                    NumberAnimation { to: -4; duration: 285; easing.type: Easing.InOutSine }
                                    onStopped: miner.rotation = s.phase === "running" ? -6 : 0
                                }
                            }
                            Repeater {
                                model: 5
                                Rectangle {
                                    required property int index
                                    property real travel: 0
                                    width: 3 + index%3; height: width; color: "#d7ad78"
                                    x: miner.x+95 + travel*(12+index*3); y: 193 + travel*(24+index*4)
                                    opacity: scene.digging ? 1-travel : 0
                                    NumberAnimation on travel { from: 0; to: 1; duration: 430+index*57; loops: Animation.Infinite; running: scene.digging }
                                }
                            }
                        }
                    }
                    Label { id: statusText; objectName: "statusLabel"; Layout.fillWidth: true; text: s.text[s.phase] || s.phase; color: win.ink; font.pixelSize: 19; font.weight: Font.DemiBold; wrapMode: Text.WordWrap }
                    Label {
                        Layout.fillWidth: true; color: win.muted; font.pixelSize: 13; wrapMode: Text.WordWrap
                        text: s.phase === "error" || s.phase === "interrupted" ? s.text.recovery : s.phase === "running" ? s.text.hint : s.busy ? s.text.opening : s.text.help
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 6
                        Repeater {
                            model: 5
                            Rectangle { required property int index; Layout.fillWidth: true; height: 4; radius: 2; color: index < s.completed ? win.accent : win.muted; opacity: index < s.completed ? 1 : 0.25; Behavior on color { ColorAnimation { duration: s.reduced ? 0 : 160 } } }
                        }
                        Label { objectName: "progressLabel"; text: s.completed+"/5"; color: win.muted; font.pixelSize: 12; Layout.leftMargin: 6 }
                    }
                    TextArea { objectName: "errorDetails"; Layout.fillWidth: true; visible: s.detail.length > 0; text: s.text.details+"\n"+s.detail; readOnly: true; wrapMode: TextEdit.Wrap; selectByMouse: true; font.pixelSize: 12 }
                }
            }
            Button { id: startButton; objectName: "startButton"; Layout.fillWidth: true; Layout.preferredHeight: 46; text: s.text.start; highlighted: true; enabled: s.canStart; font.weight: Font.DemiBold; onClicked: backend.begin() }
            Button { id: stopButton; objectName: "stopButton"; Layout.fillWidth: true; Layout.preferredHeight: 38; text: s.phase === "error" || s.phase === "interrupted" ? s.text.retry : s.text.stop; enabled: s.canStop; onClicked: backend.end() }
            RowLayout {
                Layout.fillWidth: true
                Label { Layout.fillWidth: true; text: "WARP Local Proxy · 127.0.0.1:40000"; color: win.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                Button { objectName: "settingsButton"; text: s.text.settings; onClicked: backend.settings(true) }
            }
        }
    }
    Item {
        id: overlay; anchors.fill: parent; clip: true
        Rectangle { id: wave; width: Math.hypot(win.width,win.height)*2; height: width; radius: width/2; scale: 0; opacity: 0 }
        ParallelAnimation {
            id: waveAnim
            NumberAnimation { target: wave; property: "scale"; from: 0; to: 1; duration: 520; easing.type: Easing.OutCubic }
            NumberAnimation { target: wave; property: "opacity"; from: 0.25; to: 0; duration: 520 }
        }
        Rectangle { anchors.fill: parent; color: "#101826"; opacity: success.opacity*0.12 }
        Column {
            id: success; anchors.centerIn: parent; spacing: 12; opacity: 0; scale: 0.76
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter; width: 64; height: 64; radius: 32; color: win.accent
                Shape { anchors.centerIn: parent; width: 32; height: 28; antialiasing: true; preferredRendererType: Shape.CurveRenderer; ShapePath { strokeColor: "#0b2d19"; strokeWidth: 4; fillColor: "transparent"; capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin; startX: 3; startY: 14; PathLine { x: 12; y: 23 } PathLine { x: 29; y: 4 } } }
            }
            Label { text: s.text.running; color: win.ink; font.pixelSize: 18; font.weight: Font.DemiBold }
        }
        SequentialAnimation {
            id: successAnim
            ParallelAnimation { NumberAnimation { target: success; property: "opacity"; from: 0; to: 1; duration: 210 } NumberAnimation { target: success; property: "scale"; from: 0.76; to: 1; duration: 310; easing.type: Easing.OutBack } }
            PauseAnimation { duration: 620 }
            NumberAnimation { target: success; property: "opacity"; to: 0; duration: 240 }
            onStopped: { win.successActive = false; success.opacity = 0 }
        }
    }
    Label { visible: s.validation; anchors.left: parent.left; anchors.bottom: parent.bottom; padding: 4; text: "UI VALIDATION · simulated states · no live WARP"; color: "#142337"; font.pixelSize: 10; background: Rectangle { color: "#ffd54a" } }
    Window {
        id: preferences; objectName: "settingsWindow"; visible: s.settingsOpen
        title: s.text.settings; width: Math.min(440, Screen.desktopAvailableWidth); height: Math.min(600, Screen.desktopAvailableHeight)
        minimumWidth: 360; minimumHeight: 380
        flags: Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
        transientParent: win; color: win.color
        onClosing: backend.settings(false)
        Shortcut { sequence: "Escape"; onActivated: backend.settings(false) }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 24; spacing: 12
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    width: parent.width; spacing: 12
                    Label { text: s.text.settings; color: win.ink; font.pixelSize: 24; font.weight: Font.DemiBold }
                    Label { text: s.text.language; color: win.muted }
                    ComboBox { objectName: "languageCombo"; Layout.fillWidth: true; model: ["한국어","English"]; currentIndex: s.language === "ko" ? 0 : 1; onActivated: backend.setLanguage(currentIndex === 0 ? "ko" : "en") }
                    Label { text: s.text.theme; color: win.muted }
                    ComboBox { Layout.fillWidth: true; model: [s.text.system,s.text.light,s.text.dark]; currentIndex: ["system","light","dark"].indexOf(s.theme); enabled: !s.contrast; onActivated: backend.setTheme(["system","light","dark"][currentIndex]) }
                    CheckBox { text: s.text.reduce; checked: s.reduced; enabled: !s.systemReduced; onToggled: backend.setReduced(checked) }
                    Label { text: s.text.about; color: win.muted }
                    RowLayout {
                        Image { source: s.art+"developer-avatar.png"; Layout.preferredWidth: 60; Layout.preferredHeight: 60; smooth: true; mipmap: true }
                        ColumnLayout { Label { text: "Punkthats*it · @hexagon0401"; color: win.ink } Label { text: s.version; color: win.muted; font.pixelSize: 11 } }
                    }
                    RowLayout {
                        Button { text: "GitHub"; onClicked: backend.github() }
                        Button { text: s.text.log; onClicked: backend.logs() }
                    }
                }
            }
            Button { Layout.alignment: Qt.AlignRight; text: s.text.close; onClicked: backend.settings(false) }
        }
    }
}
