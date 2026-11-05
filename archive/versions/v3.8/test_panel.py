import objc
from AppKit import (
    NSApplication, NSApp, NSStatusBar, NSVariableStatusItemLength,
    NSPanel, NSColor, NSView, NSApplicationActivationPolicyAccessory
)

class TestDelegate(objc.lookUpClass('NSObject')):
    def applicationDidFinishLaunching_(self, note):
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        btn = self.statusItem.button()
        btn.setTitle_("TEST")
        btn.setTarget_(self)
        btn.setAction_(objc.selector(self.togglePanel_, signature=b'v@:@'))
        
        # Create frameless panel
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            ((0, 0), (320, 380)),
            128 | 0, # NSWindowStyleMaskNonactivatingPanel (128) | Borderless (0)
            2, # NSBackingStoreBuffered
            False
        )
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setHasShadow_(True)
        self.panel.setFloatingPanel_(True)
        
        # Red background view to see it
        view = NSView.alloc().initWithFrame_(((0,0), (320, 380)))
        view.setWantsLayer_(True)
        view.layer().setBackgroundColor_(NSColor.redColor().CGColor())
        view.layer().setCornerRadius_(20)
        self.panel.setContentView_(view)

    def togglePanel_(self, sender):
        print("Toggling panel!")
        NSApp().activateIgnoringOtherApps_(True)
        
        if self.panel.isVisible():
            self.panel.orderOut_(None)
        else:
            # Position it under the button
            button_rect = sender.window().frame()
            # Calculate panel x and y. x = button mid x - half panel width. y = button bottom y
            x = button_rect.origin.x + (button_rect.size.width / 2) - 160
            y = button_rect.origin.y - 380 - 10 # 10px spacing
            
            self.panel.setFrameOrigin_((x, y))
            self.panel.makeKeyAndOrderFront_(None)

app = NSApplication.sharedApplication()
app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
_delegate = TestDelegate.alloc().init()
app.setDelegate_(_delegate)
NSApp().run()
