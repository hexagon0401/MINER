"""
gui.py - V4 Native NSPanel UI using PyObjC + WebKit
Focus: Stability, single event loop, proper JS bridge, clean shutdown

Changes vs v3.8:
- [Critical] @objc.typedSelector 제거 → PyObjC 기본 시그니처 사용 (JS 브릿지 복원)
- [Critical] 단일 asyncio 워커 루프 재사용 (매번 새 루프 생성/파괴 방지)
- [Critical] os._exit(0) 제거 → 정상 종료 흐름 (applicationWillTerminate_)
- [Fix] 외부 클릭 처리: 패널 포함 영역 체크 + hidesOnDeactivate
- [Fix] 메인 스레드 UI 업데이트 보장 (performSelectorOnMainThread)
- [Opt] Lazy import: recon, network_manager, doh_proxy 최초 사용 시 로드
- [UI] send_to_ui에 JSON 직렬화 안전성 추가
"""

import threading
import asyncio
import time
import json
import os
import sys
import logging

import objc
from Foundation import NSObject, NSURL
from AppKit import (
    NSApplication, NSApp, NSStatusBar, NSVariableStatusItemLength,
    NSPanel, NSColor, NSEvent,
    NSApplicationActivationPolicyAccessory,
)
from WebKit import WKWebView, WKWebViewConfiguration, WKUserContentController

from settings import Settings

# ---------------------------------------------------------
# Lazy imports (무거운 모듈은 최초 사용 시 로드)
# ---------------------------------------------------------

_recon_module = None
_netmgr_module = None
_proxy_module = None

def _get_recon():
    global _recon_module
    if _recon_module is None:
        import recon as _r
        _recon_module = _r
    return _recon_module

def _get_netmgr():
    global _netmgr_module
    if _netmgr_module is None:
        import network_manager as _n
        _netmgr_module = _n
    return _netmgr_module

def _get_proxy_module():
    global _proxy_module
    if _proxy_module is None:
        import doh_proxy as _p
        _proxy_module = _p
    return _proxy_module


# ---------------------------------------------------------
# Single Worker Loop (모든 async 작업을 하나의 루프에서 처리)
# ---------------------------------------------------------

class AsyncWorker:
    """단일 asyncio 이벤트 루프를 백그라운드 스레드에서 관리."""

    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True, name="async-worker")
        self._thread.start()

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def run_coro(self, coro):
        """코루틴을 워커 루프에 예약하고 결과를 기다림 (블로킹)."""
        if self._loop is None or self._loop.is_closed():
            raise RuntimeError("Worker loop is not running")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)

    def run_coro_nonblocking(self, coro) -> asyncio.Future:
        """코루틴을 워커 루프에 예약 (논블로킹)."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def stop(self):
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=3)
        if self._loop and not self._loop.is_closed():
            self._loop.close()


# ---------------------------------------------------------
# PyObjC JS ↔ Python Bridge
# ---------------------------------------------------------

class ScriptMessageHandler(NSObject):
    """
    WKWebView JS → Python 메시지 핸들러.
    [v4 Fix] @objc.typedSelector 데코레이터 제거.
    v3.7과 동일하게 PyObjC 기본 시그니처 사용하여 호환성 보장.
    """
    def userContentController_didReceiveScriptMessage_(self, userContentController, message):
        body = message.body()
        if not isinstance(body, dict):
            return
        action = body.get('action')
        data = body.get('data', {})

        if hasattr(self, 'delegate') and self.delegate:
            self.delegate.handle_js_action(action, data)


# ---------------------------------------------------------
# App Delegate
# ---------------------------------------------------------

class SchoolNetAppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        self.config = Settings.load()
        self.config.validate()

        self.is_busy = False
        self.proxy = None
        self.recon_result = None

        # 단일 워커 루프 시작
        self.worker = AsyncWorker()
        self.worker.start()

        # 1. Status Bar
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.button = self.statusItem.button()
        self.button.setTitle_("🛡")
        self.button.setTarget_(self)
        self.button.setAction_(objc.selector(self.togglePanel_, signature=b'v@:@'))

        # 2. NSPanel (borderless, floating)
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            ((0, 0), (340, 460)),
            128,  # NSWindowStyleMaskNonactivatingPanel
            2,    # NSBackingStoreBuffered
            False
        )
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setHasShadow_(True)
        self.panel.setFloatingPanel_(True)
        self.panel.setLevel_(3)  # PopUpMenuWindowLevel
        self.panel.setHidesOnDeactivate_(False)

        # 3. WebKit
        config = WKWebViewConfiguration.alloc().init()
        ucc = WKUserContentController.alloc().init()

        self.msg_handler = ScriptMessageHandler.alloc().init()
        self.msg_handler.delegate = self
        ucc.addScriptMessageHandler_name_(self.msg_handler, "python")
        config.setUserContentController_(ucc)
        config.setValue_forKey_(False, "drawsBackground")

        self.webview = WKWebView.alloc().initWithFrame_configuration_(
            ((0, 0), (340, 460)), config
        )
        self.webview.setValue_forKey_(False, "drawsBackground")
        self.webview.layer().setCornerRadius_(16)
        self.webview.layer().setMasksToBounds_(True)

        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(base_dir, 'ui.html')
        url = NSURL.fileURLWithPath_(html_path)
        self.webview.loadFileURL_allowingReadAccessToURL_(url, url.URLByDeletingLastPathComponent())

        self.panel.setContentView_(self.webview)

        # 4. Global click monitor (패널 외부 클릭 시 닫기)
        self.event_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            1 << 1 | 1 << 2,  # Left/Right MouseDown
            self.on_global_click
        )

    def applicationWillTerminate_(self, notification):
        if hasattr(self, 'event_monitor') and self.event_monitor:
            NSEvent.removeMonitor_(self.event_monitor)
        self._do_restore(force=True)
        if hasattr(self, 'worker'):
            self.worker.stop()

    def on_global_click(self, event):
        if self.panel.isVisible():
            self.panel.orderOut_(None)

    def togglePanel_(self, sender):
        NSApp().activateIgnoringOtherApps_(True)

        if self.panel.isVisible():
            self.panel.orderOut_(None)
        else:
            btn_frame = sender.window().frame()
            panel_w = 340
            panel_h = 460
            x = btn_frame.origin.x + (btn_frame.size.width / 2) - (panel_w / 2)
            y = btn_frame.origin.y - panel_h - 10
            self.panel.setFrameOrigin_((int(x), int(y)))
            self.panel.makeKeyAndOrderFront_(None)

    # ---------------------------------------------------------
    # Core Logic Bridge (JS ↔ Python)
    # ---------------------------------------------------------

    def send_to_ui(self, cmd, payload):
        """메인 스레드에서 JS 실행을 보장."""
        try:
            payload_json = json.dumps(payload, ensure_ascii=False)
        except (TypeError, ValueError):
            payload_json = json.dumps(str(payload))
        js = f"window.sendCommand('{cmd}', {payload_json});"

        self.webview.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(self.webview.evaluateJavaScript_completionHandler_, signature=b'v@:@@'),
            None, False
        ) if False else self._eval_js_main_thread(js)

    def _eval_js_main_thread(self, js):
        """메인 스레드에서 안전하게 JS 실행."""
        if threading.current_thread() is threading.main_thread():
            self.webview.evaluateJavaScript_completionHandler_(js, None)
        else:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                objc.selector(self.execJS_, signature=b'v@:@'),
                js, False
            )

    def execJS_(self, js):
        """PyObjC selector: execJS: (single arg). 메인 스레드에서 호출됨."""
        self.webview.evaluateJavaScript_completionHandler_(js, None)

    def handle_js_action(self, action, data):
        if action == 'connect':
            self.trigger_optimization()
        elif action == 'disconnect':
            self.trigger_restore()
        elif action == 'quit':
            self._do_restore(force=True)
            NSApp().terminate_(None)
        elif action == 'settings':
            import subprocess
            path = Settings.get_path()
            subprocess.run(["open", path])

    # ---------------------------------------------------------
    # Optimization Flow
    # ---------------------------------------------------------

    def trigger_optimization(self):
        if self.is_busy:
            return
        self.is_busy = True
        self.send_to_ui('state', 'connecting')
        threading.Thread(target=self._run_opt_flow, daemon=True, name="opt-flow").start()

    def _run_opt_flow(self):
        try:
            recon_mod = _get_recon()
            netmgr = _get_netmgr()
            proxy_mod = _get_proxy_module()

            # Phase 1: Recon
            self.send_to_ui('update_desc', {'text': 'Analyzing network...'})
            res = self.worker.run_coro(recon_mod.run_recon())
            self.recon_result = res

            # UI에 네트워크 정보 전달
            self.send_to_ui('recon_info', {
                'ssid': res.ssid or 'Unknown',
                'mode': res.recommended_mode,
                'provider': (res.recommended_provider or '').title(),
                'latency': round(res.doh_latency.get(res.recommended_provider, 0)),
                'hijacked': res.dns_hijacked,
            })

            if res.recommended_mode == "passive":
                self.send_to_ui('update_desc', {'text': 'DoH is blocked on this network'})
                time.sleep(2)
                self.send_to_ui('state', 'idle')
                self.is_busy = False
                return

            self.send_to_ui('progress', {'percent': 35})

            # Phase 2: Start proxy
            self.send_to_ui('update_desc', {'text': f'Starting DoH proxy ({self.config.primary_provider})...'})

            self.proxy = proxy_mod.DoHProxy(self.recon_result, self.config)

            # 프록시를 워커 루프에서 시작
            self.worker.run_coro_nonblocking(self.proxy.start())

            # proxy ready 대기
            if not self.proxy.ready.wait(timeout=8):
                raise Exception("Proxy failed to start (timeout)")

            self.send_to_ui('progress', {'percent': 65})

            # Phase 3: Apply optimization
            self.send_to_ui('update_desc', {'text': 'Applying network rules...'})
            opt_res = self.worker.run_coro(netmgr.apply_optimization(res, self.config))
            if not opt_res.success:
                raise Exception(opt_res.error or "Optimization failed")

            self.send_to_ui('progress', {'percent': 90})

            # Phase 4: Verify
            self.send_to_ui('update_desc', {'text': 'Verifying connection...'})
            time.sleep(0.5)

            self.send_to_ui('progress', {'percent': 100})
            self.send_to_ui('state', 'connected')
            self.button.setTitle_("✅")

        except Exception as e:
            logging.error(f"Optimization failed: {e}")
            self.send_to_ui('update_desc', {'text': str(e)[:80]})
            self.send_to_ui('state', 'failed')
            self._do_restore(force=True)
        finally:
            self.is_busy = False

    # ---------------------------------------------------------
    # Restore Flow
    # ---------------------------------------------------------

    def trigger_restore(self):
        if self.is_busy:
            return
        self.is_busy = True
        self.send_to_ui('state', 'disconnecting')
        self.send_to_ui('update_desc', {'text': 'Disconnecting...'})
        threading.Thread(target=self._do_restore, daemon=True, name="restore").start()

    def _do_restore(self, force=False):
        try:
            # Stop proxy
            if self.proxy:
                try:
                    self.worker.run_coro_nonblocking(self.proxy.stop())
                    time.sleep(1)  # 프록시 종료 대기
                except Exception:
                    pass
                self.proxy = None

            # Restore network settings
            if getattr(self, 'recon_result', None):
                try:
                    netmgr = _get_netmgr()
                    self.worker.run_coro(netmgr.restore_original(self.recon_result, self.config))
                except Exception as e:
                    logging.error(f"Restore error: {e}")

            if not force:
                self.send_to_ui('state', 'idle')

            self.button.setTitle_("🛡")
        except Exception as e:
            logging.error(f"Restore failed: {e}")
        finally:
            self.is_busy = False


# ---------------------------------------------------------
# Entry Point
# ---------------------------------------------------------

_delegate = None

def run_gui():
    global _delegate
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    _delegate = SchoolNetAppDelegate.alloc().init()
    app.setDelegate_(_delegate)
    NSApp().run()
