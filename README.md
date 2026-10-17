# EVEView

Live window previews and fast client switching for **EVE Online multiboxing on macOS**.
Inspired by EVE-O Preview.

## Features

- Live previews of every EVE client, found automatically
- Click a preview to switch to that client
- Resize previews by dragging their edges, move them anywhere
- Previews snap to each other and to screen edges, and never overlap
- Choose which clients get a preview
- Global hotkeys to jump to a character or cycle through clients
- Optional character names and active-client highlight
- Adjustable frame rate
- Interface in English, Deutsch, Français, Español, Русский, 日本語, 简体中文, 한국어, Italiano

## Install

1. Download the latest **EVEView-x.y.z.dmg** from
   [Releases](https://github.com/pacocarlesimo/eveview/releases/latest).
2. Open it and drag **EVEView** into **Applications**.
3. Open EVEView from Applications. macOS will say it can't verify the developer:
   click **Done**, then open **System Settings → Privacy & Security**, scroll down
   and click **Open Anyway** next to EVEView. You only need to do this once.
4. EVEView asks for two permissions. Turn both on in
   **System Settings → Privacy & Security**:
    - **Screen & System Audio Recording**, to show the previews
    - **Accessibility**, to switch clients and use hotkeys
5. Quit EVEView (menu bar icon **EVE → Quit**) and open it again.

EVEView has no Dock icon: look for **EVE** in the menu bar at the top of the screen.

## Usage

| Action | How |
|---|---|
| Switch to a client | Click its preview |
| Move a preview | Drag it |
| Resize a preview | Drag an edge or corner |
| Hide a client's preview | Menu bar **EVE** → uncheck the character |
| Options, frame rate, language | Menu bar **EVE** |

### Hotkeys

Open **EVE → Open config folder**, edit `config.json`, then choose **Reload configuration**.

    "hotkeys": {
      "cycle_next": "ctrl+opt+right",
      "cycle_prev": "ctrl+opt+left"
    },
    "characters": {
      "My Main":  { "hotkey": "opt+1" },
      "My Alt":   { "hotkey": "opt+2" }
    }

Modifiers: `cmd`, `opt`, `ctrl`, `shift`. Keys: `a`–`z`, `0`–`9`, `f1`–`f12`,
`left`, `right`, `up`, `down`, `tab`, `space`, `esc`.
Hotkeys are not blocked from reaching EVE, so pick combinations you don't use in game.

## Updating

Download the new .dmg and replace the app in Applications.
After an update macOS may forget the permissions: in **Privacy & Security**,
remove EVEView from both lists with the **−** button, then open the app and grant them again.

## Uninstall

Delete EVEView from Applications and the folder
`~/Library/Application Support/EVEView`.

## Requirements

macOS 13 Ventura or later.

## Building from source

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python main.py          # run from source
    bash build.sh 1.0.0               # build dist/EVEView-1.0.0.dmg

## Disclaimer

EVEView only shows previews and switches windows; it never sends input to more than one client.
It is a fan project, not affiliated with or endorsed by CCP Games.
EVE Online is a trademark of CCP hf.




https://github.com/user-attachments/assets/dd20563e-92ad-4e85-b03c-442484614bcb


