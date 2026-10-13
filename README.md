<p align="center">
  <img src="assets/eve-online-white.png" alt="EVE Online" width="300">
</p>

<h1 align="center">EveJS Controller Support</h1>

<p align="center">
  Universal controller support for EveJS, with precision cursor control, camera navigation, and automatic input switching.
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
> **Under development.** No release has been published. The first release will be **0.1.0**. The repository contains an unreleased testing build.

## Features

- **Analog cursor control:** small left-stick movements give precision; full deflection moves quickly across the screen.
- **Hold to click:** a half-second confirmation prevents accidental clicks, with a circular progress indicator and support for dragging.
- **Gentle UI attraction:** slow cursor movement draws toward nearby hovered controls; stronger movement lets you escape.
- **Camera control and ship navigation:** pan with the right stick, tap it to fly toward camera center, or hold it for one second to stop.
- **Minimal EVE-style visuals:** a white/cyan circular cursor and a small camera-center dot that stays beneath menus and windows.
- **Automatic input switching:** controller input activates controller mode; mouse or keyboard input returns to normal controls.
- **Inside the game:** starts at login and runs within the EVE client, with no background companion or notification-area icon.

## Compatibility

| Requirement | Supported configuration |
| :--- | :--- |
| EveJS | **0.12.9**, with the supported login-handshake source |
| EveJS Launcher | **1.0.53 or newer** |
| EVE client | **Build 3396210**, Windows x64 |
| Controller input | XInput-compatible devices; automatic selection or slot 0–3 |
| PlayStation controllers | Direct support, including PS5 DualSense, is not implemented yet |
| Server backend | Native or Docker server, with controller input running inside the Windows client |


Controller coverage currently uses XInput. The project is designed to grow across controller families, including native PlayStation support.

## Installation

### Current testing build

1. Choose **Code → Download ZIP** on this repository, then extract it.
2. Rename the extracted repository folder to **`evejs-controller`**.
3. Drag that entire folder into the **Mods folder for your EveJS installation**, accessible through EveJS Launcher.
4. Open **Mods**, refresh the list, and enable **EveJS Controller**. Adopt the package if prompted.
5. Restart the game server when requested, then launch EVE and log in through the launcher.
6. Center both sticks and release all buttons once, then use a controller input to enter controller mode.

The folder must contain the manifest directly:

```text
mods/
└── evejs-controller/
    ├── evejs-launcher.mod.json
    ├── controller.py
    ├── launcher-helper.ps1
    ├── loader.js.disabled
    ├── login-delivery.js
    ├── client-ui.py
    ├── preferences.json
    └── …
```

The launcher manages the loader filename when enabling/disabling the mod. No separate controller application, compilation, or runtime installation is needed.

### When releases are available

Download the mod ZIP from [Releases](https://github.com/cfin3d/EveJS-Controller-Support/releases), extract it, and drag the enclosed **`evejs-controller`** folder into Mods. Release ZIPs will contain that folder at the top level, ready to install. Follow steps 4–6 above.

<details>
<summary><strong>Updating an existing installation</strong></summary>

Close EVE before replacing the mod folder. Keep a backup of your configured `preferences.json`, replace the package with the new mod folder, and restore your preferences if the update's changelog says they remain compatible. Refresh Mods, enable the package if necessary, restart the server, and log back in.

</details>

## Usage

The mod starts inside the EVE client when you log in through EveJS Launcher. There is no separate application to launch and no taskbar or notification-area icon.

Use a controller input to switch to **controller mode**. Move the mouse, scroll, click, or use the keyboard to switch to **mouse/keyboard mode**. Fresh controller activity switches back automatically. Controller-generated cursor events do not trigger a switch to mouse mode.

Switching to mouse/keyboard input cancels unfinished holds, releases controller-owned clicks, hides the controller cursor/dot, and restores the normal pointer. Controller input applies only while EVE has foreground focus. After focus changes or controller reconnection, center the sticks and release the buttons once before resuming.

Disable the mod in the launcher to stop its input and restore the normal pointer. Restart the game server when requested.

### Cursor and hold confirmation

Use the left stick to move the circular cursor. Hold **RB** for **0.5 seconds** to confirm a left-click, or **LB** to confirm a right-click. Release early to cancel. Keep holding after confirmation and move the left stick to drag.

The cyan arc shows left-click confirmation; the amber arc shows right-click confirmation. Changing targets or moving more than 10 pixels resets an unfinished confirmation. Gentle attraction works only around real hovered UI controls while moving slowly, and disengages during clicks, drags, or physical mouse movement.

### Camera and ship movement

Move the right stick to pan/rotate the camera. A small pale-blue dot marks **camera center**, the direction used for right-stick flight. It sits in EVE's native space UI below windows and menus, and hides when UI covers the center or a menu/modal dialog is open.

- **Short right-stick press:** release before one second to request flight toward camera center. Cursor position does not affect this direction.
- **Right-stick hold:** at one second, request EVE's normal stop command. The ship slows according to its normal physics. A long hold never starts flight first or on release.

The outer orange cursor arc shows the stop timer. Navigation is available only when your character is ready in space. Chat uses your keyboard; typing automatically switches to mouse/keyboard mode.

## Controls

Only the following controls have actions assigned. Icons use a consistent white design.

| Control | Action |
| :--- | :--- |
| <img src="assets/buttons/left-stick.svg" width="28" height="28" alt="Left stick"> **Left stick — move** | Move the cursor: small deflections are precise; full deflection is fast. |
| <img src="assets/buttons/left-stick.svg" width="28" height="28" alt="Left-stick press"> **Left stick — press** | Unassigned; does nothing. |
| <img src="assets/buttons/lb.svg" width="28" height="28" alt="Left bumper"> **Left bumper** | Hold 0.5 seconds for right-click. |
| <img src="assets/buttons/rb.svg" width="28" height="28" alt="Right bumper"> **Right bumper** | Hold 0.5 seconds for left-click; keep holding to drag. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right stick"> **Right stick — move** | Pan/rotate the camera directly. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right-stick press"> **Right stick — short press** | Fly toward camera center on release. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right-stick hold"> **Right stick — hold** | Hold one second to request stop. |
| <img src="assets/buttons/lt.svg" width="28" height="28" alt="Left trigger"> <img src="assets/buttons/rt.svg" width="28" height="28" alt="Right trigger"> **Triggers** | Unassigned. |
| <img src="assets/buttons/a.svg" width="28" height="28" alt="Face button"> <img src="assets/buttons/b.svg" width="28" height="28" alt="Face button"> <img src="assets/buttons/x.svg" width="28" height="28" alt="Face button"> <img src="assets/buttons/y.svg" width="28" height="28" alt="Face button"> **Face buttons** | Unassigned. |
| <img src="assets/buttons/dpad.svg" width="28" height="28" alt="D-pad"> **D-pad** | Unassigned. |
| <img src="assets/buttons/view.svg" width="28" height="28" alt="View button"> <img src="assets/buttons/menu.svg" width="28" height="28" alt="Menu button"> **View / Menu** | Unassigned. |

Ship navigation uses EVE's native client commands. Camera movement does not drag the UI cursor or require a clear-space mouse anchor.

## Configuration

Open **Mods → EveJS Controller → Configure** in the launcher. Changes to `preferences.json` reload automatically inside the client.

| Setting | Default | Purpose |
| :--- | :--- | :--- |
| Controller | Auto-detect | Choose a specific XInput slot if a virtual controller is selected instead. |
| Stick deadzone | 20% | Suppress stick drift. |
| Maximum cursor speed | 1,100 px/s | Adjust full-deflection cursor movement. |
| Camera movement speed | 800 | Adjust the right-stick camera response. |
| Click hold | 500 ms | Set ordinary mouse-click confirmation time. |
| Right-stick stop hold | 1,000 ms | Set the separate stop confirmation time. |
| Circular cursor | On | Show the animated controller cursor. |
| UI attraction | On | Enable gentle attraction to hovered controls. |

## Troubleshooting

| Symptom | Check |
| :--- | :--- |
| The mod is missing from Mods | Confirm `evejs-launcher.mod.json` is directly inside the mod folder, then refresh Mods. Avoid an extra nested repository folder. |
| Controller input stays inactive | Enable the mod, restart the server when requested, log in through the launcher, focus EVE, and center/release the controls once. |
| Wrong controller selected | Choose the appropriate input slot in Configure. |
| Cursor changes back to the native pointer | Mouse or keyboard activity activates mouse/keyboard mode. Use fresh controller input to switch back. |
| Flight/stop does nothing | Undock and wait for your character/session to be ready. |

If startup fails, check the client log for `EVEJS_CONTROLLER_START:FAILED` or an `EVEJS_CONTROLLER:Input paused` entry, and include it when reporting an issue.

## Changelog and versions

Releases use **`MAJOR.MINOR.PATCH`** versions, beginning with **0.1.0**. See [CHANGELOG.md](CHANGELOG.md) for detailed, categorized changes. Unpublished changes remain under **Unreleased** until a release is built.

## Community

Join the [EveJS Discord](https://discord.gg/qxgMmtGmb7) or [open an issue](https://github.com/cfin3d/EveJS-Controller-Support/issues). For input problems, include the mod, EveJS and launcher versions, your controller model, and the steps that reproduce the issue.

Licensed under [GPL-3.0](LICENSE).
