cask "miner-beta" do
  version "5.0.0-beta.1"
  sha256 "f88f2adf20e353337f293d1ab01f8b5c84fd32aaa3583771ce626480d8e8ec68"

  url "https://github.com/hexagon0401/MINER/releases/download/v#{version}/MINER-v#{version}-macOS-AppleSilicon.dmg",
      verified: "github.com/hexagon0401/MINER/"
  name "MINER BETA"
  desc "Split routing and school connection records"
  homepage "https://github.com/hexagon0401/MINER"

  conflicts_with cask: "miner"
  depends_on arch: :arm64
  depends_on macos: ">= :ventura"

  app "MINER.app"

  preflight do
    app_running = system_command(
      "/usr/bin/pgrep",
      args: ["-x", "MINER"],
      must_succeed: false,
    ).exit_status.zero?
    service = system_command(
      "/bin/launchctl",
      args: ["print", "system/org.schoolnet.v5.alpha"],
      must_succeed: false,
    )
    if app_running || service.stdout.match?(/pid = \d+/)
      raise Cask::CaskError,
            "Stop and quit MINER before installing or upgrading. WARP must finish restoring first."
    end
  end

  uninstall_preflight do
    app_running = system_command(
      "/usr/bin/pgrep",
      args: ["-x", "MINER"],
      must_succeed: false,
    ).exit_status.zero?
    service = system_command(
      "/bin/launchctl",
      args: ["print", "system/org.schoolnet.v5.alpha"],
      must_succeed: false,
    )
    if app_running || service.stdout.match?(/pid = \d+/)
      raise Cask::CaskError,
            "Stop and quit MINER before uninstalling. " \
            "For complete service/data removal, use Settings > Uninstall MINER first."
    end
  end

  zap trash: [
    "~/Library/Application Support/SchoolNet v5 Alpha",
    "~/Library/Preferences/org.schoolnet.v5.alpha.plist",
  ]

  caveats <<~EOS
    Personal Cloudflare WARP must be installed and registered separately.
    This beta is ad-hoc signed and is not Apple notarized.
    Private GitHub release assets are not publicly installable; publish the repo and tap before public distribution.
    Complete helper, data and report-key removal is available in MINER Settings > Uninstall MINER.
  EOS
end
