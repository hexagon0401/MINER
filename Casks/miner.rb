cask "miner" do
  arch arm: "AppleSilicon", intel: "Intel"

  version "1.2.2"
  sha256 arm:   "cd718df042a10abdc313644d2ec07bb84a92661fc802fe690787259a3c88a244",
         intel: "79f0eb95d1f3c3a8eb7eaee7a4920a8ab03ce22c8a9e1a5c84bde97c82cd0f15"

  url "https://github.com/hexagon0401/MINER/releases/download/miner-alpha-v#{version}/MINER-ALPHA-v#{version}-macOS-#{arch}.dmg",
      verified: "github.com/hexagon0401/MINER/"
  name "MINER ALPHA"
  desc "Split routing with Cloudflare WARP for game clients"
  homepage "https://github.com/hexagon0401/MINER"

  conflicts_with cask: "miner-beta"
  depends_on macos: :ventura

  app "MINER.app"

  preflight_steps do
    run "/bin/sh", args: ["-c", <<~SH]
      if /usr/bin/pgrep -x MINER >/dev/null 2>&1 ||
          /bin/launchctl print system/org.schoolnet.v5.alpha 2>/dev/null | /usr/bin/grep -Eq 'pid = [0-9]+'; then
        echo "Stop and quit MINER before installing or upgrading. Wait for WARP restoration." >&2
        exit 1
      fi
    SH
  end

  uninstall_preflight_steps do
    run "/bin/sh", args: ["-c", <<~SH]
      if /usr/bin/pgrep -x MINER >/dev/null 2>&1 ||
          /bin/launchctl print system/org.schoolnet.v5.alpha 2>/dev/null | /usr/bin/grep -Eq 'pid = [0-9]+'; then
        echo "Stop and quit MINER before uninstalling. Use Settings > Uninstall MINER for full cleanup." >&2
        exit 1
      fi
    SH
  end

  zap trash: [
    "~/Library/Application Support/SchoolNet v5 Alpha",
    "~/Library/Preferences/org.schoolnet.v5.alpha.plist",
  ]

  caveats <<~EOS
    Personal Cloudflare WARP must be installed and registered separately.
    ALPHA is the release codename. This build is ad-hoc signed and is not Apple notarized.
    Complete helper, data and report-key removal is available in MINER Settings > Uninstall MINER.
  EOS
end
