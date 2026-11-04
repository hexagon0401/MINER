import AppKit

let applicationName = "SchoolNet v5 Alpha"
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
    var output: NSTextView!
    var buttons: [NSButton] = []
    var running = false
    var busy = false
    let resources = Bundle.main.resourceURL!
    let dataDirectory = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/SchoolNet v5 Alpha")
    var cli: String { resources.appendingPathComponent("runtime/schoolnet-cli/schoolnet-cli").path }
    var engine: String { resources.appendingPathComponent("bin/sing-box").path }

    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 660, height: 560),
                          styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = applicationName
        window.center()
        window.isReleasedWhenClosed = false
        let content = window.contentView!
        let heading = NSTextField(labelWithString: "SchoolNet v5 · Alpha")
        heading.font = .boldSystemFont(ofSize: 24)
        heading.frame = NSRect(x: 24, y: 500, width: 600, height: 34)
        content.addSubview(heading)
        let description = NSTextField(wrappingLabelWithString:
            "‘시작’ 또는 ‘WARP 자동 연결’로 Local Proxy를 설정·검증합니다.\n클라이언트와 웹 콘텐츠는 WARP, 게임 데이터는 직접 연결합니다. 최초 전환은 게임 밖에서 진행하세요.")
        description.frame = NSRect(x: 24, y: 430, width: 610, height: 60)
        content.addSubview(description)
        let specs: [(String, Selector)] = [
            ("WARP 자동 연결", #selector(connectWarp)), ("사전 점검", #selector(check)),
            ("시작", #selector(start)), ("중지", #selector(stop)),
            ("상태 확인", #selector(refresh)), ("로그 열기", #selector(openLog)),
            ("사용 안내", #selector(openGuide)), ("제거", #selector(uninstall)),
            ("WARP 연결 확인", #selector(checkWarp)), ("WARP 끄기", #selector(disconnectWarp))
        ]
        for (index, spec) in specs.enumerated() {
            let button = NSButton(title: spec.0, target: self, action: spec.1)
            button.frame = NSRect(x: 24 + (index % 4) * 154, y: 385 - (index / 4) * 40, width: 144, height: 32)
            button.bezelStyle = .rounded
            buttons.append(button)
            content.addSubview(button)
        }
        let scroll = NSScrollView(frame: NSRect(x: 24, y: 24, width: 612, height: 242))
        scroll.hasVerticalScroller = true
        scroll.borderType = .bezelBorder
        output = NSTextView(frame: scroll.bounds)
        output.isEditable = false
        output.font = .monospacedSystemFont(ofSize: 12, weight: .regular)
        scroll.documentView = output
        content.addSubview(scroll)
        let menu = NSMenu()
        let item = NSMenuItem()
        menu.addItem(item)
        let submenu = NSMenu()
        submenu.addItem(withTitle: "종료", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        item.submenu = submenu
        NSApp.mainMenu = menu
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        append("Alpha: macOS 27.1.1에서 학교 연결·게임 핑·종료 복구는 실기 확인이 필요합니다.")
        refresh()
    }

    func append(_ text: String) {
        output.string += text + "\n"
        output.scrollToEndOfDocument(nil)
    }

    func setBusy(_ value: Bool) {
        busy = value
        buttons.forEach { $0.isEnabled = !value }
    }

    func execute(_ arguments: [String], administrator: Bool = false) throws -> String {
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
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        let text = String(data: data, encoding: .utf8) ?? ""
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
        guard !busy else { return }
        setBusy(true)
        DispatchQueue.global(qos: .userInitiated).async {
            let result: Result<String, Error> = Result { try work() }
            DispatchQueue.main.async {
                self.setBusy(false)
                switch result {
                case .success(let text): self.append(text); completion?()
                case .failure(let error): self.append("실패: " + error.localizedDescription)
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
        return ["warp", operation, "--proxy-port", String(port)]
    }
    @objc func connectWarp() {
        operation { try self.execute(self.warpArguments("connect")) }
    }
    @objc func checkWarp() {
        operation { try self.execute(self.warpArguments("status")) }
    }
    @objc func disconnectWarp() {
        let alert = NSAlert()
        alert.messageText = "v5를 중지하고 WARP 연결을 끌까요?"
        alert.informativeText = "클라이언트 연결이 끊길 수 있습니다. 전체 터널이나 직접 연결로 자동 전환하지 않습니다."
        alert.addButton(withTitle: "중지하고 끄기")
        alert.addButton(withTitle: "취소")
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
        guard Bundle.main.bundleURL.path == "/Applications/SchoolNet v5 Alpha.app" else {
            append("DMG에서 앱을 Applications로 복사한 뒤 그 앱을 실행하세요."); return
        }
        operation({
            try self.ensureProfile()
            _ = try self.execute(self.warpArguments("connect"))
            return try self.execute(["desktop", "start", "--resources", self.resources.path,
                                     "--profile", self.dataDirectory.path], administrator: true)
        }, completion: { self.running = true; self.append("실행 프로세스가 시작됐습니다. 로그에서 클라이언트 warp / 게임 direct를 확인하세요.") })
    }
    @objc func stop() {
        operation({ try self.execute(["desktop", "stop"], administrator: true) },
                  completion: { self.running = false })
    }
    @objc func refresh() {
        operation {
            let text = try self.execute(["desktop", "status"])
            if let data = text.data(using: .utf8),
               let info = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                DispatchQueue.main.async { self.running = info["running"] as? Bool ?? false }
            }
            return text
        }
    }
    @objc func uninstall() {
        let alert = NSAlert()
        alert.messageText = "SchoolNet v5 Alpha를 제거할까요?"
        alert.informativeText = "실행을 중지하고 v5의 서비스·설정·로그를 제거한 뒤 앱을 휴지통으로 옮깁니다. WARP와 기존 v1~v4는 유지합니다."
        alert.addButton(withTitle: "제거")
        alert.addButton(withTitle: "취소")
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        operation({
            let result = try self.execute(["desktop", "uninstall"], administrator: true)
            let marker = self.dataDirectory.appendingPathComponent(".managed.json")
            if let data = try? Data(contentsOf: marker),
               let owner = try? JSONSerialization.jsonObject(with: data) as? [String: String], owner["id"] == identifier {
                try FileManager.default.removeItem(at: self.dataDirectory)
            }
            return result
        }, completion: {
            self.running = false
            guard Bundle.main.bundleURL.path == "/Applications/SchoolNet v5 Alpha.app" else { return }
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
        if busy { return .terminateCancel }
        guard running else { return .terminateNow }
        let alert = NSAlert()
        alert.messageText = "연결을 중지하고 종료할까요?"
        alert.addButton(withTitle: "중지 후 종료")
        alert.addButton(withTitle: "취소")
        guard alert.runModal() == .alertFirstButtonReturn else { return .terminateCancel }
        setBusy(true)
        DispatchQueue.global().async {
            do {
                _ = try self.execute(["desktop", "stop"], administrator: true)
                DispatchQueue.main.async { self.running = false; NSApp.reply(toApplicationShouldTerminate: true) }
            } catch {
                DispatchQueue.main.async { self.setBusy(false); self.append(error.localizedDescription); NSApp.reply(toApplicationShouldTerminate: false) }
            }
        }
        return .terminateLater
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
