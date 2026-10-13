# In-process controller input for EVE client build 3396210. Python 2.7 compatible.
import ctypes
import json
import math
import os
import time
try:
    import __builtin__ as _builtins
except ImportError:
    import builtins as _builtins

TAG = 0x45564354
LB, RB, RS = 0x100, 0x200, 0x80
BUTTONS = [('LT', 0x10000), ('RT', 0x20000), ('LB', LB), ('RB', RB),
           ('A', 0x1000), ('B', 0x2000), ('X', 0x4000), ('Y', 0x8000),
           ('UP', 1), ('DOWN', 2), ('LEFT', 4), ('RIGHT', 8),
           ('VIEW', 0x20), ('MENU', 0x10), ('LS', 0x40), ('RS', RS)]
BUTTON_BITS = dict(BUTTONS)
ACTIONS = [('cursor', 'Move Cursor'), ('cameraPan', 'Pan Camera'),
           ('cameraZoom', 'Zoom Camera'), ('leftClick', 'Left-Click'),
           ('rightClick', 'Right-Click'), ('fly', 'Fly Toward Camera Center'), ('stop', 'Stop Ship')]
DEFAULT_BINDINGS = dict(cursor='LEFT_STICK', cameraPan='RIGHT_STICK',
                        cameraZoom='LT+RIGHT_STICK_Y', leftClick='RB', rightClick='LB', fly='RS', stop='RS')
DEFAULTS = dict(schemaVersion=1, controllerIndex=-1, deadzone=.20, cursorSpeed=1100,
                cameraSpeed=800, cursorRing=True, cursorSnap=True, snapRadius=28,
                snapMaxSpeed=250, clickHoldMilliseconds=500, rightStickStopMilliseconds=1000,
                invertCameraPan=False, cameraZoomSpeed=.8, triggerThreshold=40,
                bindings=DEFAULT_BINDINGS, profiles={})


def binding(value, action):
    if not isinstance(value, type('')):
        try:
            if not isinstance(value, unicode):
                raise ValueError('Invalid Binding')
        except NameError:
            raise ValueError('Invalid Binding')
    if not value:
        return ''
    tokens = value.upper().split('+')
    if len(set(tokens)) != len(tokens) or len(tokens) > 4:
        raise ValueError('Invalid Binding')
    axes = [token for token in tokens if token.endswith('_STICK') or token.endswith('_STICK_Y')]
    expected = ('LEFT_STICK_Y', 'RIGHT_STICK_Y') if action == 'cameraZoom' else ('LEFT_STICK', 'RIGHT_STICK')
    analog = action in ('cursor', 'cameraPan', 'cameraZoom')
    if analog and (len(axes) != 1 or axes[0] not in expected) or not analog and axes:
        raise ValueError('Use A Stick For Movement And Buttons For Actions')
    buttons = [name for name, bit in BUTTONS if name in tokens]
    if len(buttons) + len(axes) != len(tokens):
        raise ValueError('Unknown Controller Input')
    return '+'.join(buttons + axes)


def validate_bindings(document):
    if not isinstance(document, dict) or set(document) - set(DEFAULT_BINDINGS):
        raise ValueError('Invalid Bindings')
    result = dict(DEFAULT_BINDINGS)
    result.update(document)
    result = dict((action, binding(value, action)) for action, value in result.items())
    for i, (a, title) in enumerate(ACTIONS):
        for b, other_title in ACTIONS[i + 1:]:
            if not result[a] or not result[b] or set((a, b)) == set(('fly', 'stop')):
                continue
            first = result[a].replace('_Y', '')
            second = result[b].replace('_Y', '')
            if first == second:
                raise ValueError(title + ' Conflicts With ' + other_title)
    return result


def input_mask(pad, settings):
    return pad[0] | (0x10000 if pad[5] >= settings['triggerThreshold'] else 0) | (0x20000 if pad[6] >= settings['triggerThreshold'] else 0)


def binding_mask(value):
    return sum(BUTTON_BITS.get(token, 0) for token in value.split('+'))


def released(value, pad, settings):
    mask = input_mask(pad, settings)
    needed = binding_mask(value)
    primary = BUTTON_BITS.get(value.split('+')[-1], 0)
    modifiers = needed & ~primary
    return not mask & primary and (mask & modifiers == modifiers or not mask & needed)


def matches(action, pad, settings, priority=True):
    value = settings['bindings'][action]
    if not value:
        return False
    mask, needed = input_mask(pad, settings), binding_mask(value)
    if mask & needed != needed:
        return False
    if priority:
        tokens = set(value.replace('_Y', '').split('+'))
        for other, candidate in settings['bindings'].items():
            if other == action or not candidate:
                continue
            extra = set(candidate.replace('_Y', '').split('+'))
            if tokens < extra and matches(other, pad, settings, False):
                return False
    return True


def axes(action, pad, settings):
    if not matches(action, pad, settings):
        return 0., 0.
    offset = 1 if 'LEFT_STICK' in settings['bindings'][action] else 3
    return stick(pad[offset], pad[offset + 1], settings['deadzone'])


def preferences(document):
    result = dict(DEFAULTS)
    result.update(document)
    if result['schemaVersion'] != 1:
        raise ValueError('Unsupported preferences version')
    ranges = dict(controllerIndex=(-1, 3), deadzone=(.05, .5), cursorSpeed=(100, 4000),
                  cameraSpeed=(100, 4000), snapRadius=(8, 64), snapMaxSpeed=(50, 600),
                  clickHoldMilliseconds=(200, 2000), rightStickStopMilliseconds=(500, 3000),
                  cameraZoomSpeed=(.1, 3.), triggerThreshold=(10, 240))
    for name, limits in ranges.items():
        value = result[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value) or not limits[0] <= value <= limits[1]:
            raise ValueError('Invalid ' + name)
    for name in ('controllerIndex', 'clickHoldMilliseconds', 'rightStickStopMilliseconds', 'triggerThreshold'):
        if int(result[name]) != result[name]:
            raise ValueError('Invalid ' + name)
        result[name] = int(result[name])
    for name in ('cursorRing', 'cursorSnap', 'invertCameraPan'):
        if not isinstance(result[name], bool):
            raise ValueError('Invalid ' + name)
    result['bindings'] = validate_bindings(document.get('bindings', {}))
    profiles = document.get('profiles', {})
    if not isinstance(profiles, dict) or len(profiles) > 20:
        raise ValueError('Invalid Profiles')
    for name, profile in profiles.items():
        if not name or len(name) > 40 or not isinstance(profile, dict) or 'profiles' in profile:
            raise ValueError('Invalid Profile')
        preferences(dict(profile, profiles={}))
    result['profiles'] = profiles
    return result


def stick(x, y, deadzone):
    nx, ny = x / (32768.0 if x < 0 else 32767.0), y / (32768.0 if y < 0 else 32767.0)
    length = math.sqrt(nx * nx + ny * ny)
    if length <= deadzone:
        return 0., 0.
    scale = ((min(1., length) - deadzone) / (1. - deadzone)) ** 2
    return nx / length * scale, ny / length * scale


class InputMode(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.mode, self.previous, self.anchor, self.ready = 'keyboard', None, None, False

    def step(self, pad, physical, foreground, settings):
        if pad is None or not foreground:
            self.reset()
            return False
        neutral = input_mask(pad, settings) == 0 and stick(pad[1], pad[2], settings['deadzone']) == (0., 0.) and stick(pad[3], pad[4], settings['deadzone']) == (0., 0.)
        old = self.previous
        self.previous = pad
        if not self.ready:
            if neutral:
                self.ready = True
                self.anchor = pad
            return False
        changed_buttons = old is not None and (pad[0] != old[0] or abs(pad[5] - old[5]) >= 12 or abs(pad[6] - old[6]) >= 12)
        changed_sticks = self.anchor is not None and any(abs(pad[i] - self.anchor[i]) >= 512 for i in range(1, 5))
        active_sticks = stick(pad[1], pad[2], settings['deadzone']) != (0., 0.) or stick(pad[3], pad[4], settings['deadzone']) != (0., 0.)
        if physical:
            self.mode = 'keyboard'
            self.anchor = pad
        elif changed_buttons or (changed_sticks and active_sticks):
            self.mode = 'controller'
            self.anchor = pad
        return self.mode == 'controller'


class Gestures(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.started, self.stopped, self.was_pressed = None, False, False
        self.holds = {}
        self.fly_started, self.fly_was_pressed, self.blocked = None, False, set()

    def pause_navigation(self, pad, settings):
        self.started, self.stopped, self.was_pressed = None, False, False
        self.fly_started, self.fly_was_pressed = None, False
        for action in ('fly', 'stop'):
            if matches(action, pad, settings, False):
                self.blocked.add(action)

    def step(self, pad, x, y, target, now, settings):
        pressed = matches('stop', pad, settings)
        flying = matches('fly', pad, settings)
        for name in list(self.blocked):
            if not matches(name, pad, settings, False):
                self.blocked.remove(name)
        pressed = pressed and 'stop' not in self.blocked
        flying = flying and 'fly' not in self.blocked
        shared = settings['bindings']['fly'] == settings['bindings']['stop']
        action, progress = None, 0.
        if pressed and not self.was_pressed:
            self.started, self.stopped = now, False
        if pressed and self.started is not None:
            progress = min(1., max(0., (now - self.started) * 1000. / settings['rightStickStopMilliseconds']))
            if progress >= 1. and not self.stopped:
                action, self.stopped = 'stop', True
        if not pressed and self.was_pressed and self.started is not None:
            interrupted = not released(settings['bindings']['stop'], pad, settings)
            if interrupted:
                self.blocked.add('stop')
            elif not self.stopped:
                if (now - self.started) * 1000. >= settings['rightStickStopMilliseconds']:
                    action = 'stop'
                elif shared:
                    action = 'fly'
            self.started, self.stopped = None, False
        self.was_pressed = pressed
        if not shared:
            if flying and not self.fly_was_pressed:
                self.fly_started = now
            if not flying and self.fly_was_pressed:
                if not released(settings['bindings']['fly'], pad, settings):
                    self.blocked.add('fly')
                elif action is None:
                    action = 'fly'
                self.fly_started = None
            self.fly_was_pressed = flying
        held, fills = set(), {}
        for name, button in (('leftClick', 1), ('rightClick', 2)):
            if not matches(name, pad, settings):
                self.holds.pop(button, None)
                continue
            hold = self.holds.get(button)
            if hold is None or (not hold[4] and (hold[3] != target or math.hypot(x - hold[1], y - hold[2]) > 10)):
                hold = [now, x, y, target, False]
                self.holds[button] = hold
            fill = max(0., min(1., (now - hold[0]) * 1000. / settings['clickHoldMilliseconds']))
            if fill >= 1.:
                hold[4] = True
            if hold[4]:
                held.add(button)
                fill = 1.
            fills[button] = fill
        return held, fills, action, pressed, progress


class Magnet(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.target, self.escaped, self.travel = None, None, 0.

    def step(self, x, y, dx, dy, target, dt, settings, clicking):
        if target is None:
            self.reset()
            return dx, dy, False
        identity, tx, ty, width, height = target
        if identity != self.target:
            self.target, self.travel = identity, 0.
            if identity != self.escaped:
                self.escaped = None
        distance = math.hypot(dx, dy)
        if clicking or not settings['cursorSnap'] or distance / max(.001, dt) > settings['snapMaxSpeed']:
            self.escaped = identity
            return dx, dy, False
        if not distance or identity == self.escaped:
            return dx, dy, False
        self.travel += distance
        if self.travel > settings['snapRadius'] * .35:
            self.escaped = identity
            return dx, dy, False
        cx, cy = tx + width / 2., ty + height / 2.
        if math.hypot(cx - x, cy - y) > settings['snapRadius']:
            return dx, dy, False
        pull = 1. - math.exp(-10. * dt)
        return dx + (cx - x) * pull, dy + (cy - y) * pull, True


class _Point(ctypes.Structure):
    _fields_ = [('x', ctypes.c_int32), ('y', ctypes.c_int32)]


class _Rect(ctypes.Structure):
    _fields_ = [('left', ctypes.c_int32), ('top', ctypes.c_int32), ('right', ctypes.c_int32), ('bottom', ctypes.c_int32)]


class _Gamepad(ctypes.Structure):
    _fields_ = [('buttons', ctypes.c_uint16), ('lt', ctypes.c_ubyte), ('rt', ctypes.c_ubyte),
               ('lx', ctypes.c_int16), ('ly', ctypes.c_int16), ('rx', ctypes.c_int16), ('ry', ctypes.c_int16)]


class _State(ctypes.Structure):
    _fields_ = [('packet', ctypes.c_uint32), ('pad', _Gamepad)]


class _Mouse(ctypes.Structure):
    _fields_ = [('dx', ctypes.c_int32), ('dy', ctypes.c_int32), ('data', ctypes.c_uint32),
               ('flags', ctypes.c_uint32), ('time', ctypes.c_uint32), ('extra', ctypes.c_size_t)]


class _Union(ctypes.Union):
    _fields_ = [('mouse', _Mouse)]


class _Input(ctypes.Structure):
    _fields_ = [('kind', ctypes.c_uint32), ('data', _Union)]


class WindowsInput(object):
    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.user.GetForegroundWindow.restype = ctypes.c_void_p
        self.user.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        self.user.GetClientRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(_Rect)]
        self.user.ClientToScreen.argtypes = [ctypes.c_void_p, ctypes.POINTER(_Point)]
        self.user.GetMessageExtraInfo.restype = ctypes.c_size_t
        self.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user.GetAsyncKeyState.restype = ctypes.c_int16
        self.user.SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(_Input), ctypes.c_int]
        self.user.SendInput.restype = ctypes.c_uint
        self.user.GetCursorPos.argtypes = [ctypes.POINTER(_Point)]
        self.user.GetSystemMetrics.argtypes = [ctypes.c_int]
        self.selected, self.owned = -1, set()
        self.pending = False
        self.physical_buttons = set()
        self.keys = set()
        self.xinput = None
        for name in ('xinput1_4', 'xinput9_1_0'):
            try:
                self.xinput = ctypes.WinDLL(name).XInputGetState
                break
            except (OSError, AttributeError):
                pass
        if self.xinput is None:
            raise RuntimeError('Controller input API unavailable')
        self.xinput.argtypes = [ctypes.c_uint32, ctypes.POINTER(_State)]
        self.xinput.restype = ctypes.c_uint32

    def read(self, index):
        if index != -1:
            slots = [index]
        else:
            slots = ([self.selected] if self.selected >= 0 else []) + [slot for slot in range(4) if slot != self.selected]
        for slot in slots:
            state = _State()
            if self.xinput(slot, ctypes.byref(state)) == 0:
                changed = slot != self.selected
                self.selected = slot
                p = state.pad
                return (p.buttons, p.lx, p.ly, p.rx, p.ry, p.lt, p.rt), changed
        self.selected = -1
        return None, False

    def scan(self):
        connected = {}
        for slot in range(4):
            state = _State()
            if self.xinput(slot, ctypes.byref(state)) == 0:
                p = state.pad
                connected[slot] = (p.buttons, p.lx, p.ly, p.rx, p.ry, p.lt, p.rt)
        return connected

    def foreground(self):
        pid = ctypes.c_uint32()
        self.user.GetWindowThreadProcessId(self.user.GetForegroundWindow(), ctypes.byref(pid))
        return pid.value == os.getpid()

    def position(self):
        point = _Point()
        if not self.user.GetCursorPos(ctypes.byref(point)):
            raise RuntimeError('Cursor position unavailable')
        return point.x, point.y

    def bounds(self):
        window, rect, origin = self.user.GetForegroundWindow(), _Rect(), _Point()
        if not self.foreground() or not self.user.GetClientRect(window, ctypes.byref(rect)) or not self.user.ClientToScreen(window, ctypes.byref(origin)):
            raise RuntimeError('Client bounds unavailable')
        return origin.x, origin.y, rect.right, rect.bottom

    def send(self, flags, x=0, y=0):
        event = _Input()
        event.data.mouse = _Mouse(x, y, 0, flags, 0, TAG)
        if self.user.SendInput(1, ctypes.byref(event), ctypes.sizeof(event)) != 1:
            raise RuntimeError('Controller mouse event unavailable')

    def move(self, x, y):
        left, top, width, height = self.bounds()
        x, y = max(left, min(left + width - 1, x)), max(top, min(top + height - 1, y))
        vx, vy = self.user.GetSystemMetrics(76), self.user.GetSystemMetrics(77)
        vw, vh = self.user.GetSystemMetrics(78), self.user.GetSystemMetrics(79)
        self.send(0x8000 | 0x4000 | 1, int(round((x - vx) * 65535. / max(1, vw - 1))), int(round((y - vy) * 65535. / max(1, vh - 1))))
        return x, y

    def buttons(self, desired):
        for button in list(self.owned - desired):
            if button not in self.physical_buttons:
                self.send(4 if button == 1 else 16)
            self.owned.remove(button)
        for button in desired - self.owned:
            if not self.foreground():
                return
            if self.user.GetAsyncKeyState(button) & 0x8000:
                continue
            left, top, width, height = self.bounds()
            x, y = self.position()
            if not left <= x < left + width or not top <= y < top + height:
                continue
            self.send(2 if button == 1 else 8)
            self.owned.add(button)

    def release(self):
        self.buttons(set())

    def physical(self):
        keys = set(key for key in range(8, 255) if self.user.GetAsyncKeyState(key) & 0x8000)
        changed = keys != self.keys
        self.keys = keys
        pending, self.pending = self.pending or changed, False
        return pending

    def event(self, obj, event_id, param, constants):
        if self.user.GetMessageExtraInfo() == TAG:
            return True
        self.pending = True
        if event_id in (constants.UI_MOUSEDOWN, constants.UI_MOUSEUP):
            button = param[0] if isinstance(param, (tuple, list)) and param else param
            mapping = {constants.MOUSELEFT: 1, constants.MOUSERIGHT: 2}
            button = mapping.get(button)
            if button is not None:
                if event_id == constants.UI_MOUSEDOWN:
                    self.physical_buttons.add(button)
                else:
                    self.physical_buttons.discard(button)
        return True


class CursorUi(object):
    def __init__(self, ui, helpers):
        from carbonui.primitives.container import Container
        from carbonui.primitives.vectorlinetrace import VectorLineTrace
        from carbonui.primitives.fill import Fill
        import carbonui.const as constants
        self.ui, self.helpers, self.visual = ui, helpers, 0.
        self.root = Container(parent=ui.desktop, name='evejsControllerCursor', align=constants.TOPLEFT,
                              width=70, height=70, state=constants.UI_DISABLED, idx=0)
        self.lines = [VectorLineTrace(parent=self.root, width=70, height=70, lineWidth=width,
                                     state=constants.UI_DISABLED) for width in (3., 1.25, 1.5, 2., 1.5, 2., 1.5, 2.)]
        self.dot = Fill(parent=self.root, align=constants.TOPLEFT, left=34, top=34, width=2, height=2,
                        state=constants.UI_DISABLED, color=(.84, .90, .95, 1.))
        self.mask = helpers['_CursorMask'](ui.uilib, constants)
        self.crosshair = helpers['_CameraCenterDot']()
        self.hide()

    def arc(self, line, radius, fill, color):
        line.Flush()
        count = max(1, int(48 * fill))
        for index in range(count + 1):
            angle = -math.pi / 2. + 2. * math.pi * fill * index / count
            line.AddPoint((35 + math.cos(angle) * radius, 35 + math.sin(angle) * radius), color=color)

    def update(self, active, ring, snapped, fills, stop, stop_fill, dt):
        self.crosshair.update(self.ui, active)
        self.root.display = active and ring
        self.mask.show_ring(active and ring)
        if not self.root.display:
            return
        self.visual += ((1. if snapped else 0.) - self.visual) * (1. - math.exp(-12. * dt))
        self.root.left, self.root.top = self.ui.uilib.x - 35, self.ui.uilib.y - 35
        radius = 9 + 3 * self.visual
        self.arc(self.lines[0], radius, 1., (.07, .10, .14, 1.))
        self.arc(self.lines[1], radius, 1., (.84 - .37 * self.visual, .90 + .015 * self.visual, .95 + .035 * self.visual, 1.))
        for index, button, radius, color in ((2, 1, 17., (.39, .85, 1., 1.)), (4, 2, 22., (.93, .73, .42, 1.)), (6, 0, 27., (.96, .56, .35, 1.))):
            enabled, fill = (stop, stop_fill) if button == 0 else (button in fills, fills.get(button, 0.))
            self.lines[index].display = self.lines[index + 1].display = enabled
            if enabled:
                self.arc(self.lines[index], radius, 1., (.16, .22, .28, 1.))
                self.arc(self.lines[index + 1], radius, max(.001, fill), color)

    def hide(self):
        self.mask.show_ring(False)
        self.root.display = False
        self.crosshair.update(self.ui, False)
        self.visual = 0.

    def close(self):
        self.mask.dispose()
        try:
            self.crosshair.dispose()
        finally:
            self.root.Close()


class Controller(object):
    def __init__(self, directory, ui, helpers, native=None, overlay=None, settings_api=None):
        self.directory, self.ui, self.helpers = directory, ui, helpers
        self.native, self.overlay = native or WindowsInput(), overlay or CursorUi(ui, helpers)
        self.mode, self.gestures, self.magnet = InputMode(), Gestures(), Magnet()
        self.active, self.settings, self.last_settings, self.last_tick = True, preferences({}), -1., time.time()
        self.cookie, self.constants = None, None
        self.remainder_x, self.remainder_y = 0., 0.
        self.menu = None
        try:
            self.menu = settings_api['install'](self, globals()) if settings_api else None
        except Exception:
            try:
                self.native.release()
            finally:
                self.overlay.close()
            raise

    def listen(self):
        import carbonui.const as constants
        self.constants = constants
        events = [getattr(constants, name) for name in ('UI_MOUSEMOVE', 'UI_MOUSEMOVEDRAG', 'UI_MOUSEWHEEL', 'UI_MOUSEDOWN', 'UI_MOUSEUP', 'UI_KEYDOWN', 'UI_KEYUP')]
        self.cookie = self.ui.event.RegisterForTriuiEvents(events, self.on_input)

    def on_input(self, obj, event_id, param):
        if not self.active:
            return False
        return self.native.event(obj, event_id, param, self.constants)

    def cancel(self):
        try:
            self.native.release()
        finally:
            self.gestures.reset()
            self.magnet.reset()
            self.remainder_x, self.remainder_y = 0., 0.
            self.overlay.hide()

    def load(self, now):
        if now - self.last_settings < .5:
            return
        self.last_settings = now
        with open(os.path.join(self.directory, 'activation.json'), 'rb') as stream:
            if json.load(stream).get('enabled') is not True:
                self.close()
                return
        with open(os.path.join(self.directory, 'preferences.json'), 'rb') as stream:
            content = stream.read(65537)
            if len(content) > 65536:
                raise ValueError('Oversized preferences')
            settings = preferences(json.loads(content))
        if settings != self.settings:
            self.cancel()
            self.mode.reset()
            if self.menu and (self.menu.capture or self.menu.identifying):
                self.menu.abort()
                self.menu.message('Configuration Changed; Input Detection Canceled')
            self.settings = settings

    def tick(self, now):
        self.load(now)
        if not self.active:
            return
        dt = max(.001, min(.05, now - self.last_tick))
        self.last_tick = now
        pad, changed = self.native.read(self.settings['controllerIndex'])
        if changed:
            self.mode.reset()
            self.cancel()
        physical = self.native.physical()
        foreground = self.native.foreground()
        if self.menu and self.menu.tick(now, foreground):
            self.cancel()
            self.mode.reset()
            return
        active = self.mode.step(pad, physical, foreground, self.settings)
        if not active:
            self.cancel()
            return
        x, y = self.native.position()
        dx, dy = axes('cursor', pad, self.settings)
        dx, dy = dx * self.settings['cursorSpeed'] * dt, -dy * self.settings['cursorSpeed'] * dt
        hover = self.helpers['_ec_hover_target'](self.ui)
        target = None
        if hover is not None:
            left, top, width, height = self.native.bounds()
            target = (hover['id'], left + hover['x'] * width, top + hover['y'] * height, hover['w'] * width, hover['h'] * height)
        dx, dy, snapped = self.magnet.step(x, y, dx, dy, target, dt, self.settings, matches('leftClick', pad, self.settings) or matches('rightClick', pad, self.settings))
        dx, dy = dx + self.remainder_x, dy + self.remainder_y
        step_x, step_y = int(dx), int(dy)
        self.remainder_x, self.remainder_y = dx - step_x, dy - step_y
        if step_x or step_y:
            x, y = self.native.move(x + step_x, y + step_y)
        held, fills, action, stop, stop_fill = self.gestures.step(pad, x, y, hover['id'] if hover else None, now, self.settings)
        self.native.buttons(held)
        rx, ry = axes('cameraPan', pad, self.settings)
        zx, zy = axes('cameraZoom', pad, self.settings)
        menu_layer = getattr(getattr(self.ui, 'layer', None), 'systemmenu', None)
        settings_open = bool(menu_layer is not None and getattr(menu_layer, 'display', False) and
                             any(getattr(child, 'display', False) and not getattr(child, 'destroyed', False) for child in getattr(menu_layer, 'children', [])))
        session = getattr(_builtins, 'session', None)
        if not settings_open and (rx or ry or zy) and session is not None and getattr(session, 'solarsystemid', None) and not getattr(session, 'stationid', None) and not getattr(session, 'structureid', None):
            sm = getattr(_builtins, 'sm', None)
            camera = sm.GetService('sceneManager').GetActiveSpaceCamera() if sm else None
            if camera is not None:
                if rx or ry:
                    camera.Orbit(rx * self.settings['cameraSpeed'] * dt * .005, ry * (1 if self.settings['invertCameraPan'] else -1) * self.settings['cameraSpeed'] * dt * .005)
                if zy:
                    camera.Zoom(-zy * self.settings['cameraZoomSpeed'] * dt)
        if action and not settings_open:
            print('EVEJS_CONTROLLER:' + self.helpers['_ec_navigation'](action, self.ui))
        if settings_open:
            self.gestures.pause_navigation(pad, self.settings)
            stop, stop_fill = False, 0.
        self.overlay.update(True, self.settings['cursorRing'], snapped, fills, stop, stop_fill, dt)

    def close(self):
        if not self.active:
            return
        self.active = False
        try:
            self.cancel()
        finally:
            try:
                if self.cookie is not None:
                    self.ui.event.UnregisterForTriuiEvents(self.cookie)
                    self.cookie = None
            finally:
                try:
                    if self.menu:
                        self.menu.close()
                finally:
                    self.overlay.close()

    def run(self):
        import blue
        try:
            self.listen()
            while self.active and getattr(_builtins, '_evejs_controller_native_v1', None) is self:
                blue.pyos.synchro.SleepWallclock(16)
                try:
                    self.tick(time.time())
                except Exception as error:
                    self.cancel()
                    self.mode.reset()
                    print('EVEJS_CONTROLLER:Input paused: ' + type(error).__name__)
                    blue.pyos.synchro.SleepWallclock(500)
        finally:
            self.close()


def start(directory, helpers, settings_api=None):
    import eveprefs
    import uthread
    if int(eveprefs.boot.build) != 3396210:
        return False
    ui = getattr(_builtins, 'uicore', None)
    if ui is None:
        return False
    previous = getattr(_builtins, '_evejs_controller_native_v1', None)
    if previous is not None:
        previous.close()
    controller = Controller(directory, ui, helpers, settings_api=settings_api)
    setattr(_builtins, '_evejs_controller_native_v1', controller)
    uthread.new(controller.run)
    return True
