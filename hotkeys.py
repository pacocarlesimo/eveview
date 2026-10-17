"""Global keyboard shortcuts, written as strings like ``"opt+1"`` or ``"ctrl+opt+right"``.

Note: global monitors observe key presses but cannot block them, so the key
also reaches EVE. Pick combinations you don't use in game.
"""
from AppKit import (
    NSEvent,
    NSEventMaskKeyDown,
    NSEventModifierFlagCommand,
    NSEventModifierFlagControl,
    NSEventModifierFlagOption,
    NSEventModifierFlagShift,
)

MODIFIERS = {
    "cmd": NSEventModifierFlagCommand, "command": NSEventModifierFlagCommand,
    "opt": NSEventModifierFlagOption, "option": NSEventModifierFlagOption, "alt": NSEventModifierFlagOption,
    "ctrl": NSEventModifierFlagControl, "control": NSEventModifierFlagControl,
    "shift": NSEventModifierFlagShift,
}
MOD_MASK = (NSEventModifierFlagCommand | NSEventModifierFlagOption
            | NSEventModifierFlagControl | NSEventModifierFlagShift)

#: Physical key codes (key position, independent of keyboard layout).
KEY_CODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9,
    "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "o": 31, "u": 32,
    "i": 34, "p": 35, "l": 37, "j": 38, "k": 40, "n": 45, "m": 46,
    "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26, "8": 28, "9": 25, "0": 29,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "tab": 48, "space": 49, "esc": 53, "`": 50,
    "left": 123, "right": 124, "down": 125, "up": 126,
}


def parse_hotkey(spec):
    """Parse ``"mod+mod+key"`` into ``(modifier_flags, key_code)``.

    :raises ValueError: if the string is empty or contains an unknown modifier or key.
    """
    parts = [p.strip().lower() for p in spec.split("+") if p.strip()]
    if not parts:
        raise ValueError("empty")
    *mods, key = parts
    flags = 0
    for mod in mods:
        if mod not in MODIFIERS:
            raise ValueError(f"unknown modifier '{mod}'")
        flags |= MODIFIERS[mod]
    if key not in KEY_CODES:
        raise ValueError(f"unknown key '{key}'")
    return flags, KEY_CODES[key]


class HotkeyManager:
    """Listens to key presses system-wide and runs the bound actions."""

    def __init__(self):
        self._bindings = {}
        self._monitors = []

    def set_bindings(self, bindings):
        """Replace all bindings.

        :param bindings: iterable of ``(hotkey_string, callable)``. Empty strings
            are skipped; invalid or duplicate hotkeys are logged and skipped.
        """
        parsed = {}
        for spec, action in bindings:
            if not spec:
                continue
            try:
                key = parse_hotkey(spec)
            except ValueError as e:
                print(f"[hotkeys] '{spec}' ignored: {e}")
                continue
            if key in parsed:
                print(f"[hotkeys] '{spec}' is a duplicate, keeping the first one")
                continue
            parsed[key] = action
        self._bindings = parsed

    def start(self):
        """Install the key monitors. Requires Accessibility permission."""
        self._monitors.append(
            NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSEventMaskKeyDown, self._on_global)
        )
        self._monitors.append(
            NSEvent.addLocalMonitorForEventsMatchingMask_handler_(NSEventMaskKeyDown, self._on_local)
        )

    def _match(self, event):
        if event.isARepeat():
            return None
        return self._bindings.get((event.modifierFlags() & MOD_MASK, event.keyCode()))

    def _on_global(self, event):
        action = self._match(event)
        if action is not None:
            action()

    def _on_local(self, event):
        action = self._match(event)
        if action is not None:
            action()
            return None  # swallow the event when our own app is focused
        return event