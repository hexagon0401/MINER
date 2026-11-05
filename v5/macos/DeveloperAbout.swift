import AppKit
import SwiftUI

struct MinerDeveloper: Decodable {
    let login:String
    let name:String
    let profileURL:URL
    let avatarURL:URL
    static let current:MinerDeveloper = {
        let url = Bundle.main.resourceURL!.appendingPathComponent("UIAssets/developer-profile.json")
        guard let data = try? Data(contentsOf:url),let profile = try? JSONDecoder().decode(MinerDeveloper.self,from:data) else {
            return MinerDeveloper(login:"hexagon0401",name:"Punkthats*it",profileURL:URL(string:"https://github.com/hexagon0401")!,avatarURL:URL(string:"https://avatars.githubusercontent.com/u/82876856?v=4&s=256")!)
        }
        return profile
    }()
    static let avatar = NSImage(contentsOf:Bundle.main.resourceURL!.appendingPathComponent("UIAssets/developer-avatar.png"))
}

struct MinerAbout:View {
    @ObservedObject var model:MinerModel
    private let developer = MinerDeveloper.current
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            Text(model.tr("개발자 소개","About")).font(.headline)
            HStack(spacing:14) {
                avatar.accessibilityLabel(model.tr("개발자 프로필 이미지","Developer profile image"))
                VStack(alignment:.leading,spacing:4) {
                    Text(developer.name).font(.system(size:16,weight:.semibold)).textSelection(.enabled)
                    Text("@" + developer.login).font(.caption).foregroundStyle(.secondary).textSelection(.enabled)
                    Link(model.tr("GitHub 프로필 보기 ↗","View GitHub profile ↗"),destination:developer.profileURL).font(.caption)
                }
                Spacer()
            }
            Text("MINER · " + (Bundle.main.object(forInfoDictionaryKey:"MINERPublicReleaseVersion") as? String ?? "1.1.1"))
                .font(.caption).foregroundStyle(.secondary)
        }.frame(maxWidth:.infinity,alignment:.leading)
    }
    @ViewBuilder private var avatar:some View {
        if let image = MinerDeveloper.avatar {
            Image(nsImage:image).resizable().scaledToFill().frame(width:60,height:60).clipShape(Circle())
                .overlay(Circle().stroke(Color.primary.opacity(0.12)))
        } else {
            Image(systemName:"person.crop.circle.fill").resizable().frame(width:60,height:60).foregroundStyle(.secondary)
        }
    }
}
