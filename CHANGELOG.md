# Changelog

Changes are grouped by release and category. Versions use **MAJOR.MINOR.PATCH**. No release has been published; the initial release will be **0.1.0**.

## [Unreleased]

### Added

- Native **Controller** category in EVE's Settings menu, with a matching white controller icon and native navigation, labels, buttons, sliders, toggles, and scrolling.
- Connected-controller selection, live activity detection, and **Identify Controller**, with selection saved across sessions.
- Action-based binding capture for cursor movement, camera pan/zoom, left/right click, camera-center flight, and stop, including button combinations and stick modifiers.
- Binding conflict detection, clear bindings, named configuration profiles, and **Restore Defaults** while retaining selected hardware and saved profiles.
- **Invert Camera Pan**, off by default, which reverses vertical panning independently of cursor movement and zoom.
- Camera zoom with **hold LT + right stick up/down**: up zooms in, down zooms out. Holding the zoom modifier suppresses normal panning; releasing it restores panning.
- Configurable camera zoom speed and trigger activation threshold.
- Atomic in-game configuration saves that preserve other launcher settings in the shared preferences file.
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
- A centered white EVEJS Offline logo with transparency, consistent SVG control icons and an EveJS Discord button.

### Changed

- Enlarge the controller cursor's main ring from an 18 px to a 26 px diameter, with a thicker solid white outline, a dark contrast edge, a larger white center dot, and brighter outer hold tracks.
- Apply a finer 2.7-power cursor response and a short acceleration ramp everywhere. Preserve full-stick maximum speed, immediate stopping on direction release, prompt direction reversal, and the existing camera response.
- Reduce attraction escape distance for short controls so fine movement can move between neighboring menu/list items more easily. Full-stick intent escapes attraction immediately, including while cursor speed ramps up.
- Update the repository logo to **EVEJS OFFLINE**: preserve the EVE mark, add small subtitle-style **JS** aligned to the second E's bottom edge, and center **OFFLINE** beneath EVE with the original subtitle gap and letter spacing.
- Refer to the configuration path as **Settings → Controller** throughout the user guide.
- Simplify the README with a compact usage/control guide, expandable details, and consistent title case for headings and labels.
- Remove the neutral-input instruction from the installation guide and omit unassigned controls from the displayed mappings.
- Move controller polling, cursor rendering and navigation into the EVE process.
- Replace the continuously running companion with a short-lived launcher setup helper.
- Use general controller-support branding and clearly identify current XInput coverage.
- Put controller configuration in the native settings menu; keep thirteen basic feel/device settings available in the launcher.
- Allow players to remap the agreed actions without adding new default gameplay assignments.
- Preserve existing right-stick stop holds while camera movement returns to center.

### Fixed

- Prevent cursor refreshes and coalesced controller movement with missing Windows tags from repeatedly switching to mouse/keyboard mode. Ignore stationary movement notifications while retaining immediate takeover from real movement, clicks, scrolling, and keyboard input.
- Exclude Windows gamepad virtual-key states from keyboard activity detection.
- Render the idle and moving cursor ring entirely in solid white, including its thick outer stroke, without requiring a click or hold.
- Limit the tagged mouse observer to the EVE UI thread instead of using a desktop-wide low-level hook, preventing other applications' mouse input from waiting for EVE's background message pump.
- Recognize native right-click menu rows that activate through mouse-up handlers, including submenu entries; exclude disabled or non-interactive rows.
- Keep attraction inside open menu layers and invalidate nearby-target geometry when menus open, close or rebuild, preventing attraction to controls behind the menu.
- Enable controller camera panning and zoom in station and structure hangars, using the client's active camera while keeping ship commands restricted to space.
- Classify mouse input from tagged Windows mouse messages before EVE defers UI events. Controller-generated mouse movement/drag notifications no longer trigger mouse/keyboard takeover or release confirmed held clicks.
- Keep physical mouse/keyboard takeover responsive, preserve physically held mouse buttons, and remove the native mouse observer when the mod stops.
- Retain slider callbacks for the lifetime of the Controller panel. Native weak signal references previously allowed the callbacks to disappear, so moving a slider could fail to save or apply its value.
- Attract to nearby native UI controls through read-only hit tests that honor clipping, occlusion and modal windows. Cache geometry briefly to limit repeated picking.
- Recover attraction after a fast approach, finish gentle attraction after the stick returns to center, and only treat sustained outward movement as an escape. Suppress attraction while clicking or dragging.
- Queue camera-center flight's remote request independently so native client prediction does not wait for a delayed server reply. Flight still occurs on short-press release; one-second holds only stop the ship.
- Keep controller polling responsive while flight/stop RPCs await replies, and reject queued commands after changing ships, docking, session transitions or disabling the mod.
- Resolve the native UI singleton from `carbonui.uicore`. This client does not expose it through builtins, which previously caused startup to exit before registering the Controller category.
- Register the Controller settings category without requiring a connected controller, and show **No Controller Connected** in its input status.
- Report ready, unavailable-UI, and unsupported-build startup states in the client login output instead of silently returning without a category.

### Removed

- The companion executable, manual-start command and notification-area interface.
- Unrequested face-button, D-pad, View/Menu and pause-chord assignments.
- Free-form custom key/mouse actions, replaced with remapping of the supported controller actions.
- The mouse-drag camera anchor and its configuration fields.
- Device-specific branding and the additional compatibility/testing paragraph from the README.

### Input and Lifecycle

- Physical mouse/keyboard input cancels pending controller actions, releases owned clicks and restores the native pointer.
- A stationary held stick/button cannot immediately reclaim input after mouse/keyboard takeover; fresh controller activity is required.
- Restrict input to the foreground client, and require neutral controls after focus changes or controller reconnection.
- Cancel pending flight/stop gestures on input takeover, focus loss, disconnect, invalid settings or disable.
- Remove native cursor/dot UI and unregister event listeners when the mod stops or is replaced.
- Preserve physically held mouse buttons while releasing controller ownership.
- Leave left-stick press, RT, face buttons, D-pad and View/Menu without default gameplay actions.
- Suspend camera and ship commands while the native settings menu is open; retain controller cursor movement and hold-to-click for its controls.
- Suspend controller actions during binding capture and controller identification. Cancel detection on Esc, timeout, focus loss, disconnect, or leaving the Controller panel.
- Restore owned settings-menu hooks and remove the Controller category when the mod stops or is replaced.
- Restore EVE's saved settings category when disabling the mod, including while the menu is closed, so its next opening selects a native category.
- Cancel navigation holds started in settings so closing the menu cannot issue delayed flight or stop commands.

### Compatibility and Validation

- Target EveJS **0.12.9**, launcher **1.0.53+**, and Windows x64 EVE client **build 3396210**.
- Keep native and Docker server backends, with controller input inside the Windows client.
- Keep the supported login-source verification before activation.
- Verify startup, agreed controls, hold timing, input switching, native UI helpers, settings persistence, controller selection, binding capture/conflicts, profiles, camera inversion/zoom routing, and actual launcher integration with automated checks. Live gameplay validation remains pending.
- The current input backend exposes standard XInput controls. Independently exposed rear-button input remains dependent on backend support.
- Direct PlayStation controller support, including PS5 DualSense, is not yet implemented.

[Unreleased]: https://github.com/cfin3d/EveJS-Controller-Support/commits/main/
