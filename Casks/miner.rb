cask "miner" do
  arch arm: "AppleSilicon", intel: "Intel"

  version "1.2.1"
  sha256 arm:   "4921b7527931df4d41b85c35c9e566943839bdbd6d4a777183179f3f6c9653f9",
         intel: "60cdce5ee57fa4c403aa8f28fc20713e93110af0f4491a3b40dc9969c2251f95"

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
