# Reporting Issues and Suggestions

Help improve EveJS Controller Support by describing what you observed, how to reproduce it, and the setup you used. You do not need technical expertise to submit a useful report.

**[Open a Report](https://github.com/cfin3d/EveJS-Controller-Support/issues/new/choose)** · **[Search Existing Issues](https://github.com/cfin3d/EveJS-Controller-Support/issues)** · **[Read the README](../README.md)** · **[Join EveJS Discord](https://discord.gg/qxgMmtGmb7)**

## Choose the Right Form

| Form | Use It For |
| :--- | :--- |
| **[Bug Report](https://github.com/cfin3d/EveJS-Controller-Support/issues/new?template=01-bug-report.yml)** | A broken control, unexpected behavior, UI problem, startup failure, or crash. |
| **[Feature Request](https://github.com/cfin3d/EveJS-Controller-Support/issues/new?template=02-feature-request.yml)** | A new function, better layout, accessibility option, or improvement to existing controls. |
| **[Controller Compatibility Report](https://github.com/cfin3d/EveJS-Controller-Support/issues/new?template=03-controller-compatibility.yml)** | A tested device configuration, including successful setups and remaining limitations. |
| **[EveJS Discord](https://discord.gg/qxgMmtGmb7)** | General setup questions and gameplay help. |

## Before You Submit

1. **Search Open and Closed Issues.** If the same problem already exists, add your setup and new evidence there. Link related reports when the behavior differs.
2. **Check Compatibility and Known Behavior.** Review the [README](../README.md#compatibility) and [Unreleased Changelog](../CHANGELOG.md#unreleased). Include the version you actually tested; updating is helpful but is not required to report a problem.
3. **Keep Each Report Focused.** Submit one bug or suggestion per issue. A compatibility report can summarize several tested functions and link separate bug reports.
4. **Use a Specific Title.** State the affected function and visible result. For example: `[Bug] Neocom submenu does not open with D-Pad Right`.

> [!TIP]
> **Unknown Is Fine.** If you cannot find a version, device name, or setting, write **Unknown** and submit the details you do have. Screenshots, logs, and comparison tests are optional.

## Write a Useful Bug Report

| Detail | What Helps |
| :--- | :--- |
| **Actual Behavior** | The visible result, exact error text, and impact on play. |
| **Expected Behavior** | What the same input should do. |
| **Reproduction Steps** | Starting screen, docked/undocked state, exact menu or target, button sequence, and tap/hold/release order. |
| **Frequency** | Every attempt, intermittent, or a single occurrence; include an approximate count if known. |
| **Versions and Setup** | Mod build, EveJS, launcher, client build, OS, controller, connection, and input software. |
| **Relevant Configuration** | Selected device, input backend, icon style, changed bindings, hold times, and relevant cursor/camera options. |
| **Evidence** | A labeled screenshot, short clip, or relevant sanitized log excerpt. |
| **Comparisons** | If already checked: mouse/keyboard behavior, another connection, previous build, or a workaround. |

<details>
<summary><strong>Example Reproduction Steps</strong></summary>

1. Undock and highlight a station in the overview.
2. Hold the configured radial button until its indicator fills.
3. Move the left stick to **Orbit**, then press **D-Pad Up** twice.
4. Release the stick, then release the radial button.
5. Describe the highlighted action, displayed range, toast, and actual ship movement separately.

For attraction problems, name the menu and neighboring items. For dragging, name the window and say whether the click hold completed. For timing problems, include an approximate delay and whether the game was docking, undocking, or changing sessions.

For vibration problems, include the master toggle, event toggles/strengths, **Enhanced DualSense Haptics (USB)** setting, affected pattern, and displayed **Vibration** status after **Test Vibration**. State whether the preview works but live damage feedback fails, or both fail. A preview does not require combat or destroying your ship.

</details>

### Find Your Setup Details

| Detail | Where to Look |
| :--- | :--- |
| **Mod Version** | The mod entry in the launcher's **Mods** tab. For an unreleased snapshot, also include its download date or Git commit when known. |
| **EveJS / Launcher Versions** | Your launcher or installation's version information. Copy the displayed values when available. |
| **EVE Client Build** | **Settings → About EVE**, or the client version shown on screen. |
| **Controller Name and Backend** | **Settings → Controller**: copy the selected/detected device name and **Input Backend** label. If the category is missing, state that. |
| **Controller Settings** | **Settings → Controller**: device selection, **Button Icons**, bindings, and relevant timing/cursor/camera options. |
| **Platform** | OS version; on SteamOS or another compatibility setup, include the Proton/Wine version if known. |
| **Input Software** | Steam Input, another mapper, or **Not Used**. Include the layout and whether a trackpad maps to a joystick. |
| **Server Backend** | **Native**, **Docker**, or **Unknown** for the EveJS server setup. |

An unreleased build may display the planned version **0.1.0**. The download date or commit helps distinguish snapshots that share that number.

### Screenshots and Logs

- Attach screenshots or a short video to the form's evidence field. Show the affected control and the surrounding UI when useful.
- Explain which controller input was active. A screenshot shortcut or recording control can temporarily switch the game to mouse/keyboard mode.
- If logs are available, copy the entries near the failure and the nearby error/traceback. Search for `EVEJS_CONTROLLER`, `EVEJS_CONTROLLER_START`, or `[EveJS Controller]`; startup, paused-input, and SDL fallback messages are especially useful.
- Include the approximate occurrence time when providing a log excerpt. If you cannot locate logs, submit the report without them.
- Share relevant settings or a sanitized excerpt of `preferences.json` when helpful. A full configuration file is optional.

> [!IMPORTANT]
> **Reports and Attachments Are Public.** Remove passwords, authentication tokens, account details, personal file paths, and unrelated private chat before posting. Share relevant excerpts rather than full account, profile, or launcher folders.

## Suggest a Feature

Describe **the player need**, **the proposed behavior**, and **how it would fit existing controls**. A concrete gameplay example is more useful than a feature name alone.

- For a binding or combination, explain activation, tap/hold timing, confirmation/cancellation, and any conflict with current actions.
- For a menu or HUD change, describe navigation, focus, and how normal cursor controls resume.
- For accessibility, describe the input difficulty and the adjustment that would help. Personal medical information is not needed.
- Add examples or references when helpful, and explain the specific behavior you want to adopt.

Suggestions can be discussed and refined; submission does not guarantee implementation or a release date.

## Share Controller Compatibility Results

Successful reports are welcome, especially for PlayStation controllers, Steam Controller, and Steam Deck. Record the **exact hardware**, **connection**, **platform**, **input layout**, **detected name/backend**, and whether the icons were **automatic or manually selected**.

Mark each tested function **Worked**, **Failed**, or **Not Tested**. Report USB and Bluetooth separately if their results differ; do not assume one confirms the other.

<details>
<summary><strong>Suggested Compatibility Checklist</strong></summary>

Test only the items relevant to your setup, in a safe gameplay situation. Include custom mappings if you changed the defaults.

| Area | Useful Checks |
| :--- | :--- |
| **Detection** | Device appears; Identify Controller selects it; multiple devices select correctly. |
| **Cursor** | Fine movement, attraction, held clicks, and continued hold for dragging. |
| **Camera** | Pan and trigger-plus-stick zoom while docked and in space. |
| **Ship Actions** | Short stick press flies toward camera center; long hold requests stop. |
| **Radial** | Opens over a valid target; cursor stays within the wheel; range changes, confirmation, and cancellation work. |
| **Neocom** | Select/View opens it; D-pad moves between entries/submenus; timed confirm/cancel works. |
| **Settings and Icons** | Correct button style, binding capture, combinations, custom shortcuts, and saved profiles. |
| **Vibration** | Test Vibration patterns, strength changes, master disable, and Stop Vibration. Report standard and enhanced DualSense results separately, including the displayed status and USB/Bluetooth connection. |
| **Extra Inputs** | Rear buttons or touchpad clicks can be captured when independently exposed; identify any shared mappings. |
| **Input Switching** | Physical controller and mouse/keyboard activity switch modes as expected. |
| **Reconnection** | Unplug/reconnect or wireless reconnection restores input; note changes in detected name or slot. |

</details>

Steam Input and other mappers may expose a virtual Xbox controller. Include the mapper configuration and any manual icon override so another player can reproduce your setup. Enhanced DualSense USB haptics are experimental and require a directly detected compatible device/audio endpoint; ordinary input or rumble results do not verify that output path. Gyro, touch gestures, and adaptive-trigger resistance are not currently implemented.

## After You Submit

- Watch for follow-up questions and add new evidence to the same issue.
- If asked to test a fix, include the new build/date and say which original steps now work or still fail.
- If you find a workaround, explain it without removing the original reproduction steps.
- Link related bugs from compatibility reports so each failure can be tracked separately.
