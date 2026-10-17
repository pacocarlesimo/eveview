"""py2app build configuration.

Builds a standalone EVEView.app that bundles Python and all dependencies.
Usage: ``python setup.py py2app`` (normally called by build.sh).
"""
import os

from setuptools import setup

#: Version string, injected by build.sh / the release workflow.
VERSION = os.environ.get("EVEVIEW_VERSION", "0.0.0")

OPTIONS = {
    "argv_emulation": False,
    "includes": [
        "app", "capture", "config", "finder", "hotkeys",
        "i18n", "layout", "preview", "switcher",
    ],
    "plist": {
        "CFBundleName": "EVEView",
        "CFBundleDisplayName": "EVEView",
        "CFBundleIdentifier": "io.github.eveview",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSUIElement": True,                 # menu bar only, no Dock icon
        "LSMinimumSystemVersion": "13.0",
        "NSHumanReadableCopyright": "MIT License",
    },
}

setup(
    name="EVEView",
    version=VERSION,
    app=["main.py"],
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)