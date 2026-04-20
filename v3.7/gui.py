"""
gui.py - V3.5 Native Popover UI using PyObjC + WebKit
"""

import threading
import asyncio
import time
import json
import os
import sys

import objc
from Foundation import NSObject, NSURL, NSURLRequest
from AppKit import (
    NSApplication, NSApp, NSStatusBar, NSVariableStatusItemLength,
    NSPopover, NSViewController, NSEvent,
    NSApplicationActivationPolicyAccessory
)
from WebKit import WKWebView, WKWebViewConfiguration, WKUserContentController

from settings import Settings
from recon import run_recon
from network_manager import apply_optimization, restore_original
from doh_proxy import DoHProxy

# ---------------------------------------------------------
# PyObjC Application Delegate
# ---------------------------------------------------------

class ScriptMessageHandler(NSObject):
    def userContentController_didReceiveScriptMessage_(self, userContentController, message):
        body = message.body()
        if not isinstance(body, dict): return
        action = body.get('action')
        data = body.get('data', {})
        
        if hasattr(self, 'delegate') and self.delegate:
            self.delegate.handle_js_action(action, data)

class WebViewController(NSViewController):
    def loadView(self):
        config = WKWebViewConfiguration.alloc().init()
        userContentController = WKUserContentController.alloc().init()
        
        self.msg_handler = ScriptMessageHandler.alloc().init()
        userContentController.addScriptMessageHandler_name_(self.msg_handler, "python")
        config.setUserContentController_(userContentController)
        
        # Transparent background configuration
        config.setValue_forKey_(False, "drawsBackground")
        
        self.webview = WKWebView.alloc().initWithFrame_configuration_(((0,0), (320, 380)), config)
        self.webview.setValue_forKey_(False, "drawsBackground")
        
        if sys.platform != "darwin":
            self.setView_(self.webview)
            return

        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(base_dir, 'ui.html')
        
        url = NSURL.fileURLWithPath_(html_path)
        self.webview.loadFileURL_allowingReadAccessToURL_(url, url.URLByDeletingLastPathComponent())
        
        self.setView_(self.webview)

class SchoolNetAppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        self.config = Settings.load()
        
        self.is_busy = False
        self.proxy = None
        self.proxy_thread = None
        self.proxy_loop = None
        self.recon_result = None
        
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.button = self.statusItem.button()
        self.button.setTitle_("🛡")
        self.button.setTarget_(self)
        self.button.setAction_(objc.selector(self.togglePopover_, signature=b'v@:@'))
        
        self.popover = NSPopover.alloc().init()
        self.popover.setBehavior_(1) # transient
        
        self.vc = WebViewController.alloc().init()
        self.vc.msg_handler.delegate = self
        
        self.popover.setContentViewController_(self.vc)

    def applicationWillTerminate_(self, notification):
        self._do_restore(force=True)

    def togglePopover_(self, sender):
        if self.popover.isShown():
            self.popover.performClose_(sender)
        else:
            self.popover.showRelativeToRect_ofView_preferredEdge_(sender.bounds(), sender, 3)

    # ---------------------------------------------------------
    # Core Logic Bridge
    # ---------------------------------------------------------
    
    def send_to_ui(self, cmd, payload):
        js = f"window.sendCommand('{cmd}', {json.dumps(payload)});"
        self.vc.webview.evaluateJavaScript_completionHandler_(js, None)

    def handle_js_action(self, action, data):
        if action == 'connect':
            self.trigger_optimization()
        elif action == 'disconnect':
            self.trigger_restore()
        elif action == 'quit':
            NSApplication.sharedApplication().terminate_(None)
        elif action == 'settings':
            # Opens settings.json natively
            import subprocess
            subprocess.run(["open", self.config.get_path()])

    def trigger_optimization(self):
        if self.is_busy: return
        self.is_busy = True
        self.send_to_ui('state', 'connecting')
        
        threading.Thread(target=self._run_opt_flow, daemon=True).start()

    def _run_async(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def _run_opt_flow(self):
        try:
            res = self._run_async(run_recon())
            self.recon_result = res
            
            if res.recommended_mode == "passive":
                self.send_to_ui('update_desc', {'text': 'DoH is blocked / not needed'})
                time.sleep(2)
                self.send_to_ui('state', 'idle')
                self.is_busy = False
                return
                
            self.send_to_ui('progress', {'percent': 40})
            self.send_to_ui('update_desc', {'text': f'Starting proxy ({self.config.primary_provider})...'})
            
            self.proxy_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.proxy_loop)
            self.proxy = DoHProxy(self.recon_result, self.config)
            
            self.proxy_thread = threading.Thread(target=self._proxy_worker, daemon=True)
            self.proxy_thread.start()
            
            deadline = time.time() + 5.0
            while not getattr(self.proxy, 'ready', None) and time.time() < deadline:
                time.sleep(0.1)
                
            if not getattr(self.proxy, 'ready', None) or not self.proxy.ready.wait(timeout=3):
                raise Exception("Proxy timeout")
                
            self.send_to_ui('progress', {'percent': 70})
            self.send_to_ui('update_desc', {'text': 'Applying pfctl rules...'})
            
            opt_res = self._run_async(apply_optimization(res, self.config))
            if not opt_res.success:
                raise Exception(opt_res.error)
                
            self.send_to_ui('progress', {'percent': 100})
            self.send_to_ui('update_desc', {'text': 'Verifying traffic...'})
            time.sleep(0.5)
            
            self.send_to_ui('state', 'connected')
            self.button.setTitle_("✅")

        except Exception as e:
            self.send_to_ui('update_desc', {'text': str(e)})
            self.send_to_ui('state', 'failed')
            self._do_restore(force=True)
        finally:
            self.is_busy = False

    def _proxy_worker(self):
        try:
            self.proxy_loop.run_until_complete(self.proxy.start())
        finally:
            self.proxy_loop.close()

    def trigger_restore(self):
        if self.is_busy: return
        self.is_busy = True
        self.send_to_ui('update_desc', {'text': 'Disconnecting...'})
        threading.Thread(target=self._do_restore, daemon=True).start()

    def _do_restore(self, force=False):
        if self.proxy and self.proxy_loop:
            f = asyncio.run_coroutine_threadsafe(self.proxy.stop(), self.proxy_loop)
            try: f.result(timeout=3)
            except: pass
        if self.proxy_thread:
            self.proxy_thread.join(timeout=2)
            
        self.proxy = None
        
        if getattr(self, 'recon_result', None):
            self._run_async(restore_original(self.recon_result, self.config))
            
        if not force:
            self.send_to_ui('state', 'idle')
            
        self.button.setTitle_("🛡")
        self.is_busy = False

_delegate = None

def run_gui():
    global _delegate
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    _delegate = SchoolNetAppDelegate.alloc().init()
    app.setDelegate_(_delegate)
    NSApp().run()
