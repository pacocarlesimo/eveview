"""Persistent JSON configuration.

The file lives in ``~/Library/Application Support/EVEView/config.json``.
Missing keys are filled in from :data:`DEFAULTS`, so older files keep working
when new options are added.
"""
import copy
import json
import os

CONFIG_DIR = os.path.expanduser("~/Library/Application Support/EVEView")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

#: Default value of every option.
DEFAULTS = {
    "language": "auto",
    "fps": 15,
    "preview_width": 320,
    "opacity": 1.0,
    "show_name": True,
    "name_font_size": 13,
    "highlight_active": True,
    "active_border_width": 3,
    "active_border_color": "#3FA9F5",
    "hide_active_preview": False,
    "lock_positions": False,
    "snap_enabled": True,
    "snap_distance": 12,
    "hotkeys": {
        "cycle_next": "ctrl+opt+right",
        "cycle_prev": "ctrl+opt+left",
    },
    "cycle_order": [],
    "characters": {},
    "retina_previews": True,
}


def _merge(base, override):
    """Recursively copy ``override`` into ``base``, merging nested dicts."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value


class Config:
    """In-memory configuration backed by a JSON file.

    If the file on disk is not valid JSON, defaults are used and the file is
    left untouched (``read_only``) so the user can fix it by hand.
    """

    def __init__(self):
        self.data = copy.deepcopy(DEFAULTS)
        self.read_only = False
        self.load()

    def load(self):
        """Read the file from disk.

        :return: ``True`` if the file was loaded (or created), ``False`` if it
            was invalid and defaults are being used.
        """
        data = copy.deepcopy(DEFAULTS)
        self.read_only = False
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, encoding="utf-8") as f:
                    _merge(data, json.load(f))
            except (OSError, ValueError) as e:
                print(f"[config] Invalid file, using defaults (file will NOT be modified): {e}")
                self.data = data
                self.read_only = True
                return False
        self.data = data
        self.save()
        return True

    def save(self):
        """Write the configuration atomically. Does nothing in read-only mode."""
        if self.read_only:
            return
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, CONFIG_PATH)

    def __getitem__(self, key):
        return self.data[key]

    def set(self, key, value):
        """Set a top-level option and save immediately."""
        self.data[key] = value
        self.save()

    def character(self, name):
        """Return the saved settings for a character (empty dict if none)."""
        return self.data["characters"].get(name, {})

    def _character_entry(self, name):
        return self.data["characters"].setdefault(name, {"hotkey": ""})

    def is_enabled(self, name):
        """Return whether the character's preview is enabled (default ``True``)."""
        return self.character(name).get("enabled", True)

    def set_enabled(self, name, enabled):
        """Enable or disable the preview for a character and save."""
        self._character_entry(name)["enabled"] = enabled
        self.save()

    def set_character_frame(self, name, x, y, width):
        """Store the preview position and width for a character and save."""
        self._character_entry(name).update(x=round(x), y=round(y), width=round(width))
        self.save()