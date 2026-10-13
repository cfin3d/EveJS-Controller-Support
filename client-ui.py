# Cursor target observer and reversible cursor mask for EVE client build 3396210.
# Python 2.7 compatible. Publishes only a transient ID and rectangle; no text,
# inventory data, input-handler replacements, or client archive modifications.
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


def _ec_navigation_request(lease, pid, now):
    try:
        command_id, action = lease.get('commandID'), lease.get('command')
        lease_age = now - float(lease.get('updated', 0))
        command_age = now - float(lease.get('commandCreated', 0))
        if lease.get('schema') == 1 and lease.get('pid') == pid and lease.get('active') is True and 0 <= lease_age <= .35 and 0 <= command_age <= .5 and action in ('fly', 'stop') and isinstance(command_id, (str, type(u''))) and 1 <= len(command_id) <= 64:
            return command_id, action
    except Exception:
        pass
    return None


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


def _ec_lease_active(lease, pid, now, field='active'):
    try:
        age = now - float(lease.get('updated', 0))
        return lease.get('schema') == 1 and lease.get('pid') == pid and lease.get(field) is True and 0 <= age <= .35
    except Exception:
        return False


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


class _EveControllerUiObserver(object):
    def __init__(self, directory):
        self.active = True
        self.directory = directory
        self.path = _ec_os.path.join(directory, str(_ec_os.getpid()) + '.json')
        self.temporary = self.path + '.new'
        self.mask = None
        self.crosshair = _CameraCenterDot()
        self.navigation_status = 'Ready for stick navigation'
        self.command_id = None
        seen = getattr(_ec_builtins, '_evejs_controller_navigation_seen_v1', None)
        if seen is None:
            seen = []
            setattr(_ec_builtins, '_evejs_controller_navigation_seen_v1', seen)
        self.seen_commands = seen

    def current(self):
        return self.active and getattr(_ec_builtins, '_evejs_controller_ui_v1', None) is self

    def consume_navigation(self, lease, uicore, now):
        request = _ec_navigation_request(lease, _ec_os.getpid(), now)
        if request is None or request[0] in self.seen_commands:
            return
        command_id, action = request
        self.seen_commands.append(command_id)
        del self.seen_commands[:-64]
        self.command_id = command_id
        try:
            self.navigation_status = _ec_navigation(action, uicore)
        except Exception as error:
            self.navigation_status = 'Navigation unavailable: ' + type(error).__name__

    def dispose(self):
        self.active = False
        if self.mask is not None:
            self.mask.dispose()
        self.crosshair.dispose()
        # Cleanup belongs only to this live observer. A replacement uses the same PID.
        for path in (self.path, self.temporary):
            try:
                if _ec_os.path.isfile(path):
                    _ec_os.remove(path)
            except Exception:
                pass

    def run(self):
        import blue
        while self.current():
            blue.pyos.synchro.SleepWallclock(100)
            if not self.current():
                return
            try:
                activation = _ec_os.path.join(_ec_os.path.dirname(self.directory), 'activation.json')
                if not _ec_os.path.isfile(activation):
                    self.dispose()
                    return
                with open(activation, 'rb') as stream:
                    enabled = _ec_json.load(stream).get('enabled') is True
                if not enabled:
                    self.dispose()
                    return
                uicore = getattr(_ec_builtins, 'uicore', None)
                if uicore is None:
                    continue
                if self.mask is None:
                    import carbonui.const as constants
                    self.mask = _CursorMask(uicore.uilib, constants)
                ring_active = False
                lease = {}
                try:
                    with open(_ec_os.path.join(self.directory, 'bridge.json'), 'rb') as stream:
                        lease = _ec_json.load(stream)
                    ring_active = _ec_lease_active(lease, _ec_os.getpid(), _ec_time.time(), 'visible')
                except Exception:
                    pass
                self.consume_navigation(lease, uicore, _ec_time.time())
                crosshair_active = _ec_lease_active(lease, _ec_os.getpid(), _ec_time.time())
                self.crosshair.update(uicore, crosshair_active)
                native_hidden = self.mask.show_ring(ring_active)
                document = {'schema': 1, 'pid': _ec_os.getpid(), 'hover': _ec_hover_target(uicore), 'nativeCursorHidden': native_hidden,
                            'navigationStatus': self.navigation_status, 'commandID': self.command_id}
                with open(self.temporary, 'wb') as stream:
                    stream.write(_ec_json.dumps(document, separators=(',', ':')).encode('ascii'))
                if not self.current():
                    return
                # Python 2 on Windows cannot rename over an existing file. Readers
                # treat the short replacement gap as unavailable, never stale input.
                if _ec_os.path.isfile(self.path):
                    _ec_os.remove(self.path)
                _ec_os.rename(self.temporary, self.path)
            except Exception:
                # UI transitions and transient file sharing errors are expected;
                # missing snapshots automatically disable attraction in the bridge.
                if self.mask is not None:
                    self.mask.show_ring(False)
                self.crosshair.dispose()
                continue


def _ec_start_ui_observer():
    import eveprefs
    import uthread
    if int(eveprefs.boot.build) != 3396210:
        return False
    directory = _ec_os.environ.get('CONTROLLER_UI_DIRECTORY', '')
    executable = _ec_os.environ.get('CONTROLLER_COMPANION_EXE', '')
    expected = _ec_os.path.join(_ec_os.path.dirname(executable), 'ui')
    if not directory or _ec_os.path.normcase(_ec_os.path.abspath(directory)) != _ec_os.path.normcase(_ec_os.path.abspath(expected)):
        return False
    if not _ec_os.path.isdir(directory):
        return False
    previous = getattr(_ec_builtins, '_evejs_controller_ui_v1', None)
    if previous is not None:
        previous.dispose()
    observer = _EveControllerUiObserver(directory)
    setattr(_ec_builtins, '_evejs_controller_ui_v1', observer)
    uthread.new(observer.run)
    return True


if not globals().get('_ec_test_mode', False):
    try:
        _ec_start_ui_observer()
    except Exception:
        print('EVEJS_CONTROLLER_UI:UNAVAILABLE')
