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
    var statusItem:NSStatusItem?
    var window: NSWindow!
    let model = MinerModel()
    var settingsWindow: NSWindow?
    var managedWarp = false
    var engineStoppedConfirmed=false
    var updateInfo:[String:Any] = [:]
    var updateTimer:Timer?
    var healthTimer:Timer?
    var healthBusy=false
    let backendLock=NSLock()
    var healthCancellation:CommandCancellation?
    var healthFailure=""
    var currentProxyPort=40000
    var buttons: [NSButton] = []
    var running = false { didSet { model.engine = running } }
    var busy = false
    var operationCancellation:CommandCancellation?
    var operationReadOnly=false
    var stopPending=false
    var quitPending=false
    var installationHandoffCompleted=false
    let operationTokenKey="MINER.operationCancellation"
    let resources = Bundle.main.resourceURL!
    let dataDirectory = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/SchoolNet v5 Alpha")
    var cli: String { resources.appendingPathComponent("runtime/schoolnet-cli/schoolnet-cli").path }
    var engine: String { resources.appendingPathComponent("bin/sing-box").path }

    func applicationDidFinishLaunching(_ notification: Notification) {
        StartupTrace.record("did_finish_launching")
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
        let updateItem=submenu.addItem(withTitle:"업데이트 확인 / Check for Updates…",action:#selector(manualCheckUpdate),keyEquivalent:"")
        updateItem.target=self
        submenu.addItem(.separator())
        submenu.addItem(withTitle: "종료 / Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        item.submenu = submenu
        NSApp.mainMenu = menu
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        StartupTrace.record("window_presented")
        DispatchQueue.main.async { StartupTrace.record("event_loop_ready") }
        if let index = CommandLine.arguments.firstIndex(of:"--ui-smoke"), CommandLine.arguments.count > index+2 {
            runDeltaSmoke(output:URL(fileURLWithPath:CommandLine.arguments[index+1]),arch:CommandLine.arguments[index+2])
            return
        }
        DispatchQueue.global(qos:.utility).async {
            guard FileManager.default.fileExists(atPath:self.dataDirectory.appendingPathComponent(".managed.json").path) else { return }
            do {
                _ = try self.execute(["update","finish","--platform","macos","--arch",self.updateArchitecture])
                let failure=self.dataDirectory.appendingPathComponent("Updates/install-error.txt")
                if let message=try? String(contentsOf:failure,encoding:.utf8) {
                    DispatchQueue.main.async { self.model.updateMessage=self.model.tr("이전 업데이트 실패: ","Previous update failed: ")+self.model.redact(message) }
                    try? FileManager.default.removeItem(at:failure)
                }
            }
            catch { DispatchQueue.main.async { self.append(error.localizedDescription) } }
        }
        statusItem=NSStatusBar.system.statusItem(withLength:NSStatusItem.variableLength)
        statusItem?.button?.title="MINER"
        let tray=NSMenu();let show=tray.addItem(withTitle:"MINER 열기 / Open",action:#selector(showMainWindow),keyEquivalent:"");show.target=self
        let stop=tray.addItem(withTitle:"연결 종료 / Stop",action:#selector(stop),keyEquivalent:"");stop.target=self
        let quit=tray.addItem(withTitle:"종료 / Quit",action:#selector(NSApplication.terminate(_:)),keyEquivalent:"");quit.target=NSApp
        statusItem?.menu=tray
        append("MINER "+(Bundle.main.object(forInfoDictionaryKey:"MINERDisplayVersion") as? String ?? "STRATA Preview")+": 게임 중에도 연결을 유지하세요. 실제 통계창 복귀는 시험이 필요합니다.")
        refresh()
        DispatchQueue.main.asyncAfter(deadline:.now()+4) { if self.model.autoUpdates { self.checkUpdate() } }
        updateTimer=Timer.scheduledTimer(withTimeInterval:21600,repeats:true) { _ in if self.model.autoUpdates { self.checkUpdate() } }
        healthTimer=Timer.scheduledTimer(withTimeInterval:15,repeats:true) { _ in self.model.observationClock=Date();self.checkSessionHealth() }
        NSWorkspace.shared.notificationCenter.addObserver(forName:NSWorkspace.didWakeNotification,object:nil,queue:.main) { [weak self] _ in self?.checkSessionHealth() }
    }

    @objc func showMainWindow() { guard let window=window else { return };window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true) }
    func applicationShouldHandleReopen(_ sender:NSApplication,hasVisibleWindows flag:Bool) -> Bool {
        StartupTrace.record("reopen_received");guard let window=window else { return false };window.deminiaturize(nil);showMainWindow();return true
    }
    @objc func openInstalledApplication() {
        guard !busy && !running && !managedWarp else { return }
        guard !CommandLine.arguments.contains("--installed-handoff"),MinerInstallation.compatibleInstalledBundle() != nil else {
            model.phase="error"
            model.error=model.tr("Applications의 MINER.app과 실행 중인 복사본의 버전이 다르거나 실행 경로가 임시 경로입니다. 앱을 종료하고 /Applications/MINER.app을 Finder에서 다시 여세요.","The installed copy differs or is still translocated. Quit and reopen /Applications/MINER.app in Finder.")
            return
        }
        setBusy(true);model.phase="opening_installed"
        let configuration=NSWorkspace.OpenConfiguration();configuration.createsNewApplicationInstance=true
        configuration.activates=true;configuration.arguments=["--installed-handoff"]
        NSWorkspace.shared.openApplication(at:MinerInstallation.installedURL,configuration:configuration) { application,error in
            DispatchQueue.main.async {
                self.setBusy(false)
                guard application != nil,error == nil else {
                    self.model.phase="error";self.model.error=self.model.redact(error?.localizedDescription ?? "Installed MINER could not open");return
                }
                StartupTrace.record("installed_handoff_completed");self.installationHandoffCompleted=true;NSApp.terminate(nil)
            }
        }
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
        let serialized=["warp","desktop"].contains(arguments.first ?? "")
        if serialized { backendLock.lock() }
        defer { if serialized { backendLock.unlock() } }
        let cancellation=Thread.current.threadDictionary[operationTokenKey] as? CommandCancellation
        if cancellation?.cancelled == true { throw NSError(domain:"MINER.cancelled",code:1) }
        let protected=administrator || arguments.prefix(2).elementsEqual(["desktop","helper-start"])
        var scoped=arguments
        if let token=cancellation,arguments.first=="desktop",["start","helper-start"].contains(arguments.dropFirst().first ?? "") { scoped += ["--session-id",token.session] }
        if administrator && (arguments.prefix(2).elementsEqual(["desktop","start"]) || arguments.prefix(2).elementsEqual(["desktop","helper-install"])) {
            DispatchQueue.main.async {
                guard cancellation?.cancelled != true else { return }
                self.model.phase="admin_auth";self.model.completed=3
            }
        }
        if arguments.prefix(2).elementsEqual(["warp","service-check"]) {
            DispatchQueue.main.sync {
                self.model.probeGeneration+=1;self.model.probeRequest=cancellation?.session ?? UUID().uuidString
                self.model.riotProbeStatus="NOT_RUN";self.model.probeObservedAt=0
                scoped += ["--request-id",self.model.probeRequest,"--generation",String(self.model.probeGeneration)]
            }
        }
        let executable:String
        let parameters:[String]
        if administrator {
            let command=([cli]+scoped).map(shellQuote).joined(separator:" ")
            executable="/usr/bin/osascript";parameters=["-e","do shell script "+appleString(command)+" with administrator privileges"]
        } else { executable=cli;parameters=scoped }
        let quick=arguments.prefix(2).elementsEqual(["desktop","status"]) || arguments.prefix(2).elementsEqual(["desktop","helper-status"]) || arguments.first=="session-preflight"
        let timeout:TimeInterval=quick ? 8 : arguments.prefix(2).elementsEqual(["warp","maintain"]) ? 12 : arguments.first=="update" ? 300 : administrator ? 120 : 90
        return try CommandRunner.run(executable,parameters,timeout:timeout,cancellation:cancellation,interruptible:!protected) { line in
            if cancellation?.cancelled != true { self.model.accept(line,allowed:{ cancellation?.cancelled != true }) }
        }
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

    func operation(_ work: @escaping () throws -> String, readOnly:Bool=false, completion: (() -> Void)? = nil) {
        guard !busy && !model.updateInstalling else { return }
        healthCancellation?.cancel()
        setBusy(true);operationReadOnly=readOnly
        let cancellation=CommandCancellation();operationCancellation=cancellation
        DispatchQueue.global(qos: .userInitiated).async {
            Thread.current.threadDictionary[self.operationTokenKey]=cancellation
            defer { Thread.current.threadDictionary.removeObject(forKey:self.operationTokenKey) }
            let result: Result<String, Error> = Result { try work() }
            DispatchQueue.main.async {
                self.operationCancellation=nil;self.setBusy(false)
                if self.stopPending {
                    self.stopPending=false
                    self.stop()
                    return
                }
                switch result {
                case .success(let text):
                    self.append(text)
                    if let info=try? JSONSerialization.jsonObject(with:Data(text.utf8)) as? [String:Any],let active=info["running"] as? Bool {
                        self.running=active
                        if active {
                            self.engineStoppedConfirmed=false;self.managedWarp=true
                            if info["ready"] as? Bool == false { self.model.phase="error";self.model.completed=0;self.model.error=self.model.tr("이전 연결이 준비되지 않았습니다. 중지 후 다시 연결하세요.","Previous engine is not ready. Stop and reconnect.") }
                            else { self.model.phase=self.model.effectiveProbeStatus == "PASS" ? "running" : "connection_warning";self.model.completed=5 }
                        }
                    }
                    completion?()
                case .failure(let error): self.model.recoveryNeeded = self.managedWarp || self.running || !error.localizedDescription.contains("MINER_SESSION_BLOCKED"); self.model.phase = "error"; self.model.error = self.model.redact(error.localizedDescription).replacingOccurrences(of:"MINER_SESSION_BLOCKED: ",with:""); self.append(error.localizedDescription); self.window.makeKeyAndOrderFront(nil)
                }
                if self.quitPending { self.quitPending=false;NSApp.terminate(nil) }
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
    func sessionPreflight() throws {
        let text = try execute(["session-preflight"])
        if let info = try JSONSerialization.jsonObject(with:Data(text.utf8)) as? [String:Any], info["game_open"] as? Bool == true {
            DispatchQueue.main.async {
                self.append(self.model.tr("게임 중 연결 경로를 변경합니다. 기존 연결은 자동 이전되지 않으며 게임 재접속이 필요할 수 있습니다.","Changing connection paths during a game. Existing sockets are not migrated; the game may need to reconnect."))
            }
        }
    }
    @objc func connectWarp() {
        guard !busy && !model.updateInstalling && !running else { return }
        engineStoppedConfirmed=false; model.phase = "cli_check"; model.completed = 0; model.error = ""
        operation({
            try self.sessionPreflight()
            DispatchQueue.main.sync { self.managedWarp=true }
            return try self.execute(self.warpArguments("connect"))
        }, completion: { self.model.phase = "warp_ready"; self.model.warp = true; self.model.completed = 3 })
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
        operation({
            _ = try self.execute(self.warpArguments("status"))
            return try self.execute(["warp","service-check","--proxy-port",String(self.currentProxyPort)])
        }, completion: {
            if self.running && self.model.phase == "connection_warning" && self.model.effectiveProbeStatus == "PASS" { self.model.error=""; self.model.phase="running" }
        })
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
            DispatchQueue.main.async { self.running = false;self.engineStoppedConfirmed=true }
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
        guard !busy && !model.updateInstalling && !running else { return }
        guard MinerInstallation.isInstalled() else {
            StartupTrace.record("installation_check_rejected")
            if !managedWarp && MinerInstallation.compatibleInstalledBundle() != nil && !CommandLine.arguments.contains("--installed-handoff") {
                openInstalledApplication();return
            }
            model.phase="error"
            model.error=model.tr("실행 위치: ","Running from: ")+model.redact(Bundle.main.bundleURL.path)+model.tr(" · /Applications/MINER.app을 다시 열어주세요. 사용자 Applications 폴더와 DMG 실행은 설치본과 다릅니다."," · Reopen /Applications/MINER.app. Home Applications and mounted DMG copies are different locations.");return
        }
        engineStoppedConfirmed=false; model.phase = "cli_check"; model.completed = 0; model.error = ""
        operation({
            try self.sessionPreflight()
            DispatchQueue.main.sync { self.managedWarp=true }
            try self.ensureProfile()
            _ = try self.execute(self.warpArguments("connect"))
            let engineResult:String
            if self.model.alwaysAllow {
                try self.ensureHelper()
                engineResult = try self.execute(["desktop", "helper-start", "--profile", self.dataDirectory.path])
            } else {
            engineResult = try self.execute(["desktop", "start", "--resources", self.resources.path,
                                     "--profile", self.dataDirectory.path,"--owner",String(getuid())], administrator: true)
            }
            DispatchQueue.main.sync { self.running=true;self.model.phase="service_verify";self.model.completed=4 }
            do { _ = try self.execute(["warp","service-check","--proxy-port",String(self.currentProxyPort),"--progress"]) }
            catch {
                if (error as NSError).domain == "MINER.cancelled" { throw error }
                DispatchQueue.main.sync { self.model.error=self.model.tr("분리 경로 준비됨 · Riot 서비스 확인 실패. 실제 통계 기능은 미검증입니다.","Routing ready · Riot check failed. Statistics remain unverified.") }
                self.appendProbeFailure(error)
            }
            return engineResult
        }, completion: {
            self.running=true;self.model.completed=5;self.model.warp=true
            self.model.phase=self.model.effectiveProbeStatus == "PASS" ? "running" : "connection_warning"
        })
    }
    func appendProbeFailure(_ error:Error) {
        DispatchQueue.main.async { self.append(error.localizedDescription) }
    }
    @objc func stop() {
        if busy {
            stopPending=true;model.phase="stopping";operationCancellation?.cancel()
            return
        }
        model.phase = "stopping"
        operation({
            _ = try self.stopEngine()
            DispatchQueue.main.async { self.running = false;self.engineStoppedConfirmed=true }
            return try self.execute(["warp", "restore"])
        }, completion: { self.running = false; self.model.phase = "stopped"; self.model.completed = 0; self.model.warp = true; self.model.restored = true; self.managedWarp = false;self.model.recoveryNeeded=false; if self.quitPending { self.quitPending=false;NSApp.terminate(nil) } })
    }
    @objc func refresh() {
        operation({ try self.execute(["desktop","status"]) },readOnly:true,completion:nil)
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
        if model.alwaysAllow && FileManager.default.fileExists(atPath:"/var/run/org.schoolnet.v5.alpha.helper.sock") {
            do { return try execute(["desktop","helper-stop"]) }
            catch {
                let message=error.localizedDescription
                if (error as NSError).domain=="MINER.timeout" { throw error }
                if !message.contains("administrator approval") && !message.contains("No such file") && !message.contains("Connection refused") { throw error }
            }
        }
        return try execute(["desktop","stop"],administrator:true)
    }
    func checkSessionHealth() {
        guard running && !busy && !healthBusy && !model.updateInstalling else { return }
        healthBusy=true
        let token=CommandCancellation();healthCancellation=token
        DispatchQueue.global(qos:.utility).async {
            Thread.current.threadDictionary[self.operationTokenKey]=token
            defer { Thread.current.threadDictionary.removeObject(forKey:self.operationTokenKey) }
            do {
                let status=try self.execute(["desktop","status"])
                let info=try JSONSerialization.jsonObject(with:Data(status.utf8)) as? [String:Any] ?? [:]
                guard info["running"] as? Bool == true else { throw NSError(domain:"MINER.engineGone",code:1,userInfo:[NSLocalizedDescriptionKey:"네트워크 엔진이 종료되었습니다. 일반 DNS를 복구한 뒤 다시 연결하세요."]) }
                guard info["ready"] as? Bool == true else { throw NSError(domain:"MINER.dnsNotReady",code:1,userInfo:[NSLocalizedDescriptionKey:"DNS 엔진 응답을 확인하지 못했습니다. 중지 후 다시 연결하세요. / DNS engine is not responding; stop and reconnect."]) }
                if let scope=info["scope"] as? [String:Any],scope["healthy"] as? Bool == false {
                    throw NSError(domain:"MINER.scopeChanged",code:1,userInfo:[NSLocalizedDescriptionKey:self.model.tr("네트워크 또는 DNS 설정이 변경됐습니다. 중지 후 다시 연결하세요. 설정을 자동으로 덮어쓰지 않습니다.","Network or DNS changed. Stop and reconnect; settings were not overwritten.")])
                }
                let health=try self.execute(["warp","maintain","--proxy-port",String(self.currentProxyPort)])
                let state=try JSONSerialization.jsonObject(with:Data(health.utf8)) as? [String:Any] ?? [:]
                if state["healthy"] as? Bool != true {
                    let warning=(state["warning"] as? String) ?? "WARP 프록시 확인 필요 / WARP proxy needs attention."
                    DispatchQueue.main.async {
                        self.healthBusy=false
                        guard !token.cancelled && !self.busy && self.running else { return }
                        let message=self.model.redact(warning)
                        if self.healthFailure != message { self.append(message) }
                        self.healthFailure=message;self.model.error=message;self.model.phase="connection_warning"
                    }
                } else {
                    DispatchQueue.main.async {
                        self.healthBusy=false
                        guard !token.cancelled && !self.busy && self.running else { return }
                        if self.model.effectiveProbeStatus == "PASS" && ["error","connection_warning"].contains(self.model.phase) && self.model.error==self.healthFailure { self.model.error="";self.model.phase="running" }
                        self.healthFailure=""
                    }
                }
            } catch { DispatchQueue.main.async {
                self.healthBusy=false
                guard !token.cancelled && !self.busy && self.running else { return }
                let message=self.model.redact(error.localizedDescription)
                if self.healthFailure != message { self.append(message) }
                self.healthFailure=message;self.model.error=message;self.model.phase="error"
                if (error as NSError).domain=="MINER.engineGone" { self.running=false }
            } }
        }
    }
    var updateArchitecture:String {
        #if arch(arm64)
        return "arm64"
        #else
        return "x86_64"
        #endif
    }
    @objc func manualCheckUpdate() { showSettings();checkUpdate() }
    @objc func checkUpdate() {
        guard !model.updateBusy && !busy else { return }
        if Bundle.main.object(forInfoDictionaryKey:"MINERPreview") as? Bool == true {
            model.updateAvailable=false
            model.updateMessage=model.tr("STRATA 시험판입니다. 새 프리뷰는 GitHub의 STRATA 릴리스에서 수동으로 설치하세요. 정식 ALPHA와 Homebrew는 자동 변경하지 않습니다.","STRATA preview: install new previews from GitHub. Stable ALPHA and Homebrew remain unchanged.")
            return
        }
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
            let command = "while /usr/bin/pgrep -x MINER >/dev/null; do /bin/sleep 1; done; " + shellQuote(brew) + " update && " + shellQuote(brew) + " upgrade --cask hexagon0401/miner/miner && " + shellQuote(brew) + " cleanup miner"
            let process = Process(); process.executableURL = URL(fileURLWithPath:"/usr/bin/osascript")
            process.arguments = ["-e","tell application \"Terminal\" to do script " + appleString(command)]
            do { try process.run(); NSApp.terminate(nil) } catch { model.updateMessage = error.localizedDescription }
            return
        }
        model.updateInstalling = true; model.updateBusy = true; model.updateMessage = model.tr("설치 파일 다운로드·SHA-256 검증 중…","Downloading and verifying the installer…")
        DispatchQueue.global(qos:.utility).async {
            do {
                let text = try self.execute(["update","download","--platform","macos","--arch",self.updateArchitecture,"--directory",self.dataDirectory.appendingPathComponent("Updates").path])
                let info = try JSONSerialization.jsonObject(with:Data(text.utf8)) as? [String:Any] ?? [:]
                guard info["verified"] as? Bool == true, let path = info["path"] as? String else { throw NSError(domain:identifier,code:1) }
                DispatchQueue.main.async {
                    self.startAppReplacement(path:path,info:info)
                }
            } catch { DispatchQueue.main.async { self.model.updateInstalling = false; self.model.updateBusy = false; self.model.updateMessage = self.model.redact(error.localizedDescription) } }
        }
    }
    func startAppReplacement(path:String,info:[String:Any]) {
        DispatchQueue.global(qos:.utility).async {
            do {
                guard let sha=info["sha256"] as? String,let target=info["version"] as? String else { throw NSError(domain:identifier,code:1) }
                let text=try self.execute(["update","prepare","--platform","macos","--arch",self.updateArchitecture,"--installer",path,"--sha256",sha,"--target-version",target,"--parent-pid",String(getpid())])
                let request=try JSONSerialization.jsonObject(with:Data(text.utf8)) as? [String:Any] ?? [:]
                guard request["started"] as? Bool == true else { throw NSError(domain:identifier,code:1) }
                DispatchQueue.main.async { self.model.updateInstalling=false;self.model.updateBusy=false;NSApp.terminate(nil) }
            } catch { DispatchQueue.main.async { self.model.updateInstalling=false;self.model.updateBusy=false;self.model.updateMessage=self.model.redact(error.localizedDescription) } }
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
            guard MinerInstallation.isInstalled() else { return }
            NSWorkspace.shared.recycle([Bundle.main.bundleURL]) { _, error in
                DispatchQueue.main.async {
                    if let error = error { self.append("서비스 제거 완료. 앱은 Finder에서 제거하세요: " + error.localizedDescription) }
                    else { NSApp.terminate(nil) }
                }
            }
        })
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if installationHandoffCompleted && !running && !managedWarp { return .terminateNow }
        if model.updateInstalling { return .terminateCancel }
        if busy {
            quitPending=true
            if operationReadOnly { return .terminateCancel }
            if model.phase != "stopping" { stopPending=true;model.phase="stopping";operationCancellation?.cancel() }
            window.makeKeyAndOrderFront(nil)
            return .terminateCancel
        }
        guard running || managedWarp || model.recoveryNeeded else { return .terminateNow }
        healthCancellation?.cancel()
        model.phase = "stopping";engineStoppedConfirmed=false; setBusy(true)
        DispatchQueue.global().async {
            do {
                _ = try self.stopEngine()
                DispatchQueue.main.async { self.running = false;self.engineStoppedConfirmed=true }
                _ = try self.execute(["warp", "restore"])
                DispatchQueue.main.async { self.managedWarp = false; self.model.restored = true;self.model.recoveryNeeded=false; NSApp.reply(toApplicationShouldTerminate:true) }
            } catch {
                DispatchQueue.main.async { self.setBusy(false); self.model.phase = "error"; self.model.error = self.model.redact(error.localizedDescription).replacingOccurrences(of:"MINER_SESSION_BLOCKED: ",with:""); self.append(error.localizedDescription); self.window.makeKeyAndOrderFront(nil)
                    if self.engineStoppedConfirmed {
                        let alert=NSAlert();alert.messageText=self.model.tr("MINER는 중지됐지만 WARP 복귀를 확인하지 못했습니다.","MINER stopped, but WARP restoration could not be confirmed.")
                        alert.informativeText=self.model.tr("앱을 종료한 뒤 WARP 앱에서 연결 상태를 확인할 수 있습니다.","You can quit and check the connection in the WARP app.")
                        alert.addButton(withTitle:self.model.tr("앱 종료","Quit app"));alert.addButton(withTitle:self.model.tr("계속 열기","Keep open"))
                        NSApp.reply(toApplicationShouldTerminate:alert.runModal() == .alertFirstButtonReturn)
                    } else { NSApp.reply(toApplicationShouldTerminate:false) } }
            }
        }
        return .terminateLater
    }
}

#if !STRATA_HEALTH_TESTS
@main struct MinerApplication {
    @MainActor static func main() {
        StartupTrace.record("process_started")
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        StartupTrace.record("delegate_retained")
        withExtendedLifetime(delegate) { app.run() }
    }
}

#endif
