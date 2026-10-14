# Changelog

Changes are grouped by release and category. Versions use **MAJOR.MINOR.PATCH**. No release has been published; the initial release will be **1.0.0**.

## [Unreleased]

### Added

- **Close Focused Window** on B by default: ease the cursor to the focused window's native X over 140 ms, fill the hold indicator, and activate the X only on release after the configurable **Window Close Hold**, defaulting to 1,000 ms. Continuing to hold never closes the window automatically; successful closure leaves the cursor at the X.
- Smooth cursor return on early release or interruption, with cancellation for changed window/tab focus, occlusion, disabled or replaced close controls, other controller inputs, device/focus/session/configuration changes, and input capture. Pause competing controller actions during the gesture and return; defer cursor restoration while EVE is unfocused.
- Native window/stack close actions and Settings' X callback, respecting modal priority, availability, close restrictions and confirmation dialogs. Dispatch potentially yielding close handlers separately from the input loop, revalidate the original target immediately before execution, and restore the cursor if a close is rejected while the gesture retains ownership.
- Remappable close-window input and a separate timer in native Controller settings, saved profiles and the launcher's 22-field form. Preserve existing B assignments and combinations when migrating older preferences; keep Neocom's 500 ms A/B holds and radial cancellation unchanged.
- Incoming-damage vibration using native damage notifications and weapon classification: brief light laser feedback, sharper projectile/hybrid impacts, heavier missile impacts, and a moderate fallback for unidentified or environmental damage. Match the damaged object ID to the player's currently piloted ship; exclude owned drones, fighter squadrons, deployables, structures and other objects, as well as misses/zero damage, outgoing attacks and observer messages. Bound duplicate/burst processing.
- A distinct ship-destruction burst and fading tail driven by the native **OnObjectExplode** event, including a short tracked ship-to-capsule transition window. Ignore unrelated explosions, suppress duplicate destruction effects, prioritize destruction over hit feedback, and retain a confirmed effect through the capsule transition.
- Native **Vibration** settings with a master enable toggle, overall strength, separate damage/destruction toggles and strengths, **Test Vibration**, **Stop Vibration**, and output status. Include feedback preferences in saved profiles and launcher configuration; preserve existing preferences when updating.
- Selected-device SDL rumble with XInput output fallback, bounded intensity, short output timeouts and blended hit envelopes. Cancel playback on physical mouse/keyboard takeover, focus loss, disconnection, device changes, configuration changes, or runtime shutdown; settings previews also cancel on leaving the Controller category or starting input detection.
- Optional experimental **Enhanced DualSense Haptics (USB)** for directly detected Sony DualSense/DualSense Edge devices, with distinct authored waveforms on the two haptic audio channels and silent audible channels. Require a single Sony controller and unambiguous four-channel controller audio endpoint; retain standard vibration fallback for unsupported connections, hidden identities, endpoint ambiguity, stream failures or format changes. Do not change default audio output, microphone/speaker settings or trigger resistance.
- Feedback-specific reporting guidance and compatibility checks. Validate output contracts, event filtering, cleanup and actual SDL process-local virtual rumble; physical vibration feel and enhanced USB haptics remain pending hardware testing.
- Structured GitHub forms for bug reports, feature requests, and controller compatibility feedback, including successful hardware setups. Gather reproduction details, versions, device/input configuration, and optional evidence without requiring logs or unavailable information.
- Reporting guidelines with focused issue examples, version/settings lookup help, a controller test checklist, public-attachment privacy guidance, and follow-up expectations. Link the forms from the README and provide a Discord option for general help in the issue chooser.
- Bundled SDL 3.4.18 gamepad input inside the EVE process, with direct PlayStation USB/Bluetooth drivers, Steam controller/Steam Deck driver paths, and Steam Input gamepad output. Normalize all devices to the existing positional bindings and retain XInput fallback if the bundled backend cannot initialize.
- Automatic controller-family icons and names in binding rows, conflict dialogs, and radial prompts. Add uniform white PlayStation SVG symbols and native transparent textures, with distinct Share/Create labels for detected DualShock 4/DualSense devices.
- **Button Icons** selection with Auto-Detect, Xbox, PlayStation 4, PlayStation 5, and Steam overrides for virtual devices whose physical identity is hidden by an input mapper. Include the setting in saved profiles and launcher configuration.
- Capture independently exposed rear/paddle buttons, touchpad clicks, and additional digital inputs through the existing custom binding editor without assigning new default gameplay actions.
- Named controller selection across up to 16 slots, activity-based automatic selection, hot-plug cleanup, and device-instance change detection when a slot is reused.
- Show the most recently highlighted radial range action beneath the **Range** prompt, followed by its native formatted distance. Update the distance with each adjustment, retain the readout when moving away, and reserve additional space below the wheel to keep the prompts on screen.
- Select/View opens native Neocom controller navigation, with a remappable **Open Neocom** action in Controller settings. D-pad Up/Down selects items immediately with bounded repeat; Right enters submenus and Left restores the parent selection.
- Smooth 140 ms cursor transitions bounded to the active Neocom panel and native item highlighting. Normal cursor movement, camera/ship commands, clicks, and custom actions pause until the menu closes.
- Neocom A selection and B cancellation use the configurable click/activation hold, defaulting to 500 ms, with cursor-ring progress. D-pad input remains immediate. Group selection enters its submenu; native item activation collapses Neocom and restores normal cursor control.
- White controller button icons in native binding rows, including modifier combinations, stick axes, and custom inputs. Transparent client textures are exported from the matching SVG assets.
- A visible, wheel-local radial cursor driven by absolute left-stick position and bounded to the circular menu, including full diagonal input. Physical mouse/keyboard takeover remains available.
- Custom controller-to-EVE-shortcut bindings in the native Controller settings category, with modifier/key drop-downs, a resolved action preview, controller combination capture, editing/removal, and saved-profile support. No custom bindings are assigned by default.
- Native EVE warning dialogs for controller binding conflicts, listing affected functions with **Replace Binding** and **Cancel**, defaulting to cancellation. Accepted replacements clear conflicting core inputs or remove conflicting custom entries; canceled replacements leave preferences unchanged.
- Single-press custom shortcut dispatch through the native command map, preserving command availability checks, requiring a configured EVE shortcut, pinning its action identity, and cleaning up native combat command selection after dispatch to the selected object.
- Target-aware controller radial menu: the existing left-click binding (RB by default) fills its confirmation ring for 500 ms, then opens EVE's native wheel over a valid targetable space bracket, overview entry, or locked-target icon.
- Exclusive radial navigation with left-stick wedge selection, angular hysteresis, deliberate More/submenu expansion, D-pad range adjustment with bounded repeat, release-to-confirm, and B cancellation. Native icons, action labels, disabled states, range feedback, and closing animations are retained.
- Minimal white controller prompts beneath the wheel; activation prompts follow the existing left-click binding and cancellation chooses a free button if that binding includes B. Add matching white B and D-pad SVG icons to the user guide.
- Adapt radial range control to right-stick vertical movement when a custom activation binding occupies D-Pad Up/Down, avoiding unintentional range changes from the activation hold.
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

- Set the first public release target to **1.0.0**. Align the testing-build manifest, README and reporting guidance with that target; all changes remain **Unreleased** until publication.
- Package the controller backend and its runtime/license with the installable mod folder; no companion process or separate library installation is required. Mark PlayStation/Steam physical hardware and SteamOS/Proton coverage as requiring community testing.
- Rename the shared timing control to **Click / Activation Hold** to cover normal clicks, radial opening, and Neocom A/B activation. Preserve its stored key and existing values.
- Reformat Controller settings into spaced sections, paired half-width slider fields with separate value labels, and uniform action/input/clear columns. Apply matching rows to custom bindings and keep modifier/key selection in a compact two-column editor.
- Include custom bindings in profiles and Restore Defaults while retaining existing device selection and saved profiles.
- Share the left-click binding and confirmation timer with target radial activation. Preserve normal UI hold-to-click/drag, existing preferences, and ordinary native mouse radial behavior.
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

- Recognize the native dockable-panel toolbar X used by **Ship Tree** and **Map**, including floating, side-docked and fullscreen layouts, so **Close Focused Window** can snap to and activate it. Respect each panel's native closability, visibility, hit-testing and focus; keep early-release/interruption cancellation and wait briefly for the panel's separately scheduled close task before restoring the cursor after a refusal. A successful close retains the cursor at the X, and input takeover prevents a later completion from moving it.
- Release only owned gamepad handles/subsystem references and restore owned polling-event/hint settings on shutdown or initialization failure. Keep physical input handover, tagged synthetic mouse filtering, preferences, and existing gameplay bindings intact.
- Preserve previously assigned Select/View inputs when adding the new default Neocom binding. Keep held controls from carrying actions across menu transitions; restart A confirmation when selection changes, prioritize B cancellation, and activate once per hold.
- Temporarily suppress native Neocom hover expansion during controller navigation and restore owned hooks on selection, cancellation, physical input, focus loss, disconnection, settings/configuration changes, or session transitions.
- Match the radial cursor to the normal cursor's 26 px white ring, white strokes, and 3 px white dot; remove its older dark outer circle while retaining circular bounds.
- Keep D-pad range selection stable across native control refreshes, show the range circle, and retain range focus after adjustment so centering the stick does not discard the chosen action. D-pad input can restore the most recent range wedge on the current menu level.
- Pin the validated native range callback, target argument, distance, and range fraction before queuing confirmation. Native option refreshes or closing-control changes cannot reset the distance or replace Orbit with another callback before it executes.
- Preserve button frame dimensions through the current client's intrinsic sizing API, which ignores legacy fixed-width/fixed-height attributes. Use uniform 274 × 40 binding buttons with centered icon groups, consistent icon spacing, and at least 24 px padding on each side of the longest supported combination; apply the same sizing to custom and empty binding inputs.
- Use the client's registered `radialmenu` service when installing controller radial handling. The incorrect service lookup disabled controller radial activation and allowed the ordinary mouse radial to open, bypassing the bounded left-stick cursor and exclusive menu controls.
- Fix native binding buttons rendering as thin strips by replacing fill alignment with explicit centered dimensions. Keep input, Clear/Remove, and editor buttons compact with consistent height.
- Compare existing bindings again before saving an accepted replacement; reject concurrent edits instead of silently overwriting them. Preserve unrelated launcher preferences through atomic saves.
- Suppress custom actions during Settings, capture, radial navigation, and input handover; cancel queued actions on focus/input/session/configuration changes and prevent held combinations from replaying after takeover.
- Resolve radial targets only from the current native pick and recognized in-space target surfaces, with live ballpark, session, visibility, own-ship, and native non-targetable-group checks. Never fall back to a previously selected target or an object behind a window.
- Suppress ordinary mouse-driven radial expansion for controller-owned UI clicks, without suppressing physical mouse input; restore the scoped service hook when the mod stops.
- Keep chosen radial ranges across native option refreshes and final confirmation. Revalidate action availability, label, and target before dispatch, and guard deferred native callbacks against cancellation or target/session loss.
- Consider neighboring targets while already hovering a control, including small controls between radial samples. Confirm attraction targets through native hit tests and reject covered target centers.
- Stabilize target selection at adjacent-control boundaries, let sustained outward movement select the next item, and let reversing the stick re-enter an escaped item without first returning to neutral. Finish attraction when the stick is released without pulling back to an item just escaped.
- Include the Neocom service's open panels and wide Neocom entries in attraction, including nested groups and submenus. Reject entries under hidden ancestors and refresh nearby geometry after small cursor movements or menu changes.
- Cancel the cinematic undock camera through its native transition on controller pan or zoom, then control the active primary camera immediately, matching native mouse behavior.
- Use the native manual-flight heading simulation and predicted steering command for camera-center flight when available, avoiding the ordinary direction command's two-tick owner echo delay. Send one command on short-press release, retain the ordinary command as a fallback, and keep the authoritative ship simulation unchanged.
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

- Capture controller input exclusively while a radial is open or closing. Cancel on early hold release, target changes during the hold, target loss, physical input, focus loss, disconnect, session changes, Settings, configuration changes, or disable.
- Clear pending gestures on radial entry, require released controls after exit to prevent held-input leakage, and leave the OS cursor position and mouse capture/clipping unchanged.
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
