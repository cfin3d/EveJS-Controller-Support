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
try:
    TEXT_TYPES = (str, unicode)
except NameError:
    TEXT_TYPES = (str,)

TAG = 0x45564354
LB, RB, RS = 0x100, 0x200, 0x80
BUTTONS = [('LT', 0x10000), ('RT', 0x20000), ('LB', LB), ('RB', RB),
           ('A', 0x1000), ('B', 0x2000), ('X', 0x4000), ('Y', 0x8000),
           ('UP', 1), ('DOWN', 2), ('LEFT', 4), ('RIGHT', 8),
           ('VIEW', 0x20), ('MENU', 0x10), ('LS', 0x40), ('RS', RS)]
BUTTONS += [('R4',1<<18),('L4',1<<19),('R5',1<<20),('L5',1<<21),('TOUCHPAD',1<<22),
            ('MISC1',1<<23),('MISC2',1<<24),('MISC3',1<<25),('MISC4',1<<26),('MISC5',1<<27),('MISC6',1<<28),('GUIDE',1<<29)]
BUTTON_BITS = dict(BUTTONS)
ACTIONS = [('cursor', 'Move Cursor'), ('cameraPan', 'Pan Camera / Focused UI'),
           ('cameraZoom', 'Zoom Camera'), ('leftClick', 'Left-Click / Target Radial'),
           ('rightClick', 'Right-Click'), ('fly', 'Fly Toward Camera Center'), ('stop', 'Stop Ship'),
           ('neocom', 'Open Neocom'), ('closeWindow', 'Close Focused Window')]
DEFAULT_BINDINGS = dict(cursor='LEFT_STICK', cameraPan='RIGHT_STICK',
                        cameraZoom='LT+RIGHT_STICK_Y', leftClick='RB', rightClick='LB', fly='RS', stop='RS',neocom='VIEW',closeWindow='B')
DEFAULTS = dict(schemaVersion=1, controllerIndex=-1, controllerIcons='auto', deadzone=.20, cursorSpeed=1100,
                combatHudEnabled=False,
                cameraSpeed=800, cursorRing=True, cursorSnap=True, snapRadius=28,
                snapMaxSpeed=250, clickHoldMilliseconds=500, rightStickStopMilliseconds=1000, windowCloseHoldMilliseconds=1000,
                invertCameraPan=False, cameraZoomSpeed=.8, triggerThreshold=40,
                vibrationEnabled=True, vibrationStrength=.65, damageVibration=True, destructionVibration=True,
                damageVibrationStrength=.8, destructionVibrationStrength=1., dualsenseHaptics=False,
                bindings=DEFAULT_BINDINGS, customBindings=[], profiles={})
SHORTCUT_KEYS = [(chr(code), code) for code in range(65, 91)] + [(str(i), 48+i) for i in range(10)] + [('F%d' % i, 111+i) for i in range(1,25)] + [('Space',32),('Tab',9),('Enter',13),('Escape',27),('Backspace',8),('Insert',45),('Delete',46),('Home',36),('End',35),('Page Up',33),('Page Down',34),('Up',38),('Down',40),('Left',37),('Right',39)]
SHORTCUT_MODIFIERS = [('None','NONE',()),('Ctrl','CTRL',(17,)),('Alt','ALT',(18,)),('Shift','SHIFT',(16,)),
                     ('Ctrl + Alt','CTRL+ALT',(17,18)),('Ctrl + Shift','CTRL+SHIFT',(17,16)),
                     ('Alt + Shift','ALT+SHIFT',(18,16)),('Ctrl + Alt + Shift','CTRL+ALT+SHIFT',(17,18,16))]


def binding_overlap(first, second):
    if not first or not second:
        return False
    a, b = set(first.replace('_Y','').split('+')), set(second.replace('_Y','').split('+'))
    return a <= b or b <= a


def custom_bindings(document, builtins):
    if not isinstance(document, list) or len(document) > 32:
        raise ValueError('Use At Most 32 Custom Bindings')
    result, used = [], set()
    for source in document:
        if not isinstance(source, dict) or set(source) != set(('id','modifier','key','controller','command')):
            raise ValueError('Invalid Custom Binding')
        item = dict(source)
        if any(not isinstance(value,TEXT_TYPES) for value in item.values()):
            raise ValueError('Invalid Custom Binding')
        identity = item['id']
        if not isinstance(identity, type('')):
            try:
                if not isinstance(identity, unicode): raise ValueError('Invalid Custom Binding ID')
            except NameError: raise ValueError('Invalid Custom Binding ID')
        if not identity.startswith('custom-') or not identity[7:].isdigit() or len(identity)>18 or identity in used:
            raise ValueError('Invalid Custom Binding ID')
        used.add(identity)
        if item['modifier'] not in [value for title,value,codes in SHORTCUT_MODIFIERS] or item['key'] not in dict(SHORTCUT_KEYS):
            raise ValueError('Invalid Keyboard Shortcut')
        name = item['command']
        if not name or len(name)>100 or not all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in name):
            raise ValueError('Invalid EVE Command')
        item['controller'] = binding(item['controller'], 'custom')
        if any(binding_overlap(item['controller'], value) for value in builtins.values()) or any(binding_overlap(item['controller'], old['controller']) for old in result):
            raise ValueError('Custom Binding Conflicts With An Existing Function')
        result.append(item)
    return result


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
    return stick(pad[offset], pad[offset + 1], settings['deadzone'], 2.7 if action == 'cursor' else 2.)


def preferences(document):
    result = dict(DEFAULTS)
    result.update(document)
    if result['schemaVersion'] != 1:
        raise ValueError('Unsupported preferences version')
    ranges = dict(controllerIndex=(-1, 15), deadzone=(.05, .5), cursorSpeed=(100, 4000),
                  cameraSpeed=(100, 4000), snapRadius=(8, 64), snapMaxSpeed=(50, 600),
                  clickHoldMilliseconds=(200, 2000), rightStickStopMilliseconds=(500, 3000), windowCloseHoldMilliseconds=(500,3000),
                  cameraZoomSpeed=(.1, 3.), triggerThreshold=(10, 240), vibrationStrength=(0.,1.),
                  damageVibrationStrength=(0.,1.), destructionVibrationStrength=(0.,1.))
    for name, limits in ranges.items():
        value = result[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value) or not limits[0] <= value <= limits[1]:
            raise ValueError('Invalid ' + name)
    for name in ('controllerIndex', 'clickHoldMilliseconds', 'rightStickStopMilliseconds', 'windowCloseHoldMilliseconds', 'triggerThreshold'):
        if int(result[name]) != result[name]:
            raise ValueError('Invalid ' + name)
        result[name] = int(result[name])
    for name in ('cursorRing', 'cursorSnap', 'invertCameraPan','vibrationEnabled','damageVibration','destructionVibration','dualsenseHaptics','combatHudEnabled'):
        if not isinstance(result[name], bool):
            raise ValueError('Invalid ' + name)
    if result['controllerIcons'] not in ('auto','xbox','ps4','ps5','steam'):
        raise ValueError('Invalid Controller Icon Style')
    incoming=document.get('bindings', {})
    if isinstance(incoming,dict) and 'closeWindow' not in incoming:
        legacy=list(incoming.values())
        customs=document.get('customBindings',[])
        if isinstance(customs,list):legacy.extend(item.get('controller','') for item in customs if isinstance(item,dict))
        if any(isinstance(value,TEXT_TYPES) and binding_overlap(value.upper(),'B') for value in legacy):incoming=dict(incoming,closeWindow='')
    if isinstance(incoming,dict) and 'neocom' not in incoming:
        legacy=list(incoming.values())
        customs=document.get('customBindings', [])
        if isinstance(customs,list):legacy.extend(item.get('controller','') for item in customs if isinstance(item,dict))
        if any(isinstance(value,TEXT_TYPES) and binding_overlap(value,'VIEW') for value in legacy):
            incoming=dict(incoming,neocom='')
    result['bindings'] = validate_bindings(incoming)
    result['customBindings'] = custom_bindings(document.get('customBindings', []), result['bindings'])
    profiles = document.get('profiles', {})
    if not isinstance(profiles, dict) or len(profiles) > 20:
        raise ValueError('Invalid Profiles')
    for name, profile in profiles.items():
        if not name or len(name) > 40 or not isinstance(profile, dict) or 'profiles' in profile:
            raise ValueError('Invalid Profile')
        preferences(dict(profile, profiles={}))
    result['profiles'] = profiles
    return result


def stick(x, y, deadzone, exponent=2.):
    nx, ny = x / (32768.0 if x < 0 else 32767.0), y / (32768.0 if y < 0 else 32767.0)
    length = math.sqrt(nx * nx + ny * ny)
    if length <= deadzone:
        return 0., 0.
    scale = ((min(1., length) - deadzone) / (1. - deadzone)) ** exponent
    return nx / length * scale, ny / length * scale


class WindowCloseGesture(object):
    def __init__(self,controller):
        self.controller=controller
        self.target=self.origin=self.returning=self.deferred=self.pending=None
        self.previous,self.gate,self.serial=0,False,0
        self.started,self.progress=0.,0.

    def identity(self):
        session=getattr(_builtins,'session',None)
        return tuple(getattr(session,key,None) for key in ('charid','shipid','solarsystemid','stationid','structureid'))

    def observe(self,pad):
        if self.target or self.returning:return
        settings=self.controller.settings
        if pad is None or not input_mask(pad,settings) and stick(pad[1],pad[2],settings['deadzone'])==(0.,0.) and stick(pad[3],pad[4],settings['deadzone'])==(0.,0.):
            self.gate=False;self.previous=0

    def cancel(self):
        origin=self.origin or (self.pending['origin'] if self.pending else None)
        self.target=self.origin=self.returning=self.pending=None
        self.progress=0.
        if origin is not None:
            self.gate=True;self.serial+=1
            try:
                if self.controller.native.foreground():self.controller.native.move(*origin)
                else:self.deferred=origin
            except Exception:pass

    def restore(self,now):
        self.target=None;self.progress=0.;self.gate=True;self.serial+=1
        self.returning=(now,self.controller.native.position(),self.origin)

    def animate(self,start,end,elapsed):
        t=max(0.,min(1.,elapsed/.14));ease=t*t*(3.-2.*t)
        self.controller.native.move(start[0]+(end[0]-start[0])*ease,start[1]+(end[1]-start[1])*ease)
        return t>=1.

    def point(self,target):
        left,top,width,height=self.controller.native.bounds()
        return left+target['x']*width,top+target['y']*height

    def valid_attempt(self,attempt):
        c=self.controller
        if not c.active or self.pending is not attempt or self.serial!=attempt['serial'] or self.identity()!=attempt['identity']:return False
        if not c.native.foreground() or c.mode.mode!='controller' or getattr(c.native,'pending',False):return False
        return c.native.bounds()==attempt['bounds'] and c.settings['bindings']['closeWindow']==attempt['binding'] and c.settings['windowCloseHoldMilliseconds']==attempt['duration'] and c.helpers['_ec_window_close_valid'](c.ui,attempt['target'])

    def finish(self,attempt,closed):
        if self.pending is not attempt or self.serial!=attempt['serial']:return
        self.pending=None
        if self.controller.native.foreground() and self.controller.mode.mode=='controller':
            self.controller.native.move(*(attempt['end'] if closed else attempt['origin']))
        elif not closed:self.deferred=attempt['origin']

    def step(self,pad,now,allow_start=True):
        c=self.controller;settings=c.settings;value=settings['bindings']['closeWindow']
        mask=input_mask(pad,settings);needed=binding_mask(value)
        pressed=matches('closeWindow',pad,settings)
        rising=pressed and self.previous & needed!=needed
        self.previous=mask
        self.progress=0.
        if self.deferred is not None:
            c.native.move(*self.deferred);self.deferred=None;self.gate=False;return True
        if self.returning:
            stamp,start,end=self.returning
            if self.animate(start,end,now-stamp):self.returning=self.origin=None
            return True
        if self.gate:return True
        extra=bool(mask & ~needed or stick(pad[1],pad[2],settings['deadzone'])!=(0.,0.) or stick(pad[3],pad[4],settings['deadzone'])!=(0.,0.))
        if self.pending and (mask or extra):self.serial+=1;self.pending=None
        if self.target is None:
            if not rising or not allow_start:return False
            finder=c.helpers.get('_ec_window_close_target')
            target=finder(c.ui) if finder else None
            if target is None:return False
            if extra or getattr(c.native,'owned',None) or getattr(c.native,'physical_buttons',None):self.gate=True;return True
            self.serial+=1;self.pending=None
            self.target,self.origin,self.started=target,c.native.position(),now
            self.snapshot=(self.identity(),value,settings['windowCloseHoldMilliseconds'],c.native.bounds())
            c.native.release();c.gestures.reset();c.magnet.reset();c.motion.reset()
            c.remainder_x=c.remainder_y=0.
            c.custom_epoch+=1;c.custom_down=c.custom_pressed(pad)
        target=c.helpers['_ec_window_close_valid'](c.ui,self.target)
        if not allow_start or extra or not target or self.snapshot!=(self.identity(),value,settings['windowCloseHoldMilliseconds'],c.native.bounds()) or getattr(getattr(_builtins,'session',None),'mutating',False):
            self.restore(now);return True
        end=self.point(target)
        self.progress=max(0.,min(1.,(now-self.started)/(settings['windowCloseHoldMilliseconds']/1000.)))
        if not pressed:
            if self.progress<1. or not released(value,pad,settings):self.restore(now);return True
            c.native.move(*end)
            attempt=dict(target=self.target,origin=self.origin,end=end,serial=self.serial,identity=self.identity(),binding=value,duration=settings['windowCloseHoldMilliseconds'],bounds=c.native.bounds())
            self.pending=attempt;self.target=self.origin=None;self.gate=True;self.progress=0.
            c.helpers['_ec_window_close_invoke'](self,attempt)
            return True
        self.animate(self.origin,end,now-self.started)
        return True


class CursorMotion(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.x, self.y = 0., 0.

    def step(self, x, y, dt):
        # Ease acceleration globally; releasing a direction stops it immediately.
        if not x or x * self.x < 0:
            self.x = 0.
        if not y or y * self.y < 0:
            self.y = 0.
        amount = 1. - math.exp(-dt / .075)
        self.x += (x - self.x) * amount
        self.y += (y - self.y) * amount
        return self.x, self.y


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

    def step(self, pad, x, y, target, now, settings, suppress_left=False):
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
            if name == 'leftClick' and suppress_left or not matches(name, pad, settings):
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
        self.target, self.escaped, self.travel, self.engaged = None, None, 0., False
        self.escape_direction = None

    def choose(self, x, y, dx, dy, targets, settings):
        length = math.hypot(dx, dy)
        direction = (dx / length, dy / length) if length else None
        if self.escape_direction and direction and sum(a * b for a, b in zip(self.escape_direction, direction)) < -.25:
            self.escaped, self.escape_direction = None, None
        candidates = []
        for target in targets:
            identity, tx, ty, width, height = target
            if identity == self.escaped:
                continue
            edge = math.hypot(max(tx - x, 0., x - tx - width), max(ty - y, 0., y - ty - height))
            if edge > settings['snapRadius']:
                continue
            vx, vy = tx + width / 2. - x, ty + height / 2. - y
            distance = math.hypot(vx, vy)
            if self.escaped and direction and vx * direction[0] + vy * direction[1] < -2:
                continue
            score = edge + min(distance, settings['snapRadius'] * 2) * .35
            if identity == self.target:
                score -= 4  # Hysteresis prevents alternating between neighbors.
            candidates.append((score, identity, target))
        return min(candidates)[2] if candidates else None

    def step(self, x, y, dx, dy, target, dt, settings, clicking, input_speed=None):
        if target is None:
            self.target, self.engaged, self.travel = None, False, 0.
            return dx, dy, False
        identity, tx, ty, width, height = target
        if identity != self.target:
            self.target, self.travel, self.engaged = identity, 0., False
        distance = math.hypot(dx, dy)
        if clicking or not settings['cursorSnap']:
            self.engaged = False
            return dx, dy, False
        if not distance:
            self.travel = 0.
        speed = distance / max(.001, dt) if input_speed is None else input_speed
        if speed > settings['snapMaxSpeed']:
            self.engaged = False
            return dx, dy, False
        if identity == self.escaped:
            if self.escape_direction and distance and (dx * self.escape_direction[0] + dy * self.escape_direction[1]) / distance < -.25:
                self.escaped, self.escape_direction = None, None
            else:
                return dx, dy, False
        cx, cy = tx + width / 2., ty + height / 2.
        outward = dx * (x - cx) + dy * (y - cy) > .01
        self.travel = self.travel + distance if outward else 0.
        if self.travel > min(settings['snapRadius'] * .35, min(width, height) * .25):
            self.escaped = identity
            self.escape_direction = (dx / distance, dy / distance)
            self.engaged = False
            return dx, dy, False
        edge_distance = math.hypot(max(tx - x, 0., x - tx - width), max(ty - y, 0., y - ty - height))
        if edge_distance > settings['snapRadius']:
            return dx, dy, False
        self.engaged = True
        pull = 1. - math.exp(-10. * dt)
        ax, ay = (cx - x) * pull, (cy - y) * pull
        length, maximum = math.hypot(ax, ay), settings['snapMaxSpeed'] * dt
        if length > maximum:
            ax, ay = ax * maximum / length, ay * maximum / length
        return dx + ax, dy + ay, True


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


class _MouseHook(ctypes.Structure):
    # MOUSEHOOKSTRUCT for a thread-local WH_MOUSE observer (not MSLLHOOKSTRUCT).
    _fields_ = [('point', _Point), ('window', ctypes.c_void_p),
               ('hit_test', ctypes.c_uint32), ('extra', ctypes.c_size_t)]


class WindowsInput(object):
    def __init__(self,directory=None,device_factory=None):
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
        self.mouse_hook, self.mouse_callback = None, None
        self.mouse_position = None
        self.sent_positions = []
        self.xinput = None
        for name in ('xinput1_4', 'xinput9_1_0'):
            try:
                self.xinput = ctypes.WinDLL(name).XInputGetState
                break
            except (OSError, AttributeError):
                pass
        self.devices=None
        if device_factory is not None:
            try:self.devices=device_factory(directory)
            except Exception as error:print('EVEJS_CONTROLLER:SDL unavailable; XInput fallback: '+type(error).__name__)
        if self.xinput is None and self.devices is None:
            raise RuntimeError('Controller input API unavailable')
        if self.xinput is not None:
            self.xinput.argtypes = [ctypes.c_uint32, ctypes.POINTER(_State)]
            self.xinput.restype = ctypes.c_uint32

    def start_listener(self):
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p)
        self.user.SetWindowsHookExW.argtypes = [ctypes.c_int, callback_type, ctypes.c_void_p, ctypes.c_uint32]
        self.user.SetWindowsHookExW.restype = ctypes.c_void_p
        self.user.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p]
        self.user.CallNextHookEx.restype = ctypes.c_ssize_t
        self.user.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentThreadId.argtypes = []
        kernel.GetCurrentThreadId.restype = ctypes.c_uint32
        self.mouse_position = self.position()
        self.sent_positions = []
        self.mouse_callback = callback_type(self.mouse_event)
        # Observe only messages retrieved by EVE's UI thread. A global low-level
        # hook makes desktop input wait for EVE's background message pump.
        self.mouse_hook = self.user.SetWindowsHookExW(7, self.mouse_callback, None, kernel.GetCurrentThreadId())
        if not self.mouse_hook:
            self.mouse_callback = None
            raise ctypes.WinError(ctypes.get_last_error())

    def mouse_event(self, code, message, address):
        try:
            if code == 0 and address:
                event = ctypes.cast(address, ctypes.POINTER(_MouseHook)).contents
                position = (event.point.x, event.point.y)
                moved = position != self.mouse_position
                self.mouse_position = position
                now = time.time()
                self.sent_positions = [(point, stamp) for point, stamp in self.sent_positions if now - stamp < .2]
                generated = event.extra == TAG
                if message in (0x200, 0xA0):
                    # Windows also emits movement messages for cursor/window
                    # refreshes. Coalescing may discard our SendInput tag.
                    generated = generated or not moved or any(point == position for point, stamp in self.sent_positions)
                if not generated and (message in (0x200, 0xA0, 0x20A, 0x20E) or 0x201 <= message <= 0x209 or 0x20B <= message <= 0x20D or 0xA1 <= message <= 0xAD):
                    self.pending = True
                    if message in (0x201, 0x204):
                        self.physical_buttons.add(1 if message == 0x201 else 2)
                    elif message in (0x202, 0x205):
                        self.physical_buttons.discard(1 if message == 0x202 else 2)
        except Exception:
            pass
        return self.user.CallNextHookEx(self.mouse_hook, code, message, address)

    def stop_listener(self):
        if self.mouse_hook:
            self.user.UnhookWindowsHookEx(self.mouse_hook)
            self.mouse_hook = None
        self.mouse_callback = None
        self.sent_positions = []
        self.mouse_position = None

    def read(self, index):
        if self.devices is not None:
            sample,changed=self.devices.read(index)
            self.selected=self.devices.selected
            return sample,changed
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
        if self.devices is not None:return self.devices.scan()
        connected = {}
        for slot in range(4):
            state = _State()
            if self.xinput(slot, ctypes.byref(state)) == 0:
                p = state.pad
                connected[slot] = (p.buttons, p.lx, p.ly, p.rx, p.ry, p.lt, p.rt)
        return connected

    def device_info(self):
        if self.devices is not None:return self.devices.device_info()
        return dict(name='Controller %d'%(self.selected+1) if self.selected>=0 else 'No Controller Connected',style='xbox',kind='xbox',backend='XInput')

    def close_devices(self):
        if self.devices is not None:self.devices.close()

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
        sx, sy = int(round((x - vx) * 65535. / max(1, vw - 1))), int(round((y - vy) * 65535. / max(1, vh - 1)))
        # Record both the requested and Windows' quantized absolute position
        # before delivery, then the actual position after SendInput returns.
        now = time.time()
        points = [(x, y), (vx + (sx * vw // 65536), vy + (sy * vh // 65536))]
        self.sent_positions = (self.sent_positions + [(point, now) for point in points])[-64:]
        self.send(0x8000 | 0x4000 | 1, sx, sy)
        self.sent_positions = (self.sent_positions + [(self.position(), now)])[-64:]
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
        # VK_GAMEPAD_* are controller activity, even when exposed by Windows
        # through its virtual-key state table.
        keys = set(key for key in range(8, 255) if not 0xC3 <= key <= 0xDA and self.user.GetAsyncKeyState(key) & 0x8000)
        changed = keys != self.keys
        self.keys = keys
        pending, self.pending = self.pending or changed, False
        return pending

    def event(self, obj, event_id, param, constants):
        keyboard = event_id in (getattr(constants, 'UI_KEYDOWN', None), getattr(constants, 'UI_KEYUP', None))
        key = param[0] if isinstance(param, (tuple, list)) and param else param
        if keyboard and isinstance(key, int) and 0xC3 <= key <= 0xDA:
            return True
        if getattr(self, 'mouse_hook', None) and not keyboard:
            # Deferred native drag/mouse events do not carry reliable Win32 tags.
            # The OS observer already classified the original mouse message.
            return True
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
                              width=84, height=84, state=constants.UI_DISABLED, idx=0)
        self.lines = [VectorLineTrace(parent=self.root, width=84, height=84, lineWidth=width,
                                     state=constants.UI_DISABLED) for width in (4.5, 2., 1.5, 2.5, 1.5, 2.5, 1.5, 2.5)]
        self.dot = Fill(parent=self.root, align=constants.TOPLEFT, left=40.5, top=40.5, width=3, height=3,
                        state=constants.UI_DISABLED, color=(1., 1., 1., 1.))
        self.mask = helpers['_CursorMask'](ui.uilib, constants)
        self.crosshair = helpers['_CameraCenterDot']()
        self.hide()

    def arc(self, line, radius, fill, color):
        line.Flush()
        count = max(1, int(48 * fill))
        for index in range(count + 1):
            angle = -math.pi / 2. + 2. * math.pi * fill * index / count
            line.AddPoint((42 + math.cos(angle) * radius, 42 + math.sin(angle) * radius), color=color)

    def update(self, active, ring, snapped, fills, stop, stop_fill, dt):
        self.crosshair.update(self.ui, active)
        self.root.display = active and ring
        self.mask.show_ring(active and ring)
        if not self.root.display:
            return
        self.visual += ((1. if snapped else 0.) - self.visual) * (1. - math.exp(-12. * dt))
        self.root.left, self.root.top = self.ui.uilib.x - 42, self.ui.uilib.y - 42
        radius = 13 + 2 * self.visual
        self.arc(self.lines[0], radius, 1., (1., 1., 1., 1.))
        self.arc(self.lines[1], radius, 1., (1., 1., 1., 1.))
        for index, button, radius, color in ((2, 1, 21., (.39, .85, 1., 1.)), (4, 2, 26., (.93, .73, .42, 1.)), (6, 0, 31., (.96, .56, .35, 1.))):
            enabled, fill = (stop, stop_fill) if button == 0 else (button in fills, fills.get(button, 0.))
            self.lines[index].display = self.lines[index + 1].display = enabled
            if enabled:
                self.arc(self.lines[index], radius, 1., (1., 1., 1., .65))
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
        self.native = native or (WindowsInput(directory,helpers['_Gamepads']) if '_Gamepads' in helpers else WindowsInput())
        try:self.overlay=overlay or CursorUi(ui,helpers)
        except Exception:
            closer=getattr(self.native,'close_devices',None)
            if closer:closer()
            raise
        self.mode, self.gestures, self.magnet = InputMode(), Gestures(), Magnet()
        self.motion = CursorMotion()
        self.active, self.settings, self.last_settings, self.last_tick = True, preferences({}), -1., time.time()
        self.cookie, self.constants = None, None
        self.remainder_x, self.remainder_y = 0., 0.
        self.menu = None
        self.radial, self.radial_hold, self.radial_restore = None, None, None
        self.neocom, self.neocom_previous = None, False
        self.radial_gate, self.left_previous = False, False
        self.radial_available = '_ec_radial_open' in helpers
        self.custom_down, self.custom_epoch = set(), 0
        self.window_close=WindowCloseGesture(self)
        self.ui_navigation = {}
        self.context = helpers['_ContextNavigation'](self) if '_ContextNavigation' in helpers else None
        self.feedback = None
        self.combat = None
        self.combat_gate = 0
        if '_CombatFeedback' in helpers:
            try:self.feedback=helpers['_CombatFeedback'](self)
            except Exception as error:print('EVEJS_CONTROLLER:Vibration unavailable: '+type(error).__name__)
        try:
            self.menu = settings_api['install'](self, globals()) if settings_api else None
            if '_CombatHUD' in helpers:
                self.combat = helpers['_CombatHUD'](self)
        except Exception:
            try:
                if self.feedback:
                    try:self.feedback.close()
                    except Exception:pass
                self.native.release()
            finally:
                closer=getattr(self.native,'close_devices',None)
                if closer:closer()
                self.overlay.close()
            raise

    def listen(self):
        import carbonui.const as constants
        self.constants = constants
        events = [getattr(constants, name) for name in ('UI_MOUSEMOVE', 'UI_MOUSEMOVEDRAG', 'UI_MOUSEWHEEL', 'UI_MOUSEDOWN', 'UI_MOUSEUP', 'UI_KEYDOWN', 'UI_KEYUP')]
        self.cookie = self.ui.event.RegisterForTriuiEvents(events, self.on_input)
        listener = getattr(self.native, 'start_listener', None)
        if listener:
            listener()
        if self.feedback:
            try:self.feedback.listen()
            except Exception as error:print('EVEJS_CONTROLLER:Combat feedback unavailable: '+type(error).__name__)
        install = self.helpers.get('_ec_radial_install')
        if install:
            try:
                self.radial_restore = install(self)
            except Exception as error:
                self.radial_available = False
                print('EVEJS_CONTROLLER:Radial unavailable: ' + type(error).__name__)

    def on_input(self, obj, event_id, param):
        if not self.active:
            return False
        return self.native.event(obj, event_id, param, self.constants)

    def cancel(self):
        try:
            self.ui_navigation.clear()
            if self.context:
                if self.context.active:self.radial_gate = True
                self.context.cancel()
            if self.combat:
                pad = self.mode.previous
                try:self.combat.detach(input_mask(pad, self.settings) if pad else 0)
                except Exception as error:print('EVEJS_CONTROLLER:Combat HUD cleanup unavailable: '+type(error).__name__)
            self.window_close.cancel()
            self.custom_epoch += 1
            pad = self.mode.previous
            self.custom_down = self.custom_pressed(pad) if pad else set()
            if self.radial or self.radial_hold or self.neocom:
                self.radial_gate = True
            try:
                if self.neocom:
                    self.neocom.close()
                if self.radial:
                    self.radial.close()
            finally:
                self.radial = self.radial_hold = None
                self.neocom, self.neocom_previous = None, False
                self.left_previous = False
                self.native.release()
        finally:
            self.gestures.reset()
            self.magnet.reset()
            self.motion.reset()
            self.remainder_x, self.remainder_y = 0., 0.
            self.overlay.hide()

    def custom_pressed(self, pad):
        mask = input_mask(pad, self.settings)
        return set(item['id'] for item in self.settings['customBindings'] if item['controller'] and mask & binding_mask(item['controller']) == binding_mask(item['controller']))

    def custom_tick(self, pad, settings_open):
        down = self.custom_pressed(pad)
        rising, self.custom_down = down - self.custom_down, down
        if settings_open or not rising or '_ec_custom_execute' not in self.helpers:
            return
        import uthread
        epoch = self.custom_epoch
        identity = tuple(getattr(getattr(_builtins,'session',None),key,None) for key in ('charid','shipid','solarsystemid','stationid','structureid'))
        for item in self.settings['customBindings']:
            if item['id'] not in rising:
                continue
            def execute(binding=dict(item)):
                current = tuple(getattr(getattr(_builtins,'session',None),key,None) for key in ('charid','shipid','solarsystemid','stationid','structureid'))
                if not self.active or epoch != self.custom_epoch or identity != current or self.mode.mode != 'controller' or not self.native.foreground() or self.radial or self.radial_gate or self.neocom or self.context and self.context.active:
                    return
                try:
                    self.helpers['_ec_custom_execute'](self.ui, binding)
                except Exception as error:
                    print('EVEJS_CONTROLLER:Custom shortcut unavailable: ' + type(error).__name__)
            uthread.new(execute)

    def neocom_tick(self,pad,now,settings_open,dt):
        pressed=matches('neocom',pad,self.settings)
        rising=pressed and not self.neocom_previous
        self.neocom_previous=pressed
        if self.neocom:
            fills={}
            navigation=self.neocom
            if settings_open or rising or not self.neocom.step(pad,now):
                self.neocom.close()
                self.neocom=None
                self.radial_gate=True
                self.custom_down=self.custom_pressed(pad)
            else:fills=navigation.fills
            self.native.release()
            self.overlay.update(True,self.settings['cursorRing'],True,fills,False,0.,dt)
            return True
        if self.radial or self.radial_hold or self.radial_gate or settings_open or not rising:
            return False
        opener=self.helpers.get('_ec_neocom_open')
        if opener is None:
            return False
        self.cancel()
        self.neocom_previous=pressed
        self.neocom=opener(self.ui,self,pad)
        if self.neocom is None:
            self.radial_gate=True
        self.native.release()
        return True

    def radial_tick(self, pad, x, y, now, settings_open):
        pressed = matches('leftClick', pad, self.settings)
        rising = pressed and not self.left_previous
        self.left_previous = pressed
        if self.radial_gate:
            neutral = input_mask(pad, self.settings) == 0 and stick(pad[1], pad[2], self.settings['deadzone']) == (0., 0.) and stick(pad[3], pad[4], self.settings['deadzone']) == (0., 0.)
            if neutral:
                self.radial_gate, self.left_previous = False, False
                self.custom_down = set()
            self.native.release()
            self.overlay.update(True, self.settings['cursorRing'], False, {}, False, 0., .016)
            return True, None
        if self.radial:
            radial = self.radial
            if settings_open or pad[0] & getattr(radial, 'cancel_mask', 0x2000) or not radial.valid():
                radial.close()
                self.radial, self.radial_gate = None, True
            elif not radial.finished:
                if pressed:
                    sx, sy = stick(pad[1], pad[2], self.settings['deadzone'])
                    if getattr(radial, 'range_axis', False):
                        range_y = stick(pad[3], pad[4], self.settings['deadzone'])[1]
                        range_direction = 1 if range_y > .16 else -1 if range_y < -.16 else 0
                    else:
                        range_direction = (1 if pad[0] & 1 else 0) - (1 if pad[0] & 2 else 0)
                    radial.update(sx, sy, range_direction, now)
                else:
                    # Re-read the stick on release so centering and releasing in
                    # one frame cannot execute the previous wedge.
                    sx, sy = stick(pad[1], pad[2], self.settings['deadzone'])
                    radial.update(sx, sy, 0, now)
                    radial.finish(released(self.settings['bindings']['leftClick'], pad, self.settings))
            self.native.release()
            return True, None
        if not self.radial_available or settings_open:
            return False, None
        if rising:
            target = self.helpers['_ec_radial_target'](self.ui)
            if target:
                self.radial_hold = (target, now, x, y)
        if self.radial_hold:
            target, started, start_x, start_y = self.radial_hold
            if not pressed:
                self.radial_hold = None
                return False, None
            current = self.helpers['_ec_radial_target'](self.ui)
            if current is None or current['itemID'] != target['itemID'] or math.hypot(x - start_x, y - start_y) > 10 or not self.helpers['_ec_radial_valid'](self.ui, target):
                self.radial_hold, self.radial_gate = None, True
                self.native.release()
                return True, None
            progress = min(1., max(0., (now - started) * 1000. / self.settings['clickHoldMilliseconds']))
            if progress >= 1.:
                self.custom_epoch += 1
                self.custom_down = self.custom_pressed(pad)
                self.native.release()
                self.gestures.reset()
                self.magnet.reset()
                self.motion.reset()
                self.remainder_x = self.remainder_y = 0.
                self.radial = self.helpers['_ec_radial_open'](self.ui, target, self)
                self.radial_hold = None
                self.overlay.hide()
                if self.radial and hasattr(self.overlay, 'mask'):
                    self.overlay.mask.show_ring(True)
                if self.radial is None:
                    self.radial_gate = True
                return True, None
            return False, progress
        return False, None

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
        self.combat_gate &= pad[0] if pad else 0
        self.window_close.observe(pad)
        if changed:
            if self.feedback:self.feedback.stop()
            self.mode.reset()
            self.cancel()
        physical = self.native.physical()
        foreground = self.native.foreground()
        if self.menu and self.menu.tick(now, foreground):
            if self.feedback:self.feedback.tick(now,False,foreground,pad,True)
            self.cancel()
            self.mode.reset()
            return
        active = self.mode.step(pad, physical, foreground, self.settings)
        if self.feedback:self.feedback.tick(now,active,foreground,pad)
        if not active:
            self.cancel()
            return
        if self.combat:
            try:pad = self.combat.route(pad, now)
            except Exception as error:
                self.combat_gate |= pad[0] & 0xf00f
                try:self.combat.close()
                except Exception:pass
                self.combat = None
                print('EVEJS_CONTROLLER:Combat HUD disabled; controller input retained: '+type(error).__name__)
        if self.combat_gate:pad = (pad[0] & ~self.combat_gate,) + tuple(pad[1:])
        x, y = self.native.position()
        menu_layer = getattr(getattr(self.ui, 'layer', None), 'systemmenu', None)
        settings_open = bool(menu_layer is not None and getattr(menu_layer, 'display', False) and
                             any(getattr(child, 'display', False) and not getattr(child, 'destroyed', False) for child in getattr(menu_layer, 'children', [])))
        if self.context and self.context.step(pad,now,dt):
            self.native.release()
            self.custom_down=self.custom_pressed(pad)
            self.overlay.update(True,self.settings['cursorRing'],True,self.context.fills,False,0.,dt)
            return
        if self.window_close.step(pad,now,not (self.neocom or self.radial or self.radial_hold or self.radial_gate)):
            self.native.release()
            self.gestures.reset();self.magnet.reset();self.motion.reset()
            self.remainder_x=self.remainder_y=0.
            self.custom_epoch+=1
            self.custom_down=self.custom_pressed(pad)
            self.overlay.update(True,self.settings['cursorRing'],True,{2:self.window_close.progress} if self.window_close.target else {},False,0.,dt)
            return
        if self.neocom_tick(pad,now,settings_open,dt):
            return
        exclusive, radial_progress = self.radial_tick(pad, x, y, now, settings_open)
        if exclusive:
            if self.combat:self.combat.gestures.reset(input_mask(pad,self.settings))
            return
        self.custom_tick(pad, settings_open)
        dx, dy = axes('cursor', pad, self.settings)
        requested_speed = math.hypot(dx, dy) * self.settings['cursorSpeed']
        dx, dy = self.motion.step(dx, dy, dt)
        dx, dy = dx * self.settings['cursorSpeed'] * dt, -dy * self.settings['cursorSpeed'] * dt
        hover = self.helpers['_ec_hover_target'](self.ui)
        targets = [hover] if hover else []
        if self.settings['cursorSnap'] and '_ec_snap_targets' in self.helpers:
            targets = self.helpers['_ec_snap_targets'](self.ui, self.settings['snapRadius'])
        elif not targets and self.settings['cursorSnap'] and '_ec_snap_target' in self.helpers:
            nearby = self.helpers['_ec_snap_target'](self.ui, self.settings['snapRadius'])
            targets = [nearby] if nearby else []
        geometry = []
        if targets:
            left, top, width, height = self.native.bounds()
            geometry = [(item['id'], left + item['x'] * width, top + item['y'] * height, item['w'] * width, item['h'] * height) for item in targets]
        target = self.magnet.choose(x, y, dx, dy, geometry, self.settings)
        dx, dy, snapped = self.magnet.step(x, y, dx, dy, target, dt, self.settings, matches('leftClick', pad, self.settings) or matches('rightClick', pad, self.settings), requested_speed)
        dx, dy = dx + self.remainder_x, dy + self.remainder_y
        step_x, step_y = int(dx), int(dy)
        self.remainder_x, self.remainder_y = dx - step_x, dy - step_y
        if step_x or step_y:
            x, y = self.native.move(x + step_x, y + step_y)
        held, fills, action, stop, stop_fill = self.gestures.step(pad, x, y, hover['id'] if hover else None, now, self.settings, radial_progress is not None)
        if radial_progress is not None:
            fills[1] = radial_progress
        if self.context:self.context.observe(held,now)
        self.native.buttons(held)
        rx, ry = axes('cameraPan', pad, self.settings)
        zx, zy = axes('cameraZoom', pad, self.settings)
        ui_navigation = self.helpers.get('_ec_ui_navigate')
        ui_owned = bool(ui_navigation(self,rx,ry,zy,dt)) if ui_navigation else False
        session = getattr(_builtins, 'session', None)
        if not ui_owned and not settings_open and (rx or ry or zy) and session is not None and getattr(session, 'charid', None):
            sm = getattr(_builtins, 'sm', None)
            scene = sm.GetService('sceneManager') if sm else None
            camera = scene.GetActiveCamera() if scene else None
            if camera is not None:
                # Native mouse input cancels the cinematic undock camera.
                switch = getattr(camera, 'SwitchToPrimaryCamera', None)
                if callable(switch):
                    switch()
                    camera = scene.GetActiveCamera()
                orbit, zoom = getattr(camera, 'Orbit', None), getattr(camera, 'Zoom', None)
                if (rx or ry) and callable(orbit):
                    orbit(rx * self.settings['cameraSpeed'] * dt * .005, ry * (1 if self.settings['invertCameraPan'] else -1) * self.settings['cameraSpeed'] * dt * .005)
                if zy and callable(zoom):
                    zoom(-zy * self.settings['cameraZoomSpeed'] * dt)
        if action and not settings_open and not ui_owned:
            print('EVEJS_CONTROLLER:' + self.helpers['_ec_navigation'](action, self.ui, self.dispatch_rpc))
        if settings_open or ui_owned:
            self.gestures.pause_navigation(pad, self.settings)
            stop, stop_fill = False, 0.
        self.overlay.update(True, self.settings['cursorRing'], snapped, fills, stop, stop_fill, dt)

    def dispatch_rpc(self, function, *args):
        import uthread
        session = getattr(_builtins, 'session', None)
        identity = tuple(getattr(session, key, None) for key in ('charid', 'shipid', 'solarsystemid'))
        def send():
            current = getattr(_builtins, 'session', None)
            if not self.active or identity != tuple(getattr(current, key, None) for key in ('charid', 'shipid', 'solarsystemid')) or getattr(current, 'mutating', False) or getattr(current, 'stationid', None) or getattr(current, 'structureid', None):
                return
            try:
                function(*args)
            except Exception as error:
                print('EVEJS_CONTROLLER:Navigation failed: ' + type(error).__name__)
        uthread.new(send)

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
                    listener = getattr(self.native, 'stop_listener', None)
                    if listener:
                        listener()
                finally:
                    if self.feedback:
                        try:self.feedback.close()
                        except Exception:pass
                    closer=getattr(self.native,'close_devices',None)
                    if closer:closer()
                    try:
                        if self.menu:
                            self.menu.close()
                    finally:
                        try:
                            if self.radial_restore:
                                self.radial_restore()
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
                    if self.feedback:self.feedback.stop()
                    self.cancel()
                    self.mode.reset()
                    print('EVEJS_CONTROLLER:Input paused: ' + type(error).__name__)
                    blue.pyos.synchro.SleepWallclock(500)
        finally:
            self.close()


def start(directory, helpers, settings_api=None):
    import eveprefs
    import uthread
    from carbonui.uicore import uicore
    if int(eveprefs.boot.build) != 3396210:
        print('EVEJS_CONTROLLER_START:UNSUPPORTED_BUILD')
        return False
    # This client exports its UI singleton from carbonui.uicore, not builtins.
    ui = uicore
    if ui is None:
        print('EVEJS_CONTROLLER_START:UI_UNAVAILABLE')
        return False
    previous = getattr(_builtins, '_evejs_controller_native_v1', None)
    if previous is not None:
        previous.close()
    controller = Controller(directory, ui, helpers, settings_api=settings_api)
    setattr(_builtins, '_evejs_controller_native_v1', controller)
    uthread.new(controller.run)
    print('EVEJS_CONTROLLER_START:READY')
    return True
