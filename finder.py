"""Discovery of EVE Online client windows via ScreenCaptureKit."""
import os
import re

from ScreenCaptureKit import SCShareableContent

#: Name used for a client still on the login / character-select screen.
LOGIN_NAME = "EVE"

_EVE_TITLE = re.compile(r"^EVE( - (?P<name>.+))?$")
_MIN_WIDTH = 300
_OWN_PID = os.getpid()


def character_name(title):
    """Extract the character name from an EVE window title.

    ``"EVE - John Doe"`` returns ``"John Doe"``, ``"EVE"`` returns
    :data:`LOGIN_NAME`, and any other title returns ``None``.
    """
    match = _EVE_TITLE.match(title or "")
    if not match:
        return None
    return match.group("name") or LOGIN_NAME


def _is_eve_window(window):
    """Return whether an ``SCWindow`` looks like a real EVE client window."""
    if window.windowLayer() != 0:
        return False
    if window.frame().size.width < _MIN_WIDTH:
        return False
    app = window.owningApplication()
    if app is None or app.processID() == _OWN_PID:
        return False
    return character_name(window.title()) is not None


def fetch_eve_windows(callback):
    """Asynchronously list all EVE client windows.

    :param callback: called from a system thread with a list of ``SCWindow``
        objects, or with ``None`` if the window list could not be read.
    """

    def handler(content, error):
        if error is not None or content is None:
            print(f"[finder] Could not read window list: {error}")
            callback(None)
            return
        callback([w for w in content.windows() if _is_eve_window(w)])

    SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(
        True, False, handler
    )