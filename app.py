"""Application controller.

Keeps EVE clients, preview windows, capture streams, hotkeys and the
menu-bar menu in sync.
"""
import traceback

import objc
import Quartz
from AppKit import (
    NSApplication,
    NSMenu,
    NSMenuItem,
    NSScreen,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSWorkspace,
)
from Foundation import NSObject, NSTimer, NSURL
from PyObjCTools import AppHelper

import switcher
from capture import WindowCapture
from config import CONFIG_DIR, Config
from finder import LOGIN_NAME, character_name, fetch_eve_windows
from hotkeys import HotkeyManager
from i18n import AUTO, LANGUAGE_NAMES, Translator
from preview import Preview

#: Seconds between scans for new or closed EVE windows.
REFRESH_SECONDS = 2.0
#: Seconds between checks of which client has focus.
FOCUS_SECONDS = 0.25
FPS_CHOICES = [5, 10, 15, 20, 30, 60]
#: Frame rate used while a preview is hidden.
HIDDEN_FPS = 1

#: On/off options shown in the menu: (config key, translation key).
TOGGLES = [
    ("show_name", "show_names"),
    ("highlight_active", "highlight_active"),
    ("hide_active_preview", "hide_active_preview"),
    ("lock_positions", "lock_positions"),
    ("snap_enabled", "snap"),
    ("retina_previews", "sharp_previews"),
]


def _safe(fn):
    """Decorator: log exceptions instead of letting them crash the Cocoa app."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            traceback.print_exc()
    return wrapper


class Client:
    """One running EVE window.

    ``preview`` and ``capture`` are ``None`` when the preview for this
    character is disabled; the client is still reachable via hotkeys.
    """

    def __init__(self, wid, pid, title, name):
        self.wid = wid
        self.pid = pid
        self.title = title
        self.name = name
        self.preview = None
        self.capture = None


class _MenuTarget(NSObject, protocols=[objc.protocolNamed("NSMenuDelegate")]):
    """Objective-C bridge for menu actions and for rebuilding the menu on open."""

    def init(self):
        self = objc.super(_MenuTarget, self).init()
        if self is None:
            return None
        self.actions = {}
        self.on_open = None
        return self

    def performAction_(self, sender):
        action = self.actions.get(sender.tag())
        if action is not None:
            action()

    def menuNeedsUpdate_(self, menu):
        if self.on_open is not None:
            self.on_open(menu)


class Controller:
    """Central coordinator of the application."""

    def __init__(self):
        self.config = Config()
        self.tr = Translator(self.config["language"])
        self.clients = {}          # window id -> Client
        self.active_id = None
        self.visible = True
        self.hotkeys = HotkeyManager()
        self.scale = NSScreen.mainScreen().backingScaleFactor()
        self._debounce_tokens = {}
        self._timers = []
        self._menu_target = _MenuTarget.alloc().init()
        self._status_item = None

    # --- startup ---

    def start(self):
        """Check permissions, build the menu, install hotkeys and start polling."""
        self._check_permissions()
        self._build_menu()
        self._bind_hotkeys()
        self.hotkeys.start()
        self._timers.append(NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            REFRESH_SECONDS, True, lambda timer: self.refresh()))
        self._timers.append(NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            FOCUS_SECONDS, True, lambda timer: self._check_focus()))
        self.refresh()
        print("EVEView started: look for the 'EVE' icon in the menu bar.")

    def _check_permissions(self):
        if not Quartz.CGPreflightScreenCaptureAccess():
            print("WARNING: 'Screen Recording' permission is missing. Grant it and restart.")
            Quartz.CGRequestScreenCaptureAccess()
        if not switcher.ensure_accessibility(prompt=True):
            print("WARNING: 'Accessibility' permission is missing. Grant it and restart.")

    def _bind_hotkeys(self):
        hk = self.config["hotkeys"]
        bindings = [
            (hk.get("cycle_next"), lambda: self.cycle(1)),
            (hk.get("cycle_prev"), lambda: self.cycle(-1)),
        ]
        for name, entry in self.config["characters"].items():
            bindings.append((entry.get("hotkey"), lambda n=name: self.activate_by_name(n)))
        self.hotkeys.set_bindings(bindings)

    # --- menu (rebuilt every time it opens) ---

    def _build_menu(self):
        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self._status_item.button().setTitle_("EVE")
        menu = NSMenu.alloc().init()
        menu.setDelegate_(self._menu_target)
        self._menu_target.on_open = self._populate_menu
        self._status_item.setMenu_(menu)

    def _add_item(self, menu, title, action=None, checked=None):
        """Append a menu item.

        :param action: ``callable()`` to run on click; ``None`` makes a disabled label.
        :param checked: ``True``/``False`` to show a checkmark state, ``None`` for none.
        :return: the created ``NSMenuItem``.
        """
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title, "performAction:" if action else None, "")
        if action is not None:
            tag = len(self._menu_target.actions) + 1
            self._menu_target.actions[tag] = _safe(action)
            item.setTag_(tag)
            item.setTarget_(self._menu_target)
        if checked is not None:
            item.setState_(1 if checked else 0)
        menu.addItem_(item)
        return item

    def _add_submenu(self, menu, title):
        """Append an item with an empty submenu and return the submenu."""
        item = self._add_item(menu, title)
        submenu = NSMenu.alloc().init()
        item.setSubmenu_(submenu)
        return submenu

    @_safe
    def _populate_menu(self, menu):
        tr = self.tr
        menu.removeAllItems()
        self._menu_target.actions = {}

        # Clients: checked = preview enabled
        self._add_item(menu, tr("previews"))
        clients = [self.clients[wid] for wid in self._cycle_list()]
        if not clients:
            self._add_item(menu, "   " + tr("no_clients"))
        for client in clients:
            self._add_item(menu, f"   {client.name}",
                           lambda wid=client.wid: self._toggle_client(wid),
                           checked=client.preview is not None)
        menu.addItem_(NSMenuItem.separatorItem())

        # On/off options
        for key, label in TOGGLES:
            self._add_item(menu, tr(label), lambda k=key: self._set_option(k, not self.config[k]),
                           checked=self.config[key])

        # Frame rate
        fps = self.config["fps"]
        fps_menu = self._add_submenu(menu, tr("fps", fps=fps))
        for value in FPS_CHOICES:
            self._add_item(fps_menu, str(value), lambda v=value: self._set_option("fps", v),
                           checked=value == fps)

        # Language
        language = self.config["language"]
        lang_menu = self._add_submenu(menu, tr("language"))
        self._add_item(lang_menu, tr("language_auto"), lambda: self._set_language(AUTO),
                       checked=language == AUTO)
        lang_menu.addItem_(NSMenuItem.separatorItem())
        for code, native_name in LANGUAGE_NAMES.items():
            self._add_item(lang_menu, native_name, lambda c=code: self._set_language(c),
                           checked=language == code)
        menu.addItem_(NSMenuItem.separatorItem())

        self._add_item(menu, tr("hide_all"), self.toggle_visible, checked=not self.visible)
        self._add_item(menu, tr("open_config"), self.open_config_folder)
        self._add_item(menu, tr("reload_config"), self.reload_config)
        menu.addItem_(NSMenuItem.separatorItem())
        self._add_item(menu, tr("quit"), self.quit)

    def _set_option(self, key, value):
        self.config.set(key, value)
        self._apply_config()

    def _set_language(self, code):
        self.config.set("language", code)
        self.tr.set_language(code)

    def _toggle_client(self, wid):
        client = self.clients.get(wid)
        if client is None:
            return
        self.config.set_enabled(client.name, client.preview is None)
        self._remove_client(wid)
        self.refresh()  # recreated on the next scan with the new state

    # --- syncing with EVE windows ---

    @_safe
    def refresh(self):
        """Scan for EVE windows asynchronously and sync previews on the main thread."""
        fetch_eve_windows(lambda windows: AppHelper.callAfter(self._sync, windows))

    @_safe
    def _sync(self, windows):
        if windows is None:
            return
        seen = set()
        for window in windows:
            wid = window.windowID()
            seen.add(wid)
            title = window.title()
            name = character_name(title)
            client = self.clients.get(wid)
            if client is None:
                self._add_client(window, name)
            elif client.name != name:
                # Login finished: recreate with this character's settings
                self._remove_client(wid)
                self._add_client(window, name)
            else:
                client.title = title
        for wid in list(self.clients):
            if wid not in seen:
                self._remove_client(wid)

    def _add_client(self, window, name):
        wid = window.windowID()
        client = Client(wid, window.owningApplication().processID(), window.title(), name)
        if self.config.is_enabled(name):
            self._attach_preview(client, window)
        self.clients[wid] = client
        print(f"[app] Client: {name}" + ("" if client.preview else " (preview disabled)"))
        self._apply_states()

    def _attach_preview(self, client, window):
        wid = client.wid
        f = window.frame()
        aspect = f.size.height / f.size.width

        saved = self.config.character(client.name) if client.name != LOGIN_NAME else {}
        if "x" in saved and "y" in saved:
            x, y = saved["x"], saved["y"]
            width = saved.get("width", self.config["preview_width"])
        else:
            x, y, width = self._default_frame(aspect)

        preview = Preview(
            client.name, aspect, x, y, width, self.config,
            on_click=lambda: self.activate(wid),
            on_changed=lambda: self._debounce(("persist", wid), 0.4, lambda: self._persist(wid)),
            context=lambda: self._layout_context(wid),
        )
        client.preview = preview
        try:
            w_px, h_px = preview.pixel_size(self._capture_scale())
            client.capture = WindowCapture(
                window, w_px, h_px, self.config["fps"],
                on_frame=preview.submit_frame,
                on_stop=lambda error: AppHelper.callAfter(self._capture_stopped, wid, error),
            )
        except Exception as e:
            print(f"[app] Cannot capture '{client.name}': {e}")

    def _remove_client(self, wid):
        client = self.clients.pop(wid, None)
        if client is None:
            return
        if client.capture is not None:
            client.capture.stop()
        if client.preview is not None:
            client.preview.close()
        if self.active_id == wid:
            self.active_id = None

    @_safe
    def _capture_stopped(self, wid, error):
        print(f"[app] Capture stopped ({error}); it will restart if the client is still open")
        self._remove_client(wid)

    def _default_frame(self, aspect):
        """Place a new preview in a grid starting from the top-left of the main screen."""
        vf = NSScreen.mainScreen().visibleFrame()
        w = self.config["preview_width"]
        h = w * aspect
        n = sum(1 for c in self.clients.values() if c.preview is not None)
        per_row = max(1, int((vf.size.width - 20) // (w + 10)))
        col, row = n % per_row, n // per_row
        x = vf.origin.x + 20 + col * (w + 10)
        y = vf.origin.y + vf.size.height - 20 - (row + 1) * (h + 10)
        return x, y, w

    def _layout_context(self, wid):
        """Return the rectangles a preview can snap to: other previews and screens."""
        others = [c.preview.rect() for c in self.clients.values()
                  if c.wid != wid and c.preview is not None and c.preview.visible]
        screens = []
        for screen in NSScreen.screens():
            f = screen.visibleFrame()
            screens.append((f.origin.x, f.origin.y, f.size.width, f.size.height))
        return others, screens

    def _capture_scale(self):
        """Pixels per point used for capture: Retina scale or 1x."""
        return self.scale if self.config["retina_previews"] else 1.0

    def _update_capture(self, client):
        """Match capture size to the preview, and throttle hidden previews."""
        if client.capture is None or client.preview is None:
            return
        w_px, h_px = client.preview.pixel_size(self._capture_scale())
        fps = self.config["fps"] if client.preview.visible else HIDDEN_FPS
        client.capture.update(w_px, h_px, fps)

    @_safe
    def _persist(self, wid):
        client = self.clients.get(wid)
        if client is None or client.preview is None:
            return
        if client.name != LOGIN_NAME:
            x, y, width = client.preview.frame()
            self.config.set_character_frame(client.name, x, y, width)
        self._update_capture(client)

    def _debounce(self, key, delay, fn):
        """Run ``fn`` after ``delay`` seconds, cancelling earlier calls with the same key."""
        token = object()
        self._debounce_tokens[key] = token

        def run():
            if self._debounce_tokens.get(key) is token:
                fn()

        AppHelper.callLater(delay, run)

    # --- switching clients ---

    @_safe
    def activate(self, wid):
        """Bring the client with window id ``wid`` to the front."""
        client = self.clients.get(wid)
        if client is None:
            return
        switcher.activate_window(client.pid, client.title)
        self._set_active(wid)

    @_safe
    def activate_by_name(self, name):
        """Bring the client of character ``name`` to the front, if running."""
        for client in self.clients.values():
            if client.name == name:
                self.activate(client.wid)
                return

    @_safe
    def cycle(self, step):
        """Activate the next (``step=1``) or previous (``step=-1``) client."""
        order = self._cycle_list()
        if not order:
            return
        if self.active_id in order:
            index = (order.index(self.active_id) + step) % len(order)
        else:
            index = 0 if step > 0 else -1
        self.activate(order[index])

    def _cycle_list(self):
        """Window ids ordered by ``cycle_order`` first, then alphabetically."""
        preferred = self.config["cycle_order"]

        def key(client):
            rank = preferred.index(client.name) if client.name in preferred else len(preferred)
            return rank, client.name, client.wid

        return [c.wid for c in sorted(self.clients.values(), key=key)]

    @_safe
    def _check_focus(self):
        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        pid = front.processIdentifier() if front is not None else None
        candidates = [c for c in self.clients.values() if c.pid == pid]

        if not candidates:
            active = None
        elif len(candidates) == 1:
            active = candidates[0].wid
        else:  # several clients in one process: match the focused window title
            title = switcher.focused_window_title(pid)
            active = next((c.wid for c in candidates if c.title == title), self.active_id)

        self._set_active(active)

    def _set_active(self, wid):
        if wid == self.active_id:
            return
        self.active_id = wid
        self._apply_states()

    def _apply_states(self):
        """Update border, visibility and capture rate of every preview."""
        hide_active = self.config["hide_active_preview"]
        for client in self.clients.values():
            if client.preview is None:
                continue
            is_active = client.wid == self.active_id
            client.preview.set_active(is_active)
            client.preview.set_visible(self.visible and not (hide_active and is_active))
            self._update_capture(client)

    def _apply_config(self):
        """Re-apply styling and capture settings to all previews."""
        for client in self.clients.values():
            if client.preview is not None:
                client.preview.apply_style(self.config)
        self._apply_states()

    # --- menu actions ---

    def toggle_visible(self):
        """Show or hide all previews."""
        self.visible = not self.visible
        self._apply_states()

    def reload_config(self):
        """Reload the JSON file and recreate every preview from it."""
        self.config.load()
        self.tr.set_language(self.config["language"])
        self._bind_hotkeys()
        for wid in list(self.clients):
            self._remove_client(wid)
        self.refresh()
        print("[app] Configuration reloaded")

    def open_config_folder(self):
        """Open the configuration folder in Finder."""
        NSWorkspace.sharedWorkspace().openURL_(NSURL.fileURLWithPath_(CONFIG_DIR))

    def quit(self):
        """Stop all captures and quit."""
        for wid in list(self.clients):
            self._remove_client(wid)
        NSApplication.sharedApplication().terminate_(None)