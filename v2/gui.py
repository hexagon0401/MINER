"""
gui.py - rumps MenuBarApp (v2)

Fixes vs v1:
- [Critical] on_quit: daemon thread + 즉시 quit → DNS 127.0.0.1 고착 버그
  → restore를 동기로 완료한 후 quit 실행
- [Critical] proxy 준비 대기: sleep(1) → proxy.ready(threading.Event) 대기
- [Race] 동시 작업 방지: _busy 플래그로 중복 실행 차단
- [Blocking] measure_latency: 동기 HTTP → 비동기 루프에서 실행 (UI 블로킹 방지)
- [UX] 설정 UI: CSV 입력 → 개별 항목별 Window
- [i18n] Quit 버튼 번역 추가
- asyncio 이벤트 루프 재사용 패턴 정리
"""

import rumps
import threading
import asyncio
import logging
import time
from dataclasses import asdict

from recon import run_recon, format_recon_report, PROVIDERS
from network_manager import apply_optimization, restore_original, measure_latency_async
from doh_proxy import DoHProxy
from locales import t, set_language
from settings import Settings


def _run_async(coro):
    """새 이벤트 루프를 만들어 코루틴을 동기적으로 실행."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class SchoolNetApp(rumps.App):
    def __init__(self, config: Settings):
        super().__init__("🛡")
        self.config = config
        set_language(self.config.language)

        self.recon_result  = None
        self.proxy:        DoHProxy | None = None
        self.proxy_thread: threading.Thread | None = None
        self.proxy_loop:   asyncio.AbstractEventLoop | None = None

        # 동시 작업 방지 플래그
        self._busy = False

        self.btn_analyze  = rumps.MenuItem(t("analyze_button"),  callback=self.on_analyze)
        self.btn_optimize = rumps.MenuItem(t("optimize_button"), callback=None)  # 분석 전 비활성
        self.btn_restore  = rumps.MenuItem(t("restore_button"),  callback=None)  # 최적화 전 비활성

        self.lbl_status  = rumps.MenuItem(t("status_inactive"))
        self.lbl_network = rumps.MenuItem("🌐 Network: Unknown")
        self.lbl_mode    = rumps.MenuItem("🔒 Mode: -")

        self.btn_settings = rumps.MenuItem("⚙️ " + t("settings_title"), callback=self.on_settings)
        self.btn_about    = rumps.MenuItem("❓ " + t("about_title"),    callback=self.on_about)
        self.btn_quit     = rumps.MenuItem(t("quit_label"),             callback=self.on_quit)

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
            self.btn_quit,
        ]

    def check_first_launch(self):
        if self.config.first_launch:
            rumps.alert(t("first_launch_title"), t("first_launch_body"))
            self.config.first_launch = False
            self.config.save()

    # ──────────────────────────────────────────
    # Live status timer (비동기 latency 측정)
    # ──────────────────────────────────────────

    @rumps.timer(10)
    def update_live_status(self, _):
        """latency 측정을 별도 스레드에서 비동기로 실행 → UI 블로킹 방지."""
        if not self.proxy or not self.recon_result:
            return

        p_name = self.recon_result.recommended_provider or self.config.primary_provider
        url = PROVIDERS.get(p_name, PROVIDERS["quad9"])

        def _update():
            lat = _run_async(measure_latency_async(url))
            self.lbl_status.title = f"{t('status_active')} · {p_name.title()} · {lat:.0f}ms"

        threading.Thread(target=_update, daemon=True).start()

    # ──────────────────────────────────────────
    # Analyze
    # ──────────────────────────────────────────

    def _do_recon(self):
        try:
            res = _run_async(run_recon())
            self.recon_result = res

            if res.dns_hijacked:
                self.config.obfuscation_enabled = True

            summary = format_recon_report(res)

            self.lbl_network.title = f"🌐 Network: {res.ssid or 'Unknown'}"
            self.lbl_mode.title    = f"🔒 Mode: {t('mode_' + res.recommended_mode)}"

            if res.recommended_mode == "passive":
                self.btn_optimize.set_callback(None)
                rumps.alert("분석 결과", f"{t('recon_doh_blocked')}\n\n{summary}")
            elif res.captive_portal:
                self.btn_optimize.set_callback(None)
                rumps.alert("분석 결과", f"Captive portal 감지!\n\n{summary}")
            else:
                self.btn_optimize.set_callback(self.on_optimize)
                rumps.alert("분석 결과", summary)

            self.config.last_ssid = res.ssid
            self.config.save()

        except Exception as e:
            logging.exception("Recon failed")
            rumps.alert("오류", str(e))
        finally:
            self._busy = False

    def on_analyze(self, _):
        if self._busy:
            rumps.alert("알림", "현재 다른 작업이 진행 중입니다.")
            return
        self._busy = True
        rumps.notification("SchoolNet Optimizer", "", "네트워크 분석 중... (~5초)")
        threading.Thread(target=self._do_recon, daemon=True).start()

    # ──────────────────────────────────────────
    # Optimize
    # ──────────────────────────────────────────

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

            # [Fix] sleep(1) → proxy.ready 이벤트 대기 (최대 5초)
            # proxy가 생성되기 전 self.proxy가 None일 수 있으므로 thread 시작 직후 대기
            deadline = time.time() + 5.0
            while self.proxy is None and time.time() < deadline:
                time.sleep(0.05)

            if self.proxy is None or not self.proxy.ready.wait(timeout=3.0):
                rumps.alert("오류", "프록시가 시작되지 않았습니다. 잠시 후 다시 시도하세요.")
                self._do_restore()
                return

            opt_res = _run_async(apply_optimization(self.recon_result, self.config))

            if opt_res.success:
                p_name = self.recon_result.recommended_provider or self.config.primary_provider
                lat = _run_async(measure_latency_async(PROVIDERS.get(p_name, PROVIDERS["quad9"])))
                self.lbl_status.title = f"{t('status_active')} · {p_name.title()} · {lat:.0f}ms"
                rumps.notification("SchoolNet Optimizer", "", t("notification_optimized"))
                self.btn_optimize.set_callback(None)
                self.btn_restore.set_callback(self.on_restore)
            else:
                rumps.alert("최적화 실패", str(opt_res.error))
                self._do_restore()

        except Exception as e:
            logging.exception("Optimize failed")
            rumps.alert("오류", str(e))
            self._do_restore()
        finally:
            self._busy = False

    def on_optimize(self, _):
        if self._busy:
            rumps.alert("알림", "현재 다른 작업이 진행 중입니다.")
            return
        if not self.recon_result:
            self.on_analyze(None)
            return
        self._busy = True
        threading.Thread(target=self._do_optimize, daemon=True).start()

    # ──────────────────────────────────────────
    # Restore (버튼 클릭용 — 별도 스레드)
    # ──────────────────────────────────────────

    def _do_restore(self):
        if self.proxy and self.proxy_loop:
            future = asyncio.run_coroutine_threadsafe(self.proxy.stop(), self.proxy_loop)
            try:
                future.result(timeout=5)
            except Exception:
                pass
        if self.proxy_thread:
            self.proxy_thread.join(timeout=3)
        self.proxy        = None
        self.proxy_thread = None
        self.proxy_loop   = None

        if self.recon_result:
            _run_async(restore_original(self.recon_result, self.config))

        self.lbl_status.title = t("status_inactive")
        self.btn_optimize.set_callback(self.on_optimize if self.recon_result else None)
        self.btn_restore.set_callback(None)
        rumps.notification("SchoolNet Optimizer", "", t("notification_restored"))

    def on_restore(self, _):
        if self._busy:
            rumps.alert("알림", "현재 다른 작업이 진행 중입니다.")
            return
        self._busy = True
        def _thread():
            self._do_restore()
            self._busy = False
        threading.Thread(target=_thread, daemon=True).start()

    # ──────────────────────────────────────────
    # Settings (UX 개선: 개별 항목 입력)
    # ──────────────────────────────────────────

    def on_settings(self, _):
        # Provider 선택
        win_provider = rumps.Window(
            title=t("settings_title"),
            message=f"DoH Provider (quad9 / cloudflare / adguard)\n현재: {self.config.primary_provider}",
            default_text=self.config.primary_provider,
            dimensions=(300, 30),
        )
        r = win_provider.run()
        if not r.clicked:
            return
        provider = r.text.strip().lower()
        if provider not in ("quad9", "cloudflare", "adguard"):
            rumps.alert("오류", f"알 수 없는 provider: {provider}")
            return

        # Obfuscation
        win_obs = rumps.Window(
            title=t("settings_title"),
            message=f"난독화 모드 (y / n)\n현재: {'y' if self.config.obfuscation_enabled else 'n'}",
            default_text="y" if self.config.obfuscation_enabled else "n",
            dimensions=(300, 30),
        )
        r = win_obs.run()
        if not r.clicked:
            return
        obfuscation = r.text.strip().lower() == "y"

        # Language
        win_lang = rumps.Window(
            title=t("settings_title"),
            message=f"언어 (ko / en)\n현재: {self.config.language}",
            default_text=self.config.language,
            dimensions=(300, 30),
        )
        r = win_lang.run()
        if not r.clicked:
            return
        lang = r.text.strip().lower()
        if lang not in ("ko", "en"):
            rumps.alert("오류", f"알 수 없는 언어: {lang}")
            return

        # Autostart
        win_auto = rumps.Window(
            title=t("settings_title"),
            message=f"자동 시작 (y / n)\n현재: {'y' if self.config.auto_start else 'n'}",
            default_text="y" if self.config.auto_start else "n",
            dimensions=(300, 30),
        )
        r = win_auto.run()
        if not r.clicked:
            return
        auto_start = r.text.strip().lower() == "y"

        self.config.primary_provider    = provider
        self.config.obfuscation_enabled = obfuscation
        self.config.language            = lang
        self.config.auto_start          = auto_start
        self.config.save()
        set_language(lang)

        if auto_start:
            self.config.enable_autostart()
        else:
            self.config.disable_autostart()

        rumps.alert(t("settings_title"), "설정이 저장되었습니다.")

    # ──────────────────────────────────────────
    # About / Quit
    # ──────────────────────────────────────────

    def on_about(self, _):
        msg = "Version 2.0.0\n\n"
        msg += t("warning_mac") + "\n"
        msg += t("warning_dpi") + "\n"
        msg += t("warning_restore")
        rumps.alert(t("about_title"), msg)

    def on_quit(self, _):
        """
        [Fix] v1: daemon thread에서 restore → 완료 전 quit → DNS 고착
        v2: restore를 동기로 완료한 후 종료
        """
        # 프록시 중지 및 DNS 복원 (블로킹)
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
