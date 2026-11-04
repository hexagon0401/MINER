import unittest
import re

from schoolnet.config import CLIENT_PATHS, GAMES, Profile, build_config


class ProfileTests(unittest.TestCase):
    def test_default_routes_only_selected_tcp_through_proxy(self):
        config = build_config(Profile())
        route = config["route"]
        self.assertEqual(route["final"], "direct")
        proxy_rules = [r for r in route["rules"] if r.get("outbound") == "warp"]
        self.assertEqual(len(proxy_rules), 2)
        self.assertTrue(all(r["network"] == "tcp" for r in proxy_rules))
        self.assertIn("LeagueClient", proxy_rules[0]["process_name"])
        self.assertNotIn("LeagueofLegends", proxy_rules[0]["process_name"])
        self.assertNotIn("port_range", proxy_rules[0])

    def test_embedded_web_helpers_match_without_tunneling_safari_or_game_bundle(self):
        expressions = CLIENT_PATHS["macos"]
        for path in [
            "/Applications/Riot Client.app/Contents/Frameworks/Riot Client Helper (Renderer).app/Contents/MacOS/Riot Client Helper (Renderer)",
            "/Applications/League of Legends.app/Contents/LoL/LeagueClientUx.app/Contents/Frameworks/Network Helper.app/Contents/MacOS/Network Helper",
        ]:
            self.assertTrue(any(re.search(pattern, path) for pattern in expressions), path)
        for path in ["/Applications/Safari.app/Contents/MacOS/Safari",
                     "/Applications/League of Legends.app/Contents/LoL/Game/LeagueofLegends.app/Contents/MacOS/LeagueofLegends"]:
            self.assertFalse(any(re.search(pattern, path) for pattern in expressions), path)
        self.assertIn("Riot Client Helper (Renderer)", Profile().clients)

    def test_every_client_selector_has_tcp_proxy_and_explicit_quic_rejection(self):
        rules = build_config(Profile())["route"]["rules"]
        for selector in ["process_name", "process_path_regex"]:
            tcp = next(r for r in rules if selector in r and r.get("outbound") == "warp")
            udp = next(r for r in rules if selector in r and r.get("action") == "reject")
            self.assertEqual(tcp[selector], udp[selector])
            self.assertEqual(udp["method"], "default")
            self.assertTrue(udp["no_drop"])

    def test_game_has_explicit_priority_on_both_platforms(self):
        for platform in ["macos", "windows"]:
            with self.subTest(platform=platform):
                rules = build_config(Profile(platform=platform))["route"]["rules"]
                game_index = next(i for i, r in enumerate(rules) if r.get("process_name") == GAMES[platform])
                proxy_index = next(i for i, r in enumerate(rules) if r.get("outbound") == "warp")
                self.assertLess(game_index, proxy_index)
                self.assertEqual(rules[game_index]["outbound"], "direct")

    def test_no_udp_socks_assumption(self):
        config = build_config(Profile())
        socks = next(o for o in config["outbounds"] if o["tag"] == "warp")
        self.assertEqual(socks["network"], "tcp")
        self.assertEqual(socks["inet4_bind_address"], "127.0.0.1")
        udp_reject = next(r for r in config["route"]["rules"] if r.get("action") == "reject")
        self.assertEqual(udp_reject["network"], "udp")
        self.assertIn("process_name", udp_reject)

    def test_dns_is_verified_doh_inside_warp(self):
        server = build_config(Profile())["dns"]["servers"][0]
        self.assertEqual(server["detour"], "warp")
        self.assertEqual(server["type"], "https")
        self.assertTrue(server["tls"]["enabled"])
        self.assertNotIn("insecure", server["tls"])

    def test_optional_kernel_exclusion_only_exact_observed_hosts(self):
        profile = Profile(game_cidrs=["8.8.8.8/32", "2606:4700:4700::1001/128"])
        self.assertEqual(build_config(profile)["inbounds"][0]["route_exclude_address"], profile.game_cidrs)
        for cidr in ["0.0.0.0/0", "8.8.8.0/24", "192.168.0.1/32", "1.1.1.1/32", "8.8.8.8/33"]:
            with self.subTest(cidr=cidr), self.assertRaises(ValueError):
                Profile(game_cidrs=[cidr]).validate()

    def test_rejects_invalid_configuration_and_game_overlap(self):
        for changes in [{"platform": "linux"}, {"proxy_port": True}, {"proxy_port": 0},
                        {"mtu": 9000}, {"mtu": 1200}, {"extra_clients": ["LeagueofLegends"]},
                        {"extra_clients": ["/bin/program"]}, {"extra_clients": "LeagueClient"},
                        {"physical_interface": "en0\nmalformed"}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Profile(**changes).validate()

    def test_output_is_independent_and_interface_selection_is_exclusive(self):
        profile = Profile(physical_interface="en0")
        first = build_config(profile)
        first["route"]["rules"].clear()
        second = build_config(profile)
        self.assertTrue(second["route"]["rules"])
        self.assertNotIn("auto_detect_interface", second["route"])
        self.assertEqual(second["route"]["default_interface"], "en0")


if __name__ == "__main__":
    unittest.main()
