# Changelog

Changes are grouped by release and category. Versions use **MAJOR.MINOR.PATCH**. No release has been published; the initial release will be **0.1.0**.

## [Unreleased]

### Added

- Controller input running inside the EVE client, with automatic selection of XInput-compatible devices across slots 0–3.
- Automatic switching between controller mode and mouse/keyboard mode based on physical input.
- Tagged controller-generated mouse events so they do not trigger mouse/keyboard mode.
- Analog left-stick cursor navigation with a radial deadzone, squared precision curve and retained fractional movement for slow control.
- Left-bumper right-click and right-bumper left-click with a configurable 500 ms confirmation hold.
- Early-release cancellation, confirmation reset after changing targets/moving away, and continued confirmed holds for dragging.
- Native white/cyan circular cursor with fluid attraction feedback and separate left-click, right-click and stop progress arcs.
- Gentle attraction to the centers of real hovered UI controls, with escape through strong or sustained stick movement.
- Right-stick camera movement through the client's camera API.
- Camera-center flight on short right-stick release, independent of cursor position.
- A native stop-ship request after a separate one-second right-stick hold, with no preceding flight or flight on release.
- A static camera-center dot beneath native menus/windows, hidden for center UI occlusion or open menus/modal dialogs.
- Automatic startup at EveJS login and live launcher configuration reloads.
- Launcher installation, configuration, activation and disable/remove integration.
- A centered white EVE Online logo with transparency, consistent SVG control icons and an EveJS Discord button.

### Changed

- Simplify the README with a compact usage/control guide, expandable details, and consistent title case for headings and labels.
- Remove the neutral-input instruction from the installation guide and omit unassigned controls from the displayed mappings.
- Move controller polling, cursor rendering and navigation into the EVE process.
- Replace the continuously running companion with a short-lived launcher setup helper.
- Use general controller-support branding and clearly identify current XInput coverage.
- Simplify configuration to the ten settings used by the agreed controls.
- Preserve existing right-stick stop holds while camera movement returns to center.

### Removed

- The companion executable, manual-start command and notification-area interface.
- Unrequested face-button, D-pad, View/Menu and pause-chord assignments.
- Optional custom key/mouse binding actions; existing extra bindings are ignored.
- The mouse-drag camera anchor and its configuration fields.
- Device-specific branding and the additional compatibility/testing paragraph from the README.

### Input and Lifecycle

- Physical mouse/keyboard input cancels pending controller actions, releases owned clicks and restores the native pointer.
- A stationary held stick/button cannot immediately reclaim input after mouse/keyboard takeover; fresh controller activity is required.
- Restrict input to the foreground client, and require neutral controls after focus changes or controller reconnection.
- Cancel pending flight/stop gestures on input takeover, focus loss, disconnect, invalid settings or disable.
- Remove native cursor/dot UI and unregister event listeners when the mod stops or is replaced.
- Preserve physically held mouse buttons while releasing controller ownership.
- Leave left-stick press, triggers, face buttons, D-pad and View/Menu without gameplay actions.

### Compatibility and Validation

- Target EveJS **0.12.9**, launcher **1.0.53+**, and Windows x64 EVE client **build 3396210**.
- Keep native and Docker server backends, with controller input inside the Windows client.
- Keep the supported login-source verification before activation.
- Verify startup, agreed controls, hold timing, input switching, native UI helpers and actual launcher integration with automated checks. Live gameplay validation remains pending.
- Direct PlayStation controller support, including PS5 DualSense, is not yet implemented.

[Unreleased]: https://github.com/cfin3d/EveJS-Controller-Support/commits/main/
