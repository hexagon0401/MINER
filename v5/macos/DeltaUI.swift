import AppKit
import SwiftUI

private let deltaNavy = Color(red:0.055,green:0.075,blue:0.122)
private let deltaGreen = Color(red:0.055,green:0.984,blue:0.180)
private let deltaRed = Color(red:1,green:0.353,blue:0.380)

// Default values defer to macOS. Fixtures can exercise both native preferences
// without trying to write SwiftUI's read-only accessibility environment keys.
struct DeltaAccessibility {
    var reduceMotion:Bool? = nil
    var reduceTransparency:Bool? = nil
    var increasedContrast:Bool? = nil
}
private struct DeltaAccessibilityKey:EnvironmentKey {
    static let defaultValue = DeltaAccessibility()
}
extension EnvironmentValues {
    var deltaAccessibility:DeltaAccessibility {
        get { self[DeltaAccessibilityKey.self] }
        set { self[DeltaAccessibilityKey.self] = newValue }
    }
}

enum DeltaArt {
    static let images: [String:NSImage] = Dictionary(uniqueKeysWithValues: ["full-window-strata","shaft-reveal","dig-wall-cracks","pickaxe-impact","dirt-particle-cluster","pebble","skylight-beam","exit-ceiling"].map { name in
        (name,NSImage(contentsOf:Bundle.main.resourceURL!.appendingPathComponent("UIAssets/delta-" + name + ".png")) ?? NSImage())
    })
}
private func deltaArt(_ name:String) -> Image { Image(nsImage:DeltaArt.images[name] ?? NSImage()) }

private struct DeltaGlass: ViewModifier {
    var radius: CGFloat
    @Environment(\.accessibilityReduceTransparency) private var systemReduceTransparency
    @Environment(\.deltaAccessibility) private var accessibility
    private var reduceTransparency:Bool { accessibility.reduceTransparency ?? systemReduceTransparency }
    func body(content:Content) -> some View {
        if reduceTransparency {
            content.background(deltaNavy,in:RoundedRectangle(cornerRadius:radius))
                .overlay(RoundedRectangle(cornerRadius:radius).stroke(.white.opacity(0.35)))
        } else {
            glass(content)
        }
    }
    @ViewBuilder private func glass(_ content:Content) -> some View {
        #if compiler(>=6.2)
        if #available(macOS 26.0, *) {
            content.glassEffect(.regular,in:RoundedRectangle(cornerRadius:radius))
        } else {
            fallback(content)
        }
        #else
        fallback(content)
        #endif
    }
    private func fallback(_ content:Content) -> some View {
        content.background(.ultraThinMaterial,in:RoundedRectangle(cornerRadius:radius))
            .overlay(RoundedRectangle(cornerRadius:radius).stroke(.white.opacity(0.17)))
    }
}

private struct DeltaCave: View {
    @ObservedObject var model:MinerModel
    let size:CGSize
    let shaft:Bool
    let light:Bool
    @State private var errorDrop = false
    @Environment(\.deltaAccessibility) private var accessibility
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    private var reduceMotion:Bool { accessibility.reduceMotion ?? systemReduceMotion }
    private var sy:CGFloat { size.height/610 }
    private var minerX:CGFloat { model.mining ? size.width/2 + CGFloat(model.completed)*16 : size.width*0.66 }
    var body: some View {
        TimelineView(.animation(minimumInterval:1.0/30,paused:!model.mining || !model.active || reduceMotion)) { context in
            let t = model.mining && model.active && !reduceMotion ? context.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy:0.57)/0.57 : 0
            cave(t)
        }.allowsHitTesting(false).accessibilityHidden(true)
        .task(id:model.phase + String(model.active)) {
            errorDrop = false
            guard model.phase == "error" else { return }
            if reduceMotion || !model.active { errorDrop = true; return }
            try? await Task.sleep(nanoseconds:16_000_000)
            guard !Task.isCancelled else { return }
            withAnimation(.easeIn(duration:0.22)) { errorDrop = true }
        }
    }
    private func cave(_ t:Double) -> some View {
        ZStack {
            deltaArt("full-window-strata").resizable().frame(width:size.width,height:size.height)
            school
            underground(t)
            illumination
            miner(t)
            debris(t)
        }.frame(width:size.width,height:size.height)
        .animation(.easeInOut(duration:reduceMotion ? 0.12 : 0.55),value:model.completed)
    }
    private var school: some View {
        ZStack {
            art("school").resizable().scaledToFit().frame(width:190,height:110)
                .scaleEffect(shaft ? 0.92 : 1).offset(y:shaft ? -8 : 0)
                .position(x:size.width/2,y:184*sy)
            deltaArt("shaft-reveal").resizable().scaledToFit().frame(width:110,height:100*sy)
                .mask(Rectangle().scaleEffect(x:1,y:shaft ? 1 : 0,anchor:.top))
                .position(x:size.width/2,y:254*sy)
        }.animation(.easeInOut(duration:reduceMotion ? 0.12 : 0.6),value:shaft)
    }
    private func underground(_ t:Double) -> some View {
        ZStack {
            art("tunnel").resizable().scaledToFit().frame(width:min(370,size.width-100),height:114)
                .blendMode(.multiply).clipShape(Capsule()).position(x:size.width/2+25,y:328*sy)
            if model.mining {
                deltaArt("dig-wall-cracks").resizable().scaledToFit().frame(width:36,height:66)
                    .opacity(t > 0.52 ? 0.8 : 0.2).position(x:minerX+47,y:310*sy)
                deltaArt("pickaxe-impact").resizable().scaledToFit().frame(width:24,height:24)
                    .opacity(t > 0.55 && t < 0.72 ? 0.9 : 0).position(x:minerX+45,y:299*sy)
            }
        }.offset(x: !reduceMotion && model.mining && t > 0.60 && t < 0.74 ? -1.5 : 0)
    }
    private var illumination: some View {
        ZStack {
            deltaArt("exit-ceiling").resizable().scaledToFit().frame(width:110,height:28).position(x:minerX,y:251*sy)
            deltaArt("skylight-beam").resizable().scaledToFit().frame(width:150,height:130).position(x:minerX,y:303*sy)
        }.opacity(light ? 1 : 0)
    }
    private func miner(_ t:Double) -> some View {
        art("mascot-runtime-256").resizable().scaledToFit().frame(width:108,height:108)
            .rotationEffect(.degrees(light ? -7 : model.phase == "error" ? -5 : t == 0 ? 0 : sin(t * .pi * 2)*5))
            .offset(x:model.phase == "error" ? -3 : 0,y:t == 0 ? 0 : sin(t * .pi * 2))
            .position(x:minerX,y:312*sy)
            .animation(.easeOut(duration:reduceMotion ? 0.12 : 0.22),value:model.phase)
    }
    @ViewBuilder private func debris(_ t:Double) -> some View {
        if model.mining && !reduceMotion && model.active {
            ForEach(0..<4) { index in
                Rectangle().fill(Color(red:0.82,green:0.65,blue:0.47))
                    .frame(width:CGFloat(3+index%3),height:CGFloat(3+index%3)).opacity(1-t)
                    .position(x:minerX+42+CGFloat(index*5)+CGFloat(t*12),y:316*sy+CGFloat(index*5)+CGFloat(t*22))
            }
            if t > 0.72 {
                deltaArt("pebble").resizable().scaledToFit().frame(width:9,height:9)
                    .opacity(1-t).position(x:minerX+57+CGFloat(t*12),y:337*sy+CGFloat(t*12))
            }
        }
        if model.phase == "error" {
            art("rock").resizable().scaledToFit().frame(width:28,height:28).position(x:minerX+43,y:350*sy)
            deltaArt("pebble").resizable().scaledToFit().frame(width:12,height:12)
                .offset(y:errorDrop ? 0 : -16).position(x:minerX+55,y:342*sy)
        }
    }
}

struct DeltaRoot: View {
    @ObservedObject var model:MinerModel
    let controller:AppDelegate
    var visualAudit:((Double,CGFloat,[String:CGRect])->Void)? = nil
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    private var reduceMotion:Bool { accessibility.reduceMotion ?? systemReduceMotion }
    @Environment(\.accessibilityReduceTransparency) private var systemReduceTransparency
    @Environment(\.deltaAccessibility) private var accessibility
    private var reduceTransparency:Bool { accessibility.reduceTransparency ?? systemReduceTransparency }
    @Environment(\.colorSchemeContrast) private var systemContrast
    private var increasedContrast:Bool { accessibility.increasedContrast ?? (systemContrast == .increased) }
    @State private var shaft = false
    @State private var light = false
    @State private var blur:CGFloat = 0
    @State private var checkOpacity:Double = 0
    @State private var checkScale:CGFloat = 0.76
    @State private var checkLift:CGFloat = 0
    @State private var waveColor = deltaGreen
    @State private var waveOrigin = CGPoint.zero
    @State private var waveScale:CGFloat = 0.01
    @State private var waveOpacity:Double = 0
    @State private var successPlayed = false
    @State private var generation = 0
    @State private var successTask:Task<Void,Never>?
    @State private var waveTask:Task<Void,Never>?
    @State private var revealTask:Task<Void,Never>?
    @State private var joke = ""
    @State private var controlFrames:[String:CGRect] = [:]
    @State private var lastAnnouncement = ""
    private var base:MinerRoot { MinerRoot(model:model,controller:controller) }
    private var phaseKey:String { model.phase + String(model.engine) + String(model.active) }

    var body: some View {
        GeometryReader { geo in
            canvas(geo.size)
        }.ignoresSafeArea().environment(\.colorScheme,.dark)
        .sheet(isPresented:$model.diagnostics) { base.diagnosticsPanel }
        .onReceive(NotificationCenter.default.publisher(for:NSApplication.didBecomeActiveNotification)) { _ in model.active = true }
        .onReceive(NotificationCenter.default.publisher(for:NSApplication.didResignActiveNotification)) { _ in model.active = false }
        .onChange(of:phaseKey) { _ in synchronize() }
        .onChange(of:checkOpacity) { value in visualAudit?(value,blur,controlFrames) }
        .onChange(of:blur) { value in visualAudit?(checkOpacity,value,controlFrames) }
        .onDisappear { cancelVisuals(); waveTask?.cancel(); revealTask?.cancel(); waveOpacity = 0 }
        .task(id:model.phase + model.language + String(model.active)) { await rotateJokes() }
    }
    private func canvas(_ size:CGSize) -> some View {
        ZStack {
            background
            regularContent(size).blur(radius:reduceMotion ? 0 : blur)
            Color.black.opacity(checkOpacity*0.12).allowsHitTesting(false)
            successOverlay.position(x:size.width/2,y:size.height/2).allowsHitTesting(false)
            pulseLayer(size).allowsHitTesting(false).accessibilityHidden(true)
        }.frame(width:size.width,height:size.height).clipped().coordinateSpace(name:"deltaWindow")
        .onPreferenceChange(DeltaControlFrames.self) { controlFrames = $0; visualAudit?(checkOpacity,blur,$0) }
    }
    private var background: some View {
        ZStack {
            if reduceTransparency { deltaNavy }
            else { Rectangle().fill(.ultraThinMaterial) }
            LinearGradient(colors:[deltaNavy.opacity(reduceTransparency ? 1 : increasedContrast ? 0.82 : 0.66),deltaNavy.opacity(reduceTransparency ? 1 : 0.85)],startPoint:.top,endPoint:.bottom)
        }.allowsHitTesting(false)
    }
    private func regularContent(_ size:CGSize) -> some View {
        let sy = size.height/610
        return ZStack {
            DeltaCave(model:model,size:size,shaft:shaft,light:light)
            header.frame(width:size.width-52,height:44).position(x:size.width/2,y:85*sy)
            Text(jokeText).font(.system(size:11)).foregroundStyle(.white.opacity(0.53)).lineLimit(1)
                .frame(width:size.width-100).position(x:size.width/2,y:374*sy)
            statusPanel.frame(width:size.width-80,height:model.phase == "error" ? 72 : 58)
                .position(x:size.width/2,y:(389+29)*sy)
            startButton(size).position(x:size.width/2,y:459*sy+24)
            stopButton(size).position(x:size.width/2,y:515*sy+18)
            footer.frame(width:size.width-52,height:38).position(x:size.width/2,y:583*sy)
        }.foregroundStyle(Color(red:0.90,green:0.91,blue:0.90))
    }
    private var header: some View {
        HStack(alignment:.top) {
            VStack(alignment:.leading,spacing:4) {
                Text("MINER").font(.system(size:25,weight:.semibold))
                Text("Dig your way out.").font(.system(size:11,weight:.medium)).foregroundStyle(.white.opacity(0.65))
            }
            Spacer()
            Button { controller.refresh(); model.diagnostics = true } label: {
                HStack(spacing:5) { Circle().fill(base.chipColor).frame(width:6,height:6); Text(base.chipText) }
                    .font(.system(size:11)).padding(8).modifier(DeltaGlass(radius:12))
            }.buttonStyle(.plain).padding(.top,6)
        }
    }
    private var statusPanel: some View {
        VStack(alignment:.leading,spacing:4) {
            HStack {
                Text(model.title).font(.system(size:16,weight:.semibold)).lineLimit(1)
                Spacer()
                Text("\(model.completed)/5").font(.system(size:11)).foregroundStyle(.white.opacity(0.6))
            }
            Text(model.detail).font(.system(size:11)).lineLimit(model.phase == "error" ? 2 : 1)
                .foregroundStyle(model.phase == "error" ? Color.red : Color.white.opacity(0.7))
            HStack(spacing:5) {
                ForEach(0..<5) { index in Capsule().fill(index < model.completed ? Color.green : Color.gray.opacity(0.24)).frame(height:4) }
            }
        }.padding(.horizontal,12).padding(.vertical,7).modifier(DeltaGlass(radius:15))
        .accessibilityElement(children:.combine)
    }
    private func startButton(_ size:CGSize) -> some View {
        Button {
            guard !model.busy && !model.engine else { return }
            pulse(size,stop:false)
            controller.start()
        } label: {
            Text(base.actionText).font(.system(size:14,weight:.semibold)).foregroundStyle(deltaNavy)
                .frame(width:min(340,size.width-80),height:48)
                .background(deltaGreen.opacity(model.busy || model.engine ? 0.45 : 1),in:RoundedRectangle(cornerRadius:15))
        }.buttonStyle(.plain).keyboardShortcut(.defaultAction).disabled(model.busy || model.engine)
        .background(GeometryReader { proxy in Color.clear.preference(key:DeltaControlFrames.self,value:["start":proxy.frame(in:.named("deltaWindow"))]) })
    }
    private func stopButton(_ size:CGSize) -> some View {
        Button {
            guard !model.busy && (model.engine || model.warp) else { return }
            cancelVisuals(); pulse(size,stop:true)
            controller.stop()
        } label: {
            Text(model.tr("중지","Stop")).font(.system(size:14,weight:.medium)).frame(width:166,height:36)
                .modifier(DeltaGlass(radius:12))
        }.buttonStyle(.plain).disabled(model.busy || (!model.engine && !model.warp))
        .background(GeometryReader { proxy in Color.clear.preference(key:DeltaControlFrames.self,value:["stop":proxy.frame(in:.named("deltaWindow"))]) })
    }
    private var footer: some View {
        VStack(spacing:6) {
            base.tools
            base.badges
        }
    }
    private var jokeText:String {
        if model.phase == "admin_auth" || model.phase == "error" { return " " }
        if model.mining { return joke }
        return model.engine ? model.tr("땅굴 속에도 빛이 있답니다.","A little light at the end of the tunnel.") : " "
    }
    private var successOverlay: some View {
        Image(systemName:"checkmark.circle.fill").resizable().scaledToFit()
            .foregroundStyle(.green).frame(width:64,height:64)
            .background(GeometryReader { proxy in Color.clear.preference(key:DeltaControlFrames.self,value:["success":proxy.frame(in:.named("deltaWindow"))]) })
            .overlay(alignment:.bottom) {
                Text(model.tr("연결 완료","Connected")).font(.system(size:18,weight:.semibold))
                    .foregroundStyle(.white).fixedSize().offset(y:32)
            }
            .scaleEffect(checkScale).opacity(checkOpacity).offset(y:checkLift)
        .accessibilityHidden(checkOpacity == 0)
    }
    private func pulseLayer(_ size:CGSize) -> some View {
        let diameter = hypot(size.width,size.height)*2
        return Group {
            if reduceMotion {
                waveColor.opacity(waveOpacity).frame(width:size.width,height:size.height)
            } else {
                Circle().fill(waveColor).frame(width:diameter,height:diameter).scaleEffect(waveScale)
                    .opacity(waveOpacity).position(waveOrigin)
            }
        }
    }
    private func pulse(_ size:CGSize,stop:Bool) {
        waveTask?.cancel()
        waveColor = stop ? deltaRed : deltaGreen
        let measured = controlFrames[stop ? "stop" : "start"]
        waveOrigin = measured.map { CGPoint(x:$0.midX,y:$0.midY) } ?? CGPoint(x:size.width/2,y:(stop ? 515 : 459)*size.height/610 + (stop ? 18 : 24))
        waveScale = 0.01; waveOpacity = stop ? 0.30 : 0.32
        let duration = reduceMotion ? 0.12 : stop ? 0.48 : 0.52
        waveTask = Task {
            try? await Task.sleep(nanoseconds:16_000_000)
            guard !Task.isCancelled else { return }
            withAnimation(.easeOut(duration:duration)) { waveScale = 1; waveOpacity = 0 }
            try? await Task.sleep(nanoseconds:UInt64(duration*1_000_000_000))
            guard !Task.isCancelled else { return }
            waveOpacity = 0
        }
    }
    private func cancelVisuals() {
        generation += 1; successTask?.cancel(); revealTask?.cancel()
        withAnimation(.easeOut(duration:0.12)) { light = false; blur = 0; checkOpacity = 0; checkLift = 0 }
    }
    private func synchronize() {
        if !model.active { cancelVisuals(); waveTask?.cancel(); waveOpacity = 0; return }
        if model.phase == "cli_check" {
            successPlayed = false; lastAnnouncement = ""
            if revealTask == nil || !shaft {
                revealTask?.cancel()
                revealTask = Task {
                    try? await Task.sleep(nanoseconds:reduceMotion ? 0 : 180_000_000)
                    guard !Task.isCancelled else { return }
                    withAnimation(.easeInOut(duration:reduceMotion ? 0.12 : 0.6)) { shaft = true }
                }
            }
        }
        if ["error","stopping","stopped","warp_ready"].contains(model.phase) {
            cancelVisuals()
            if model.phase != "warp_ready" { successPlayed = false }
            if model.phase == "error" {
                waveTask?.cancel(); waveOpacity = 0
                announce(model.title + ". " + model.detail,key:"error:" + model.error)
            }
            if model.phase == "stopped" { shaft = false }
        }
        if model.phase == "running" && model.engine && !successPlayed {
            successPlayed = true; shaft = true; playSuccess()
        }
    }
    private func playSuccess() {
        announce(model.tr("연결 완료. 분리 라우팅 엔진 실행 중.","Connected. Split-routing engine is running."),key:"running")
        generation += 1; let ticket = generation
        checkScale = 0.76; checkOpacity = 0; checkLift = 0
        successTask?.cancel()
        successTask = Task {
            do {
                withAnimation(.easeOut(duration:reduceMotion ? 0.12 : 0.26)) { light = true }
                try await Task.sleep(nanoseconds:230_000_000)
                guard ticket == generation else { return }
                if !reduceMotion { withAnimation(.easeIn(duration:0.22)) { blur = 10 } }
                try await Task.sleep(nanoseconds:120_000_000)
                checkScale = 0.76; checkLift = 0
                withAnimation(.easeOut(duration:0.26)) { checkOpacity = 1; checkScale = 1 }
                try await Task.sleep(nanoseconds:770_000_000)
                guard ticket == generation else { return }
                withAnimation(.easeOut(duration:0.42)) { blur = 0; checkOpacity = 0; checkLift = -6 }
                try await Task.sleep(nanoseconds:430_000_000)
            } catch { }
            if ticket == generation { blur = 0; checkOpacity = 0; checkLift = 0 }
        }
    }
    private func announce(_ text:String,key:String) {
        guard lastAnnouncement != key else { return }
        lastAnnouncement = key
        guard let window = controller.window else { return }
        NSAccessibility.post(element:window,notification:.announcementRequested,userInfo:[.announcement:text,.priority:NSAccessibilityPriorityLevel.high.rawValue])
    }
    private func rotateJokes() async {
        while !Task.isCancelled && model.mining && model.active {
            if model.language == "ko", let lines = model.copy["lolParodies"] as? [[String:Any]] {
                joke = lines.filter { ($0["states"] as? [String] ?? []).contains(model.phase) }.randomElement()?["text"] as? String ?? ""
            } else { joke = "One small tunnel. One steady connection." }
            try? await Task.sleep(nanoseconds:5_000_000_000)
        }
    }
}

private struct DeltaControlFrames: PreferenceKey {
    static var defaultValue:[String:CGRect] = [:]
    static func reduce(value:inout [String:CGRect],nextValue:()->[String:CGRect]) { value.merge(nextValue(),uniquingKeysWith: { _,new in new }) }
}
