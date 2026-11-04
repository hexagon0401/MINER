import AppKit
import SwiftUI
import UniformTypeIdentifiers

private func schoolLevel(_ level:String,_ model:MinerModel) -> String {
    switch level {case "high":return model.tr("고등학교","High schools");case "middle":return model.tr("중학교","Middle schools");default:return model.tr("초등학교","Elementary schools")}
}
struct SchoolSummaryView:View {
    @ObservedObject var community:SchoolCommunityModel
    @ObservedObject var model:MinerModel
    let controller:AppDelegate
    var body:some View {
        VStack(alignment:.leading,spacing:10) {
            Text(model.tr("학교 현황","School coverage")).font(.headline)
            Picker(model.tr("기록 범위","Records"),selection:$community.scope) {
                Text(model.tr("내 기기","This Mac")).tag("mine")
                Text(model.tr("전국 공유","Community")).tag("national")
            }.pickerStyle(.segmented)
            ForEach(["high","middle","elementary"],id:\.self) { level in
                HStack {
                    Text(schoolLevel(level,model));Spacer()
                    Text(total(level)).monospacedDigit()
                }.font(.system(size:12))
            }
            Text(community.scope == "mine" ? model.tr("내 기기의 누적 성공 기록입니다. 전국 인증과 구분됩니다.","Cumulative records on this Mac, separate from community approval.") : model.tr("승인된 성공 학교 수입니다. 미개방·미동기화 수치는 —로 표시합니다.","Approved schools. Unavailable community totals are shown as —."))
                .font(.caption).foregroundStyle(.secondary)
            if community.metadata.fixture { Text(model.tr("테스트 자료 · 전국 통계 아님","Test fixtures · not national statistics")).font(.caption).foregroundStyle(.orange) }
            if !community.ready { Text(model.tr("공식 전체 학교 명부 준비 중 · 임의의 전국 수치를 표시하지 않습니다.","Complete official catalog pending. Nationwide totals are not estimated.")).font(.caption).foregroundStyle(.orange) }
            if !community.configuration.open { Text(model.tr("공유 제보는 아직 개방되지 않았습니다.","Community submissions are not open yet.")).font(.caption).foregroundStyle(.secondary) }
            Button(model.tr("상세 내역 · 학교 인증…","Details · Check my school…")) { controller.showSchools() }
        }.onAppear { community.load() }
    }
    private func total(_ level:String) -> String {
        guard community.ready else { return "— / —" }
        let value = community.counts.map { String($0[level,default:0]) } ?? "—"
        return value + " / " + String(community.metadata.counts[level,default:0])
    }
}
struct SchoolDetailsView:View {
    @ObservedObject var community:SchoolCommunityModel
    @ObservedObject var model:MinerModel
    @State private var verification = false
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            heading
            filters
            if !community.error.isEmpty { Text(community.error).font(.caption).foregroundStyle(.red).textSelection(.enabled) }
            if !community.ready {
                Text(model.tr("공식 NEIS 전체 명부가 필요합니다. 샘플 데이터는 전국 현황에 사용하지 않습니다.","A complete official NEIS catalog is required. Samples are not used for nationwide coverage."))
                    .font(.callout).foregroundStyle(.secondary).frame(maxWidth:.infinity,maxHeight:.infinity)
            } else { schoolList }
            navigation
            attribution
        }.padding(20).frame(minWidth:600,minHeight:480)
        .onAppear { community.load();community.search(reset:true) }
        .onChange(of:community.scope) { _ in community.search(reset:true) }
        .onChange(of:community.flagFilter) { _ in community.search(reset:true) }
        .onChange(of:model.engine) { _ in community.invalidate() }
        .onChange(of:model.phase) { value in if value == "stopping" || value == "error" { community.invalidate() } }
        .sheet(isPresented:$verification,onDismiss:{community.closeVerification()}) {
            SchoolVerificationView(community:community,model:model) { verification = false }
        }
    }
    private var heading:some View {
        VStack(alignment:.leading,spacing:8) {
            Text(model.tr("학교별 연결 기록","School connection records")).font(.title2)
            if community.metadata.fixture { Text(model.tr("테스트 자료 · 전국 통계 아님","Test fixtures · not national statistics")).font(.caption).foregroundStyle(.orange) }
            Picker(model.tr("범위","Records"),selection:$community.scope) {
                Text(model.tr("내 기기","This Mac")).tag("mine");Text(model.tr("전국 공유","Community")).tag("national")
            }.pickerStyle(.segmented).frame(width:300)
            Text(model.tr("초록: 성공 이력 있음 · 빨강: 성공 미확인. 빨강은 작동 불가능을 뜻하지 않습니다.","Green: prior success. Red: no confirmed success; it does not prove failure."))
                .font(.caption).foregroundStyle(.secondary)
            if community.scope == "national" {
                HStack {
                    Text(community.sharedUpdated.map { model.tr("마지막 동기화: ","Last sync: ") + $0 } ?? model.tr("공유 데이터 미개방·미동기화","Community data unavailable"))
                    Spacer()
                    Button(model.tr("동기화","Sync")) { community.sync() }.disabled(!community.configuration.open || community.syncing)
                }.font(.caption)
            }
        }
    }
    private var filters:some View {
        VStack(spacing:8) {
            HStack {
                TextField(model.tr("지역: 시·도 / 시·군·구","Region / district"),text:$community.regionSearch)
                TextField(model.tr("학교명","School name"),text:$community.nameSearch)
            }.textFieldStyle(.roundedBorder)
            HStack {
                Picker(model.tr("학교급","Level"),selection:$community.level) {
                    Text(model.tr("전체","All")).tag("")
                    ForEach(["high","middle","elementary"],id:\.self) { level in Text(schoolLevel(level,model)).tag(level) }
                }
                Picker(model.tr("깃발","Flag"),selection:$community.flagFilter) {
                    Text(model.tr("전체","All")).tag("all");Text(model.tr("초록","Green")).tag("green");Text(model.tr("빨강","Red")).tag("red")
                }.frame(width:160)
            }
        }
    }
    private var schoolList:some View {
        List(community.rows) { school in
            Button {
                community.choose(school);verification = true
            } label: {
                SchoolListRow(school:school,flag:community.flags[school.id] ?? SchoolFlag(),model:model)
            }.buttonStyle(.plain)
        }.overlay {
            if community.rows.isEmpty { Text(model.tr("검색 결과 없음","No matching schools")).foregroundStyle(.secondary) }
        }
    }
    private var navigation:some View {
        HStack {
            Button(model.tr("이전","Previous")) { community.offset = max(0,community.offset-100);community.search() }.disabled(community.offset == 0)
            Text("\(community.offset+1) – \(community.offset+community.rows.count)").font(.caption).monospacedDigit()
            Button(model.tr("다음","Next")) { community.offset += 100;community.search() }.disabled(community.rows.count<100)
            Spacer()
            Text(model.tr("학교를 선택해 인증·내보내기","Select a school to diagnose or export")).font(.caption).foregroundStyle(.secondary)
        }
    }
    private var attribution:some View {
        VStack(alignment:.leading,spacing:3) {
            Text(community.metadata.attribution)
            Text(model.tr("명부 기준일: ","Catalog date: ") + (community.metadata.as_of.isEmpty ? "—" : community.metadata.as_of))
        }.font(.system(size:10)).foregroundStyle(.secondary)
    }
}
private struct SchoolListRow:View {
    let school:SchoolRecord
    let flag:SchoolFlag
    @ObservedObject var model:MinerModel
    var body:some View {
        HStack(spacing:12) {
            Image(systemName:"flag.fill").foregroundStyle(flag.green ? Color.green : Color.red).font(.system(size:20))
            VStack(alignment:.leading,spacing:3) {
                Text(school.name).fontWeight(.medium)
                Text(school.region).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            VStack(alignment:.trailing,spacing:3) {
                Text(flag.green ? model.tr("성공 이력 있음","Prior success") : model.tr("성공 미확인","Unconfirmed")).font(.caption)
                if let day = flag.lastSuccess { Text(String(day.prefix(10))).font(.caption2).foregroundStyle(.secondary) }
                if flag.stale { Text(model.tr("90일 경과 · 재확인 필요","90+ days · recheck advised")).font(.caption2).foregroundStyle(.orange) }
                if let failure = flag.lastFailure,flag.lastSuccess == nil || failure >= (flag.lastSuccess ?? "") {
                    Text(model.tr("최근 실패·미확인 기록","Recent failure / unconfirmed record")).font(.caption2).foregroundStyle(.red)
                }
            }
        }.padding(.vertical,5).contentShape(Rectangle()).accessibilityElement(children:.combine)
    }
}
struct SchoolVerificationView:View {
    @ObservedObject var community:SchoolCommunityModel
    @ObservedObject var model:MinerModel
    let close:()->Void
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            HStack { Text(model.tr("내 학교 연결 확인","Check my school connection")).font(.title2);Spacer();Button(model.tr("닫기","Close"),action:close) }
            ScrollView {
                VStack(alignment:.leading,spacing:16) {
                    schoolHeading
                    diagnosisControls
                    confirmations
                    resultControls
                    reportControls
                }.frame(maxWidth:.infinity,alignment:.leading)
            }
        }.padding(22).frame(width:580,height:610)
    }
    private var schoolHeading:some View {
        VStack(alignment:.leading,spacing:6) {
            Text(community.selected?.name ?? "—").font(.headline)
            Text(community.selected?.region ?? "").font(.caption).foregroundStyle(.secondary)
            Text(model.tr("학교 위치·재학 여부는 자동 인증되지 않습니다. 진단은 엔진·프록시 연결을 확인하며, 실제 클라이언트 사용은 본인 확인입니다.","School presence and enrollment cannot be automatically verified. Diagnostics check the engine and proxy; client usage is self-reported."))
                .font(.caption).foregroundStyle(.secondary)
            Toggle(model.tr("현재 선택한 학교의 네트워크를 사용 중입니다.","I am currently using the selected school's network."),isOn:$community.schoolNetworkConfirmed)
        }
    }
    private var diagnosisControls:some View {
        VStack(alignment:.leading,spacing:7) {
            Text(model.tr("1. 연결 진단","1. Connection diagnostics")).font(.headline)
            Text(model.tr("메인 창에서 MINER를 시작한 상태에서 검사하세요. 진단은 WARP 설정이나 게임 경로를 변경하지 않습니다.","Start MINER in its main window first. Diagnostics do not change WARP settings or game routes.")).font(.caption).foregroundStyle(.secondary)
            HStack {
                Button(model.tr("진단하기","Run diagnostics")) { community.diagnose(engineRunning:model.engine) }
                    .disabled(!community.schoolNetworkConfirmed || !model.engine || community.working)
                if community.working {
                    ProgressView().controlSize(.small)
                    if community.diagnosis == nil { Button(model.tr("취소","Cancel")) { community.invalidate() } }
                }
            }
            if let diagnosis = community.diagnosis {
                Label(diagnosis.passed ? model.tr("엔진·WARP 진단 통과","Engine and WARP checks passed") : model.tr("진단 실패·미확인","Diagnostics failed or unconfirmed"),systemImage:diagnosis.passed ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                    .foregroundStyle(diagnosis.passed ? Color.green : Color.orange).font(.caption)
            }
        }
    }
    private var confirmations:some View {
        VStack(alignment:.leading,spacing:8) {
            Text(model.tr("2. 실제 사용 확인","2. Confirm actual use")).font(.headline)
            Toggle(model.tr("Riot/LoL 클라이언트 로그인·로비를 정상적으로 사용했습니다.","I successfully used Riot/LoL client login and lobby."),isOn:$community.clientConfirmed)
            outcomePicker(model.tr("게임","Game"),$community.game)
            outcomePicker(model.tr("영상·웹","Media / web"),$community.video)
            outcomePicker(model.tr("게임 후 클라이언트 복귀","Return to client"),$community.clientReturn)
        }
    }
    private func outcomePicker(_ title:String,_ binding:Binding<String>) -> some View {
        Picker(title,selection:binding) {
            Text(model.tr("미확인","Not tested")).tag("not_tested")
            Text(model.tr("정상","Passed")).tag("pass")
            Text(model.tr("문제 있음","Failed")).tag("fail")
        }.pickerStyle(.segmented)
    }
    private var resultControls:some View {
        VStack(alignment:.leading,spacing:8) {
            HStack {
                Button(model.tr("내 기기에 성공 기록","Save local success")) { community.record(success:true) }
                    .buttonStyle(.borderedProminent).disabled(!community.canRecordSuccess || community.working)
                Button(model.tr("실패·미확인 기록","Save failure / unconfirmed")) { community.record(success:false) }
                    .disabled(community.diagnosis == nil || community.working)
            }
            if !community.notice.isEmpty { Text(noticeText).font(.caption).foregroundStyle(.secondary) }
            if !community.error.isEmpty { Text(community.error).font(.caption).foregroundStyle(.red).textSelection(.enabled) }
            Text(model.tr("성공 기록은 내 기기 깃발만 바꿉니다. 전국 공유는 운영자의 검토 후 반영됩니다.","Saving changes only this Mac's flag. Community coverage changes after operator review.")).font(.caption).foregroundStyle(.secondary)
        }
    }
    private var reportControls:some View {
        VStack(alignment:.leading,spacing:8) {
            HStack {
                Button(model.tr("제보 JSON 내보내기…","Export report JSON…"),action:exportReport).disabled(community.savedReportId == nil)
                Button(model.tr("검토 요청","Submit for review")) { community.submit() }.disabled(community.savedReportId == nil || !community.configuration.open || community.syncing)
            }
            Text(model.tr("공유 서버는 아직 미개방입니다. 내보내기는 선택 사항이며 이름·학번·SSID·IP·원본 로그를 포함하지 않습니다.","The community service is not open yet. Optional exports exclude names, student IDs, SSIDs, IPs and raw logs.")).font(.caption).foregroundStyle(.secondary)
        }
    }
    private var noticeText:String {
        switch community.notice {
        case "network_changed":return model.tr("연결 경로가 바뀌었습니다. 진단을 다시 실행하세요.","Network path changed. Run diagnostics again.")
        case "engine_not_running":return model.tr("먼저 메인 창에서 MINER를 시작하세요.","Start MINER in its main window first.")
        case "timeout":return model.tr("진단 제한 시간 45초가 지났습니다.","Diagnostics reached the 45-second limit.")
        case "saved_locally":return model.tr("내 기기에 저장했습니다. 전국 집계에는 반영되지 않았습니다.","Saved on this Mac; community totals are unchanged.")
        case "diagnosis_passed":return model.tr("진단 통과. 실제 클라이언트 사용을 확인한 뒤 저장하세요.","Diagnostics passed. Confirm actual client use before saving.")
        case "submitted_for_review":return model.tr("검토 대기 중입니다. 아직 전국 성공 집계에 반영되지 않았습니다.","Awaiting review. Community success totals are unchanged.")
        case "diagnose_again":return model.tr("진단 결과가 오래됐습니다. 다시 검사하세요.","Diagnostics are stale. Run them again.")
        default:return model.tr("진단에 실패했거나 확인되지 않았습니다. 기존 상태·로그에서 원인을 확인하세요.","Diagnostics failed or remain unconfirmed. Check the existing status/log tools.")
        }
    }
    private func exportReport() {
        community.exportReport { data,id in
            let panel = NSSavePanel();panel.allowedContentTypes = [.json]
            panel.nameFieldStringValue = "MINER-school-report-" + id + ".json"
            panel.begin { response in
                guard response == .OK,let url = panel.url else { return }
                do { try data.write(to:url,options:.atomic) }
                catch { community.error = error.localizedDescription }
            }
        }
    }
}
