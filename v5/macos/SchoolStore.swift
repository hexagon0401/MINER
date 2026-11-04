import Foundation
import SQLite3
import CryptoKit
import Security

struct SchoolRecord:Identifiable,Codable {
    let id:String
    let name:String
    let level:String
    let province:String
    let district:String
    let address:String
    var region:String { province + (district.isEmpty ? "" : " · " + district) }
}
struct SchoolCatalogMetadata:Decodable {
    let complete:Bool
    let fixture:Bool
    let catalog_version:String
    let as_of:String
    let source_url:String
    let attribution:String
    let counts:[String:Int]
    static let missing = SchoolCatalogMetadata(complete:false,fixture:false,catalog_version:"",as_of:"",source_url:"https://open.neis.go.kr/",attribution:"교육부·시도교육청 / NEIS",counts:[:])
}
struct SchoolFlag {
    var lastSuccess:String?
    var lastFailure:String?
    var green:Bool { lastSuccess != nil }
    var stale:Bool {
        guard let lastSuccess = lastSuccess, let date = SchoolDates.parse(lastSuccess) else { return false }
        return Date().timeIntervalSince(date) > 90*86400
    }
}
enum SchoolDates {
    static func string(_ date:Date) -> String {
        let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime]
        return f.string(from:date)
    }
    static func parse(_ string:String) -> Date? {
        let f = ISO8601DateFormatter(); f.formatOptions = string.count == 10 ? [.withFullDate] : [.withInternetDateTime]
        return f.date(from:string)
    }
}
struct SchoolChecks:Codable {
    let engine_running:Bool
    let native_platform:Bool
    let engine_schema:Bool
    let warp_local_proxy_mode:Bool
    let socks5_greeting:Bool
    let warp_trace:Bool
    var passed:Bool { engine_running && native_platform && engine_schema && warp_local_proxy_mode && socks5_greeting && warp_trace }
    static let failed = SchoolChecks(engine_running:false,native_platform:false,engine_schema:false,warp_local_proxy_mode:false,socks5_greeting:false,warp_trace:false)
}
struct SchoolDiagnostic:Decodable {
    let schemaVersion:Int
    let passed:Bool
    let checks:SchoolChecks
    let failureCode:String?
}
struct SchoolChallenge:Codable { let id:String; let nonce:String }
struct SchoolReportBody:Codable {
    var schemaVersion = 1
    let id:String
    let schoolId:String
    let catalogVersion:String
    let diagnosedAt:String
    let appVersion:String
    let osMajor:Int
    let checks:SchoolChecks
    let schoolNetworkConfirmed:Bool
    let clientConfirmed:Bool
    let game:String
    let video:String
    let clientReturn:String
    let outcome:String
    let failureCode:String?
    var challenge:SchoolChallenge? = nil
    enum CodingKeys:String,CodingKey {
        case schemaVersion,id,schoolId,catalogVersion,diagnosedAt,appVersion,osMajor,checks,schoolNetworkConfirmed,clientConfirmed,game,video,clientReturn,outcome,failureCode,challenge
    }
    func encode(to encoder:Encoder) throws {
        var c = encoder.container(keyedBy:CodingKeys.self)
        try c.encode(schemaVersion,forKey:.schemaVersion); try c.encode(id,forKey:.id)
        try c.encode(schoolId,forKey:.schoolId); try c.encode(catalogVersion,forKey:.catalogVersion)
        try c.encode(diagnosedAt,forKey:.diagnosedAt); try c.encode(appVersion,forKey:.appVersion)
        try c.encode(osMajor,forKey:.osMajor); try c.encode(checks,forKey:.checks)
        try c.encode(schoolNetworkConfirmed,forKey:.schoolNetworkConfirmed); try c.encode(clientConfirmed,forKey:.clientConfirmed)
        try c.encode(game,forKey:.game); try c.encode(video,forKey:.video); try c.encode(clientReturn,forKey:.clientReturn)
        try c.encode(outcome,forKey:.outcome)
        // Explicit nulls are part of the signed wire contract, not missing keys.
        try c.encode(failureCode,forKey:.failureCode); try c.encode(challenge,forKey:.challenge)
    }
}
struct SignedSchoolReport:Codable { let payload:SchoolReportBody; let publicKey:String; let signature:String }
struct SchoolSnapshot:Decodable {
    struct Entry:Decodable { let schoolId:String; let lastSuccessDay:String?; let lastFailureDay:String? }
    let schemaVersion:Int
    let catalogVersion:String
    let sequence:Int
    let generatedAt:String
    let counts:[String:Int]
    let schools:[Entry]
}
struct SignedSchoolSnapshot:Decodable { let payload:String; let signature:String }

func schoolError(_ message:String) -> NSError { NSError(domain:"MINER.Schools",code:1,userInfo:[NSLocalizedDescriptionKey:message]) }

enum SchoolCrypto {
    static let service = "org.schoolnet.v5.alpha.community"
    static let account = "report-signing-v1"
    static func encoded(_ data:Data) -> String { data.base64EncodedString().replacingOccurrences(of:"+",with:"-").replacingOccurrences(of:"/",with:"_").replacingOccurrences(of:"=",with:"") }
    static func decoded(_ string:String) throws -> Data {
        guard string.range(of:"^[A-Za-z0-9_-]+$",options:.regularExpression) != nil else { throw schoolError("Invalid signed data encoding") }
        let value = string.replacingOccurrences(of:"-",with:"+").replacingOccurrences(of:"_",with:"/")
        guard let data = Data(base64Encoded:value + String(repeating:"=",count:(4-value.count%4)%4)) else { throw schoolError("Invalid signed data encoding") }
        return data
    }
    static func canonical<T:Encodable>(_ value:T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys,.withoutEscapingSlashes]
        return try encoder.encode(value)
    }
    static func key() throws -> P256.Signing.PrivateKey {
        let query:[String:Any] = [kSecClass as String:kSecClassGenericPassword,kSecAttrService as String:service,kSecAttrAccount as String:account,kSecReturnData as String:true]
        var result:CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary,&result)
        if status == errSecSuccess, let data = result as? Data { return try P256.Signing.PrivateKey(rawRepresentation:data) }
        guard status == errSecItemNotFound else { throw schoolError("Keychain access failed (\(status))") }
        let key = P256.Signing.PrivateKey()
        let item:[String:Any] = [kSecClass as String:kSecClassGenericPassword,kSecAttrService as String:service,kSecAttrAccount as String:account,kSecValueData as String:key.rawRepresentation,kSecAttrAccessible as String:kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]
        let added = SecItemAdd(item as CFDictionary,nil)
        guard added == errSecSuccess else { throw schoolError("Could not save report signing key (\(added))") }
        return key
    }
    static func removeKey() throws {
        let item:[String:Any] = [kSecClass as String:kSecClassGenericPassword,kSecAttrService as String:service,kSecAttrAccount as String:account]
        let result = SecItemDelete(item as CFDictionary)
        guard result == errSecSuccess || result == errSecItemNotFound else { throw schoolError("Could not remove report key (\(result))") }
    }
    static func sign(_ body:SchoolReportBody,key:P256.Signing.PrivateKey) throws -> SignedSchoolReport {
        let data = try canonical(body)
        return SignedSchoolReport(payload:body,publicKey:encoded(key.publicKey.x963Representation),signature:encoded(try key.signature(for:data).rawRepresentation))
    }
}

private final class SchoolDatabase {
    private var handle:OpaquePointer?
    init(_ url:URL,readOnly:Bool) throws {
        let flags = (readOnly ? SQLITE_OPEN_READONLY : SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE)|SQLITE_OPEN_FULLMUTEX
        guard sqlite3_open_v2(url.path,&handle,flags,nil) == SQLITE_OK else {
            if let handle = handle { sqlite3_close(handle) }; handle = nil
            throw schoolError("Could not open school data")
        }
        sqlite3_busy_timeout(handle,3000)
    }
    deinit { sqlite3_close(handle) }
    func script(_ sql:String) throws {
        guard sqlite3_exec(handle,sql,nil,nil,nil) == SQLITE_OK else { throw schoolError(String(cString:sqlite3_errmsg(handle))) }
    }
    func rows(_ sql:String,_ parameters:[String] = []) throws -> [[String:String]] {
        var statement:OpaquePointer?
        guard sqlite3_prepare_v2(handle,sql,-1,&statement,nil) == SQLITE_OK else { throw schoolError("School query could not be prepared") }
        defer { sqlite3_finalize(statement) }
        let transient = unsafeBitCast(-1,to:sqlite3_destructor_type.self)
        for (index,value) in parameters.enumerated() {
            guard sqlite3_bind_text(statement,Int32(index+1),value,-1,transient) == SQLITE_OK else { throw schoolError("School query binding failed") }
        }
        var rows:[[String:String]] = []
        while true {
            let result = sqlite3_step(statement)
            if result == SQLITE_DONE { break }
            guard result == SQLITE_ROW else { throw schoolError(String(cString:sqlite3_errmsg(handle))) }
            var row:[String:String] = [:]
            for col in 0..<sqlite3_column_count(statement) {
                if let value = sqlite3_column_text(statement,col) { row[String(cString:sqlite3_column_name(statement,col))] = String(cString:value) }
            }
            rows.append(row)
        }
        return rows
    }
}

final class SchoolRepository {
    let metadata:SchoolCatalogMetadata
    let available:Bool
    private let catalog:SchoolDatabase
    private let local:SchoolDatabase
    private let allowFixtures:Bool
    init(catalogURL:URL,localURL:URL,allowFixtures:Bool = false) throws {
        self.allowFixtures = allowFixtures
        catalog = try SchoolDatabase(catalogURL,readOnly:true)
        let rows = try catalog.rows("SELECT key,value FROM catalog_meta")
        var values:[String:Any] = [:]
        for row in rows {
            if let key = row["key"],let value = row["value"],let data = value.data(using:.utf8) { values[key] = try JSONSerialization.jsonObject(with:data,options:.fragmentsAllowed) }
        }
        metadata = try JSONDecoder().decode(SchoolCatalogMetadata.self,from:JSONSerialization.data(withJSONObject:values))
        available = metadata.complete && (!metadata.fixture || allowFixtures)
        local = try SchoolDatabase(localURL,readOnly:false)
        let version = try local.rows("PRAGMA user_version").first?["user_version"] ?? "0"
        guard version == "0" || version == "1" else { throw schoolError("Newer community database preserved; this app cannot modify it") }
        try local.script("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS local_reports(id TEXT PRIMARY KEY,school_id TEXT NOT NULL,catalog_version TEXT NOT NULL,diagnosed_at TEXT NOT NULL,outcome TEXT NOT NULL,envelope TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS local_school_flags ON local_reports(school_id,outcome,diagnosed_at);
        CREATE TABLE IF NOT EXISTS local_uploads(id TEXT PRIMARY KEY,envelope TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS public_snapshot(id INTEGER PRIMARY KEY CHECK(id=1),sequence INTEGER NOT NULL,envelope TEXT NOT NULL);
        PRAGMA user_version=1;
        """)
    }
    static func ownedURL(_ directory:URL) throws -> URL {
        let fm = FileManager.default
        let marker = directory.appendingPathComponent(".managed.json")
        if fm.fileExists(atPath:directory.path) {
            let data = try Data(contentsOf:marker)
            guard let object = try JSONSerialization.jsonObject(with:data) as? [String:String],object["id"] == identifier else { throw schoolError("Unowned settings directory preserved") }
        } else {
            try fm.createDirectory(at:directory,withIntermediateDirectories:true)
            try JSONSerialization.data(withJSONObject:["id":identifier]).write(to:marker,options:.atomic)
        }
        let url = directory.appendingPathComponent("community.sqlite3")
        if (try? url.resourceValues(forKeys:[.isSymbolicLinkKey]).isSymbolicLink) == true { throw schoolError("Community database must not be a symbolic link") }
        return url
    }
    private func record(_ row:[String:String]) -> SchoolRecord {
        SchoolRecord(id:row["id"]!,name:row["name"]!,level:row["level"]!,province:row["province"]!,district:row["district"]!,address:row["address"]!)
    }
    func school(_ id:String) throws -> SchoolRecord? {
        guard available,let row = try catalog.rows("SELECT * FROM schools WHERE id=? AND active=1",[id]).first else { return nil }
        return record(row)
    }
    static func searchKey(_ text:String) -> String { text.precomposedStringWithCanonicalMapping.lowercased().filter { !$0.isWhitespace } }
    private func like(_ text:String) -> String { "%" + Self.searchKey(text).replacingOccurrences(of:"\\",with:"\\\\").replacingOccurrences(of:"%",with:"\\%").replacingOccurrences(of:"_",with:"\\_") + "%" }
    func search(name:String,region:String,level:String,offset:Int = 0,greenIDs:Set<String> = [],onlyGreen:Bool? = nil) throws -> [SchoolRecord] {
        guard available else { return [] }
        let sql = "SELECT * FROM schools WHERE active=1 AND search_name LIKE ? ESCAPE '\\' AND search_region LIKE ? ESCAPE '\\' AND (?='' OR level=?) ORDER BY province,district,name,id"
        if let onlyGreen = onlyGreen {
            let candidates = try catalog.rows(sql,[like(name),like(region),level,level]).map(record)
            return Array(candidates.filter { greenIDs.contains($0.id) == onlyGreen }.dropFirst(max(0,offset)).prefix(100))
        }
        return try catalog.rows(sql + " LIMIT 100 OFFSET ?",[like(name),like(region),level,level,String(max(0,offset))]).map(record)
    }
    func localFlags() throws -> [String:SchoolFlag] {
        let rows = try local.rows("SELECT school_id,MAX(CASE WHEN outcome='success' THEN diagnosed_at END) AS success,MAX(CASE WHEN outcome='failure' THEN diagnosed_at END) AS failure FROM local_reports GROUP BY school_id")
        return Dictionary(uniqueKeysWithValues:rows.map { ($0["school_id"]!,SchoolFlag(lastSuccess:$0["success"],lastFailure:$0["failure"])) })
    }
    func counts(_ flags:[String:SchoolFlag]) throws -> [String:Int] {
        var counts = ["high":0,"middle":0,"elementary":0]
        for (id,flag) in flags where flag.green { if let school = try school(id) { counts[school.level,default:0] += 1 } }
        return counts
    }
    func save(_ report:SignedSchoolReport) throws {
        let p = report.payload
        guard p.schemaVersion == 1,p.catalogVersion == metadata.catalog_version,try school(p.schoolId) != nil else { throw schoolError("Catalog changed; select your school again") }
        let data = try SchoolCrypto.canonical(report)
        let key = try P256.Signing.PublicKey(x963Representation:SchoolCrypto.decoded(report.publicKey))
        let signature = try P256.Signing.ECDSASignature(rawRepresentation:SchoolCrypto.decoded(report.signature))
        guard key.isValidSignature(signature,for:try SchoolCrypto.canonical(p)) else { throw schoolError("Invalid local report signature") }
        let success = p.checks.passed && p.schoolNetworkConfirmed && p.clientConfirmed && p.failureCode == nil
        guard p.outcome == (success ? "success" : "failure"),[p.game,p.video,p.clientReturn].allSatisfy({["pass","fail","not_tested"].contains($0)}) else { throw schoolError("Invalid report outcome") }
        guard let at = SchoolDates.parse(p.diagnosedAt),at <= Date().addingTimeInterval(30) else { throw schoolError("Invalid report date") }
        let text = String(decoding:data,as:UTF8.self)
        if let old = try local.rows("SELECT envelope FROM local_reports WHERE id=?",[p.id]).first {
            guard old["envelope"] == text else { throw schoolError("Conflicting report ID") }; return
        }
        _ = try local.rows("INSERT INTO local_reports VALUES(?,?,?,?,?,?)",[p.id,p.schoolId,p.catalogVersion,p.diagnosedAt,p.outcome,text])
    }
    func latestReport(schoolID:String) throws -> SignedSchoolReport? {
        guard let raw = try local.rows("SELECT envelope FROM local_reports WHERE school_id=? ORDER BY diagnosed_at DESC,id DESC LIMIT 1",[schoolID]).first?["envelope"] else { return nil }
        return try JSONDecoder().decode(SignedSchoolReport.self,from:Data(raw.utf8))
    }
    func export(_ id:String) throws -> Data {
        guard let text = try local.rows("SELECT envelope FROM local_reports WHERE id=?",[id]).first?["envelope"],let data = text.data(using:.utf8) else { throw schoolError("Local report not found") }
        return data
    }
    func pendingUpload(_ id:String) throws -> Data? {
        guard let raw = try local.rows("SELECT envelope FROM local_uploads WHERE id=?",[id]).first?["envelope"] else { return nil }
        return Data(raw.utf8)
    }
    func prepareUpload(_ id:String,data:Data) throws {
        let raw = String(decoding:data,as:UTF8.self)
        if let old = try pendingUpload(id) { guard old == data else { throw schoolError("Upload envelope already exists") };return }
        _ = try local.rows("INSERT INTO local_uploads VALUES(?,?)",[id,raw])
    }
    func installSnapshot(_ data:Data,publicKey:Data) throws -> SchoolSnapshot {
        guard data.count <= 8*1024*1024 else { throw schoolError("Snapshot is too large") }
        let signed = try JSONDecoder().decode(SignedSchoolSnapshot.self,from:data)
        let payload = try SchoolCrypto.decoded(signed.payload)
        let key = try Curve25519.Signing.PublicKey(rawRepresentation:publicKey)
        guard key.isValidSignature(try SchoolCrypto.decoded(signed.signature),for:payload) else { throw schoolError("Untrusted community snapshot") }
        let snapshot = try JSONDecoder().decode(SchoolSnapshot.self,from:payload)
        guard snapshot.schemaVersion == 1,snapshot.catalogVersion == metadata.catalog_version,snapshot.sequence >= 0 else { throw schoolError("Snapshot/catalog version mismatch") }
        let previous = Int(try local.rows("SELECT sequence FROM public_snapshot WHERE id=1").first?["sequence"] ?? "-1") ?? -1
        guard snapshot.sequence >= previous else { throw schoolError("Older snapshot rejected; cached data preserved") }
        var ids = Set<String>(); var counts = ["high":0,"middle":0,"elementary":0]
        for entry in snapshot.schools {
            guard ids.insert(entry.schoolId).inserted,let school = try school(entry.schoolId) else { throw schoolError("Unknown or duplicate snapshot school") }
            for day in [entry.lastSuccessDay,entry.lastFailureDay].compactMap({$0}) {
                guard day.count == 10,let at = SchoolDates.parse(day),at <= Date().addingTimeInterval(86400) else { throw schoolError("Invalid snapshot date") }
            }
            if entry.lastSuccessDay != nil { counts[school.level,default:0] += 1 }
        }
        guard counts == snapshot.counts else { throw schoolError("Snapshot school totals do not match") }
        _ = try local.rows("INSERT INTO public_snapshot VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET sequence=excluded.sequence,envelope=excluded.envelope",[String(snapshot.sequence),String(decoding:data,as:UTF8.self)])
        return snapshot
    }
    func cachedSnapshot(publicKey:Data) throws -> SchoolSnapshot? {
        guard let raw = try local.rows("SELECT envelope FROM public_snapshot WHERE id=1").first?["envelope"] else { return nil }
        return try installSnapshot(Data(raw.utf8),publicKey:publicKey)
    }
}
