"""EVEView entry point.

Starts the Cocoa application as a menu-bar-only app (no Dock icon) and hands
control to :class:`app.Controller`.
"""
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
from PyObjCTools import AppHelper

from app import Controller


def main():
    """Create the application, start the controller and run the event loop."""
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    controller = Controller()
    controller.start()

    # installInterrupt lets Ctrl+C in the terminal stop the app cleanly.
    AppHelper.runEventLoop(installInterrupt=True)


if __name__ == "__main__":
    main()