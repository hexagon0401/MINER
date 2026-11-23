import AppKit
import CoreGraphics
import Foundation

@main struct LaunchInspector {
    @MainActor static func main() throws {
        let pid=pid_t(CommandLine.arguments[1])!
        guard let app=NSRunningApplication(processIdentifier:pid),!app.isTerminated else {
            print("{\"running\":false}");return
        }
        if CommandLine.arguments.contains("--quit") { _=app.terminate() }
        let windows=CGWindowListCopyWindowInfo([.optionOnScreenOnly,.excludeDesktopElements],kCGNullWindowID) as? [[String:Any]] ?? []
        let visible=windows.contains { entry in
            guard entry[kCGWindowOwnerPID as String] as? Int == Int(pid),entry[kCGWindowLayer as String] as? Int == 0,
                  let bounds=entry[kCGWindowBounds as String] as? [String:Any] else { return false }
            return (bounds["Width"] as? Double ?? 0)>=500 && (bounds["Height"] as? Double ?? 0)>=500
        }
        let value:[String:Any]=["running":true,"finished_launching":app.isFinishedLaunching,"visible_main_window":visible]
        print(String(data:try JSONSerialization.data(withJSONObject:value),encoding:.utf8)!)
    }
}
