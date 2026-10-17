#!/bin/bash
# Build EVEView.app and a drag-to-install .dmg.
# Usage: bash build.sh [version]     e.g. bash build.sh 1.0.0
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${1:-0.0.0}"
export EVEVIEW_VERSION="$VERSION"

echo "==> Building EVEView $VERSION"
rm -rf build dist .build-venv

# Isolated build environment
python3 -m venv .build-venv
source .build-venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt py2app

python setup.py py2app

# Ad-hoc signature: required to run on Apple Silicon, no Apple account needed
codesign --force --deep --sign - dist/EVEView.app

# Disk image with a shortcut to /Applications
mkdir -p dist/dmg
cp -R dist/EVEView.app dist/dmg/
ln -s /Applications dist/dmg/Applications
hdiutil create -volname "EVEView" -srcfolder dist/dmg -ov -format UDZO "dist/EVEView-${VERSION}.dmg"
rm -rf dist/dmg

echo "==> Done: dist/EVEView-${VERSION}.dmg"