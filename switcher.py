"""Bringing a specific EVE window to the front, via the Accessibility API."""
from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication
from ApplicationServices import (
    AXIsProcessTrustedWithOptions,
    AXUIElementCopyAttributeValue,
    AXUIElementCreateApplication,
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
    kAXFocusedWindowAttribute,
    kAXFrontmostAttribute,
    kAXMainAttribute,
    kAXMinimizedAttribute,
    kAXRaiseAction,
    kAXTitleAttribute,
    kAXTrustedCheckOptionPrompt,
    kAXWindowsAttribute,
)

_AX_SUCCESS = 0


def ensure_accessibility(prompt=True):
    """Return whether this process has Accessibility permission.

    :param prompt: if ``True`` and permission is missing, macOS shows its
        system prompt.
    """
    return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: prompt}))


def _ax_get(element, attribute):
    """Read an AX attribute, returning ``None`` on error."""
    err, value = AXUIElementCopyAttributeValue(element, attribute, None)
    return value if err == _AX_SUCCESS else None


def focused_window_title(pid):
    """Return the title of the focused window of process ``pid``, or ``None``."""
    app = AXUIElementCreateApplication(pid)
    window = _ax_get(app, kAXFocusedWindowAttribute)
    return _ax_get(window, kAXTitleAttribute) if window is not None else None


def activate_window(pid, title):
    """Bring the window titled ``title`` of process ``pid`` to the front.

    Un-minimizes the window if needed, raises it, then activates the
    application both through Accessibility and ``NSRunningApplication``.
    """
    app_element = AXUIElementCreateApplication(pid)

    for window in _ax_get(app_element, kAXWindowsAttribute) or []:
        if _ax_get(window, kAXTitleAttribute) == title:
            if _ax_get(window, kAXMinimizedAttribute):
                AXUIElementSetAttributeValue(window, kAXMinimizedAttribute, False)
            AXUIElementSetAttributeValue(window, kAXMainAttribute, True)
            AXUIElementPerformAction(window, kAXRaiseAction)
            break

    AXUIElementSetAttributeValue(app_element, kAXFrontmostAttribute, True)
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is not None:
        app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)