import AppKit
import Combine
import Foundation
import Network
import CryptoKit

struct SchoolCommunityConfiguration:Decodable {
    let enabled:Bool
    let apiBaseURL:String?
    let snapshotPublicKey:String?
    static let closed = SchoolCommunityConfiguration(enabled:false,apiBaseURL:nil,snapshotPublicKey:nil)
    static var bundled:SchoolCommunityConfiguration {
        guard let url = Bundle.main.resourceURL?.appendingPathComponent("Community/community-config.json"),let data = try? Data(contentsOf:url),let value = try? JSONDecoder().decode(Self.self,from:data) else { return .closed }
        return value
    }
    var baseURL:URL? {
        guard enabled,let value = apiBaseURL,let url = URL(string:value),url.scheme == "https",url.host != nil,url.user == nil,url.password == nil,url.query == nil,url.fragment == nil else { return nil }
        return url
    }
    var publicKey:Data? { guard let value = snapshotPublicKey,let key = try? SchoolCrypto.decoded(value),key.count == 32 else { return nil };return key }
    var open:Bool { baseURL != nil && publicKey != nil }
}

private final class SchoolDiagnosticTask {
    private let lock = NSLock()
    private let process = Process()
    private var cancelled = false
    private var timedOut = false
    func cancel(timeout:Bool = false) {
        lock.lock(); cancelled = true; timedOut = timeout
        if process.isRunning { process.terminate() };lock.unlock()
    }
    func run(cli:String,directory:URL,engine:String) throws -> SchoolDiagnostic {
        guard !CommandLine.arguments.contains("--ui-smoke") else { throw schoolError("Backend actions disabled in UI fixtures") }
        let pipe = Pipe()
        process.executableURL = URL(fileURLWithPath:cli)
        process.arguments = ["community-diagnose","--directory",directory.path,"--engine",engine]
        process.standardOutput = pipe; process.standardError = FileHandle.nullDevice
        lock.lock()
        if cancelled { lock.unlock();throw schoolError("diagnosis_cancelled") }
        do { try process.run();lock.unlock() } catch { lock.unlock();throw error }
        DispatchQueue.global().asyncAfter(deadline:.now()+45) { [weak self] in
            guard let self = self else { return }
            self.lock.lock();let running = self.process.isRunning;self.lock.unlock()
            if running { self.cancel(timeout:true) }
        }
        let data = pipe.fileHandleForReading.readDataToEndOfFile();process.waitUntilExit()
        lock.lock();let stopped = cancelled;let timeout = timedOut;lock.unlock()
        if stopped { throw schoolError(timeout ? "diagnosis_timeout" : "diagnosis_cancelled") }
        guard process.terminationStatus == 0,data.count <= 65536 else { throw schoolError("diagnostic_failed") }
        let result = try JSONDecoder().decode(SchoolDiagnostic.self,from:data)
        guard result.schemaVersion == 1,result.passed == result.checks.passed else { throw schoolError("invalid_diagnostic_response") }
        return result
    }
}

final class SchoolCommunityModel:ObservableObject {
    @Published var metadata = SchoolCatalogMetadata.missing
    @Published var ready = false
    @Published var rows:[SchoolRecord] = []
    @Published var localCounts:[String:Int] = [:]
    @Published var localFlags:[String:SchoolFlag] = [:]
    @Published var sharedCounts:[String:Int]?
    @Published var sharedFlags:[String:SchoolFlag] = [:]
    @Published var sharedUpdated:String?
    @Published var scope = "mine"
    @Published var nameSearch = ""
    @Published var regionSearch = ""
    @Published var level = ""
    @Published var flagFilter = "all"
    @Published var offset = 0
    @Published var selected:SchoolRecord?
    @Published var loading = false
    @Published var working = false
    @Published var diagnosis:SchoolDiagnostic?
    @Published var schoolNetworkConfirmed = false
    @Published var clientConfirmed = false
    @Published var game = "not_tested"
    @Published var video = "not_tested"
    @Published var clientReturn = "not_tested"
    @Published var error = ""
    @Published var notice = ""
    @Published var savedReportId:String?
    @Published var syncing = false
    let configuration:SchoolCommunityConfiguration
    private let queue = DispatchQueue(label:"org.miner.community.store",qos:.userInitiated)
    private let dataDirectory:URL
    private let catalogURL:URL
    private let cli:String
    private let engine:String
    private let allowFixtures:Bool
    private var repository:SchoolRepository?
    private var loaded = false
    private var query = 0
    private var diagnosticGeneration = 0
    private var checkedGeneration = -1
    private var diagnosedAt:Date?
    private var task:SchoolDiagnosticTask?
    private var monitor:NWPathMonitor?
    private var firstPath = true
    private var latestReport:SignedSchoolReport?
    private var subscriptions = Set<AnyCancellable>()

    init(dataDirectory:URL,catalogURL:URL,cli:String,engine:String,configuration:SchoolCommunityConfiguration = .bundled,allowFixtures:Bool = false) {
        self.dataDirectory = dataDirectory;self.catalogURL = catalogURL;self.cli = cli;self.engine = engine;self.configuration = configuration;self.allowFixtures = allowFixtures
        Publishers.CombineLatest3($nameSearch,$regionSearch,$level).debounce(for:.milliseconds(250),scheduler:RunLoop.main)
            .sink { [weak self] _ in self?.search(reset:true) }.store(in:&subscriptions)
    }
    deinit { task?.cancel();monitor?.cancel() }
    var flags:[String:SchoolFlag] { scope == "mine" ? localFlags : sharedFlags }
    var counts:[String:Int]? { scope == "mine" ? localCounts : sharedCounts }
    var visibleRows:[SchoolRecord] { rows.filter { flagFilter == "all" || (flags[$0.id]?.green == true ? "green" : "red") == flagFilter } }
    var canRecordSuccess:Bool { ready && diagnosis?.passed == true && schoolNetworkConfirmed && clientConfirmed && checkedGeneration == diagnosticGeneration && diagnosedAt.map { Date().timeIntervalSince($0) <= 600 } == true }
    func load() {
        guard !loaded else { return };loaded = true;loading = true
        queue.async {
            do {
                let url = try SchoolRepository.ownedURL(self.dataDirectory)
                let repo = try SchoolRepository(catalogURL:self.catalogURL,localURL:url,allowFixtures:self.allowFixtures)
                self.repository = repo
                let flags = try repo.localFlags();let counts = try repo.counts(flags)
                var snapshot:SchoolSnapshot?
                if let key = self.configuration.publicKey { snapshot = try? repo.cachedSnapshot(publicKey:key) }
                DispatchQueue.main.async {
                    self.metadata = repo.metadata;self.ready = repo.available;self.localFlags = flags;self.localCounts = counts
                    if let snapshot = snapshot { self.apply(snapshot) }
                    self.loading = false;self.search(reset:true)
                }
            } catch { DispatchQueue.main.async { self.loading = false;self.error = error.localizedDescription } }
        }
    }
    func search(reset:Bool = false) {
        if reset { offset = 0 };query += 1
        let ticket = query,name = nameSearch,region = regionSearch,kind = level,start = offset
        let ids = Set(flags.filter { $0.value.green }.map { $0.key })
        let onlyGreen:Bool? = flagFilter == "all" ? nil : flagFilter == "green"
        queue.async {
            do {
                let records = try self.repository?.search(name:name,region:region,level:kind,offset:start,greenIDs:ids,onlyGreen:onlyGreen) ?? []
                DispatchQueue.main.async { if ticket == self.query { self.rows = records } }
            } catch { DispatchQueue.main.async { if ticket == self.query { self.error = error.localizedDescription } } }
        }
    }
    func choose(_ school:SchoolRecord) {
        invalidate();selected = school;schoolNetworkConfirmed = false;clientConfirmed = false
        game = "not_tested";video = "not_tested";clientReturn = "not_tested";notice = "";error = ""
        beginMonitoring()
        queue.async {
            do {
                let saved = try self.repository?.latestReport(schoolID:school.id)
                DispatchQueue.main.async {
                    if self.selected?.id == school.id && self.diagnosis == nil {
                        self.latestReport = saved;self.savedReportId = saved?.payload.id
                    }
                }
            } catch { DispatchQueue.main.async { self.error = error.localizedDescription } }
        }
    }
    func beginMonitoring() {
        guard monitor == nil else { return }
        firstPath = true
        let value = NWPathMonitor();monitor = value
        value.pathUpdateHandler = { [weak self] _ in
            DispatchQueue.main.async {
                guard let self = self else { return }
                if self.firstPath { self.firstPath = false;return }
                self.invalidate();self.notice = "network_changed"
            }
        }
        value.start(queue:DispatchQueue(label:"org.miner.community.path"))
    }
    func closeVerification() { invalidate();monitor?.cancel();monitor = nil;selected = nil }
    func invalidate() {
        diagnosticGeneration += 1;task?.cancel();task = nil;working = false
        diagnosis = nil;diagnosedAt = nil;checkedGeneration = -1;savedReportId = nil;latestReport = nil
    }
    func diagnose(engineRunning:Bool) {
        guard selected != nil,schoolNetworkConfirmed,!working else { return }
        guard engineRunning else { notice = "engine_not_running";return }
        invalidate();error = "";notice = "";working = true
        let work = SchoolDiagnosticTask();task = work
        let generation = diagnosticGeneration
        DispatchQueue.global(qos:.userInitiated).async {
            let result = Result { try work.run(cli:self.cli,directory:self.dataDirectory,engine:self.engine) }
            DispatchQueue.main.async {
                guard generation == self.diagnosticGeneration else { return }
                self.working = false;self.task = nil
                switch result {
                case .success(let value): self.diagnosis = value;self.diagnosedAt = Date();self.checkedGeneration = generation;self.notice = value.passed ? "diagnosis_passed" : "diagnostic_failed"
                case .failure(let error): self.notice = error.localizedDescription == "diagnosis_timeout" ? "timeout" : "diagnostic_failed"
                }
            }
        }
    }
    func record(success:Bool) {
        guard let school = selected,let diagnostic = diagnosis,let date = diagnosedAt,checkedGeneration == diagnosticGeneration,Date().timeIntervalSince(date) <= 600,!working else { notice = "diagnose_again";return }
        if success && !canRecordSuccess { return }
        // A manual failure record must not accidentally turn green.
        let client = success && clientConfirmed
        let version = Bundle.main.object(forInfoDictionaryKey:"SchoolNetReleaseVersion") as? String ?? "5.0.0-beta.2"
        let body = SchoolReportBody(id:UUID().uuidString.lowercased(),schoolId:school.id,catalogVersion:metadata.catalog_version,diagnosedAt:SchoolDates.string(date),appVersion:version,osMajor:ProcessInfo.processInfo.operatingSystemVersion.majorVersion,checks:diagnostic.checks,schoolNetworkConfirmed:schoolNetworkConfirmed,clientConfirmed:client,game:game,video:video,clientReturn:clientReturn,outcome:success ? "success" : "failure",failureCode:diagnostic.failureCode)
        working = true;let generation = diagnosticGeneration
        queue.async {
            do {
                guard let repo = self.repository else { throw schoolError("Catalog not loaded") }
                let signed = try SchoolCrypto.sign(body,key:SchoolCrypto.key())
                try repo.save(signed)
                let flags = try repo.localFlags();let counts = try repo.counts(flags)
                DispatchQueue.main.async {
                    self.working = false;self.localFlags = flags;self.localCounts = counts
                    if generation == self.diagnosticGeneration { self.savedReportId = body.id;self.latestReport = signed;self.notice = "saved_locally" }
                }
            } catch { DispatchQueue.main.async { self.working = false;self.error = error.localizedDescription } }
        }
    }
    func exportReport(_ completion:@escaping (Data,String)->Void) {
        guard let id = savedReportId else { return }
        queue.async {
            do {
                guard let data = try self.repository?.export(id) else { throw schoolError("Local report not found") }
                DispatchQueue.main.async { completion(data,id) }
            } catch { DispatchQueue.main.async { self.error = error.localizedDescription } }
        }
    }
    private func apply(_ snapshot:SchoolSnapshot) {
        sharedCounts = snapshot.counts;sharedUpdated = snapshot.generatedAt
        sharedFlags = Dictionary(uniqueKeysWithValues:snapshot.schools.map { ($0.schoolId,SchoolFlag(lastSuccess:$0.lastSuccessDay,lastFailure:$0.lastFailureDay)) })
    }
    func sync() {
        guard configuration.open,let base = configuration.baseURL,let key = configuration.publicKey,!syncing else { return }
        syncing = true;error = ""
        Task {
            do {
                let data = try await SchoolCommunityTransport.request(base:base,path:"v1/snapshot")
                queue.async {
                    do {
                        guard let repo = self.repository else { throw schoolError("Catalog not loaded") }
                        let snapshot = try repo.installSnapshot(data,publicKey:key)
                        DispatchQueue.main.async { self.apply(snapshot);self.syncing = false }
                    } catch { DispatchQueue.main.async { self.error = error.localizedDescription;self.syncing = false } }
                }
            } catch { DispatchQueue.main.async { self.error = error.localizedDescription;self.syncing = false } }
        }
    }
    // Upload is explicit, opt-in, and closed in the beta 2 release configuration.
    // Persist the exact signed envelope before POST so a retry remains idempotent.
    func submit() {
        guard configuration.open,let base = configuration.baseURL,let report = latestReport,!syncing else { return }
        syncing = true;error = ""
        queue.async {
            do {
                guard let repo = self.repository else { throw schoolError("Catalog not loaded") }
                let pending = try repo.pendingUpload(report.payload.id)
                Task {
                    do {
                        let envelope:Data
                        if let pending = pending { envelope = pending }
                        else {
                            guard let at = SchoolDates.parse(report.payload.diagnosedAt),Date().timeIntervalSince(at) <= 600 else { throw schoolError("diagnose_again") }
                            let response = try await SchoolCommunityTransport.request(base:base,path:"v1/challenges",json:["publicKey":report.publicKey])
                            let challenge = try JSONDecoder().decode(SchoolChallenge.self,from:response)
                            var body = report.payload;body.challenge = challenge
                            let signed = try SchoolCrypto.sign(body,key:SchoolCrypto.key());envelope = try SchoolCrypto.canonical(signed)
                            try await withCheckedThrowingContinuation { (continuation:CheckedContinuation<Void,Error>) in
                                self.queue.async {
                                    do { try repo.prepareUpload(report.payload.id,data:envelope);continuation.resume() }
                                    catch { continuation.resume(throwing:error) }
                                }
                            }
                        }
                        let response = try await SchoolCommunityTransport.request(base:base,path:"v1/reports",data:envelope)
                        let status = try JSONDecoder().decode(SchoolSubmission.self,from:response)
                        guard status.id == report.payload.id,["pending","approved","rejected","revoked"].contains(status.status) else { throw schoolError("invalid_submission_response") }
                        DispatchQueue.main.async { self.notice = "submitted_for_review";self.syncing = false }
                    } catch { DispatchQueue.main.async { self.error = error.localizedDescription;self.syncing = false } }
                }
            } catch { DispatchQueue.main.async { self.error = error.localizedDescription;self.syncing = false } }
        }
    }
}
private struct SchoolSubmission:Decodable { let id:String;let status:String }
enum SchoolCommunityTransport {
    static func request(base:URL,path:String,json:[String:String]? = nil,data:Data? = nil) async throws -> Data {
        var request = URLRequest(url:base.appendingPathComponent(path));request.timeoutInterval = 15
        if json != nil || data != nil {
            request.httpMethod = "POST";request.setValue("application/json",forHTTPHeaderField:"Content-Type")
            request.httpBody = try data ?? JSONSerialization.data(withJSONObject:json!)
        }
        let config = URLSessionConfiguration.ephemeral;config.timeoutIntervalForResource = 30
        let session = URLSession(configuration:config);defer { session.finishTasksAndInvalidate() }
        let (result,response) = try await session.data(for:request)
        guard let http = response as? HTTPURLResponse else { throw schoolError("community_unavailable") }
        guard (200..<300).contains(http.statusCode) else { throw schoolError("community_request_failed (\(http.statusCode))") }
        guard result.count <= 8*1024*1024 else { throw schoolError("community_response_too_large") }
        return result
    }
}
