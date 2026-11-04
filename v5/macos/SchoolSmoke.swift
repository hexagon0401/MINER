import Foundation
import CryptoKit

// Fixture-only native checks: no WARP commands, Keychain writes or live reports.
enum SchoolSmoke {
    struct Vectors:Decodable {
        let testOnly:Bool
        let canonicalReport:String
        let report:SignedSchoolReport
        let snapshotPublicKey:String
        let snapshot:SignedSchoolSnapshot
        let olderSnapshot:SignedSchoolSnapshot
    }
    struct Result { let checks:[String];let directory:URL }
    static func run(fixture:URL,vectors vectorsURL:URL,output:URL) throws -> Result {
        var checks:[String] = []
        func expect(_ value:Bool,_ message:String) throws { guard value else { throw schoolError(message) };checks.append(message) }
        let directory = output.appendingPathComponent("school-fixture-" + UUID().uuidString)
        let local = try SchoolRepository.ownedURL(directory)
        let repo = try SchoolRepository(catalogURL:fixture,localURL:local,allowFixtures:true)
        try expect(repo.metadata.fixture && repo.available && repo.metadata.counts["high"] == 2,"School fixture is explicitly marked and has known official-ID counts")
        let duplicate = try repo.search(name:"테스트한빛",region:"",level:"")
        try expect(duplicate.count == 2 && duplicate[0].id != duplicate[1].id,"Duplicate names remain distinct schools")
        try expect(try repo.search(name:"테스트한빛".decomposedStringWithCanonicalMapping,region:"테스트서울",level:"high").count == 1,"Korean normalization and region/level filters")
        try expect(try repo.search(name:"%' OR 1=1--",region:"",level:"").isEmpty,"School search safely binds special characters")
        let vectors = try JSONDecoder().decode(Vectors.self,from:Data(contentsOf:vectorsURL))
        let canonical = try SchoolCrypto.canonical(vectors.report.payload)
        try expect(vectors.testOnly && String(decoding:canonical,as:UTF8.self) == vectors.canonicalReport,"Swift and Worker canonical report bytes match")
        let publicKey = try P256.Signing.PublicKey(x963Representation:SchoolCrypto.decoded(vectors.report.publicKey))
        let signature = try P256.Signing.ECDSASignature(rawRepresentation:SchoolCrypto.decoded(vectors.report.signature))
        try expect(publicKey.isValidSignature(signature,for:canonical),"Worker/Node P256 raw signature verifies in CryptoKit")
        try repo.save(vectors.report);try repo.save(vectors.report)
        var flags = try repo.localFlags()
        try expect(flags["TEST:H1"]?.green == true && flags["TEST:H1"]?.stale == true,"Old local success remains green with 90-day stale marker")
        try expect(try repo.counts(flags)["high"] == 1,"Repeated report does not double-count a school")
        let key = P256.Signing.PrivateKey()
        let source = vectors.report.payload
        let second = SchoolReportBody(id:UUID().uuidString.lowercased(),schoolId:source.schoolId,catalogVersion:source.catalogVersion,diagnosedAt:SchoolDates.string(Date()),appVersion:source.appVersion,osMajor:source.osMajor,checks:source.checks,schoolNetworkConfirmed:true,clientConfirmed:true,game:"not_tested",video:"not_tested",clientReturn:"not_tested",outcome:"success",failureCode:nil)
        try repo.save(SchoolCrypto.sign(second,key:key))
        try expect(try repo.counts(repo.localFlags())["high"] == 1,"Two successful reports still count one school")
        let failure = SchoolReportBody(id:UUID().uuidString.lowercased(),schoolId:source.schoolId,catalogVersion:source.catalogVersion,diagnosedAt:SchoolDates.string(Date()),appVersion:source.appVersion,osMajor:source.osMajor,checks:source.checks,schoolNetworkConfirmed:true,clientConfirmed:false,game:"fail",video:"not_tested",clientReturn:"not_tested",outcome:"failure",failureCode:nil)
        try repo.save(SchoolCrypto.sign(failure,key:key));flags = try repo.localFlags()
        try expect(flags["TEST:H1"]?.green == true && flags["TEST:H1"]?.lastFailure != nil,"Recent failure does not erase historical success")
        var corrupt = try JSONSerialization.jsonObject(with:SchoolCrypto.canonical(vectors.report)) as! [String:Any]
        var body = corrupt["payload"] as! [String:Any];body["schoolId"] = "TEST:M1";corrupt["payload"] = body
        let forged = try JSONDecoder().decode(SignedSchoolReport.self,from:JSONSerialization.data(withJSONObject:corrupt))
        var rejected = false
        do { try repo.save(forged) } catch { rejected = true }
        try expect(rejected,"Tampered local report rejected")
        let exported = try repo.export(source.id)
        let object = try JSONSerialization.jsonObject(with:exported) as! [String:Any]
        let payload = object["payload"] as! [String:Any]
        try expect(payload["failureCode"] is NSNull && payload["challenge"] is NSNull,"Export includes explicit null wire fields")
        try expect(payload["ssid"] == nil && payload["ip"] == nil && payload["logs"] == nil,"Report export excludes SSID, IP and raw logs")
        let snapshotData = try JSONSerialization.data(withJSONObject:["payload":vectors.snapshot.payload,"signature":vectors.snapshot.signature])
        let snapshotKey = try SchoolCrypto.decoded(vectors.snapshotPublicKey)
        let snapshot = try repo.installSnapshot(snapshotData,publicKey:snapshotKey)
        try expect(snapshot.counts["high"] == 1 && snapshot.sequence == 2,"Signed Ed25519 community snapshot verifies separately from local reports")
        let older = try JSONSerialization.data(withJSONObject:["payload":vectors.olderSnapshot.payload,"signature":vectors.olderSnapshot.signature])
        rejected = false;do { _ = try repo.installSnapshot(older,publicKey:snapshotKey) } catch { rejected = true }
        try expect(rejected && (try repo.cachedSnapshot(publicKey:snapshotKey))?.sequence == 2,"Snapshot rollback rejected and last good cache preserved")
        let upload = try SchoolCrypto.canonical(vectors.report)
        try repo.prepareUpload(source.id,data:upload);try repo.prepareUpload(source.id,data:upload)
        try expect(try repo.pendingUpload(source.id) == upload,"Exact pending upload envelope survives retry")
        try exported.write(to:output.appendingPathComponent("miner-school-native-report.json"))
        return Result(checks:checks,directory:directory)
    }
}
