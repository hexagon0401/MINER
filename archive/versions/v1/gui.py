"""
gui.py - rumps MenuBarApp
"""

import rumps
import threading
import asyncio
import logging
import time
from dataclasses import asdict

from recon import run_recon, format_recon_report, PROVIDERS
from network_manager import apply_optimization, restore_original, measure_latency
from doh_proxy import DoHProxy
from locales import t, set_language
from settings import Settings

class SchoolNetApp(rumps.App):
    def __init__(self, config: Settings):
        super(SchoolNetApp, self).__init__("🛡")
        self.config = config
        set_language(self.config.language)
        
        self.recon_result = None
        self.proxy = None
        self.proxy_thread = None
        self.proxy_loop = None

        self.btn_analyze = rumps.MenuItem(t("analyze_button"), callback=self.on_analyze)
        self.btn_optimize = rumps.MenuItem(t("optimize_button"), callback=self.on_optimize)
        self.btn_restore = rumps.MenuItem(t("restore_button"), callback=self.on_restore)
        
        self.btn_optimize.set_callback(None) 
        self.btn_restore.set_callback(None)  

        self.lbl_status = rumps.MenuItem(t("status_inactive"))
        self.lbl_network = rumps.MenuItem("🌐 Network: Unknown")
        self.lbl_mode = rumps.MenuItem("🔒 Mode: -")

        self.btn_settings = rumps.MenuItem("⚙️ " + t("settings_title"), callback=self.on_settings)
        self.btn_about = rumps.MenuItem("❓ " + t("about_title"), callback=self.on_about)

        self.menu = [
            self.btn_analyze,
            None,
            self.btn_optimize,
            self.btn_restore,
            None,
            self.lbl_status,
            self.lbl_network,
            self.lbl_mode,
            None,
            self.btn_settings,
            self.btn_about,
            rumps.MenuItem("Quit", callback=self.on_quit) 
        ]
        
    def check_first_launch(self):
        if self.config.first_launch:
            rumps.alert(
                title=t("first_launch_title"),
                message=t("first_launch_body")
            )
            self.config.first_launch = False
            self.config.save()

    @rumps.timer(5)
    def update_live_status(self, _):
        if self.proxy and self.recon_result:
            p_name = self.recon_result.recommended_provider or self.config.primary_provider
            lat = measure_latency(PROVIDERS.get(p_name, PROVIDERS["quad9"]))
            self.lbl_status.title = f"{t('status_active')} · {p_name.title()} · {lat:.0f}ms"

    def _do_recon(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            res = loop.run_until_complete(run_recon())
            loop.close()
            
            self.recon_result = res
            
            if res.dns_hijacked:
                self.config.obfuscation_enabled = True
                
            summary = asyncio.run(format_recon_report(res))
            
            rumps.notification("Recon Complete", "", "Analysis done. Check menu.")
            
            self.lbl_network.title = f"🌐 Network: {res.ssid or 'Unknown'}"
            self.lbl_mode.title = f"🔒 Mode: {t('mode_' + res.recommended_mode)}"
            
            if res.recommended_mode == "passive":
                self.btn_optimize.set_callback(None)
                rumps.alert("Analysis Result", f"{t('recon_doh_blocked')}\n\n{summary}")
            elif res.captive_portal:
                self.btn_optimize.set_callback(None)
                rumps.alert("Analysis Result", f"Captive portal detected!\n\n{summary}")
            else:
                self.btn_optimize.set_callback(self.on_optimize)
                rumps.alert("Analysis Result", summary)
                
            self.config.last_ssid = res.ssid
            self.config.save()
            
        except Exception as e:
            rumps.alert("Error", str(e))

    def on_analyze(self, _):
        rumps.alert("Notice", "Analyzing network... (takes ~5s)")
        threading.Thread(target=self._do_recon, daemon=True).start()

    def _start_proxy_thread(self):
        self.proxy_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.proxy_loop)
        self.proxy = DoHProxy(self.recon_result, self.config)
        self.proxy_loop.run_until_complete(self.proxy.start())
        self.proxy_loop.close()

    def _do_optimize(self):
        try:
            self.proxy_thread = threading.Thread(target=self._start_proxy_thread, daemon=True)
            self.proxy_thread.start()
            
            time.sleep(1) 
            
            loop = asyncio.new_event_loop()
            opt_res = loop.run_until_complete(apply_optimization(self.recon_result, self.config))
            loop.close()
            
            if opt_res.success:
                p_name = self.recon_result.recommended_provider or self.config.primary_provider
                lat = measure_latency(PROVIDERS.get(p_name, PROVIDERS["quad9"]))
                self.lbl_status.title = f"{t('status_active')} · {p_name.title()} · {lat:.0f}ms"
                
                rumps.notification(
                    "SchoolNet Optimizer",
                    "",
                    t("notification_optimized")
                )
                self.btn_optimize.set_callback(None)
                self.btn_restore.set_callback(self.on_restore)
            else:
                rumps.alert("Optimization Failed", str(opt_res.error))
                self.on_restore(None)
                
        except Exception as e:
            rumps.alert("Error", str(e))
            self.on_restore(None)

    def on_optimize(self, _):
        if not self.recon_result:
            self.on_analyze(None)
            return

        threading.Thread(target=self._do_optimize, daemon=True).start()

    def _do_restore(self):
        if self.proxy:
            if self.proxy_loop:
                asyncio.run_coroutine_threadsafe(self.proxy.stop(), self.proxy_loop)
            self.proxy_thread.join(timeout=2)
            self.proxy = None
            
        if self.recon_result:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(restore_original(self.recon_result, self.config))
            loop.close()
            
        self.lbl_status.title = t("status_inactive")
        self.btn_optimize.set_callback(self.on_optimize)
        self.btn_restore.set_callback(None)
        
        rumps.notification("SchoolNet Optimizer", "", t("notification_restored"))

    def on_restore(self, _):
        threading.Thread(target=self._do_restore, daemon=True).start()

    def on_settings(self, _):
        window = rumps.Window(
            title=t("settings_title"),
            message="Format: [provider: quad9/cloudflare/adguard], [obfuscation: y/n], [autostart: y/n], [lang: ko/en]\ne.g. quad9, y, n, ko",
            default_text=f"{self.config.primary_provider}, {'y' if self.config.obfuscation_enabled else 'n'}, {'y' if self.config.auto_start else 'n'}, {self.config.language}",
            dimensions=(300, 50)
        )
        response = window.run()
        if response.clicked:
            parts = [p.strip() for p in response.text.split(',')]
            if len(parts) >= 4:
                self.config.primary_provider = parts[0]
                self.config.obfuscation_enabled = parts[1].lower() == 'y'
                self.config.auto_start = parts[2].lower() == 'y'
                self.config.language = parts[3]
                
                self.config.save()
                set_language(self.config.language)
                
                if self.config.auto_start:
                    self.config.enable_autostart()
                else:
                    self.config.disable_autostart()
                    
                rumps.alert("Settings Saved", "Changes applied.")

    def on_about(self, _):
        msg = "Version 1.0.0\n\n"
        msg += t("warning_mac") + "\n"
        msg += t("warning_dpi") + "\n"
        msg += t("warning_restore")
        rumps.alert(t("about_title"), msg)

    def on_quit(self, _):
        self._do_restore()
        rumps.quit_application()
