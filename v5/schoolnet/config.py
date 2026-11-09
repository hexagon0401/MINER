"""Generate sing-box 1.12 configuration without changing OS settings."""
from dataclasses import asdict, dataclass, field
from ipaddress import ip_network
import re

ENGINE_VERSION = "1.12.0"
CLIENTS = {
    "macos": ["RiotClientServices", "RiotClientUx", "RiotClientUxRender",
              "LeagueClient", "LeagueClientUx", "LeagueClientUx Helper",
              "LeagueClientUx Helper (Renderer)", "LeagueClientUx Helper (GPU)"],
    "windows": ["RiotClientServices.exe", "RiotClientUx.exe", "RiotClientUxRender.exe",
                "LeagueClient.exe", "LeagueClientUx.exe", "LeagueClientUxRender.exe"],
}
# CEF/Chromium helper processes make the embedded web/video requests separately.
# Match the client bundle path as well as basenames; never tunnel every browser.
CLIENT_PATHS = {
    "macos": [r"(?i)/(?:Riot Client|RiotClient(?:Services|Ux|UxRender)|LeagueClient(?:Ux)?)(?: Helper(?: \([^/]+\))?)?\.app/Contents/"],
    "windows": [],
}
CLIENTS["macos"] += [
    "Riot Client", "Riot Client Helper", "Riot Client Helper (Renderer)",
    "Riot Client Helper (GPU)", "Riot Client Helper (Plugin)",
    "RiotClientUx Helper", "RiotClientUx Helper (Renderer)", "RiotClientUx Helper (GPU)",
    "RiotClientUxRender Helper", "LeagueClientUx Helper (Plugin)",
]
GAMES = {
    "macos": ["LeagueofLegends", "League of Legends"],
    "windows": ["League of Legends.exe"],
}
RIOT_DOMAINS = ["riotgames.com", "riotcdn.net", "riotgames.net", "pvp.net", "leagueoflegends.com",
                "lolstatic.com", "lolstatic-a.akamaihd.net", "lolesports.com"]
DNS_V4 = "172.30.255.2"
DNS_V6 = "fdfe:dcba:9876::2"
FAKE_V4 = "198.18.0.0/15"
FAKE_V6 = "fdfe:dcba:9876:1000::/64"
SELECTIVE_ROUTES = [FAKE_V4, FAKE_V6]


@dataclass
class Profile:
    platform: str = "macos"
    proxy_port: int = 40000
    mtu: int = 1500
    physical_interface: str = ""
    extra_clients: list[str] = field(default_factory=list)
    game_cidrs: list[str] = field(default_factory=list)
    dns_forward_port: int = 40001

    def validate(self):
        if self.platform not in CLIENTS:
            raise ValueError("platform must be macos or windows")
        if type(self.dns_forward_port) is not int or not 1024 <= self.dns_forward_port <= 65535:
            raise ValueError("invalid local DNS forwarder port")
        if type(self.proxy_port) is not int or not 1024 <= self.proxy_port <= 65535:
            raise ValueError("proxy_port must be an integer in 1024..65535")
        if type(self.mtu) is not int or not 1280 <= self.mtu <= 1500:
            raise ValueError("mtu must be an integer in 1280..1500")
        if not isinstance(self.physical_interface, str) or not re.fullmatch(r"[\w .-]{0,100}", self.physical_interface):
            raise ValueError("invalid physical_interface")
        if not isinstance(self.extra_clients, list) or len(self.extra_clients) > 32:
            raise ValueError("extra_clients must be a list of at most 32 exact process names")
        for name in self.extra_clients:
            if not isinstance(name, str) or not name or len(name) > 200 or any(c in name for c in "/\\\x00\n\r"):
                raise ValueError("extra_clients must contain exact executable basenames")
            if name.casefold() in {n.casefold() for n in GAMES[self.platform]}:
                raise ValueError("game executable cannot be a tunneled client")
        if not isinstance(self.game_cidrs, list) or len(self.game_cidrs) > 64:
            raise ValueError("game_cidrs must be a list of at most 64 observed host routes")
        for cidr in self.game_cidrs:
            network = ip_network(cidr, strict=True)
            if network.prefixlen != network.max_prefixlen or not network.network_address.is_global:
                raise ValueError("game_cidrs only accepts observed public /32 or /128 host routes")
            if str(network.network_address) in {"1.1.1.1", "1.0.0.1"}:
                raise ValueError("DNS resolver is not a game host route")
        return self

    @property
    def clients(self):
        return sorted(set(CLIENTS[self.platform] + self.extra_clients))

    def to_dict(self):
        return asdict(self)


def build_config(profile: Profile) -> dict:
    """Direct is the default. Only recognized client TCP enters WARP SOCKS."""
    p = profile.validate()
    tun = {
        "type": "tun", "tag": "schoolnet-tun",
        "address": ["172.30.255.1/30", "fdfe:dcba:9876::1/126"],
        # Strict mode enforces DNS on Windows and can block ordinary interface
        # traffic. Fail-closed applies to Riot's proxy rules, not the whole host.
        "mtu": p.mtu, "auto_route": True, "strict_route": False, "stack": "system",
        # Never install 0/0 routes. Real game/browser/Kakao IPs stay in the OS
        # network stack; only synthetic Riot addresses reach this interface.
        "route_address": SELECTIVE_ROUTES.copy(),
    }
    if p.game_cidrs:
        tun["route_exclude_address"] = list(p.game_cidrs)
    # WARP owns the encrypted transport. Keep its daemon outside the proxy rule.
    rules = [
        {"port": 53, "action": "hijack-dns"},
        {"process_name": GAMES[p.platform], "action": "route", "outbound": "direct"},
    ]
    # The kernel sends only Riot synthetic addresses here. Do not depend on
    # renderer process names or expensive per-connection client attribution.
    rules += [
        {"inbound":["schoolnet-tun"],"network":"tcp","action":"route","outbound":"warp"},
        {"inbound":["schoolnet-tun"],"network":"udp","action":"reject","method":"default","no_drop":True},
    ]
    dns_rules = [
        {"domain": ["miner-health.invalid"], "action": "predefined", "rcode": "NOERROR",
         "answer": ["miner-health.invalid. 1 IN A 127.0.0.1"]},
        {"domain_suffix": RIOT_DOMAINS, "query_type": ["A", "AAAA"], "action": "route", "server": "riot-addresses"},
    ]
    route = {"rules": rules, "final": "direct", "default_domain_resolver": "direct-dns"}
    if p.physical_interface:
        route["default_interface"] = p.physical_interface
    else:
        route["auto_detect_interface"] = True
    return {
        # Per-connection info logging was costly during download/browser bursts.
        "log": {"level": "warn", "timestamp": True},
        "dns": {
            "servers": [{"type": "fakeip", "tag": "riot-addresses", "inet4_range": FAKE_V4, "inet6_range": FAKE_V6},
                        {"type": "udp", "tag": "direct-dns", "server": "127.0.0.1", "server_port": p.dns_forward_port,
                         "inet4_bind_address": "127.0.0.1"}],
            "rules": dns_rules, "final": "direct-dns", "independent_cache": True, "cache_capacity": 4096,
        },
        "inbounds": [tun],
        "outbounds": [
            {"type": "direct", "tag": "direct"},
            {"type": "socks", "tag": "warp", "server": "127.0.0.1",
             "server_port": p.proxy_port, "version": "5", "network": "tcp",
             "inet4_bind_address": "127.0.0.1"},
        ],
        "route": route,
        "experimental": {"cache_file": {"enabled": True, "path": "fakeip-cache.db", "store_fakeip": True}},
    }
