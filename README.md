<p align="center">
  <img src="assets/evejs-offline-white.png" alt="EVEJS Offline" width="300">
</p>

<h1 align="center">EveJS Controller Support</h1>

<p align="center">
  Universal controller support for EveJS, with precision cursor control, camera navigation, and automatic input switching.
</p>

<p align="center">
  <img alt="Status: Unreleased" src="https://img.shields.io/badge/Status-Unreleased-57606a?style=for-the-badge">
  <img alt="EveJS 0.12.9" src="https://img.shields.io/badge/EveJS-0.12.9-ffffff?style=for-the-badge&amp;labelColor=24292f">
  <img alt="Launcher 1.0.53 or Newer" src="https://img.shields.io/badge/Launcher-1.0.53%2B-ffffff?style=for-the-badge&amp;labelColor=24292f">
</p>

<p align="center">
  <a href="https://discord.gg/qxgMmtGmb7"><img alt="Join the EveJS Discord" src="https://img.shields.io/badge/EveJS_Discord-Join-5865f2?style=for-the-badge&amp;logo=discord&amp;logoColor=white"></a>
  <a href="https://github.com/cfin3d/EveJS-Controller-Support/issues"><img alt="Report an Issue" src="https://img.shields.io/badge/Issues-Report-24292f?style=for-the-badge&amp;logo=github&amp;logoColor=white"></a>
  <a href="CHANGELOG.md"><img alt="Read the Changelog" src="https://img.shields.io/badge/Changelog-Read-24292f?style=for-the-badge"></a>
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#compatibility">Compatibility</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#usage">Usage</a> ·
  <a href="#controls">Controls</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#support">Support</a>
</p>

---

> [!NOTE]
> **Unreleased Testing Build.** The first release will be **0.1.0**.

## Features

- **Precision Cursor Control:** finer movement with smooth acceleration everywhere, plus attraction to UI controls and context-menu items.
- **Click Confirmation:** circular progress feedback with support for dragging.
- **Camera and Ship Navigation:** pan, zoom, fly toward camera center, and stop.
- **Controller Settings:** select a device, customize bindings, and save profiles in EVE's settings menu.
- **Automatic Input Switching:** move freely between controller and mouse/keyboard controls.
- **In-Game Runtime:** starts at login; no separate application or tray icon.

## Compatibility

| Requirement | Supported Configuration |
| :--- | :--- |
| EveJS | **0.12.9** |
| EveJS Launcher | **1.0.53+** |
| EVE Client | **Build 3396210**, Windows x64 |
| Controller Input | XInput-compatible devices |
| Server Backend | Native or Docker |

Direct PlayStation support, including PS5 DualSense, is not available yet.

## Installation

1. **Download:** select **Code → Download ZIP**, then extract it.
2. **Prepare:** rename the extracted folder to **`evejs-controller`**.
3. **Install:** drag the folder into your EveJS installation's **Mods** folder.
4. **Enable:** refresh **Mods** in the launcher and enable **EveJS Controller**. Adopt the package if prompted.
5. **Launch:** restart the server when requested, then log in through EveJS Launcher.

<details>
<summary><strong>Folder Layout</strong></summary>

The manifest belongs directly inside the mod folder:

```text
mods/
└── evejs-controller/
    ├── evejs-launcher.mod.json
    └── …
```

</details>

<details>
<summary><strong>Release Downloads and Updates</strong></summary>

- **Release Downloads:** when available, download a ZIP from [Releases](https://github.com/cfin3d/EveJS-Controller-Support/releases). Extract it and drag the enclosed `evejs-controller` folder into Mods, then follow steps 4–5 above.
- **Updates:** close EVE and back up `preferences.json`. Replace the mod folder, restore compatible settings according to the changelog, refresh Mods, and restart/log in when requested.

</details>

## Usage

| Mode | How to Activate |
| :--- | :--- |
| **Controller Mode** | Use a controller input. |
| **Mouse/Keyboard Mode** | Move, click, or scroll the mouse, or use the keyboard. |

Switching is automatic. Mouse/keyboard input cancels unfinished controller holds and restores the normal pointer.

### Controls

| Control | Action |
| :--- | :--- |
| <img src="assets/buttons/left-stick.svg" width="28" height="28" alt="Left Stick"> **Left Stick** | Move the cursor. Small movements are precise; full deflection is fast. |
| <img src="assets/buttons/lb.svg" width="28" height="28" alt="Left Bumper"> **Left Bumper** | Hold **0.5 seconds** for right-click. |
| <img src="assets/buttons/rb.svg" width="28" height="28" alt="Right Bumper"> **Right Bumper** | Hold **0.5 seconds** over a target to open its radial menu. On normal UI, hold for left-click and continue holding to drag. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right Stick"> **Right Stick** | Pan/rotate the camera in space or while docked. |
| <img src="assets/buttons/lt.svg" width="28" height="28" alt="Left Trigger"> <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right Stick"> **Hold Left Trigger + Right Stick** | Move **up** to zoom in or **down** to zoom out. Release the trigger to resume panning. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right Stick Press"> **Right Stick — Short Press** | Release before one second to fly toward camera center. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right Stick Hold"> **Right Stick — Hold** | Hold **one second** to request stop. |

These are the default bindings. Release a bumper early to cancel its click. A long right-stick hold stops the ship without first issuing flight.

### Target Radial Menu

Hold **RB** over a targetable space bracket, overview entry, or locked-target icon until the cyan indicator fills. Windows, empty space, your own ship, and non-targetable objects do not open the controller radial.

| Control While Open | Action |
| :--- | :--- |
| <img src="assets/buttons/left-stick.svg" width="28" height="28" alt="Left Stick"> **Left Stick** | Move the cursor within the wheel to select a wedge. Hold toward **More** to open its additional options. |
| <img src="assets/buttons/dpad.svg" width="28" height="28" alt="D-Pad Up / Down"> **D-Pad Up / Down** | Increase / decrease a range action's distance. Keeps that action selected, including after centering the stick. |
| <img src="assets/buttons/rb.svg" width="28" height="28" alt="Right Bumper"> **Release Right Bumper** | Execute the highlighted action once. Release without a highlighted action to cancel. |
| <img src="assets/buttons/b.svg" width="28" height="28" alt="B"> **B** | Cancel immediately. |

Normal cursor, click, camera, zoom, flight, and stop controls pause while the wheel is open. Mouse/keyboard activity cancels it. Release the controls after closing to resume normal controller input.

<details>
<summary><strong>Radial Behavior and Bindings</strong></summary>

- Uses EVE's native actions, disabled states, range values, icons, and animations. Available actions depend on the target.
- Keeps the original target until closing; target loss, docking, session changes, or opening Settings cancels the wheel.
- **Left-Click / Target Radial** shares one configurable binding and the click hold timer. Existing bindings and preferences are preserved.
- The wheel displays its activation and cancel buttons. If the activation binding includes **B**, the cancel prompt uses a free face button, or left-stick press if necessary.
- If the activation binding uses **D-Pad Up / Down**, the right stick adjusts range vertically instead; its normal camera actions remain paused.
- Centering the left stick clears selection unless a range adjustment is active. D-pad input can restore the last range action on the current level; use **B** to cancel after adjusting a range.

</details>

<details>
<summary><strong>Cursor Feedback</strong></summary>

| Indicator | Meaning |
| :--- | :--- |
| **Cyan Arc** | Left-click or target radial confirmation. |
| **Amber Arc** | Right-click confirmation. |
| **Orange Arc** | Stop confirmation. |
| **Center Dot** | Flight direction; hidden beneath menus and when UI covers camera center. |

- **UI Attraction:** move slowly toward a nearby control or context-menu item; strong or sustained outward movement escapes attraction. It pauses while clicking or dragging.
- **White Cursor Ring:** a larger, solid white outline; the camera-center dot keeps its minimal size.
- **Hold Reset:** changing targets or moving more than 10 pixels restarts an unfinished click hold.

</details>

## Configuration

In EVE, open **Settings → Controller**. Changes save and apply automatically.

| Option | Use |
| :--- | :--- |
| **Controller** | Auto-detect or choose a connected device. **Identify Controller** selects the device you use next. |
| **Camera** | Adjust pan/zoom speed and toggle **Invert Camera Pan** for vertical panning. |
| **Cursor and Hold Timing** | Adjust precision, UI attraction, cursor appearance, and click/stop timing. |
| **Bindings** | Compact white button icons show each input or combination. Rebind an action or clear its input; conflicts show a confirmation before replacing the previous assignment. |
| **Custom Bindings** | Choose a modifier and keyboard key, capture a controller button/combination, then select **Add Binding**. |
| **Profiles** | Save, load, or delete named configurations; **Restore Defaults** restores the default controls and feel. |

<details>
<summary><strong>Defaults and Binding Capture</strong></summary>

| Setting | Default |
| :--- | :--- |
| Controller | Auto-Detect |
| Stick Deadzone | 20% |
| Maximum Cursor Speed | 1,100 px/s |
| Camera Movement Speed | 800 |
| Camera Zoom Speed | 0.8 |
| Invert Camera Pan | Off |
| Click Hold | 500 ms |
| Right Stick Stop Hold | 1,000 ms |
| Circular Cursor | On |
| UI Attraction | On |

- **Capture:** select the binding, release controls, then press buttons or move a stick. Hold modifiers while moving the stick; release a button combination to finish recording it.
- **Cancel:** select **Cancel Input Detection**, press Esc, or wait 15 seconds.
- **Tap/Hold:** flight occurs on release; stop uses the configured hold time. They can share one binding.
- **Rear Buttons:** separate bindings require independently exposed inputs. The current backend exposes standard XInput buttons, sticks, and triggers; rear buttons mapped to those inputs share their bindings.
- **Launcher:** basic feel settings remain available under **Mods → EveJS Controller → Configure** and use the same configuration file.

</details>

<details>
<summary><strong>Custom Shortcuts and Conflicts</strong></summary>

- Uses keyboard shortcuts configured in **Settings → Shortcuts**. The editor shows the EVE action assigned to the selected modifier/key; configure an unassigned shortcut there first.
- Custom actions run once per controller press through EVE's native command dispatcher. They pause in Settings, during input capture, and while the controller radial is open.
- Selecting an existing custom row opens it for editing; **Remove** deletes it. Custom bindings are included in saved profiles.
- **Replace Binding** removes the conflicting controller assignments and saves the new one. **Cancel** leaves the existing configuration intact.
- A replacement can disable a core controller action. The dialog names affected actions and explains when replacing left-click requires mouse/keyboard to configure a replacement.
- Supports up to **32 custom bindings**. If an EVE shortcut later changes to another action, the old custom binding does not execute that new action automatically.

</details>

## Support

Join the [EveJS Discord](https://discord.gg/qxgMmtGmb7) or [report an issue](https://github.com/cfin3d/EveJS-Controller-Support/issues). Include your versions, controller model, and reproduction steps.

<details>
<summary><strong>Troubleshooting</strong></summary>

| Problem | Check |
| :--- | :--- |
| **Mod Missing** | Check the folder layout above, then refresh Mods. |
| **Input Inactive** | Enable the mod, restart when requested, log in through the launcher, and focus EVE. |
| **Wrong Controller** | Open **Settings → Controller → Identify Controller**, then use the desired device. |
| **Native Pointer Returns** | Mouse/keyboard activity changes modes. Use controller input to switch back. |
| **Flight/Stop Unavailable** | Undock and wait for the character/session to be ready. |

For startup failures, include client-log entries containing `EVEJS_CONTROLLER_START:FAILED` or `EVEJS_CONTROLLER:Input paused`.

</details>

---

**Versions:** `MAJOR.MINOR.PATCH`, starting at **0.1.0**. See the [Changelog](CHANGELOG.md) for detailed updates.

Licensed under [GPL-3.0](LICENSE).
