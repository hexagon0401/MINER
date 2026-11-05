import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from main import main
from schoolnet.config import Profile, build_config
from schoolnet.runtime import check_engine, instance_lock, warp_mode, write_json
from schoolnet.probe import socks_connect


class RuntimeTests(unittest.TestCase):
    def test_stale_temporary_file_does_not_block_settings_and_bad_json_preserves_previous(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"settings.json"
            stale=path.with_suffix(".json.tmp");stale.write_text("interrupted earlier save")
            write_json(path,{"language":"ko"})
            self.assertEqual({"language":"ko"},json.loads(path.read_text()))
            with self.assertRaises(TypeError):write_json(path,{"bad":object()})
            self.assertEqual({"language":"ko"},json.loads(path.read_text()))
            self.assertEqual("interrupted earlier save",stale.read_text())
    def test_init_preserves_existing_profile_and_render_regenerates(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["init", "--directory", directory]), 0)
            path = Path(directory) / "profile.json"
            before = path.read_bytes()
            self.assertEqual(main(["init", "--directory", directory, "--proxy-port", "45678"]), 1)
            self.assertEqual(path.read_bytes(), before)
            profile = json.loads(before)
            profile["proxy_port"] = 45678
            write_json(path, profile)
            self.assertEqual(main(["render", "--directory", directory]), 0)
            config = json.loads((Path(directory) / "sing-box.json").read_text())
            self.assertEqual(config["outbounds"][1]["server_port"], 45678)

    def test_profile_lock_is_exclusive_and_released(self):
        with tempfile.TemporaryDirectory() as directory:
            with instance_lock(directory):
                with self.assertRaises(ValueError):
                    with instance_lock(directory):
                        pass
            with instance_lock(directory):
                pass

    def test_warp_full_tunnel_and_unknown_output_rejected(self):
        for output in ["Mode: WarpWithDnsOverHttps\n", "unrecognized output", "Mode: WarpProxyFake\n"]:
            with self.subTest(output=output), patch("schoolnet.runtime.Path.is_file", return_value=True), patch(
                "schoolnet.runtime.subprocess.run", return_value=subprocess.CompletedProcess([], 0, stdout=output)
            ), self.assertRaises(ValueError):
                warp_mode("/fixture/warp-cli")

    def test_warp_proxy_mode_recognized_without_dumping_settings(self):
        with patch("schoolnet.runtime.Path.is_file", return_value=True), patch(
            "schoolnet.runtime.subprocess.run", return_value=subprocess.CompletedProcess(
                [], 0, stdout="(Custom configuration) Mode: WarpProxy on port 40000\n")
        ):
            self.assertEqual(warp_mode("/fixture/warp-cli"), "WarpProxy")

    def test_engine_version_rejected_before_execution(self):
        with patch("schoolnet.runtime.subprocess.run", return_value=subprocess.CompletedProcess(
            [], 0, stdout="sing-box version 1.13.0\n")) as call, self.assertRaises(ValueError):
            check_engine("sing-box", "unused.json")
        self.assertEqual(call.call_count, 1)

    def test_proxy_port_mismatch_rejected(self):
        with patch("schoolnet.runtime.Path.is_file", return_value=True), patch(
            "schoolnet.runtime.subprocess.run", return_value=subprocess.CompletedProcess(
                [], 0, stdout="Mode: WarpProxy on port 45678\n")
        ), self.assertRaisesRegex(ValueError, "port differs"):
            warp_mode("/fixture/warp-cli", 40000)

    @unittest.skipUnless(os.name == "posix", "POSIX process signaling integration")
    def test_termination_reaches_child_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "cleaned"
            engine = root / "fake-engine"
            engine.write_text(f'''#!{sys.executable}
import signal, time
from pathlib import Path
def stop(*args):
    Path({str(marker)!r}).write_text("graceful")
    raise SystemExit(0)
signal.signal(signal.SIGTERM, stop)
print("fixture-ready", flush=True)
while True: time.sleep(.05)
''')
            engine.chmod(0o755)
            code = f'''from schoolnet import runtime
runtime.doctor = lambda *a: {{"preflight_ok": True, "engine": {str(engine)!r}}}
runtime.is_admin = lambda: True
raise SystemExit(runtime.run({directory!r}))
'''
            child = subprocess.Popen([sys.executable, "-u", "-c", code], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True)
            try:
                self.assertIn("Engine starting", child.stdout.readline())
                self.assertIn("fixture-ready", child.stdout.readline())
                child.send_signal(signal.SIGTERM)
                stdout, stderr = child.communicate(timeout=5)
                self.assertEqual(child.returncode, 0, stderr)
                self.assertEqual(marker.read_text(), "graceful")
                self.assertIn("Engine exited", stdout)
                with instance_lock(directory):
                    pass
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()


class EngineIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("SCHOOLNET_TEST_ENGINE"), "set SCHOOLNET_TEST_ENGINE for real schema validation")
    def test_both_platforms_with_actual_pinned_engine(self):
        engine = os.environ["SCHOOLNET_TEST_ENGINE"]
        with tempfile.TemporaryDirectory() as directory:
            for platform in ["macos", "windows"]:
                with self.subTest(platform=platform):
                    path = Path(directory) / "config.json"
                    write_json(path, build_config(Profile(platform=platform)))
                    check_engine(engine, path)

    @unittest.skipUnless(os.environ.get("SCHOOLNET_TEST_ENGINE"), "set SCHOOLNET_TEST_ENGINE for engine outbound integration")
    def test_real_engine_socks_chain_without_tun_or_route_changes(self):
        from test_probe import server, SocksHandler, TCPHandler
        engine = os.environ["SCHOOLNET_TEST_ENGINE"]
        with tempfile.TemporaryDirectory() as directory, server(TCPHandler) as target, server(SocksHandler) as proxy:
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                listen_port = reservation.getsockname()[1]
            config = build_config(Profile(proxy_port=proxy))
            # Replace TUN with a loopback SOCKS listener. Select the generated WARP
            # outbound explicitly: process attribution still requires native TUN tests.
            config["inbounds"] = [{"type": "socks", "tag": "smoke", "listen": "127.0.0.1", "listen_port": listen_port}]
            config["route"]["rules"].insert(0, {"inbound": ["smoke"], "action": "route", "outbound": "warp"})
            path = Path(directory) / "config.json"
            write_json(path, config)
            with (Path(directory) / "engine.log").open("w+") as log:
                child = subprocess.Popen([engine, "run", "-c", str(path)], stdout=log, stderr=log)
                try:
                    deadline = time.monotonic() + 5
                    while True:
                        try:
                            sock = socket.create_connection(("127.0.0.1", listen_port), timeout=1)
                            break
                        except OSError:
                            if time.monotonic() > deadline or child.poll() is not None:
                                log.seek(0)
                                self.fail(log.read())
                            time.sleep(.02)
                    with sock:
                        socks_connect(sock, "127.0.0.1", target)
                    log.flush()
                finally:
                    child.terminate()
                    child.wait(timeout=5)
                log.seek(0)
                self.assertIn("outbound/socks[warp]", log.read())


if __name__ == "__main__":
    unittest.main()
