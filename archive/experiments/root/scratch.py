import objc
from Foundation import NSObject, NSLog, NSURL, NSURLRequest
from AppKit import NSApplication, NSApp, NSStatusBar, NSVariableStatusItemLength, NSWindow, NSPopover, NSViewController, NSEvent, NSApplicationActivationPolicyProhibited
from WebKit import WKWebView, WKWebViewConfiguration, WKUserContentController

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        NSLog("App started")
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        button = self.statusItem.button()
        button.setTitle_("Test")
        button.setTarget_(self)
        button.setAction_(objc.selector(self.togglePopover_, signature=b'v@:@'))
        
        self.popover = NSPopover.alloc().init()
        self.popover.setBehavior_(1) # transient
        
        vc = NSViewController.alloc().init()
        config = WKWebViewConfiguration.alloc().init()
        self.webview = WKWebView.alloc().initWithFrame_configuration_(((0,0), (300, 300)), config)
        self.webview.loadHTMLString_baseURL_("<h1>Hello from WebKit</h1>", None)
        
        vc.setView_(self.webview)
        self.popover.setContentViewController_(vc)
        
    def togglePopover_(self, sender):
        if self.popover.isShown():
            self.popover.performClose_(sender)
        else:
            self.popover.showRelativeToRect_ofView_preferredEdge_(sender.bounds(), sender, 3) # 3 = NSMinYEdge

if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    NSApp().run()
