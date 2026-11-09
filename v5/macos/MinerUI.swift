import AppKit
import SwiftUI
import Combine

final class MinerModel: ObservableObject {
    @Published var phase = "idle"
    @Published var completed = 0
    @Published var busy = false
    @Published var engine = false
    @Published var warp = false
    @Published var restored = false
    @Published var error = ""
    @Published var logs = ""
    @Published var active = true
    @Published var language = UserDefaults.standard.string(forKey: "miner.language") ?? "ko" {
        didSet { UserDefaults.standard.set(language, forKey: "miner.language") }
    }
    @Published var diagnostics = false
    @Published var settings = false
    @Published var alwaysAllow = UserDefaults.standard.object(forKey:"miner.alwaysAllow") as? Bool ?? true {
        didSet { UserDefaults.standard.set(alwaysAllow,forKey:"miner.alwaysAllow") }
    }
    @Published var updateBusy = false
    @Published var updateInstalling = false
    @Published var updateMessage = ""
    @Published var updateAvailable = false
    @Published var autoUpdates = UserDefaults.standard.object(forKey:"miner.autoUpdates") as? Bool ?? true {
        didSet { UserDefaults.standard.set(autoUpdates,forKey:"miner.autoUpdates") }
    }
    let copy: [String: Any] = {
        guard let url = Bundle.main.resourceURL?.appendingPathComponent("UIAssets/copy-ko.json"),
              let data = try? Data(contentsOf: url), let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [:] }
        return object
    }()
    func tr(_ ko: String, _ en: String) -> String { language == "ko" ? ko : en }
    var mining: Bool { busy && ["cli_check", "proxy_connect", "tls_verify", "routing"].contains(phase) }
    var title: String {
        if phase == "stopping" { return tr("중지 및 WARP 복귀 중…", "Stopping and restoring WARP…") }
        if language == "ko", let table = copy["systemStatus"] as? [String: [String: String]], let text = table[phase]?["title"] { return text }
        return ["idle":"Ready to dig", "cli_check":"Checking WARP CLI…", "proxy_connect":"Connecting Local Proxy…", "tls_verify":"Verifying secure connection…", "admin_auth":"Approving the network helper…", "routing":"Configuring split routing…", "warp_ready":"WARP is ready", "running":"Connected", "stopped":"Connection stopped", "error":"Network connection failed"][phase] ?? "MINER"
    }
    var detail: String {
        if phase == "error" { return error }
        if phase == "stopped" && restored { return tr("엔진 중지 · WARP UDP Traffic and DNS 복귀 확인", "Engine stopped · WARP UDP Traffic and DNS restored") }
        if language == "ko", let table = copy["systemStatus"] as? [String: [String: String]], let text = table[phase]?["detail"] { return text }
        return ["idle":"Start to inspect the connection path.", "cli_check":"Checking WARP CLI capabilities", "proxy_connect":"Verifying Local Proxy on port 40000", "tls_verify":"Verifying TLS and warp=on", "admin_auth":"Use the native macOS authorization dialog", "routing":"Starting the split-routing engine", "warp_ready":"Proxy verified · routing engine not started", "running":"Split-routing engine is running", "stopping":"Waiting for shutdown and WARP restoration", "stopped":"Engine stopped · WARP state shown separately"][phase] ?? ""
    }
    func accept(_ line: String) {
        guard let data = line.data(using: .utf8), let event = try? JSONSerialization.jsonObject(with: data) as? [String: Any], event["event"] as? String == "progress", let p = event["phase"] as? String, let n = event["completed"] as? Int else { return }
        DispatchQueue.main.async {
            self.phase = p; self.completed = min(5, max(0,n))
            if n >= 3 { self.warp = true; self.restored = false }
        }
    }
    func redact(_ text: String) -> String {
        text.replacingOccurrences(of: NSHomeDirectory(), with: "~")
            .replacingOccurrences(of: "(?i)(authorization|token|password|secret)\\s*[:=]\\s*\\S+", with: "$1=[redacted]", options: .regularExpression)
            .replacingOccurrences(of: "\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b", with: "[address]", options: .regularExpression)
    }
}

enum MinerArt {
    static let images: [String:NSImage] = Dictionary(uniqueKeysWithValues: ["school","tunnel","rock","spotlight","mascot-runtime-256"].map { name in
        (name, NSImage(contentsOf:Bundle.main.resourceURL!.appendingPathComponent("UIAssets/" + name + ".png")) ?? NSImage())
    })
}
func art(_ name: String) -> Image { Image(nsImage: MinerArt.images[name] ?? NSImage()) }
struct MinerScene: View {
    @ObservedObject var model: MinerModel
    @Environment(\.accessibilityReduceMotion) var reduceMotion
    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0/30, paused: !model.mining || reduceMotion || !model.active)) { context in
            let t = model.mining && !reduceMotion && model.active ? context.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 0.57) / 0.57 : 0
            GeometryReader { geo in
                let idle = ["idle", "stopped"].contains(model.phase)
                let x = idle ? geo.size.width * 0.72 : 72 + (geo.size.width - 180) * CGFloat(model.completed) / 5
                ZStack {
                    LinearGradient(colors: [Color(red:0.078,green:0.11,blue:0.17),Color(red:0.031,green:0.051,blue:0.082)], startPoint:.top,endPoint:.bottom)
                    art("school").resizable().scaledToFit().frame(width:172,height:90).scaleEffect(idle ? 1 : 0.45).opacity(idle ? 1 : 0).position(x:geo.size.width/2,y:idle ? 60 : 20).animation(reduceMotion ? .easeOut(duration:0.15) : .easeInOut(duration:0.6),value:idle)
                    if !idle {
                        art("tunnel").resizable().scaledToFit().padding(8).offset(x: abs(t-0.65) < 0.05 ? -1.5 : 0)
                        Capsule().fill(Color(red:0.028,green:0.043,blue:0.07)).frame(width:max(40,x),height:88).position(x:x/2+20,y:91)
                        if model.phase != "running" { Rectangle().fill(Color(red:0.71,green:0.54,blue:0.39)).frame(width:8,height:86).position(x:x+48,y:92) }
                    }
                    if model.phase == "running" {
                        art("spotlight").resizable().scaledToFit().frame(width:140,height:170).position(x:x,y:78)
                        Image(systemName:"checkmark.circle.fill").font(.system(size:34)).foregroundStyle(.green).position(x:x,y:30)
                    }
                    art("mascot-runtime-256").resizable().scaledToFit().frame(width:idle ? 86 : 108,height:108)
                        .rotationEffect(.degrees(model.phase == "running" ? -8 : model.phase == "error" ? -5 : (t == 0 ? 0 : sin(t * .pi * 2)*5)))
                        .offset(y:t == 0 ? 0 : sin(t * .pi * 2))
                        .position(x:x,y:idle ? 134 : 119)
                    if model.phase == "error" { art("rock").resizable().scaledToFit().frame(width:54,height:54).position(x:x+56,y:123) }
                    if model.mining && !reduceMotion && model.active {
                        ForEach(0..<4) { index in
                            Rectangle().fill(Color(red:0.82,green:0.65,blue:0.47))
                                .frame(width:CGFloat(3+index%3),height:CGFloat(3+index%3))
                                .opacity(1-t).position(x:x+46+CGFloat(index*4)+CGFloat(t*10),y:90+CGFloat(index*8)+CGFloat(t*22))
                        }
                    }
                }.clipShape(RoundedRectangle(cornerRadius:24)).overlay(RoundedRectangle(cornerRadius:24).stroke(.white.opacity(0.12)))
                .animation(reduceMotion ? .easeOut(duration:0.15) : .easeInOut(duration:0.55),value:model.completed)
                .accessibilityElement(children:.ignore).accessibilityLabel(model.title + ", \(model.completed)/5, " + model.detail)
            }
        }
    }
}
struct MinerRoot: View {
    @ObservedObject var model: MinerModel
    let controller: AppDelegate
    @State var joke = ""
    var chipColor: Color { model.phase == "error" ? .red : model.engine ? .green : model.busy ? .yellow : .gray }
    var chipText: String {
        if model.phase == "error" { return model.tr("오류","Error") }
        if model.engine { return model.tr("실행 중","Running") }
        return model.busy ? model.tr("연결 중","Connecting") : model.tr("대기","Idle")
    }
    var actionText: String { model.phase == "error" ? model.tr("다시 시도","Try again") : model.tr("시작","Start") }
    var jokeText: String {
        if model.mining && model.phase != "admin_auth" { return joke }
        return model.phase == "running" ? model.tr("땅굴 속에도 빛이 있답니다.","A little light at the end of the tunnel.") : " "
    }
    var warpText: String {
        if model.restored { return "WARP: UDP · Traffic and DNS" }
        return "WARP: " + (model.warp ? model.tr("연결됨 · SOCKS5","Connected · SOCKS5") : model.tr("미확인","Unknown"))
    }
    var header: some View {
        HStack {
            VStack(alignment:.leading,spacing:3) {
                Text("MINER").font(.system(size:24,weight:.semibold))
                Text("Dig your way out.").font(.system(size:11,weight:.medium)).foregroundStyle(.secondary)
            }
            Spacer()
            Button { controller.refresh(); model.diagnostics = true } label: {
                HStack(spacing:5) {
                    Circle().fill(chipColor).frame(width:6,height:6)
                    Text(chipText)
                }.font(.system(size:11,weight:.medium)).padding(8).background(.thinMaterial,in:Capsule())
            }.buttonStyle(.plain)
        }.frame(height:42)
    }
    var statusPanel: some View {
        VStack(alignment:.leading,spacing:5) {
            HStack {
                Text(model.title).font(.system(size:16,weight:.semibold))
                Spacer()
                Text("\(model.completed)/5").font(.system(size:11)).foregroundStyle(.secondary)
            }
            Text(model.detail).font(.system(size:12))
                .foregroundStyle(model.phase == "error" ? Color.red : Color.secondary)
                .lineLimit(2).textSelection(.enabled)
            Text(jokeText).font(.system(size:11)).foregroundStyle(.tertiary).lineLimit(1)
            HStack(spacing:5) {
                ForEach(0..<5) { index in
                    Capsule().fill(index < model.completed ? Color.green : Color.gray.opacity(0.24)).frame(height:4)
                }
            }
        }.frame(maxWidth:.infinity,alignment:.leading).frame(height:84)
    }
    var actions: some View {
        HStack(spacing:12) {
            Button { controller.start() } label: { Text(actionText).frame(maxWidth:.infinity,minHeight:28) }
                .buttonStyle(.borderedProminent).tint(Color(red:0.05,green:0.85,blue:0.15))
                .keyboardShortcut(.defaultAction).frame(maxWidth:.infinity).disabled(model.busy || model.engine)
            Button { controller.stop() } label: { Text(model.tr("중지","Stop")).frame(width:100,height:28) }
                .buttonStyle(.bordered).frame(width:124).disabled(model.busy || (!model.engine && !model.warp))
        }.controlSize(.large)
    }
    var tools: some View {
        HStack {
            Button(model.tr("WARP 자동 연결","Connect WARP")) { controller.connectWarp() }.disabled(model.busy || model.engine)
            Spacer()
            Menu(model.tr("⋯ 도구","⋯ Tools")) {
                Button(model.tr("WARP 열기","Open WARP")) { controller.openWarp() }
                Button(model.tr("사전 점검","Preflight")) { controller.check(); model.diagnostics = true }
                Button(model.tr("상태·로그","Status & logs")) { controller.showDiagnostics() }
                Button(model.tr("WARP 연결 확인","Check WARP")) { controller.checkWarp(); model.diagnostics = true }
                Button(model.tr("WARP 연결 끄기","Disconnect WARP")) { controller.disconnectWarp() }
                Button(model.tr("도움말","Help")) { controller.openGuide() }
                Divider()
                Button(model.tr("설정…","Settings…")) { controller.showSettings() }.keyboardShortcut(",",modifiers:.command)
            }.menuStyle(.borderlessButton).fixedSize().disabled(model.busy)
        }.buttonStyle(.plain).font(.system(size:11))
    }
    var badges: some View {
        HStack {
            Text(warpText)
            Spacer()
            Text(model.engine ? "ENGINE: ON" : "ENGINE: OFF")
        }.font(.system(size:10)).foregroundStyle(.secondary)
    }
    var diagnosticsPanel: some View {
        VStack(alignment:.leading,spacing:12) {
            Text(model.tr("상태·로그","Status & logs")).font(.headline)
            Text(model.detail).font(.caption).textSelection(.enabled)
            ScrollView {
                Text(model.redact(model.logs)).font(.system(size:11,design:.monospaced))
                    .textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading)
            }.frame(minWidth:470,minHeight:260)
            HStack {
                Button(model.tr("복사","Copy")) {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(model.redact(model.logs),forType:.string)
                }
                Button(model.tr("로그 파일 열기","Open log file")) { controller.openLog() }
                Spacer()
                Button(model.tr("닫기","Close")) { model.diagnostics = false }
            }
        }.padding(20)
    }
    func rotateJokes() async {
        while !Task.isCancelled && model.mining && model.active {
            if model.language == "ko", let lines = model.copy["lolParodies"] as? [[String:Any]] {
                let eligible = lines.filter { ($0["states"] as? [String] ?? []).contains(model.phase) }
                joke = eligible.randomElement()?["text"] as? String ?? ""
            } else { joke = "One small tunnel. One steady connection." }
            try? await Task.sleep(nanoseconds:5_000_000_000)
        }
    }
    var body: some View {
        GeometryReader { geo in
            VStack(spacing:10) {
                header
                MinerScene(model:model).frame(height:max(140,min(184,geo.size.height-320)))
                statusPanel
                actions
                tools
                badges
            }.padding(20)
        }.background(.regularMaterial)
        .sheet(isPresented:$model.diagnostics) { diagnosticsPanel }
        .onReceive(NotificationCenter.default.publisher(for:NSApplication.didBecomeActiveNotification)) { _ in model.active = true }
        .onReceive(NotificationCenter.default.publisher(for:NSApplication.didResignActiveNotification)) { _ in model.active = false }
        .task(id:model.phase + model.language + String(model.active)) { await rotateJokes() }
    }
}
struct MinerSettings: View {
    @ObservedObject var model: MinerModel
    let controller: AppDelegate
    var body: some View {
        ScrollView {
          VStack(alignment:.leading,spacing:14) {
            Text(model.tr("MINER 설정","MINER Settings")).font(.title2)
            Picker(model.tr("언어","Language"),selection:$model.language) { Text("한국어").tag("ko"); Text("English").tag("en") }.pickerStyle(.segmented)
            Text(model.tr("중지·종료 시 WARP를 UDP Traffic and DNS로 복귀합니다.","Stopping or quitting restores WARP to UDP Traffic and DNS.")).font(.caption).foregroundStyle(.secondary)
            Toggle(model.tr("관리자 승인 항상 허용 · 도우미 재사용","Remember approval · reuse helper"),isOn:$model.alwaysAllow).disabled(model.busy || model.engine)
            Text(model.tr("최초 설치·도우미 업데이트 시 한 번 승인합니다. 비밀번호를 저장하지 않으며 재부팅해도 자동 연결하지 않습니다. 해제하면 연결할 때마다 인증합니다. 복구 도우미는 비정상 종료 시 DNS를 복구하며 앱 제거 시 삭제됩니다.","Approve once when installing or updating the helper. No password is stored and no tunnel starts at login. Disable to authorize each session. The recovery helper restores DNS after a crash and is removed when uninstalling MINER.")).font(.caption).foregroundStyle(.secondary)
            Divider()
            Text(model.tr("앱 업데이트","App updates")).font(.headline)
            Toggle(model.tr("새 버전 자동 확인·알림","Automatically check and notify"),isOn:$model.autoUpdates)
            Button(model.tr("업데이트 확인","Check for updates")) { controller.checkUpdate() }.disabled(model.updateBusy || model.busy)
            if model.updateAvailable {
                Button(model.tr("업데이트 설치","Install update")) { controller.installUpdate() }.disabled(model.updateBusy || model.busy || model.engine)
            }
            if model.updateBusy { ProgressView().controlSize(.small) }
            Text(model.updateMessage).font(.caption).textSelection(.enabled)
            Divider()
            MinerAbout(model:model)
            Divider()
            Button(role:.destructive) { controller.uninstall() } label: { Text(model.tr("MINER 제거…","Uninstall MINER…")) }.disabled(model.busy || model.updateBusy)
          }.padding(24)
        }.frame(minWidth:440,minHeight:520)
    }
}
