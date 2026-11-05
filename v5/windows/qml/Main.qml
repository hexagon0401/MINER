import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes
import QtQuick.Effects
import QtQuick.Window

ApplicationWindow {
    id: win; objectName: "mainWindow"
    visible: true; title: "MINER"
    width: Math.min(560, Screen.desktopAvailableWidth)
    height: Math.min(680, Screen.desktopAvailableHeight)
    minimumWidth: 480; minimumHeight: 440
    property var s: backend.state
    property color ink: s.contrast ? palette.windowText : "#353a45"
    property color muted: s.contrast ? palette.windowText : "#596173"
    property color accent: s.contrast ? systemPalette.highlight : "#1bd642"
    property bool flush: s.controlLayout === "flush"
    // Pearl White's supplied reference is static. No mining or success-loop timers.
    property bool motionAllowed: false
    property bool successActive: false
    property int nativeTextMode: statusText.renderType
    font.family: s.fontFamily; font.pixelSize: 14
    color: s.contrast ? palette.window : "#f6f8ff"
    SystemPalette { id: systemPalette }
    palette.highlight: s.contrast ? systemPalette.highlight : "#13bb46"
    palette.accent: s.contrast ? systemPalette.highlight : "#13bb46"
    onClosing: function(close) { close.accepted = backend.requestClose() }
    Shortcut { sequence: "Ctrl+,"; onActivated: backend.settings(true) }
    Connections { target: backend; function onCloseRequested() { win.close() } }
    component CopyText: Label {
        renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality
        color: win.ink
    }
    component PearlButton: Button {
        id: control
        property string kind: "stop"
        property bool integrated: false
        property int labelSize: 18
        hoverEnabled: true
        padding: 8
        font.family: s.latinFontFamily; font.pixelSize: labelSize; font.weight: Font.Bold
        Accessible.name: text
        background: Rectangle {
            id: surface
            radius: control.integrated ? 0 : 11
            border.width: control.integrated ? 0 : 1
            border.color: s.contrast ? systemPalette.windowText : control.kind === "start" ? "#54ec68" : control.kind === "kill" ? "#e9c3cd" : "#cdd6e7"
            opacity: control.enabled ? 1 : 0.58
            gradient: Gradient {
                GradientStop { position: 0; color: s.contrast ? systemPalette.button : control.kind === "start" ? "#32e652" : control.kind === "kill" ? "#fffafb" : "#f8faff" }
                GradientStop { position: 1; color: s.contrast ? systemPalette.button : control.kind === "start" ? "#08c82e" : control.kind === "kill" ? "#f9e4e9" : "#e9eefb" }
            }
            layer.enabled: !control.integrated && !s.contrast && s.effectsSupported
            layer.effect: MultiEffect {
                shadowEnabled: true; shadowColor: control.kind === "start" ? "#1d8141" : control.kind === "kill" ? "#8f5463" : "#52678b"
                shadowOpacity: 0.12; shadowBlur: 0.35; shadowVerticalOffset: control.down ? 1 : 4
            }
            Rectangle { anchors.fill: parent; anchors.margins: 1; radius: parent.radius; color: control.down ? "#16000000" : control.hovered ? "#0bffffff" : "transparent" }
            Rectangle { anchors.fill: parent; anchors.margins: 2; radius: Math.max(0,parent.radius-2); color: "transparent"; border.width: control.activeFocus ? 2 : 0; border.color: s.contrast ? systemPalette.highlight : "#4577bf" }
            Behavior on opacity { NumberAnimation { duration: s.reduced ? 0 : 100 } }
        }
        contentItem: CopyText {
            text: control.text; font: control.font
            color: s.contrast ? systemPalette.buttonText : control.kind === "start" ? "white" : control.kind === "kill" ? "#733d48" : "#424a5b"
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            opacity: control.enabled ? 1 : 0.6
        }
    }
    Rectangle {
        anchors.fill: parent; visible: !s.contrast
        gradient: Gradient {
            GradientStop { position: 0; color: "#fcfdff" }
            GradientStop { position: 0.54; color: "#f1f4ff" }
            GradientStop { position: 1; color: "#edf2ff" }
        }
    }
    Shape {
        anchors.fill: parent; visible: !s.contrast
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: win.width*0.08; centerY: win.height*0.31; centerRadius: win.width*0.95
                focalX: centerX; focalY: centerY
                GradientStop { position: 0; color: "#b3d9ebff" }
                GradientStop { position: 1; color: "#00d9ebff" }
            }
            startX: 0; startY: 0
            PathLine { x: win.width; y: 0 } PathLine { x: win.width; y: win.height } PathLine { x: 0; y: win.height } PathLine { x: 0; y: 0 }
        }
        ShapePath {
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: win.width*0.95; centerY: win.height*0.7; centerRadius: win.width*0.85
                focalX: centerX; focalY: centerY
                GradientStop { position: 0; color: "#a0e6e1ff" }
                GradientStop { position: 1; color: "#00e6e1ff" }
            }
            startX: 0; startY: 0
            PathLine { x: win.width; y: 0 } PathLine { x: win.width; y: win.height } PathLine { x: 0; y: win.height } PathLine { x: 0; y: 0 }
        }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.leftMargin: 20; anchors.rightMargin: 20; anchors.topMargin: 12; anchors.bottomMargin: 16; spacing: 16
        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width; spacing: 16
                Item {
                    Layout.fillWidth: true; Layout.preferredHeight: 76
                    Column {
                        anchors.horizontalCenter: parent.horizontalCenter; spacing: 5
                        Image {
                            objectName: "pearlWordmark"; anchors.horizontalCenter: parent.horizontalCenter
                            width: 204; height: 47; source: s.pearlArt+"mascot/MINER-wordmark-transparent.png"
                            sourceClipRect: Qt.rect(185,180,1795,407)
                            fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
                            Accessible.name: "MINER"; Accessible.role: Accessible.StaticText; visible: !s.contrast
                        }
                        CopyText { visible: s.contrast; anchors.horizontalCenter: parent.horizontalCenter; text: "MINER"; font.pixelSize: 36; font.weight: Font.ExtraBold }
                        CopyText { text: "Dig your way out."; font.pixelSize: 20; font.weight: Font.DemiBold; color: win.muted }
                    }
                }
                Rectangle {
                    id: hero; objectName: "heroPanel"
                    Layout.fillWidth: true; Layout.preferredHeight: win.height < 600 ? 150 : 258
                    radius: 23; border.width: 1; border.color: s.contrast ? systemPalette.windowText : "#e2ffffff"
                    gradient: Gradient {
                        GradientStop { position: 0; color: s.contrast ? systemPalette.window : "#86ffffff" }
                        GradientStop { position: 1; color: s.contrast ? systemPalette.window : "#5aeef0ff" }
                    }
                    Shape {
                        anchors.fill: parent; anchors.margins: 1; visible: !s.contrast
                        preferredRendererType: Shape.CurveRenderer
                        ShapePath {
                            strokeColor: "transparent"; fillColor: "#50c9e2ff"
                            startX: 0; startY: hero.height*0.42
                            PathCubic { x: hero.width-2; y: hero.height*0.85; control1X: hero.width*0.25; control1Y: hero.height*0.4; control2X: hero.width*0.35; control2Y: hero.height*0.92 }
                            PathLine { x: hero.width-2; y: hero.height-24 }
                            PathQuad { x: hero.width-24; y: hero.height-2; controlX: hero.width-2; controlY: hero.height-2 }
                            PathLine { x: 23; y: hero.height-2 }
                            PathQuad { x: 0; y: hero.height-24; controlX: 0; controlY: hero.height-2 }
                            PathLine { x: 0; y: hero.height*0.42 }
                        }
                        ShapePath {
                            strokeColor: "transparent"; fillColor: "#4cded4ff"
                            startX: hero.width-2; startY: hero.height*0.63
                            PathCubic { x: 0; y: hero.height*0.94; control1X: hero.width*0.7; control1Y: hero.height*0.64; control2X: hero.width*0.5; control2Y: hero.height*0.92 }
                            PathLine { x: 0; y: hero.height-24 }
                            PathQuad { x: 23; y: hero.height-2; controlX: 0; controlY: hero.height-2 }
                            PathLine { x: hero.width-24; y: hero.height-2 }
                            PathQuad { x: hero.width-2; y: hero.height-24; controlX: hero.width-2; controlY: hero.height-2 }
                            PathLine { x: hero.width-2; y: hero.height*0.63 }
                        }
                    }
                    Image {
                        objectName: "pearlMascot"
                        anchors.centerIn: parent; width: parent.width*0.85; height: parent.height*0.94
                        source: s.pearlArt+"mascot/miner-transparent.png"
                        sourceClipRect: Qt.rect(190,140,980,1030)
                        fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
                        Accessible.name: "MINER mascot"; Accessible.role: Accessible.Graphic
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 4
                    CopyText { id: statusText; objectName: "statusLabel"; Layout.fillWidth: true; text: s.text[s.phase] || s.phase; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 25; font.weight: Font.ExtraBold; wrapMode: Text.WordWrap }
                    CopyText {
                        Layout.fillWidth: true; color: win.muted; font.pixelSize: 14; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
                        text: s.phase === "error" || s.phase === "interrupted" ? s.text.recovery : s.phase === "disconnected" ? s.text.disconnected_hint : s.phase === "running" ? s.text.hint : s.busy ? s.text.opening : s.text.help
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Repeater { model: 5; Rectangle { required property int index; Layout.fillWidth: true; height: 8; radius: 4; color: index < s.completed ? win.accent : s.contrast ? systemPalette.mid : "#c3cce2" } }
                    CopyText { objectName: "progressLabel"; text: s.completed+"/5"; color: win.muted; font.pixelSize: 14; font.weight: Font.DemiBold; Layout.leftMargin: 5 }
                }
                TextArea { objectName: "errorDetails"; Layout.fillWidth: true; visible: s.detail.length>0; text: s.text.details+"\n"+s.detail; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; font.pixelSize: 13 }
            }
        }
        Rectangle {
            id: controls; objectName: "controlPlate"
            Layout.fillWidth: true; Layout.preferredHeight: 52 + (win.flush ? 0 : 12) + 43
            color: win.flush ? "#28ffffff" : "transparent"; radius: win.flush ? 6 : 0
            border.width: win.flush ? 1 : 0; border.color: s.contrast ? systemPalette.windowText : "#c7d0e4"
            ColumnLayout {
                anchors.fill: parent; anchors.margins: win.flush ? 1 : 0; spacing: win.flush ? 0 : 12
                PearlButton { id: startButton; objectName: "startButton"; Layout.fillWidth: true; Layout.preferredHeight: 52; kind: "start"; text: "START"; labelSize: 27; integrated: win.flush; enabled: s.canStart; Accessible.name: s.text.start; onClicked: backend.begin() }
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 43; spacing: win.flush ? 0 : 8
                    PearlButton { id: stopButton; objectName: "stopButton"; Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.minimumWidth: 0; Layout.fillHeight: true; text: "STOP"; integrated: win.flush; enabled: s.canStop; Accessible.name: s.text.stop; onClicked: backend.end() }
                    PearlButton {
                        objectName: "killButton"; Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.minimumWidth: 0; Layout.fillHeight: true; kind: "kill"; text: "KILL SWITCH"; integrated: win.flush; enabled: s.canKill
                        Accessible.description: s.text.kill_hint
                        ToolTip.visible: hovered; ToolTip.text: s.text.kill_hint; ToolTip.delay: 500
                        onClicked: backend.kill()
                    }
                }
            }
            Rectangle { visible: win.flush; x: 1; y: 52; width: parent.width-2; height: 1; color: "#cbd4e7" }
            Rectangle { visible: win.flush; x: parent.width/2; y: 53; width: 1; height: parent.height-54; color: "#e9c3cd" }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 32; spacing: 8
            CopyText { Layout.fillWidth: true; text: "WARP Local Proxy · 127.0.0.1:40000"; color: win.ink; font.pixelSize: 12; wrapMode: Text.WordWrap }
            PearlButton {
                objectName: "settingsButton"; text: s.text.settings; labelSize: 13; Layout.preferredWidth: 78; Layout.preferredHeight: 32
                contentItem: RowLayout { spacing: 5; Image { visible: !s.contrast; source: s.pearlArt+"icons/settings.svg"; Layout.preferredWidth: 18; Layout.preferredHeight: 18; sourceSize: Qt.size(36,36); smooth: true } CopyText { text: s.text.settings; font.pixelSize: 13; color: win.ink } }
                onClicked: backend.settings(true)
            }
        }
    }
    CopyText { visible: s.validation; anchors.left: parent.left; anchors.bottom: parent.bottom; padding: 3; text: "UI VALIDATION · simulated states · no live WARP"; font.pixelSize: 10; color: "#142337"; background: Rectangle { color: "#ffd54a" } }
    ApplicationWindow {
        id: preferences; objectName: "settingsWindow"; visible: s.settingsOpen
        font.family: s.fontFamily; font.pixelSize: 14
        title: s.text.settings; width: Math.min(440,Screen.desktopAvailableWidth); height: Math.min(600,Screen.desktopAvailableHeight)
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
                    CopyText { text: s.text.settings; font.pixelSize: 24; font.weight: Font.DemiBold }
                    CopyText { text: s.text.language; color: win.muted }
                    ComboBox { objectName: "languageCombo"; Layout.fillWidth: true; model: ["한국어","English"]; currentIndex: s.language === "ko" ? 0 : 1; onActivated: backend.setLanguage(currentIndex===0 ? "ko" : "en") }
                    CopyText { text: s.text.theme; color: win.muted }
                    CopyText { text: s.text.pearl }
                    CopyText { text: s.text.layout; color: win.muted }
                    ComboBox { objectName: "layoutCombo"; Layout.fillWidth: true; model: [s.text.rounded,s.text.flush]; currentIndex: win.flush ? 1 : 0; onActivated: backend.setLayout(currentIndex===0 ? "rounded" : "flush") }
                    CheckBox { text: s.text.reduce; checked: s.reduced; enabled: !s.systemReduced; onToggled: backend.setReduced(checked) }
                    CopyText { text: s.text.about; color: win.muted }
                    RowLayout {
                        Image { source: s.art+"developer-avatar.png"; Layout.preferredWidth: 60; Layout.preferredHeight: 60; smooth: true; mipmap: true }
                        ColumnLayout { CopyText { text: "Punkthats*it · @hexagon0401" } CopyText { text: s.version; color: win.muted; font.pixelSize: 11 } }
                    }
                    RowLayout { Button { text: "GitHub"; onClicked: backend.github() } Button { text: s.text.log; onClicked: backend.logs() } }
                }
            }
            Button { Layout.alignment: Qt.AlignRight; text: s.text.close; onClicked: backend.settings(false) }
        }
    }
}
