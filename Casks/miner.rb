cask "miner" do
  arch arm: "AppleSilicon", intel: "Intel"

  version "1.0.1"
  sha256 arm:   "faa0ee9d376b199f1892cd9a7e5710d45aec332413315e9721beb9879392fdf2",
         intel: "36ec74c4e8ea72db0c00bb099a71e4795a071ac30b0fa71049d08da70cad641c"

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
