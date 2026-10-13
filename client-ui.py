# Native UI helpers for EVE client build 3396210.
# Python 2.7 compatible. Uses native hit-testing and reversible cursor masking.
# Does not modify client archives or replace input handlers.
# Explicit stick gestures call the existing client flight/stop functions.
import json as _ec_json
import os as _ec_os
import time as _ec_time
try:
    import __builtin__ as _ec_builtins
except ImportError:
    import builtins as _ec_builtins


def _ec_hover_target(uicore):
    desktop = getattr(uicore, 'desktop', None)
    uilib = getattr(uicore, 'uilib', None)
    node = getattr(uilib, 'mouseOver', None)
    if desktop is None or node is None:
        return None
    try:
        dx, dy, dw, dh = desktop.GetAbsolute()
        if dw <= 0 or dh <= 0:
            return None
        chain = []
        for unused in range(24):
            if node is None or node is desktop:
                break
            chain.append(node)
            node = getattr(node, 'parent', None)
        modal = uicore.registry.GetModalWindow()
        if modal is not None and modal not in chain:
            return None
        # Native mouseOver supplies EVE's hit-test result, respecting occlusion.
        # Take the nearest enabled clickable ancestor, never a nearby guessed box.
        for candidate in chain:
            if getattr(candidate, 'destroyed', False) or not getattr(candidate, 'display', True):
                return None
            kind = type(candidate).__name__.lower()
            if any(part in kind for part in ('edit', 'slider', 'scrollbar', 'resize')):
                return None
            has_handler = getattr(candidate, 'HasEventHandler', None)
            if not callable(has_handler) or not has_handler('OnClick'):
                continue
            if getattr(candidate, 'state', 0) in (1, 2):
                continue
            is_enabled = getattr(candidate, 'IsEnabled', None)
            if callable(is_enabled) and not is_enabled():
                return None
            x, y, w, h = candidate.GetAbsolute()
            if w < 6 or h < 6 or w > 480 or h > 128 or w * h > 36000:
                return None
            x, y = x - dx, y - dy
            if x < 0 or y < 0 or x + w > dw or y + h > dh:
                return None
            return {'id': str(id(candidate)), 'x': float(x) / dw, 'y': float(y) / dh,
                    'w': float(w) / dw, 'h': float(h) / dh}
    except Exception:
        return None
    return None


class _CameraCenterCoordinates(object):
    def __init__(self, original, x, y):
        self.original, self.x, self.y = original, x, y

    def __getattr__(self, name):
        return getattr(self.original, name)


class _CameraCenterUi(object):
    def __init__(self, original):
        self.original = original
        x, y, width, height = original.desktop.GetAbsolute()
        self.uilib = _CameraCenterCoordinates(original.uilib, x + width / 2.0, y + height / 2.0)

    def __getattr__(self, name):
        return getattr(self.original, name)


def _ec_call_center_direction(native, camera, uicore):
    import types
    # Reuse the client's own flight function with private read-only coordinates.
    # Do not move the OS cursor, replace uicore, or modify native function globals.
    code = getattr(native, '__code__', getattr(native, 'func_code', None))
    namespace = getattr(native, '__globals__', getattr(native, 'func_globals', None))
    defaults = getattr(native, '__defaults__', getattr(native, 'func_defaults', None))
    closure = getattr(native, '__closure__', getattr(native, 'func_closure', None))
    if code is None or namespace is None:
        raise RuntimeError('Native flight function is unavailable')
    private = dict(namespace)
    private['uicore'] = _CameraCenterUi(uicore)
    centered = types.FunctionType(code, private, 'EveControllerCameraCenterFlight', defaults, closure)
    return centered(camera)


def _ec_navigation(action, uicore):
    session = getattr(_ec_builtins, 'session', None)
    sm = getattr(_ec_builtins, 'sm', None)
    if sm is None or session is None or not getattr(session, 'charid', None) or not getattr(session, 'shipid', None):
        return 'Navigation unavailable: character not ready'
    if getattr(session, 'mutating', False) or not getattr(session, 'solarsystemid', None) or getattr(session, 'stationid', None) or getattr(session, 'structureid', None):
        return 'Navigation unavailable: not flying in space'
    if action == 'stop':
        uicore.cmd.CmdStopShip()
        return 'Stop ship requested'
    if action != 'fly':
        return 'Navigation unavailable: unknown action'
    camera = sm.GetService('sceneManager').GetActiveSpaceCamera()
    if camera is None or sm.GetService('michelle').GetRemotePark() is None:
        return 'Navigation unavailable: space camera not ready'
    from eve.client.script.ui.camera.cameraUtil import SetShipDirection
    _ec_call_center_direction(SetShipDirection, camera, uicore)
    return 'Camera-center flight requested'


def _ec_crosshair_clear(uicore, layer):
    # Native hit-testing is read-only and does not move or capture the pointer.
    # Also hide for open menus/modal dialogs, including translucent backgrounds.
    try:
        if uicore.registry.GetModalWindow() is not None:
            return False
        for name in ('menu', 'utilmenu', 'systemmenu'):
            menu = getattr(uicore.layer, name, None)
            if menu is not None and getattr(menu, 'display', False):
                if any(getattr(child, 'display', False) and not getattr(child, 'destroyed', False) for child in menu.children):
                    return False
        x, y, width, height = uicore.desktop.GetAbsolute()
        if width <= 0 or height <= 0:
            return False
        unused, picked = uicore.uilib.PickScreenPosition(int(uicore.ScaleDpi(x + width / 2.0)), int(uicore.ScaleDpi(y + height / 2.0)))
        return picked is None or picked is layer or picked is uicore.desktop or picked is getattr(uicore.layer, 'viewstate', None)
    except Exception:
        return False


class _CameraCenterDot(object):
    def __init__(self):
        self.dot = None
        self.parent = None

    def update(self, uicore, active):
        session = getattr(_ec_builtins, 'session', None)
        layer = getattr(uicore.layer, 'inflight', None)
        visible = active and session is not None and getattr(session, 'charid', None) and getattr(session, 'shipid', None) and getattr(session, 'solarsystemid', None) and not any(getattr(session, field, None) for field in ('stationid', 'structureid', 'mutating'))
        visible = bool(visible and layer is not None and not getattr(layer, 'destroyed', False) and getattr(layer, 'display', False))
        if self.dot is not None and (getattr(self.dot, 'destroyed', False) or self.parent is not layer):
            self.dispose()
        if visible and self.dot is None:
            from carbonui.primitives.fill import Fill
            import carbonui.const as constants
            # Inflight is below main windows and menus in the native view stack.
            # Backmost child + UI_DISABLED prevents interception of any input.
            self.dot = Fill(parent=layer, name='evejsControllerCameraCenter', align=constants.TOPLEFT,
                            width=3, height=3, state=constants.UI_DISABLED, idx=-1,
                            color=(.78, .9, 1.0, .85))
            self.parent = layer
        if self.dot is not None:
            self.dot.display = visible and _ec_crosshair_clear(uicore, layer)
            if self.dot.display:
                x, y, width, height = uicore.desktop.GetAbsolute()
                lx, ly, unused_width, unused_height = layer.GetAbsolute()
                self.dot.left, self.dot.top = x + width / 2.0 - lx - 1.5, y + height / 2.0 - ly - 1.5

    def dispose(self):
        if self.dot is not None and not getattr(self.dot, 'destroyed', False):
            self.dot.Close()
        self.dot = self.parent = None


class _CursorMask(object):
    def __init__(self, uilib, constants):
        self.uilib = uilib
        self.original = getattr(uilib, 'SetCursor', None)
        self.none = getattr(constants, 'UICURSOR_NONE', None)
        self.last = getattr(constants, 'UICURSOR_DEFAULT', None)
        self.hidden = False
        self.wrapper = None
        if not callable(self.original) or self.none is None or self.last is None:
            return
        def setter(cursor, *args, **kwargs):
            self.last = cursor
            return self.original(self.none if self.hidden else cursor, *args, **kwargs)
        try:
            uilib.SetCursor = setter
            self.wrapper = setter
        except Exception:
            pass

    def show_ring(self, active):
        if self.wrapper is None:
            return False
        try:
            if active != self.hidden:
                self.hidden = active
                self.original(self.none if active else self.last)
            return self.hidden
        except Exception:
            self.hidden = False
            self.dispose()
            return False

    def dispose(self):
        try:
            if self.hidden:
                self.hidden = False
                self.original(self.last)
            if self.wrapper is not None and self.uilib.SetCursor is self.wrapper:
                self.uilib.SetCursor = self.original
        except Exception:
            pass
        self.wrapper = None
