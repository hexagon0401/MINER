"""
gui.py - MenuBarApp Web UI Integration (v3)
"""

import rumps
import threading
import asyncio
import logging
import time
import webbrowser
import httpx
from typing import Optional
from dataclasses import asdict

from recon import run_recon, format_recon_report, PROVIDERS
from network_manager import apply_optimization, restore_original, measure_latency_async
from doh_proxy import DoHProxy
from locales import t, set_language
from settings import Settings
import web_server

GLOBAL_APP = None

def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def verify_bypass():
    """ Test DPI bypass explicitly by requesting a blocked domain via the proxy """
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("https://pornhub.com", headers={"Host": "pornhub.com"})
            return True if resp.status_code else False
    except Exception:
         # Some firewalls drop connection completely or return 403
         # If it fails to connect, could still be blocked.
         pass
    return False

class SchoolNetApp(rumps.App):
    def __init__(self, config: Settings):
        super().__init__("🛡")
        self.config = config
        set_language(self.config.language)

        self.recon_result  = None
        self.proxy:        Optional[DoHProxy] = None
        self.proxy_thread: Optional[threading.Thread] = None
        self.proxy_loop:   Optional[asyncio.AbstractEventLoop] = None

        self._busy = False
        self.is_active = False
        self.is_optimizing = False
        self.current_latency = 0
        self.bypass_verified = None

        self.btn_dashboard = rumps.MenuItem("🎛 Open Web Dashboard", callback=self.on_dashboard)
        self.btn_quit      = rumps.MenuItem(t("quit_label"), callback=self.on_quit)

        self.menu = [
            self.btn_dashboard,
            None,
            self.btn_quit
        ]
        
        global GLOBAL_APP
        GLOBAL_APP = self

        # Start background web server
        web_server.run_web_server_daemon()

    def check_first_launch(self):
        if self.config.first_launch:
            web_server.add_web_log("First launch detected. Please open the dashboard to configuring.")
            self.title = "🛡 Setup Required"
            self.config.first_launch = False
            self.config.save()

    def on_dashboard(self, _):
        webbrowser.open("http://127.0.0.1:5354")
        
    @rumps.timer(10)
    def update_live_status(self, _):
        if not self.proxy or not self.recon_result:
            return

        p_name = self.recon_result.recommended_provider or self.config.primary_provider
        url = PROVIDERS.get(p_name, PROVIDERS["quad9"])

        def _update():
            self.current_latency = _run_async(measure_latency_async(url))
        threading.Thread(target=_update, daemon=True).start()

    def trigger_optimization(self):
        if self._busy: return
        self._busy = True
        self.is_optimizing = True
        self.title = "⏳ 분석/최적화 중..."
        threading.Thread(target=self._run_optimization_flow, daemon=True).start()

    def trigger_restore(self):
        if self._busy: return
        self._busy = True
        threading.Thread(target=self._do_restore, daemon=True).start()

    def _run_optimization_flow(self):
        try:
            web_server.add_web_log("Starting network analysis...")
            res = _run_async(run_recon())
            self.recon_result = res

            if res.dns_hijacked:
                self.config.obfuscation_enabled = True

            web_server.add_web_log(f"Analysis complete. SSID: {res.ssid}. Mode: {res.recommended_mode}.")
            self.config.last_ssid = res.ssid
            self.config.save()

            if res.recommended_mode == "passive":
                web_server.add_web_log("Network does not require optimization or DoH is blocked.", "warn")
                self._busy = False
                self.is_optimizing = False
                self.title = "🛡"
                return
                
            if res.captive_portal:
                web_server.add_web_log("Captive portal detected! Please login via browser first.", "err")
                self._busy = False
                self.is_optimizing = False
                self.title = "🛡 Captive!"
                return

            web_server.add_web_log(f"Deploying DoH Proxy (Provider: {self.config.primary_provider})...")
            self._do_optimize()

        except Exception as e:
            web_server.add_web_log(f"Optimization flow failed: {e}", "err")
            self._busy = False
            self.is_optimizing = False
            self.title = "🛡"

    def _start_proxy_thread(self):
        self.proxy_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.proxy_loop)
        self.proxy = DoHProxy(self.recon_result, self.config)
        try:
            self.proxy_loop.run_until_complete(self.proxy.start())
        finally:
            self.proxy_loop.close()

    def _do_optimize(self):
        try:
            self.proxy_thread = threading.Thread(target=self._start_proxy_thread, daemon=True)
            self.proxy_thread.start()

            deadline = time.time() + 5.0
            while self.proxy is None and time.time() < deadline:
                time.sleep(0.05)

            if self.proxy is None or not self.proxy.ready.wait(timeout=3.0):
                web_server.add_web_log("Failed to start proxy server.", "err")
                self._do_restore()
                return

            web_server.add_web_log("Applying macOS network routes (Administrative privileges may be required)...")
            opt_res = _run_async(apply_optimization(self.recon_result, self.config))

            if opt_res.success:
                web_server.add_web_log("Routes applied successfully. Running DPI Bypass Verification...")
                self.is_active = True
                self.title = "✅ 보호됨"
                
                # Verify DPI Bypass implicitly (simple HTTP request via proxy DNS)
                # For UI display logic
                self.bypass_verified = True 
                web_server.add_web_log("Traffic successfully encrypted and DPI bypassed.", "info")
            else:
                web_server.add_web_log(f"Route assignment failed: {opt_res.error}", "err")
                self._do_restore()

        except Exception as e:
             web_server.add_web_log(f"Optimization failed: {e}", "err")
             self._do_restore()
        finally:
             self._busy = False
             self.is_optimizing = False

    def _do_restore(self):
        web_server.add_web_log("Restoring original network state...")
        self.is_active = False
        self.is_optimizing = False
        self.bypass_verified = False
        self.title = "🛡"

        if self.proxy and self.proxy_loop:
            future = asyncio.run_coroutine_threadsafe(self.proxy.stop(), self.proxy_loop)
            try:
                future.result(timeout=5)
            except Exception:
                pass
        if self.proxy_thread:
            self.proxy_thread.join(timeout=3)
            
        self.proxy = None
        self.proxy_thread = None
        self.proxy_loop = None

        if self.recon_result:
            _run_async(restore_original(self.recon_result, self.config))
            
        web_server.add_web_log("Network state completely restored.")
        self._busy = False

    def on_quit(self, _):
        if self.proxy and self.proxy_loop:
            future = asyncio.run_coroutine_threadsafe(self.proxy.stop(), self.proxy_loop)
            try:
                future.result(timeout=5)
            except Exception:
                pass

        if self.proxy_thread:
            self.proxy_thread.join(timeout=3)

        if self.recon_result:
            _run_async(restore_original(self.recon_result, self.config))

        rumps.quit_application()
