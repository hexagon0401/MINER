import AppKit
import SwiftUI

// Native UI fixtures only. This entry point never starts WARP, the helper or TUN.
// Capture our own view tree, without reading the desktop or using screen recording.
private final class DeltaSmokeAudit {
    var check:Double = 0
    var blur:CGFloat = 0
    var frames:[String:CGRect] = [:]
    var sawSuccess = false
    func accept(_ check:Double,_ blur:CGFloat,_ frames:[String:CGRect]) {
        self.check = check; self.blur = blur; self.frames = frames
        if check > 0 { sawSuccess = true }
    }
}

extension AppDelegate {
    func runDeltaSmoke(output:URL,arch:String) {
        Task { @MainActor in
            var checks:[String] = []
            let audit = DeltaSmokeAudit()
            @MainActor func require(_ condition:Bool,_ message:String) throws {
                guard condition else { throw NSError(domain:"MINER.NativeUI",code:1,userInfo:[NSLocalizedDescriptionKey:message]) }
                checks.append(message)
            }
            @MainActor func settle(_ milliseconds:UInt64 = 160) async throws {
                try await Task.sleep(nanoseconds:milliseconds*1_000_000)
                self.window.contentView?.layoutSubtreeIfNeeded()
                self.window.displayIfNeeded()
            }
            @MainActor func install(reduced:Bool = false,highContrast:Bool = false) {
                let root = DeltaRoot(model:self.model,controller:self,visualAudit:audit.accept)
                    .environment(\.deltaAccessibility,DeltaAccessibility(reduceMotion:reduced,reduceTransparency:reduced,increasedContrast:highContrast))
                let backdrop = self.window.contentView!
                backdrop.subviews.forEach { $0.removeFromSuperview() }
                let host = NSHostingView(rootView:root)
                host.frame = backdrop.bounds; host.autoresizingMask = [.width,.height]
                backdrop.addSubview(host)
            }
            @MainActor func capture(_ name:String) throws {
                let view = self.window.contentView!
                guard let bitmap = view.bitmapImageRepForCachingDisplay(in:view.bounds) else {
                    throw NSError(domain:"MINER.NativeUI",code:2,userInfo:[NSLocalizedDescriptionKey:"Cannot render native view"])
                }
                view.cacheDisplay(in:view.bounds,to:bitmap)
                guard let png = bitmap.representation(using:.png,properties:[:]),png.count > 1000 else {
                    throw NSError(domain:"MINER.NativeUI",code:3,userInfo:[NSLocalizedDescriptionKey:"Empty native view render"])
                }
                try png.write(to:output.appendingPathComponent("miner-ui-\(arch)-\(name).png"))
            }
            do {
                try FileManager.default.createDirectory(at:output,withIntermediateDirectories:true)
                install()
                try await settle(300)
                try require(self.window.title == "MINER" && self.window.titleVisibility == .hidden,"MINER name and hidden native title")
                try require(self.window.titlebarAppearsTransparent && self.window.styleMask.contains(.fullSizeContentView),"Full-window native titlebar material")
                try require(self.window.frame.size == NSSize(width:560,height:610),"560x610 entire window")
                try require(self.window.minSize == NSSize(width:520,height:570),"520x570 minimum window")
                try require(self.window.isMovableByWindowBackground && self.window.styleMask.contains(.resizable),"Native drag and resize enabled")
                try require([NSWindow.ButtonType.closeButton,.miniaturizeButton,.zoomButton].allSatisfy { self.window.standardWindowButton($0) != nil },"Native traffic lights retained")
                try require(self.window.collectionBehavior.contains(.fullScreenNone),"No forced fullscreen")
                try require(MinerArt.images.values.allSatisfy { $0.isValid } && DeltaArt.images.values.allSatisfy { $0.isValid },"All original and Delta image assets loaded")
                try require(self.model.completed == 0 && audit.check == 0,"Idle has zero real ticks and no success check")
                let start = audit.frames["start"] ?? .zero
                let stop = audit.frames["stop"] ?? .zero
                try require(abs(start.minY-459)<2 && abs(start.width-340)<2 && abs(stop.minY-515)<2,"Measured Start and Stop placement matches spec")
                self.window.appearance = NSAppearance(named:.aqua)
                try await settle(); try capture("idle-light")
                self.window.appearance = NSAppearance(named:.darkAqua)
                try await settle(); try capture("idle-dark")
                self.window.setFrame(NSRect(origin:self.window.frame.origin,size:NSSize(width:520,height:570)),display:true)
                self.model.language = "en"
                try await settle(); try capture("minimum-english")
                let smallStop = audit.frames["stop"] ?? .zero
                try require(smallStop.maxY < 570 && smallStop.width >= 160,"Minimum-size controls remain visible")
                self.window.setFrame(NSRect(origin:self.window.frame.origin,size:NSSize(width:560,height:610)),display:true)
                self.model.language = "ko"; self.model.phase = "warp_ready"; self.model.warp = true; self.model.completed = 3
                try await settle(700); try capture("warp-only")
                try require(audit.check == 0 && !audit.sawSuccess && self.model.completed == 3,"WARP-only does not claim full-engine success")
                self.model.phase = "running"; self.model.engine = true; self.model.completed = 5
                try await settle(700); try capture("success")
                let success = audit.frames["success"] ?? .zero
                try require(abs(success.midX-280)<2 && abs(success.midY-305)<2,"Native check icon at exact entire-window center")
                try require(audit.check > 0 && audit.blur > 0 && audit.sawSuccess,"Verified running drives sharp check and background blur")
                try await settle(1050); try capture("restored")
                try require(audit.check == 0 && audit.blur == 0 && self.model.completed == 5,"Success restores normal content without changing ticks")
                self.model.phase = "stopped"; self.model.engine = false; self.model.completed = 0
                try await settle()
                self.model.phase = "running"; self.model.engine = true; self.model.completed = 5
                try await settle(450)
                self.model.phase = "stopping"
                try await settle(150); try capture("stop-interrupt")
                try require(audit.check == 0 && audit.blur == 0,"Stop cancels success within 180ms")
                self.model.engine = false; self.model.completed = 2; self.model.phase = "error"
                self.model.error = "WARP 프록시 연결을 확인하세요. 도구 → 상태·로그에서 원인을 확인할 수 있습니다."
                try await settle(300); try capture("error")
                try require(audit.check == 0 && audit.blur == 0 && self.model.detail == self.model.error,"Actionable error preserves real completed stage")
                self.model.phase = "idle"; self.model.completed = 0
                install(reduced:true,highContrast:true)
                try await settle()
                self.model.phase = "running"; self.model.engine = true; self.model.completed = 5
                try await settle(700); try capture("accessible-success")
                try require(audit.check > 0 && audit.blur == 0,"Reduce Motion retains check without blur")
                self.model.phase = "error"
                try await settle(150)
                try require(audit.check == 0 && audit.blur == 0,"Error cancels reduced-motion success")
                self.model.phase = "idle"; self.model.engine = false; self.model.completed = 0
                self.showSettings(); try await settle()
                try require(self.settingsWindow?.isVisible == true,"Native settings window opens")
                self.settingsWindow?.close()
                let result:[String:Any] = ["ok":true,"architecture":arch,"checks":checks,"network_actions":0]
                try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:output.appendingPathComponent("miner-ui-\(arch).json"))
                print("MINER native UI smoke passed: \(checks.count) checks")
                self.running = false; self.managedWarp = false
                NSApp.terminate(nil)
            } catch {
                let result:[String:Any] = ["ok":false,"architecture":arch,"checks":checks,"error":error.localizedDescription]
                try? JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:output.appendingPathComponent("miner-ui-\(arch).json"))
                fputs("MINER native UI smoke failed: \(error)\n",stderr)
                exit(1)
            }
        }
    }
}
