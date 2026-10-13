<p align="center">
  <img src="assets/eve-online-white.png" alt="EVE Online" width="300">
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

- **Precision Cursor Control:** smooth analog movement and gentle attraction to UI controls.
- **Click Confirmation:** circular progress feedback with support for dragging.
- **Camera and Ship Navigation:** pan, fly toward camera center, and stop using the right stick.
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
| <img src="assets/buttons/rb.svg" width="28" height="28" alt="Right Bumper"> **Right Bumper** | Hold **0.5 seconds** for left-click; continue holding and move the cursor to drag. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right Stick"> **Right Stick** | Pan/rotate the camera. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right Stick Press"> **Right Stick — Short Press** | Release before one second to fly toward camera center. |
| <img src="assets/buttons/right-stick.svg" width="28" height="28" alt="Right Stick Hold"> **Right Stick — Hold** | Hold **one second** to request stop. |

Release a bumper early to cancel its click. A long right-stick hold stops the ship without first issuing flight.

<details>
<summary><strong>Cursor Feedback</strong></summary>

| Indicator | Meaning |
| :--- | :--- |
| **Cyan Arc** | Left-click confirmation. |
| **Amber Arc** | Right-click confirmation. |
| **Orange Arc** | Stop confirmation. |
| **Center Dot** | Flight direction; hidden beneath menus and when UI covers camera center. |

- **UI Attraction:** move slowly toward a control to attract the cursor; stronger movement escapes it.
- **Hold Reset:** changing targets or moving more than 10 pixels restarts an unfinished click hold.

</details>

## Configuration

Open **Mods → EveJS Controller → Configure**. Settings reload automatically.

| Setting | Default |
| :--- | :--- |
| Controller | Auto-Detect |
| Stick Deadzone | 20% |
| Maximum Cursor Speed | 1,100 px/s |
| Camera Movement Speed | 800 |
| Click Hold | 500 ms |
| Right Stick Stop Hold | 1,000 ms |
| Circular Cursor | On |
| UI Attraction | On |

## Support

Join the [EveJS Discord](https://discord.gg/qxgMmtGmb7) or [report an issue](https://github.com/cfin3d/EveJS-Controller-Support/issues). Include your versions, controller model, and reproduction steps.

<details>
<summary><strong>Troubleshooting</strong></summary>

| Problem | Check |
| :--- | :--- |
| **Mod Missing** | Check the folder layout above, then refresh Mods. |
| **Input Inactive** | Enable the mod, restart when requested, log in through the launcher, and focus EVE. |
| **Wrong Controller** | Choose its input slot in Configure. |
| **Native Pointer Returns** | Mouse/keyboard activity changes modes. Use controller input to switch back. |
| **Flight/Stop Unavailable** | Undock and wait for the character/session to be ready. |

For startup failures, include client-log entries containing `EVEJS_CONTROLLER_START:FAILED` or `EVEJS_CONTROLLER:Input paused`.

</details>

---

**Versions:** `MAJOR.MINOR.PATCH`, starting at **0.1.0**. See the [Changelog](CHANGELOG.md) for detailed updates.

Licensed under [GPL-3.0](LICENSE).
