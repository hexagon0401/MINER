import Foundation
import Darwin

@main struct CommandSmoke {
    static func main() throws {
        let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
        defer { try? FileManager.default.removeItem(at:root) }
        var checks:[String]=[]
        let pid=root.appendingPathComponent("writer.pid")
        let begin=Date()
        let text=try CommandRunner.run("/bin/sh",["-c","sleep 30 & echo $! > '\(pid.path)'; echo complete"],timeout:2)
        assert(text.contains("complete") && Date().timeIntervalSince(begin)<2)
        if let value=try? String(contentsOf:pid),let child=Int32(value.trimmingCharacters(in:.whitespacesAndNewlines)) { Darwin.kill(child,SIGKILL) }
        checks.append("Inherited stdout does not keep an exited command alive")
        let timeoutStart=Date()
        do { _=try CommandRunner.run("/bin/sleep",["30"],timeout:0.15);fatalError("Missing timeout") }
        catch { assert((error as NSError).domain=="MINER.timeout") }
        assert(Date().timeIntervalSince(timeoutStart)<3)
        checks.append("Hung command terminates within a bounded deadline")
        let cancellation=CommandCancellation()
        DispatchQueue.global().asyncAfter(deadline:.now()+0.15) { cancellation.cancel() }
        do { _=try CommandRunner.run("/bin/sleep",["30"],timeout:30,cancellation:cancellation);fatalError("Missing cancellation") }
        catch { assert((error as NSError).domain=="MINER.cancelled") }
        checks.append("Cancel terminates the active operation")
        try? FileManager.default.removeItem(atPath:"/tmp/.miner-cancel-\(getuid())-\(cancellation.session)")
        let data:[String:Any]=["ok":true,"checks":checks]
        print(String(data:try JSONSerialization.data(withJSONObject:data),encoding:.utf8)!)
    }
}
