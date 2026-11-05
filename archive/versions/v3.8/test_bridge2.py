import objc, sys
from Foundation import NSObject
from AppKit import NSApplication, NSApp, NSWindow
from WebKit import WKWebView, WKWebViewConfiguration, WKUserContentController

class MyHandler(NSObject):
    @objc.signature(b'v@:@@')
    def userContentController_didReceiveScriptMessage_(self, ucc, message):
        print("PYTHON SAYS:", message.body())
        sys.stdout.flush()
        NSApp().terminate_(None)

app = NSApplication.sharedApplication()

win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(((0,0),(300,300)), 15, 2, False)
conf = WKWebViewConfiguration.alloc().init()
ucc = WKUserContentController.alloc().init()
        
handler = MyHandler.alloc().init()
ucc.addScriptMessageHandler_name_(handler, "python")
conf.setUserContentController_(ucc)
        
wv = WKWebView.alloc().initWithFrame_configuration_(((0,0),(300,300)), conf)
wv.loadHTMLString_baseURL_("""
        <script>
        window.setTimeout(() => window.webkit.messageHandlers.python.postMessage('auto-ping'), 500);
        </script>
""", None)

win.setContentView_(wv)
win.makeKeyAndOrderFront_(None)

app.run()
