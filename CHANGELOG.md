# Changelog

Changes are grouped by release and category. Versions use **MAJOR.MINOR.PATCH**. No release has been published; the initial release will be **0.1.0**.

## [Unreleased]

### Added

- Windows x64 controller companion with Xbox/XInput support and automatic selection across slots 0–3.
- Legion Go Gamepad/XInput configuration support.
- Analog left-stick cursor movement with a radial deadzone, a squared precision curve, and configurable maximum speed.
- Left-bumper right-click and right-bumper left-click, each confirmed by a configurable 500 ms hold.
- Early-release cancellation and hold reset when the cursor changes targets or moves away before confirmation.
- Continued mouse-button holds for dragging, plus optional confirmed double-click bindings.
- Minimal white/cyan circular cursor with animated UI attraction and separate confirmation arcs for left-click, right-click and stopping.
- Gentle attraction to the center of real hovered UI controls, with escape through strong or sustained stick movement.
- Right-stick camera panning with configurable drag button, speed and clear-space anchor.
- Camera-center flight on a short right-stick press/release, independent of cursor position.
- Native stop-ship command after a separate one-second right-stick hold, without issuing flight before stopping or on release.
- Static camera-center dot in the native space UI, below windows and menus, with center-occlusion and menu/modal hiding.
- D-pad scrolling, face-button shortcuts, View/Menu shortcuts, and a View + Menu pause chord.
- Automatic startup at EveJS login, a notification-area status window, and live configuration reloads.
- EveJS Launcher discovery, configuration, activation and disable/remove integration.

### Input and lifecycle

- Restrict controller input to the selected foreground EVE client.
- Release owned inputs on focus loss, disconnect, pause, invalid settings and shutdown.
- Require neutral controls after focus/device changes and camera drag completion.
- Restore the UI cursor after camera dragging; preserve an existing right-stick stop timer when the stick returns to center.
- Cancel pending flight/stop gestures on focus loss, disconnect or pause.
- Expire navigation requests quickly and suppress duplicates across client-observer reconnects.
- Restore the native cursor when the controller overlay is inactive or its heartbeat expires.
- Hide/remove the center dot when inactive, docked, during session transitions or when the client observer stops.
- Leave left-stick press inactive and LT/RT unassigned by default.

### Compatibility

- Target EveJS **0.12.9**, launcher **1.0.53+**, and Windows x64 EVE client **build 3396210**.
- Declare native and Docker server backends, with controller input handled by the Windows client companion.
- Reject unsupported login-handshake revisions before activation.

### Documentation and packaging

- Add installation, compatibility, usage, configuration and troubleshooting guidance.
- Add uniform white SVG Xbox-style control icons and an EveJS Discord button.
- Add a centered white EVE Online logo with a transparent background.
- Keep the repository root installable as a single mod folder.
- Prepare release packaging around a top-level `evejs-controller` folder, beginning with version **0.1.0**.

### Validation status

- Controller logic, login startup, client UI, native navigation delegation, center-dot behavior and launcher integration pass automated checks.
- Live EVE gameplay, Xbox controller use, Docker runtime behavior and Legion Go hardware validation remain pending.

[Unreleased]: https://github.com/cfin3d/EveJS-Controller-Support/commits/main/
