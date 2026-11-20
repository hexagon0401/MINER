import Foundation
import Darwin

final class CommandCancellation {
    private let lock=NSLock()
    private var stopped=false
    let session="\(Int(Date().timeIntervalSince1970))-\(UUID().uuidString.replacingOccurrences(of:"-",with:"").lowercased())"
    func cancel() {
        lock.lock();stopped=true;lock.unlock()
        let path="/tmp/.miner-cancel-\(getuid())-\(session)"
        let fd=Darwin.open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,mode_t(0o600))
        if fd>=0 { Darwin.close(fd) }
    }
    var cancelled:Bool { lock.lock(); defer { lock.unlock() }; return stopped }
}

// Read only available bytes; a grandchild inheriting stdout cannot hold the UI
// operation forever after its actual child has exited.
enum CommandRunner {
    static func run(_ executable:String,_ arguments:[String],timeout:TimeInterval,
                    cancellation:CommandCancellation?=nil,interruptible:Bool=true,onLine:((String)->Void)?=nil) throws -> String {
        let process=Process();process.executableURL=URL(fileURLWithPath:executable);process.arguments=arguments
        let pipe=Pipe();process.standardOutput=pipe;process.standardError=pipe
        let done=DispatchSemaphore(value:0)
        process.terminationHandler={ _ in done.signal() }
        let fd=pipe.fileHandleForReading.fileDescriptor
        _=fcntl(fd,F_SETFL,fcntl(fd,F_GETFL)|O_NONBLOCK)
        let queue=DispatchQueue(label:"MINER.command.output")
        var output=Data();var pending=Data()
        func drain() {
            var bytes=[UInt8](repeating:0,count:8192)
            for _ in 0..<16 {
                let count=Darwin.read(fd,&bytes,bytes.count)
                if count<=0 { break }
                let chunk=Data(bytes.prefix(count));output.append(chunk);pending.append(chunk)
                if output.count>131072 { output=Data(output.suffix(131072)) }
                while let end=pending.firstIndex(of:10) {
                    onLine?(String(decoding:pending.prefix(upTo:end),as:UTF8.self));pending.removeSubrange(...end)
                }
                if pending.count>8192 { pending=Data(pending.suffix(8192)) }
            }
        }
        let reader=DispatchSource.makeReadSource(fileDescriptor:fd,queue:queue)
        reader.setEventHandler { drain() }
        reader.setCancelHandler { try? pipe.fileHandleForReading.close() }
        reader.resume()
        defer { reader.cancel() }
        if cancellation?.cancelled == true { throw NSError(domain:"MINER.cancelled",code:1,userInfo:[NSLocalizedDescriptionKey:"연결 작업을 취소했습니다. / Connection cancelled."]) }
        try process.run();try? pipe.fileHandleForWriting.close()
        let deadline=Date().addingTimeInterval(timeout)
        var interrupted=false
        while done.wait(timeout:.now()+0.05) == .timedOut {
            if (interruptible && cancellation?.cancelled == true) || Date()>=deadline {
                interrupted=true
                if process.isRunning { process.terminate() }
                if done.wait(timeout:.now()+1) == .timedOut {
                    if process.isRunning { Darwin.kill(process.processIdentifier,SIGKILL) }
                    _=done.wait(timeout:.now()+1)
                }
                break
            }
        }
        queue.sync { drain() }
        if interrupted {
            let cancelled=cancellation?.cancelled == true
            throw NSError(domain:cancelled ? "MINER.cancelled":"MINER.timeout",code:1,userInfo:[NSLocalizedDescriptionKey:cancelled ? "연결 작업을 취소했습니다. / Connection cancelled.":"명령 응답 시간이 초과됐습니다. 중지 및 복구를 다시 시도하세요. / Command timed out; retry Stop and recovery."])
        }
        let text=String(decoding:output,as:UTF8.self)
        guard process.terminationStatus==0 else { throw NSError(domain:"MINER.command",code:Int(process.terminationStatus),userInfo:[NSLocalizedDescriptionKey:String(text.suffix(4000))]) }
        return text
    }
}
