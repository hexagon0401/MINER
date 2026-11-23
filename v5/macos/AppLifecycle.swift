import AppKit
import Foundation

enum MinerInstallation {
    static let installedURL=URL(fileURLWithPath:"/Applications/MINER.app",isDirectory:true)
    static func sameLocation(_ first:URL,_ second:URL) -> Bool {
        let a=first.standardizedFileURL.resolvingSymlinksInPath()
        let b=second.standardizedFileURL.resolvingSymlinksInPath()
        guard let left=try? FileManager.default.attributesOfItem(atPath:a.path),
              let right=try? FileManager.default.attributesOfItem(atPath:b.path),
              let leftVolume=left[.systemNumber] as? NSNumber,let rightVolume=right[.systemNumber] as? NSNumber,
              let leftFile=left[.systemFileNumber] as? NSNumber,let rightFile=right[.systemFileNumber] as? NSNumber else { return false }
        return leftVolume == rightVolume && leftFile == rightFile
    }
    static func isInstalled(_ url:URL=Bundle.main.bundleURL) -> Bool { sameLocation(url,installedURL) }
    static func kind(_ url:URL=Bundle.main.bundleURL) -> String {
        if isInstalled(url) { return "system_applications" }
        let path=url.standardizedFileURL.path
        if path.contains("/AppTranslocation/") { return "translocated" }
        if path.hasPrefix("/Volumes/") { return "mounted_volume" }
        if path.hasPrefix(FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Applications").path+"/") { return "user_applications" }
        return "other_copy"
    }
    static func compatibleInstalledBundle() -> Bundle? {
        guard let installed=Bundle(url:installedURL),installed.bundleIdentifier == identifier,
              installed.object(forInfoDictionaryKey:"CFBundleExecutable") as? String == "MINER",
              let ownBuild=Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String,
              installed.object(forInfoDictionaryKey:"CFBundleVersion") as? String == ownBuild else { return nil }
        return installed
    }
}

enum StartupTrace {
    private static let queue=DispatchQueue(label:"MINER.startup.trace")
    private static var initialized=false
    static func record(_ stage:String) {
        // Fixed stages/category only; no paths, account data or network state.
        let value:[String:Any]=["stage":stage,"at":Date().timeIntervalSince1970,"pid":ProcessInfo.processInfo.processIdentifier,
                                "installation_kind":MinerInstallation.kind()]
        guard let bytes=try? JSONSerialization.data(withJSONObject:value),var line=String(data:bytes,encoding:.utf8) else { return }
        line += "\n"
        let encoded=Data(line.utf8)
        if let data=line.data(using:.utf8) { try? FileHandle.standardError.write(contentsOf:data) }
        queue.async {
            let args=CommandLine.arguments
            let url:URL
            if let index=args.firstIndex(of:"--startup-log"),args.count>index+1 { url=URL(fileURLWithPath:args[index+1]) }
            else { url=FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/MINER/startup.jsonl") }
            do {
                try FileManager.default.createDirectory(at:url.deletingLastPathComponent(),withIntermediateDirectories:true)
                if !initialized {
                    if FileManager.default.fileExists(atPath:url.path) {
                        let previous=url.appendingPathExtension("previous")
                        try? FileManager.default.removeItem(at:previous)
                        try FileManager.default.moveItem(at:url,to:previous)
                    }
                    FileManager.default.createFile(atPath:url.path,contents:nil,attributes:[.posixPermissions:0o600]);initialized=true
                }
                guard let handle=try? FileHandle(forWritingTo:url) else { return }
                defer { try? handle.close() }
                if try handle.seekToEnd()<65536 { try handle.write(contentsOf:encoded) }
            } catch { /* Startup diagnostics must never prevent app launch. */ }
        }
    }
}
