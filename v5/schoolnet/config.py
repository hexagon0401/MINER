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
GAMES = {
    "macos": ["LeagueofLegends", "League of Legends"],
    "windows": ["League of Legends.exe"],
}


@dataclass
class Profile:
    platform: str = "macos"
    proxy_port: int = 40000
    mtu: int = 1500
    physical_interface: str = ""
    extra_clients: list[str] = field(default_factory=list)
    game_cidrs: list[str] = field(default_factory=list)

    def validate(self):
        if self.platform not in CLIENTS:
            raise ValueError("platform must be macos or windows")
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
        "mtu": p.mtu, "auto_route": True, "strict_route": True, "stack": "system",
    }
    if p.game_cidrs:
        tun["route_exclude_address"] = list(p.game_cidrs)
    # WARP owns the encrypted transport. Keep its daemon outside the proxy rule.
    rules = [
        {"process_name": ["warp-svc", "warp-svc.exe", "CloudflareWARP", "Cloudflare WARP"],
         "action": "route", "outbound": "direct"},
        {"port": 53, "action": "hijack-dns"},
        {"process_name": GAMES[p.platform], "action": "route", "outbound": "direct"},
        {"ip_is_private": True, "action": "route", "outbound": "direct"},
        {"process_name": p.clients, "network": "tcp", "action": "route", "outbound": "warp"},
        # WARP local proxy UDP support is not assumed. QUIC may fall back to TCP;
        # other client UDP features can fail. Never mislabel a direct leak as tunnelled.
        {"process_name": p.clients, "network": "udp", "action": "reject", "no_drop": True},
    ]
    route = {"rules": rules, "final": "direct", "default_domain_resolver": "warp-dns"}
    if p.physical_interface:
        route["default_interface"] = p.physical_interface
    else:
        route["auto_detect_interface"] = True
    return {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "servers": [{"type": "https", "tag": "warp-dns", "server": "1.1.1.1",
                         "server_port": 443, "path": "/dns-query", "detour": "warp",
                         "tls": {"enabled": True, "server_name": "cloudflare-dns.com"}}],
            "final": "warp-dns", "cache_capacity": 4096,
        },
        "inbounds": [tun],
        "outbounds": [
            {"type": "direct", "tag": "direct"},
            {"type": "socks", "tag": "warp", "server": "127.0.0.1",
             "server_port": p.proxy_port, "version": "5", "network": "tcp",
             "inet4_bind_address": "127.0.0.1"},
        ],
        "route": route,
    }
