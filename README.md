<p align="center">
  <img src="assets/eve-online-white.png" alt="EVE Online" width="300">
</p>

<h1 align="center">EveJS Controller Support</h1>

<p align="center">
  Controller navigation for EveJS on Windows, built for Xbox controllers and the Lenovo Legion Go.
</p>

<p align="center">
  <img alt="Status: unreleased" src="https://img.shields.io/badge/status-unreleased-57606a?style=for-the-badge">
  <img alt="EveJS 0.12.9" src="https://img.shields.io/badge/EveJS-0.12.9-ffffff?style=for-the-badge&amp;labelColor=24292f">
  <img alt="Launcher 1.0.53 or newer" src="https://img.shields.io/badge/Launcher-1.0.53%2B-ffffff?style=for-the-badge&amp;labelColor=24292f">
</p>

<p align="center">
  <a href="https://discord.gg/qxgMmtGmb7"><img alt="Join the EveJS Discord" src="https://img.shields.io/badge/EveJS_Discord-Join-5865f2?style=for-the-badge&amp;logo=discord&amp;logoColor=white"></a>
  <a href="https://github.com/cfin3d/EveJS-Controller-Support/issues"><img alt="Report an issue" src="https://img.shields.io/badge/Issues-Report-24292f?style=for-the-badge&amp;logo=github&amp;logoColor=white"></a>
  <a href="CHANGELOG.md"><img alt="Read the changelog" src="https://img.shields.io/badge/Changelog-Read-24292f?style=for-the-badge"></a>
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#compatibility">Compatibility</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#controls">Controls</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#troubleshooting">Troubleshooting</a>
</p>

---

> [!NOTE]
> **Under development.** No release has been published. The first release will be **0.1.0**. The current repository contains an unreleased testing build; in-game behavior on Xbox controllers and Legion Go hardware still needs validation.

## Features

- **Analog cursor control:** small left-stick movements give precision; full deflection moves quickly across the screen.
- **Hold to click:** a half-second confirmation prevents accidental clicks, with a circular progress indicator and support for dragging.
- **Gentle UI attraction:** slow cursor movement draws toward nearby hovered controls; stronger movement lets you escape.
- **Camera control and ship navigation:** pan with the right stick, tap it to fly toward camera center, or hold it for one second to stop.
- **Minimal EVE-style visuals:** a white/cyan circular cursor and a small camera-center dot that stays beneath menus and windows.
- **Automatic startup:** enable the mod in EveJS Launcher and the controller companion starts at login.

## Compatibility

| Requirement | Supported configuration |
| :--- | :--- |
| EveJS | **0.12.9**, with the supported login-handshake source |
| EveJS Launcher | **1.0.53 or newer** |
| EVE client | **Build 3396210**, Windows x64 |
| Controller | Xbox/XInput-compatible gamepad; automatic selection or XInput slot 0–3 |
| Legion Go | **Gamepad / XInput mode**, with FPS mode off |
| Server backend | Native or Docker; the controller companion runs on the Windows client PC |

Other EveJS/client revisions are not supported by this build. Live native and Docker gameplay testing is pending. EVE and the companion should run at the same Windows privilege level.

## Installation

### Current testing build

1. Choose **Code → Download ZIP** on this repository, then extract it.
2. Rename the extracted repository folder to **`evejs-controller`**.
3. Drag that entire folder into the **Mods folder for your EveJS installation**, accessible through EveJS Launcher.
4. Open **Mods**, refresh the list, and enable **EveJS Controller**. Adopt the package if prompted.
5. Restart the game server when requested, then launch EVE and log in through the launcher.
6. Center both sticks and release all buttons to activate controller input.

The folder must contain the manifest directly:

```text
mods/
└── evejs-controller/
    ├── evejs-launcher.mod.json
    ├── EveJSController.exe
    ├── loader.js.disabled
    ├── login-delivery.js
    ├── client-ui.py
    ├── preferences.json
    └── …
```

The launcher manages the loader filename when enabling/disabling the mod. No manual companion launch, compilation, or separate runtime installation is needed.

### When releases are available

Download the mod ZIP from [Releases](https://github.com/cfin3d/EveJS-Controller-Support/releases), extract it, and drag the enclosed **`evejs-controller`** folder into Mods. Release ZIPs will contain that folder at the top level, ready to install. Follow steps 4–6 above.

<details>
<summary><strong>Updating an existing installation</strong></summary>

Close EVE and quit the controller companion before replacing its executable. Keep a backup of your configured `preferences.json`, replace the package with the new mod folder, and restore your preferences if the update's changelog says they remain compatible. Refresh Mods, enable the package if necessary, restart the server, and log back in.

</details>

## Usage

After login, look for **EveJS Controller** in the Windows notification area. Its status window shows the selected controller, input state, client UI availability, and the most recent navigation request. Closing the window hides it; **Quit** stops the companion.

Controller input is active only while the selected EVE client has foreground focus. Returning from Alt-Tab, reconnecting a controller, or finishing a camera drag requires neutral inputs before mouse control resumes. Disable the mod in the launcher to stop the companion and restart the server when requested.

### Cursor and hold confirmation

Use the left stick to move the circular cursor. Hold **RB** for **0.5 seconds** to confirm a left-click, or **LB** to confirm a right-click. Release early to cancel. Keep holding after confirmation and move the left stick to drag.

The cyan arc shows left-click confirmation; the amber arc shows right-click confirmation. Changing targets or moving more than 10 pixels resets an unfinished confirmation. Gentle attraction works only around real hovered UI controls while moving slowly, and disengages during clicks, drags, camera motion, or physical mouse movement.

### Camera and ship movement

Move the right stick to pan/rotate the camera. A small pale-blue dot marks **camera center**, the direction used for right-stick flight. It sits in EVE's native space UI below windows and menus, and hides when UI covers the center or a menu/modal dialog is open.

- **Short right-stick press:** release before one second to request flight toward camera center. Cursor position does not affect this direction.
- **Right-stick hold:** at one second, request EVE's normal stop command. The ship slows according to its normal physics. A long hold never starts flight first or on release.

The outer orange cursor arc shows the stop timer. Navigation is available only when your character is ready in space. Chat still uses your keyboard or the Legion Go's on-screen keyboard.

## Controls

Icons use a consistent white Xbox-style design. The table describes the default mappings.

| Button | Action |
| :--- | :--- |
| <img src="assets/buttons/left-stick.svg" width="28" height="28" alt="Left stick"> **Left stick — move** | Move the cursor with analog precision. |
| <img src="assets/buttons/left-stick.svg" width="28" height="28" alt="Left-stick press"> **Left stick — press** | Unassigned; does nothing. |
| <img src="assets/buttons/lb.svg" width="28" height="28" alt="LB"> **LB** | Hold 0.5 seconds for right-click. |
| <img src="assets/buttons/rb.svg" width="28" height="28" alt="RB"> **RB** | Hold 0.5 seconds for left-click; keep holding to drag. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right stick"> **Right stick — move** | Pan/rotate the camera; center the stick to release the drag and restore the cursor. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right-stick press"> **Right stick — short press** | Fly toward camera center on release. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right-stick hold"> **Right stick — hold** | Hold one second to request stop. |
| <img src="assets/buttons/lt.svg" width="28" height="28" alt="LT"> <img src="assets/buttons/rt.svg" width="28" height="28" alt="RT"> **LT / RT** | Unassigned; neither changes cursor speed. |
| <img src="assets/buttons/dpad.svg" width="28" height="28" alt="D-pad"> **D-pad — up/down** | Scroll the hovered UI, or zoom over space. |
| <img src="assets/buttons/dpad.svg" width="28" height="28" alt="D-pad"> **D-pad — left/right** | Left/right arrow keys. |
| <img src="assets/buttons/a.svg" width="28" height="28" alt="A"> **A** | Hold-confirmed left-click, like RB. |
| <img src="assets/buttons/b.svg" width="28" height="28" alt="B"> **B** | Escape / back. |
| <img src="assets/buttons/x.svg" width="28" height="28" alt="X"> **X — hold** | Hold Ctrl; combine with RB for Ctrl + left-click, such as target locking with the default EVE shortcut. |
| <img src="assets/buttons/y.svg" width="28" height="28" alt="Y"> **Y** | Tab. |
| <img src="assets/buttons/view.svg" width="28" height="28" alt="View"> **View / Back** | Ctrl + Space on release; stop ship with EVE's default shortcut. |
| <img src="assets/buttons/menu.svg" width="28" height="28" alt="Menu"> **Menu / Start** | Escape on release. |
| <img src="assets/buttons/view.svg" width="28" height="28" alt="View"> <img src="assets/buttons/menu.svg" width="28" height="28" alt="Menu"> **View + Menu** | Pause/resume controller input. |

Keyboard shortcuts follow your EVE bindings. Right-stick flight/stop uses the native client commands and does not depend on keyboard shortcuts.

## Configuration

Open **Mods → EveJS Controller → Configure** in the launcher. Changes to `preferences.json` reload automatically while the companion is running.

| Setting | Default | Purpose |
| :--- | :--- | :--- |
| Controller | Auto-detect | Choose a specific XInput slot if a virtual controller is selected instead. |
| Stick deadzone | 20% | Suppress stick drift. |
| Maximum cursor speed | 1,100 px/s | Adjust full-deflection cursor movement. |
| Maximum camera speed | 800 px/s | Adjust camera dragging. |
| Click hold | 500 ms | Set ordinary mouse-click confirmation time. |
| Right-stick stop hold | 1,000 ms | Set the separate stop confirmation time. |
| Circular cursor | On | Show the animated controller cursor. |
| UI attraction | On | Enable gentle attraction to hovered controls. |

### Camera drag anchor

Camera dragging starts at **50% across and 40% down** the client window. Keep that point in clear space. If a window covers it, adjust the advanced **Camera anchor across/down window** settings. The drag anchor does not change camera-center flight direction.

Camera dragging temporarily owns the pointer and suspends normal mouse bindings. Centering the right stick restores the previous pointer location. A right-stick press already in progress can still complete its flight/stop gesture.

<details>
<summary><strong>Custom button bindings</strong></summary>

Supported names include `MOUSE_LEFT`, `MOUSE_RIGHT`, `MOUSE_MIDDLE`, `DOUBLE_LEFT_CLICK`, `CTRL`, `SHIFT`, `ALT`, letters, digits, `F1`–`F24`, `ENTER`, `ESC`, `TAB`, `SPACE`, arrows, and common editing keys. Use `+` for a chord, such as `CTRL+SPACE`, or `tap:` for a brief keyboard press, such as `tap:F1`.

Mouse bindings always use hold confirmation. `DOUBLE_LEFT_CLICK` sends one pair of brief clicks after confirmation. `SCROLL_UP` and `SCROLL_DOWN` must stand alone. Right-stick press is reserved for flight/stop; left-stick press remains inactive. Keep keyboard actions on View/Menu, which run on release to distinguish them from the pause chord.

</details>

## Troubleshooting

| Symptom | Check |
| :--- | :--- |
| The mod is missing from Mods | Confirm `evejs-launcher.mod.json` is directly inside the mod folder, then refresh Mods. Avoid an extra nested repository folder. |
| No controller companion after login | Confirm the mod is enabled, restart the game server, and log in through the launcher. Check the server log for `[EveJS Controller] Login startup ready`. |
| Input stays inactive | Focus EVE, center both sticks, release all buttons, and check the companion status window. |
| Wrong controller selected | Choose its XInput slot in Configure; Legion Go must use Gamepad/XInput mode. |
| Duplicate or unexpected inputs | Check whether another controller mapper is active. |
| Camera dragging moves a UI window | Move the configured camera drag anchor into clear space. |
| Native pointer remains visible | Check the companion's cursor status; unsupported masking APIs retain the native pointer. |
| Flight/stop does nothing | Undock, wait for the character/session to be ready, and check the navigation status in the companion window. |

<details>
<summary><strong>Diagnostic startup</strong></summary>

`StartController.cmd` is an optional troubleshooting entry point. Normal installation starts the companion automatically. Quit any standalone copy before testing the launcher-managed copy.

If automatic startup fails, check the client log for `EVEJS_CONTROLLER_START:FAILED`. Include that log entry and the companion status when reporting the issue.

</details>

## Changelog and versions

Releases use **`MAJOR.MINOR.PATCH`** versions, beginning with **0.1.0**. See [CHANGELOG.md](CHANGELOG.md) for detailed, categorized changes. Unpublished changes remain under **Unreleased** until a release is built.

## Community

Join the [EveJS Discord](https://discord.gg/qxgMmtGmb7) or [open an issue](https://github.com/cfin3d/EveJS-Controller-Support/issues). For input problems, include the mod, EveJS and launcher versions, your controller model, and the steps that reproduce the issue.

Licensed under [GPL-3.0](LICENSE).
