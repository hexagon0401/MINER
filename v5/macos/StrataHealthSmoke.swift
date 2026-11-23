import Foundation
import AppKit
@main struct StrataHealthSmoke {
    @MainActor static func main() throws {
        let temp=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:temp,withIntermediateDirectories:true)
        defer { try? FileManager.default.removeItem(at:temp) }
        let installed=temp.appendingPathComponent("MINER.app"),duplicate=temp.appendingPathComponent("MINER 2.app"),alias=temp.appendingPathComponent("volume-alias")
        try FileManager.default.createDirectory(at:installed,withIntermediateDirectories:true)
        try FileManager.default.createDirectory(at:duplicate,withIntermediateDirectories:true)
        try FileManager.default.createSymbolicLink(at:alias,withDestinationURL:installed)
        assert(MinerInstallation.sameLocation(installed,alias))
        assert(!MinerInstallation.sameLocation(installed,duplicate))
        assert(!MinerInstallation.sameLocation(installed,temp.appendingPathComponent("missing")))
        let model=MinerModel();model.engine=true;model.probeRequest="r1";model.probeGeneration=1
        let event:[String:Any]=["event":"component_status","component":"riot_service","status":"FAIL","request_id":"r1","generation":1,"observed_at":Date().timeIntervalSince1970,"ttl_seconds":60,"reason_code":"RIOT_PROBE_FAILED"]
        model.accept(String(data:try JSONSerialization.data(withJSONObject:event),encoding:.utf8)!)
        RunLoop.current.run(until:Date().addingTimeInterval(0.05))
        assert(model.engine && model.effectiveProbeStatus=="FAIL")
        var stale=event;stale["request_id"]="old";stale["status"]="PASS"
        model.accept(String(data:try JSONSerialization.data(withJSONObject:stale),encoding:.utf8)!)
        RunLoop.current.run(until:Date().addingTimeInterval(0.05));assert(model.riotProbeStatus=="FAIL")
        model.probeObservedAt=Date().timeIntervalSince1970-100;assert(model.effectiveProbeStatus=="UNKNOWN")
        assert(!CommandRunner.userFailure("{\"event\":\"progress\",\"phase\":\"service_verify\"}\nRiot service check failed").contains("progress"))
        assert(!CommandRunner.userFailure("{\"event\":\"component_status\"}").contains("component_status"))
        print("STRATA G1: engine/probe separation, stale request, TTL and human error filtering passed; no network actions")
    }
}
