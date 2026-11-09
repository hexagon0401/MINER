import AppKit
import SwiftUI

let applicationName = "MINER"
let identifier = "org.schoolnet.v5.alpha"

func shellQuote(_ value: String) -> String {
    return "'" + value.replacingOccurrences(of: "'", with: "'\\''") + "'"
}

func appleString(_ value: String) -> String {
    return "\"" + value.replacingOccurrences(of: "\\", with: "\\\\")
        .replacingOccurrences(of: "\"", with: "\\\"") + "\""
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    let model = MinerModel()
    var settingsWindow: NSWindow?
    var managedWarp = false
    var updateInfo:[String:Any] = [:]
    var updateTimer:Timer?
    var healthTimer:Timer?
    var healthBusy=false
    var currentProxyPort=40000
    var buttons: [NSButton] = []
    var running = false { didSet { model.engine = running } }
    var busy = false
    let resources = Bundle.main.resourceURL!
    let dataDirectory = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/SchoolNet v5 Alpha")
    var cli: String { resources.appendingPathComponent("runtime/schoolnet-cli/schoolnet-cli").path }
    var engine: String { resources.appendingPathComponent("bin/sing-box").path }

    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x:0,y:0,width:560,height:610), styleMask:[.titled,.closable,.miniaturizable,.resizable], backing:.buffered, defer:false)
        window.title = "MINER"
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.titlebarSeparatorStyle = .none
        window.styleMask.insert(.fullSizeContentView)
        window.setFrame(NSRect(x:0,y:0,width:560,height:610), display:false)
        window.isMovableByWindowBackground = true
        window.isOpaque = false
        window.backgroundColor = .clear
        window.minSize = NSSize(width:520,height:570)
        window.collectionBehavior = [.fullScreenNone]
        window.isReleasedWhenClosed = false
        let backdrop = NSVisualEffectView(frame:window.contentView!.bounds)
        backdrop.material = .underWindowBackground
        backdrop.blendingMode = .behindWindow
        backdrop.state = .followsWindowActiveState
        let host = NSHostingView(rootView:DeltaRoot(model:model,controller:self))
        host.frame = backdrop.bounds
        host.autoresizingMask = [.width,.height]
        backdrop.addSubview(host)
        window.contentView = backdrop
        window.center()
        let menu = NSMenu()
        let item = NSMenuItem()
        menu.addItem(item)
        let submenu = NSMenu()
        let settingsItem = submenu.addItem(withTitle: "설정 / Settings…", action: #selector(showSettings), keyEquivalent: ",")
        settingsItem.target = self
        submenu.addItem(.separator())
        submenu.addItem(withTitle: "종료 / Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        item.submenu = submenu
        NSApp.mainMenu = menu
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        if let index = CommandLine.arguments.firstIndex(of:"--ui-smoke"), CommandLine.arguments.count > index+2 {
            runDeltaSmoke(output:URL(fileURLWithPath:CommandLine.arguments[index+1]),arch:CommandLine.arguments[index+2])
            return
        }
        append("MINER ALPHA v1.2.0: 게임 중에도 MINER와 WARP Local Proxy 연결을 유지하세요.")
        refresh()
        DispatchQueue.main.asyncAfter(deadline:.now()+4) { if self.model.autoUpdates { self.checkUpdate() } }
        updateTimer=Timer.scheduledTimer(withTimeInterval:21600,repeats:true) { _ in if self.model.autoUpdates { self.checkUpdate() } }
        healthTimer=Timer.scheduledTimer(withTimeInterval:15,repeats:true) { _ in self.checkSessionHealth() }
    }

    func append(_ text: String) {
        model.logs += model.redact(text) + "\n"
        if model.logs.count > 64000 { model.logs = String(model.logs.suffix(64000)) }
    }

    func setBusy(_ value: Bool) {
        busy = value
        model.busy = value
    }

    func execute(_ arguments: [String], administrator: Bool = false) throws -> String {
        guard !CommandLine.arguments.contains("--ui-smoke") else {
            throw NSError(domain:identifier,code:1,userInfo:[NSLocalizedDescriptionKey:"Network/backend actions are disabled in UI smoke fixtures"])
        }
        if administrator && (arguments.prefix(2).elementsEqual(["desktop", "start"]) || arguments.prefix(2).elementsEqual(["desktop", "helper-install"])) {
            DispatchQueue.main.async { self.model.phase = "admin_auth"; self.model.completed = 3 }
        }
        let process = Process()
        if administrator {
            let command = ([cli] + arguments).map(shellQuote).joined(separator: " ")
            process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
            process.arguments = ["-e", "do shell script " + appleString(command) + " with administrator privileges"]
        } else {
            process.executableURL = URL(fileURLWithPath: cli)
            process.arguments = arguments
        }
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        try process.run()
        var collected = Data()
        var pending = Data()
        while true {
            let chunk = pipe.fileHandleForReading.availableData
            if chunk.isEmpty { break }
            collected.append(chunk); pending.append(chunk)
            while let index = pending.firstIndex(of: 10) {
                let line = String(data: pending.prefix(upTo:index), encoding:.utf8) ?? ""
                self.model.accept(line)
                pending.removeSubrange(...index)
            }
        }
        process.waitUntilExit()
        let text = String(data: collected, encoding: .utf8) ?? ""
        guard process.terminationStatus == 0 else {
            throw NSError(domain: identifier, code: Int(process.terminationStatus),
                          userInfo: [NSLocalizedDescriptionKey: text])
        }
        return text
    }

    func ensureProfile() throws {
        let marker = dataDirectory.appendingPathComponent(".managed.json")
        let manager = FileManager.default
        if manager.fileExists(atPath: dataDirectory.path) {
            let data = try Data(contentsOf: marker)
            let owner = try JSONSerialization.jsonObject(with: data) as? [String: String]
            guard owner?["id"] == identifier else {
                throw NSError(domain: identifier, code: 1, userInfo: [NSLocalizedDescriptionKey: "기존 설정 폴더의 소유 정보를 확인할 수 없어 보존했습니다."])
            }
        } else {
            try manager.createDirectory(at: dataDirectory, withIntermediateDirectories: true)
            try JSONSerialization.data(withJSONObject: ["id": identifier]).write(to: marker, options: .atomic)
        }
        if !manager.fileExists(atPath: dataDirectory.appendingPathComponent("profile.json").path) {
            _ = try execute(["init", "--directory", dataDirectory.path, "--platform", "macos"])
        } else {
            // Rebuild old alpha route rules without discarding profile settings.
            _ = try execute(["render", "--directory", dataDirectory.path])
        }
    }

    func operation(_ work: @escaping () throws -> String, completion: (() -> Void)? = nil) {
        guard !busy && !model.updateBusy else { return }
        setBusy(true)
        DispatchQueue.global(qos: .userInitiated).async {
            let result: Result<String, Error> = Result { try work() }
            DispatchQueue.main.async {
                self.setBusy(false)
                switch result {
                case .success(let text): self.append(text); completion?()
                case .failure(let error): self.model.phase = "error"; self.model.error = self.model.redact(error.localizedDescription); self.append(error.localizedDescription); self.window.makeKeyAndOrderFront(nil)
                }
            }
        }
    }

    @objc func openWarp() {
        NSWorkspace.shared.open(URL(fileURLWithPath: "/Applications/Cloudflare WARP.app"))
    }
    func warpArguments(_ operation: String) throws -> [String] {
        try ensureProfile()
        let data = try Data(contentsOf: dataDirectory.appendingPathComponent("profile.json"))
        let profile = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let port = profile?["proxy_port"] as? Int ?? 40000
        currentProxyPort=port
        return ["warp", operation, "--proxy-port", String(port), "--progress"]
    }
    @objc func connectWarp() {
        guard !busy && !model.updateBusy && !running else { return }
        managedWarp = true; model.phase = "cli_check"; model.completed = 0; model.error = ""
        operation({ try self.execute(self.warpArguments("connect")) }, completion: { self.model.phase = "warp_ready"; self.model.warp = true; self.model.completed = 3 })
    }
    @objc func showSettings() {
        if settingsWindow == nil {
            let settings = NSWindow(contentRect:NSRect(x:0,y:0,width:420,height:380),styleMask:[.titled,.closable],backing:.buffered,defer:false)
            settings.title = "MINER Settings"
            settings.isReleasedWhenClosed = false
            settings.contentView = NSHostingView(rootView:MinerSettings(model:model,controller:self))
            settings.center(); settingsWindow = settings
        }
        settingsWindow?.makeKeyAndOrderFront(nil)
    }
    @objc func showDiagnostics() {
        let log = URL(fileURLWithPath:"/Library/Application Support/SchoolNet v5 Alpha/engine.log")
        if let data = try? Data(contentsOf:log), let text = String(data:data.suffix(32000),encoding:.utf8) { append(text) }
        model.diagnostics = true
        refresh()
    }
    @objc func checkWarp() {
        operation { try self.execute(self.warpArguments("status")) }
    }
    @objc func disconnectWarp() {
        let alert = NSAlert()
        alert.messageText = model.tr("v5를 중지하고 WARP 연결을 끌까요?", "Stop v5 and disconnect WARP?")
        alert.informativeText = model.tr("클라이언트 연결이 끊길 수 있습니다. 전체 터널이나 직접 연결로 자동 전환하지 않습니다.", "Client sessions may disconnect. No automatic full-tunnel or direct fallback.")
        alert.addButton(withTitle: model.tr("중지하고 끄기", "Stop and disconnect"))
        alert.addButton(withTitle: model.tr("취소", "Cancel"))
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        operation({
            _ = try self.execute(["desktop", "stop"], administrator: true)
            DispatchQueue.main.async { self.running = false }
            return try self.execute(self.warpArguments("disconnect"))
        }, completion: { self.running = false })
    }
    @objc func openGuide() {
        NSWorkspace.shared.open(resources.appendingPathComponent("UserGuide.txt"))
    }
    @objc func openLog() {
        let path = "/Library/Application Support/SchoolNet v5 Alpha/engine.log"
        if FileManager.default.fileExists(atPath: path) {
            NSWorkspace.shared.open(URL(fileURLWithPath: path))
        } else { append("아직 실행 로그가 없습니다.") }
    }
    @objc func check() {
        operation {
            try self.ensureProfile()
            return try self.execute(["doctor", "--directory", self.dataDirectory.path, "--engine", self.engine])
        }
    }
    @objc func start() {
        guard !busy && !model.updateBusy && !running else { return }
        guard Bundle.main.bundleURL.path == "/Applications/MINER.app" else {
            model.phase="error";model.error=model.tr("DMG에서 앱을 Applications로 복사한 뒤 실행하세요.","Copy MINER from the DMG to Applications before starting."); return
        }
        managedWarp = true; model.phase = "cli_check"; model.completed = 0; model.error = ""
        operation({
            try self.ensureProfile()
            _ = try self.execute(self.warpArguments("connect"))
            if self.model.alwaysAllow {
                try self.ensureHelper()
                return try self.execute(["desktop", "helper-start", "--profile", self.dataDirectory.path])
            }
            return try self.execute(["desktop", "start", "--resources", self.resources.path,
                                     "--profile", self.dataDirectory.path,"--owner",String(getuid())], administrator: true)
        }, completion: { self.running = true; self.model.phase = "running"; self.model.completed = 5; self.model.warp = true })
    }
    @objc func stop() {
        guard !busy else { return }
        model.phase = "stopping"
        operation({
            if self.running { _ = try self.stopEngine() }
            DispatchQueue.main.async { self.running = false }
            return try self.execute(["warp", "restore"])
        }, completion: { self.running = false; self.model.phase = "stopped"; self.model.completed = 0; self.model.warp = true; self.model.restored = true; self.managedWarp = false })
    }
    @objc func refresh() {
        operation {
            let text = try self.execute(["desktop", "status"])
            if let data = text.data(using: .utf8),
               let info = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                DispatchQueue.main.async { self.running = info["running"] as? Bool ?? false; if self.running { self.model.phase = "running"; self.model.completed = 5; self.managedWarp = true } }
            }
            return text
        }
    }
    func helperReady() -> Bool {
        guard let text = try? execute(["desktop","helper-status"]), let data = text.data(using:.utf8),
              let info = try? JSONSerialization.jsonObject(with:data) as? [String:Any] else { return false }
        return (info["version"] as? String) == (Bundle.main.object(forInfoDictionaryKey:"SchoolNetReleaseVersion") as? String)
    }
    func ensureHelper() throws {
        if helperReady() { return }
        _ = try execute(["desktop","helper-install","--resources",resources.path,"--profile",dataDirectory.path,"--owner",String(getuid())],administrator:true)
        guard helperReady() else { throw NSError(domain:identifier,code:1,userInfo:[NSLocalizedDescriptionKey:"MINER helper did not become ready"] ) }
    }
    func stopEngine() throws -> String {
        if model.alwaysAllow && helperReady() { return try execute(["desktop","helper-stop"]) }
        return try execute(["desktop","stop"],administrator:true)
    }
    func checkSessionHealth() {
        guard running && !busy && !healthBusy && !model.updateBusy else { return }
        healthBusy=true
        DispatchQueue.global(qos:.utility).async {
            do {
                let status=try self.execute(["desktop","status"])
                let info=try JSONSerialization.jsonObject(with:Data(status.utf8)) as? [String:Any] ?? [:]
                guard info["running"] as? Bool == true else { throw NSError(domain:identifier,code:1,userInfo:[NSLocalizedDescriptionKey:"네트워크 엔진이 종료되었습니다. 일반 DNS를 복구한 뒤 다시 연결하세요."]) }
                _ = try self.execute(["warp","maintain","--proxy-port",String(self.currentProxyPort)])
                DispatchQueue.main.async { self.healthBusy=false }
            } catch { DispatchQueue.main.async { self.healthBusy=false; self.model.error=self.model.redact(error.localizedDescription);self.model.phase="error" } }
        }
    }
    var updateArchitecture:String {
        #if arch(arm64)
        return "arm64"
        #else
        return "x86_64"
        #endif
    }
    @objc func checkUpdate() {
        guard !model.updateBusy && !busy else { return }
        model.updateBusy = true; model.updateMessage = model.tr("최신 정식 버전을 확인하고 있습니다.","Checking the latest official release.")
        DispatchQueue.global(qos:.utility).async {
            do {
                let text = try self.execute(["update","check","--platform","macos","--arch",self.updateArchitecture])
                let info = try JSONSerialization.jsonObject(with:Data(text.utf8)) as? [String:Any] ?? [:]
                DispatchQueue.main.async {
                    self.updateInfo = info; self.model.updateBusy = false
                    self.model.updateAvailable = info["available"] as? Bool == true
                    NSApp.dockTile.badgeLabel=self.model.updateAvailable ? "↑" : nil
                    self.model.updateMessage = self.model.updateAvailable ? self.model.tr("새 버전: ","New release: ") + (info["version"] as? String ?? "") + self.model.tr(" · 연결을 중지한 뒤 설치하세요."," · Stop MINER before installing.") : self.model.tr("최신 버전입니다.","You are up to date.")
                }
            } catch { DispatchQueue.main.async { self.model.updateBusy = false; self.model.updateMessage = self.model.redact(error.localizedDescription) } }
        }
    }
    @objc func installUpdate() {
        guard model.updateAvailable && !model.updateBusy && !busy && !running else { return }
        if updateInfo["manager"] as? String == "homebrew" {
            guard let brew = updateInfo["brew"] as? String, ["/opt/homebrew/bin/brew","/usr/local/bin/brew"].contains(brew) else { return }
            let command = "while /usr/bin/pgrep -x MINER >/dev/null; do /bin/sleep 1; done; " + shellQuote(brew) + " update && " + shellQuote(brew) + " upgrade --cask hexagon0401/miner/miner"
            let process = Process(); process.executableURL = URL(fileURLWithPath:"/usr/bin/osascript")
            process.arguments = ["-e","tell application \"Terminal\" to do script " + appleString(command)]
            do { try process.run(); NSApp.terminate(nil) } catch { model.updateMessage = error.localizedDescription }
            return
        }
        model.updateBusy = true; model.updateMessage = model.tr("설치 파일 다운로드·SHA-256 검증 중…","Downloading and verifying the installer…")
        DispatchQueue.global(qos:.utility).async {
            do {
                let text = try self.execute(["update","download","--platform","macos","--arch",self.updateArchitecture,"--directory",self.dataDirectory.appendingPathComponent("Updates").path])
                let info = try JSONSerialization.jsonObject(with:Data(text.utf8)) as? [String:Any] ?? [:]
                guard info["verified"] as? Bool == true, let path = info["path"] as? String else { throw NSError(domain:identifier,code:1) }
                DispatchQueue.main.async {
                    self.model.updateBusy = false
                    self.model.updateMessage = self.model.tr("검증 완료. DMG에서 MINER를 응용 프로그램 폴더로 옮겨 교체하세요.","Verified. Drag MINER from the DMG to Applications to replace it.")
                    NSWorkspace.shared.open(URL(fileURLWithPath:path)); NSApp.terminate(nil)
                }
            } catch { DispatchQueue.main.async { self.model.updateBusy = false; self.model.updateMessage = self.model.redact(error.localizedDescription) } }
        }
    }
    @objc func uninstall() {
        let alert = NSAlert()
        alert.messageText = model.tr("MINER를 제거할까요?", "Uninstall MINER?")
        alert.informativeText = model.tr("실행을 중지하고 v5의 서비스·설정·로그를 제거한 뒤 앱을 휴지통으로 옮깁니다. WARP와 기존 v1~v4는 유지합니다.", "Stop MINER, remove its service, settings and logs, then move the app to Trash. WARP and v1–v4 are kept.")
        alert.addButton(withTitle: model.tr("제거", "Uninstall"))
        alert.addButton(withTitle: model.tr("취소", "Cancel"))
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        operation({
            let result = try self.execute(["desktop", "uninstall"], administrator: true)
            if self.managedWarp || self.running { _ = try self.execute(["warp", "restore"]) }
            let marker = self.dataDirectory.appendingPathComponent(".managed.json")
            if let data = try? Data(contentsOf: marker),
               let owner = try? JSONSerialization.jsonObject(with: data) as? [String: String], owner["id"] == identifier {
                try FileManager.default.removeItem(at: self.dataDirectory)
            }
            return result
        }, completion: {
            self.running = false; self.managedWarp = false
            guard Bundle.main.bundleURL.path == "/Applications/MINER.app" else { return }
            NSWorkspace.shared.recycle([Bundle.main.bundleURL]) { _, error in
                DispatchQueue.main.async {
                    if let error = error { self.append("서비스 제거 완료. 앱은 Finder에서 제거하세요: " + error.localizedDescription) }
                    else { NSApp.terminate(nil) }
                }
            }
        })
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if busy || model.updateBusy { return .terminateCancel }
        guard running || managedWarp else { return .terminateNow }
        model.phase = "stopping"; setBusy(true)
        DispatchQueue.global().async {
            do {
                if self.running { _ = try self.stopEngine() }
                DispatchQueue.main.async { self.running = false }
                _ = try self.execute(["warp", "restore"])
                DispatchQueue.main.async { self.managedWarp = false; self.model.restored = true; NSApp.reply(toApplicationShouldTerminate:true) }
            } catch {
                DispatchQueue.main.async { self.setBusy(false); self.model.phase = "error"; self.model.error = self.model.redact(error.localizedDescription); self.append(error.localizedDescription); self.window.makeKeyAndOrderFront(nil); NSApp.reply(toApplicationShouldTerminate:false) }
            }
        }
        return .terminateLater
    }
}

@main struct MinerApplication {
    @MainActor static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        app.run()
    }
}
