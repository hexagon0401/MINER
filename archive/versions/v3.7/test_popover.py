import objc, sys
from AppKit import NSApplication, NSApp, NSStatusBar, NSVariableStatusItemLength, NSPopover, NSViewController, NSApplicationActivationPolicyAccessory, NSColor, NSView

class TestDelegate(objc.lookUpClass('NSObject')):
    def applicationDidFinishLaunching_(self, note):
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        btn = self.statusItem.button()
        btn.setTitle_("TEST")
        btn.setTarget_(self)
        btn.setAction_(objc.selector(self.togglePopover_, signature=b'v@:@'))
        
        self.popover = NSPopover.alloc().init()
        self.popover.setBehavior_(1)
        
        vc = NSViewController.alloc().init()
        # Create dummy view
        view = NSView.alloc().initWithFrame_(((0,0), (200, 200)))
        view.setWantsLayer_(True)
        view.layer().setBackgroundColor_(NSColor.redColor().CGColor())
        vc.setView_(view)
        
        self.popover.setContentViewController_(vc)

    def togglePopover_(self, sender):
        print("Toggling popover!", sender)
        if self.popover.isShown():
            self.popover.performClose_(sender)
        else:
            self.popover.showRelativeToRect_ofView_preferredEdge_(sender.bounds(), sender, 3)

app = NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
_delegate = TestDelegate.alloc().init()
app.setDelegate_(_delegate)
print("Starting...")
NSApp().run()
