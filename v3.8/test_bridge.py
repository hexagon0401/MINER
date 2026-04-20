import objc
from Foundation import NSObject, NSURL
from AppKit import NSApplication, NSApp, NSWindow, NSColor, NSBackingStoreBuffered
from WebKit import WKWebView, WKWebViewConfiguration, WKUserContentController

class ScriptMessageHandler(NSObject):
    def userContentController_didReceiveScriptMessage_(self, userContentController, message):
        print("PYTHON RECEIVED:", message.body())
        if message.body() == "stop":
            NSApp().terminate_(None)

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, note):
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            ((0,0),(300,300)), 15, 2, False
        )
        conf = WKWebViewConfiguration.alloc().init()
        ucc = WKUserContentController.alloc().init()
        
        self.handler = ScriptMessageHandler.alloc().init()
        ucc.addScriptMessageHandler_name_(self.handler, "python")
        conf.setUserContentController_(ucc)
        
        self.wv = WKWebView.alloc().initWithFrame_configuration_(((0,0),(300,300)), conf)
        self.wv.loadHTMLString_baseURL_("""
        <html><body>
        <button onclick="window.webkit.messageHandlers.python.postMessage('hello')">Send Hello</button>
        <button onclick="window.webkit.messageHandlers.python.postMessage('stop')">Stop</button>
        <script>
        console.log("loaded JS");
        window.setTimeout(() => window.webkit.messageHandlers.python.postMessage('auto-ping'), 1000);
        </script>
        </body></html>
        """, None)
        win.setContentView_(self.wv)
        win.makeKeyAndOrderFront_(None)
        self.win = win

app = NSApplication.sharedApplication()
delegate = AppDelegate.alloc().init()
app.setDelegate_(delegate)
NSApp().run()
