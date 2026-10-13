# Native System Menu integration for EVE client build 3396210.
import ctypes
import json
import os
import sys
import time

PANEL_ID = 'evejs-controller'
PROFILE_KEYS = ('bindings', 'deadzone', 'cursorSpeed', 'cameraSpeed', 'cameraZoomSpeed',
                'invertCameraPan', 'cursorRing', 'cursorSnap', 'snapRadius', 'snapMaxSpeed',
                'clickHoldMilliseconds', 'rightStickStopMilliseconds', 'triggerThreshold')


def prepare_icon(directory):
    import blue
    resource = 'cache:/evejs-controller/controller-settings.png'
    destination = blue.paths.ResolvePathForWriting(resource)
    folder = os.path.dirname(destination)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with open(os.path.join(directory, 'assets', 'controller-settings.png'), 'rb') as stream:
        content = stream.read(32769)
    if len(content) > 32768 or not content.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Invalid Controller Icon')
    with open(destination, 'wb') as stream:
        stream.write(content)
    return resource


def write_preferences(directory, patch, validate):
    path = os.path.join(directory, 'preferences.json')
    with open(path, 'rb') as stream:
        content = stream.read(65537)
    if len(content) > 65536:
        raise ValueError('Configuration Is Too Large')
    document = json.loads(content)
    document.update(patch)
    result = validate(document)
    data = (json.dumps(document, indent=2, sort_keys=True) + '\n').encode('utf-8')
    if len(data) > 65536:
        raise ValueError('Configuration Is Too Large')
    temporary = path + '.controller-settings.tmp'
    try:
        with open(temporary, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == 'nt':
            move = ctypes.WinDLL('kernel32', use_last_error=True).MoveFileExW
            move.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
            move.restype = ctypes.c_int
            try:
                source = temporary if isinstance(temporary, unicode) else temporary.decode(sys.getfilesystemencoding() or 'mbcs')
                target = path if isinstance(path, unicode) else path.decode(sys.getfilesystemencoding() or 'mbcs')
            except NameError:
                source, target = temporary, path
            if not move(source, target, 9):
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            os.rename(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return result


def display_binding(value):
    names = dict(LEFT_STICK='Left Stick', RIGHT_STICK='Right Stick',
                 LEFT_STICK_Y='Left Stick Up/Down', RIGHT_STICK_Y='Right Stick Up/Down',
                 UP='D-Pad Up', DOWN='D-Pad Down', LEFT='D-Pad Left', RIGHT='D-Pad Right',
                 VIEW='View', MENU='Menu')
    return ' + '.join(names.get(token, token) for token in value.split('+')) if value else 'Disabled'


class ControllerSettings(object):
    def __init__(self, controller, api):
        from eve.client.script.ui.shared.systemMenu.systemmenu import SystemMenu, system_menu_selected_tab_setting, PANELID_CAMERA
        from carbonui.control.scrollContainer import ScrollContainer
        from carbonui.control.combo import Combo
        from carbonui.control.checkbox import Checkbox
        from carbonui.control.slider import Slider
        from carbonui.control.button import Button
        from carbonui.control.singlelineedits.singleLineEditText import SingleLineEditText
        from carbonui.primitives.container import Container
        from eve.client.script.ui.control.eveLabel import EveLabelSmall
        from eve.client.script.ui.shared.systemMenu.systemMenuHeader import SystemMenuHeader
        import carbonui.const as const
        self.controller, self.api, self.cls, self.const = controller, api, SystemMenu, const
        self.native_selection, self.fallback = system_menu_selected_tab_setting, PANELID_CAMERA
        self.icon = prepare_icon(controller.directory)
        self.Scroll, self.Combo, self.Checkbox, self.Slider = ScrollContainer, Combo, Checkbox, Slider
        self.Button, self.Edit, self.Container, self.Label, self.Header = Button, SingleLineEditText, Container, EveLabelSmall, SystemMenuHeader
        self.panels, self.widgets, self.connected, self.previous = [], {}, {}, {}
        self.capture, self.identifying, self.ready, self.collected = None, False, False, set()
        self.deadline, self.last_scan, self.message_until = 0., -1., 0.
        self.selected_profile, self.closed, self.rendered_settings = None, False, None
        self.original_tree, self.original_load = SystemMenu.__dict__['ConstructTreeData'], SystemMenu.__dict__['LoadPanel']
        manager = self

        def construct(menu, *args, **kwargs):
            result = manager.original_tree(menu, *args, **kwargs)
            if not manager.closed:
                previous = menu.panelsByID.get(PANEL_ID)
                if previous is not None and not getattr(previous, 'destroyed', False):
                    previous.Close()
                panel = manager.Scroll(name=PANEL_ID, parent=menu.panelCont, display=False)
                menu.panelsByID[PANEL_ID] = panel
                manager.panels = [(m, p) for m, p in manager.panels if not getattr(p, 'destroyed', False) and m is not menu]
                manager.panels.append((menu, panel))
                menu.menuTreeData.AddNode(label='Controller', nodeID=PANEL_ID, icon=manager.icon)
            return result

        def load(menu, panel_id, *args, **kwargs):
            if panel_id == PANEL_ID and not manager.closed:
                panel = menu.panelsByID[PANEL_ID]
                if not getattr(panel, '_controller_loaded', False):
                    manager.build(panel)
            return manager.original_load(menu, panel_id, *args, **kwargs)

        self.tree_hook, self.load_hook = construct, load
        SystemMenu.ConstructTreeData, SystemMenu.LoadPanel = construct, load
        menu = getattr(getattr(controller.ui, 'layer', None), 'systemmenu', None)
        try:
            if menu is not None and getattr(menu, 'display', False) and getattr(menu, 'panelCont', None):
                self.reconstruct(menu)
        except Exception:
            self.close()
            raise

    def reconstruct(self, menu):
        # The native menu owns selection, focus, sizing, colors and navigation.
        selected = next((key for key, panel in menu.panelsByID.items() if getattr(panel, 'display', False)), None)
        if selected == PANEL_ID and self.closed:
            selected = self.fallback
        menu.ReconstructLayout(selected)

    def visible(self):
        return any(not getattr(panel, 'destroyed', False) and getattr(menu, 'display', False) and getattr(panel, 'display', False) for menu, panel in self.panels)

    def message(self, text):
        self.message_until = time.time() + 3.
        status = self.widgets.get('status')
        if status is not None and not getattr(status, 'destroyed', False):
            status.text = text

    def save(self, patch, rebuild=False):
        try:
            result = write_preferences(self.controller.directory, patch, self.api['preferences'])
            self.controller.cancel()
            self.controller.mode.reset()
            self.controller.settings = result
            self.rendered_settings = result
            if rebuild:
                self.rebuild()
            self.message('Settings Saved')
            return True
        except ValueError as error:
            failure = str(error)
        except Exception:
            failure = 'Unable To Save Settings'
        self.rebuild()
        self.message(failure)
        return False

    def rebuild(self):
        for menu, panel in self.panels:
            if not getattr(panel, 'destroyed', False) and getattr(panel, '_controller_loaded', False):
                panel.Flush()
                self.build(panel)

    def row(self, parent, height=36):
        return self.Container(parent=parent, align=self.const.TOTOP, height=height, padBottom=4)

    def button(self, parent, label, func, **kwargs):
        return self.Button(parent=parent, label=label, func=func, align=self.const.TORIGHT, padLeft=6, **kwargs)

    def choose_controller(self, combo, label, value):
        self.abort()
        self.save({'controllerIndex': value})

    def controller_options(self):
        selected = self.controller.settings['controllerIndex']
        return [('Auto-Detect', -1)] + [('Controller %d%s' % (slot + 1, ' (Connected)' if slot in self.connected else ' (Disconnected)'), slot)
                                      for slot in range(4) if slot in self.connected or slot == selected]

    def build(self, panel):
        panel._controller_loaded = True
        settings = self.controller.settings
        self.widgets = {}
        self.rendered_settings = settings
        self.Header(parent=panel, text='Controller', padTop=0)
        row = self.row(panel)
        self.widgets['selector'] = self.Combo(parent=row, align=self.const.TOLEFT, width=230, options=self.controller_options(), select=settings['controllerIndex'], callback=self.choose_controller)
        self.button(row, 'Identify Controller', self.identify)
        self.widgets['status'] = self.Label(parent=panel, align=self.const.TOTOP, text='Use A Controller Input To Identify Activity', padBottom=10)
        self.widgets['cancel'] = self.Button(parent=panel, align=self.const.TOTOP, label='Cancel Input Detection', func=self.abort, display=bool(self.capture or self.identifying), padBottom=8)
        self.Header(parent=panel, text='Camera', padTop=12)
        self.check(panel, 'invertCameraPan', 'Invert Camera Pan', 'Reverse Vertical Panning; Cursor Movement And Zoom Keep Their Direction')
        self.slider(panel, 'cameraSpeed', 'Pan Speed', 100, 4000, 50)
        self.slider(panel, 'cameraZoomSpeed', 'Zoom Speed', .1, 3., .1)
        self.Header(parent=panel, text='Cursor', padTop=12)
        self.slider(panel, 'deadzone', 'Stick Deadzone', .05, .5, .01)
        self.slider(panel, 'cursorSpeed', 'Cursor Speed (px/s)', 100, 4000, 50)
        self.check(panel, 'cursorRing', 'Circular Cursor')
        self.check(panel, 'cursorSnap', 'UI Attraction')
        self.slider(panel, 'snapRadius', 'Attraction Radius (px)', 8, 64, 1)
        self.slider(panel, 'snapMaxSpeed', 'Attraction Speed Limit (px/s)', 50, 600, 10)
        self.Header(parent=panel, text='Hold Timing', padTop=12)
        self.slider(panel, 'clickHoldMilliseconds', 'Click Hold (ms)', 200, 2000, 50)
        self.slider(panel, 'rightStickStopMilliseconds', 'Stop Hold (ms)', 500, 3000, 100)
        self.slider(panel, 'triggerThreshold', 'Trigger Activation', 10, 240, 5)
        self.Header(parent=panel, text='Bindings', padTop=12)
        self.Label(parent=panel, align=self.const.TOTOP, text='Select A Binding, Release Controls, Then Press Buttons Or Move A Stick. Hold Modifiers To Record A Combination.', padBottom=8)
        for action, title in self.api['ACTIONS']:
            row = self.row(panel, 50)
            self.Label(parent=row, align=self.const.TOPLEFT, text=title + (' (Tap)' if action == 'fly' else ' (Hold)' if action == 'stop' else ''), state=self.const.UI_DISABLED)
            self.button(row, 'Clear', self.clear_callback(action), width=55)
            control = self.Button(parent=row, align=self.const.BOTTOMLEFT, label=display_binding(settings['bindings'][action]), func=self.capture_callback(action))
            self.widgets['binding:' + action] = control
        self.Label(parent=panel, align=self.const.TOTOP, text='Rear Buttons Can Be Bound When Exposed As Independent Inputs. The Current Input Backend Exposes Standard Controller Buttons And Triggers.', padBottom=8)
        self.Header(parent=panel, text='Profiles', padTop=12)
        row = self.row(panel)
        profiles = sorted(settings['profiles'])
        if self.selected_profile not in profiles:
            self.selected_profile = profiles[0] if profiles else None
        self.widgets['profiles'] = self.Combo(parent=row, align=self.const.TOLEFT, width=200, options=[(name, name) for name in profiles] or [('No Saved Profiles', '')], select=self.selected_profile or '', callback=self.choose_profile)
        self.button(row, 'Load', self.load_profile)
        self.button(row, 'Delete', self.delete_profile)
        row = self.row(panel)
        self.widgets['profile_name'] = self.Edit(parent=row, align=self.const.TOLEFT, width=200, setvalue='', hint='Profile Name', maxLength=40)
        self.button(row, 'Save Profile', self.save_profile)
        row = self.row(panel)
        self.button(row, 'Restore Defaults', self.restore_defaults)

    def clear_callback(self, action):
        return lambda *args: self.set_binding(action, '')

    def capture_callback(self, action):
        return lambda *args: self.begin_capture(action)

    def check(self, panel, key, title, hint=''):
        self.widgets[key] = self.Checkbox(parent=panel, align=self.const.TOTOP, text=title, checked=self.controller.settings[key], hint=hint,
                                         callback=lambda control: self.save({key: bool(control.GetValue())}), padBottom=6)

    def slider(self, panel, key, title, low, high, step):
        row = self.row(panel, 44)
        value = self.controller.settings[key]
        label = self.Label(parent=row, align=self.const.TOPLEFT, text=title + ': ' + str(value), state=self.const.UI_DISABLED)
        def change(control):
            value = round(control.GetValue() / step) * step
            value = max(low, min(high, value))
            if step >= 1:
                value = int(value)
            else:
                value = round(value, 2)
            if self.save({key: value}):
                label.text = title + ': ' + str(value)
                control.SetValue(value)
        self.widgets[key] = self.Slider(parent=row, align=self.const.TOTOP, padTop=22, height=16, minValue=low, maxValue=high, value=value, isInteger=step >= 1, callback=change)

    def begin_capture(self, action):
        self.abort()
        self.capture, self.deadline = action, time.time() + 15.
        self.message('Release Controls, Then Enter A Binding')
        self.widgets['cancel'].display = True
        self.controller.cancel()

    def identify(self, *args):
        self.abort()
        self.identifying, self.deadline = True, time.time() + 15.
        self.previous = self.controller.native.scan()
        self.message('Use The Controller You Want To Select')
        self.widgets['cancel'].display = True
        self.controller.cancel()

    def abort(self, *args):
        self.capture, self.identifying, self.ready, self.collected = None, False, False, set()
        cancel = self.widgets.get('cancel')
        if cancel is not None and not getattr(cancel, 'destroyed', False):
            cancel.display = False

    def set_binding(self, action, value):
        bindings = dict(self.controller.settings['bindings'])
        bindings[action] = value
        if self.save({'bindings': bindings}, rebuild=True):
            return True
        return False

    def choose_profile(self, combo, label, value):
        self.selected_profile = value or None

    def save_profile(self, *args):
        name = self.widgets['profile_name'].GetValue().strip()
        if not name or len(name) > 40 or any(ord(c) < 32 or c in '<>&' for c in name):
            self.message('Enter A Profile Name (1-40 Characters)')
            return
        profiles = dict(self.controller.settings['profiles'])
        profiles[name] = dict((key, self.controller.settings[key]) for key in PROFILE_KEYS)
        self.selected_profile = name
        self.save({'profiles': profiles}, rebuild=True)

    def load_profile(self, *args):
        profile = self.controller.settings['profiles'].get(self.selected_profile)
        if profile:
            self.abort()
            self.save(dict((key, profile[key]) for key in PROFILE_KEYS if key in profile), rebuild=True)

    def delete_profile(self, *args):
        profiles = dict(self.controller.settings['profiles'])
        if self.selected_profile in profiles:
            profiles.pop(self.selected_profile)
            self.save({'profiles': profiles}, rebuild=True)

    def restore_defaults(self, *args):
        self.abort()
        self.save(dict((key, self.api['DEFAULTS'][key]) for key in PROFILE_KEYS), rebuild=True)

    def tick(self, now, foreground):
        detecting = bool(self.capture or self.identifying)
        if not self.visible() or not foreground:
            if detecting:
                self.abort()
                return True
            return False
        if now - self.last_scan < (0. if detecting else .2):
            return detecting
        self.last_scan = now
        pads = self.controller.native.scan()
        if set(pads) != set(self.connected):
            self.connected = pads
            self.widgets['selector'].LoadOptions(self.controller_options(), self.controller.settings['controllerIndex'])
        if self.rendered_settings != self.controller.settings and not detecting:
            self.rebuild()
        keys = getattr(self.controller.native, 'keys', set())
        if detecting and (now >= self.deadline or 27 in keys):
            self.abort()
            self.message('Input Detection Canceled')
            return True
        activity = [slot for slot, pad in pads.items() if slot in self.previous and
                    (pad[0] != self.previous[slot][0] or any(abs(pad[i] - self.previous[slot][i]) >= (12 if i >= 5 else 2000) for i in range(1, 7)))]
        self.previous = pads
        if self.identifying and activity:
            slot = activity[0]
            self.abort()
            self.save({'controllerIndex': slot}, rebuild=True)
            self.message('Controller %d Selected' % (slot + 1))
            return True
        if self.capture:
            slot = self.controller.settings['controllerIndex']
            if slot < 0:
                slot = self.controller.native.selected
            pad = pads.get(slot)
            if pad is None:
                self.abort()
                self.message('Controller Disconnected')
                return True
            mask = self.api['input_mask'](pad, self.controller.settings)
            centered = self.api['stick'](pad[1], pad[2], self.controller.settings['deadzone']) == (0., 0.) and self.api['stick'](pad[3], pad[4], self.controller.settings['deadzone']) == (0., 0.)
            if not self.ready:
                self.ready = not mask and centered
                return True
            buttons = [name for name, bit in self.api['BUTTONS'] if mask & bit]
            analog = self.capture in ('cursor', 'cameraPan', 'cameraZoom')
            if analog:
                choices = [(max(abs(pad[1]), abs(pad[2])), 'LEFT_STICK'), (max(abs(pad[3]), abs(pad[4])), 'RIGHT_STICK')]
                if self.capture == 'cameraZoom':
                    choices = [(abs(pad[2]), 'LEFT_STICK_Y'), (abs(pad[4]), 'RIGHT_STICK_Y')]
                strength, name = max(choices)
                if strength >= 16000:
                    action = self.capture
                    self.abort()
                    self.set_binding(action, '+'.join(buttons + [name]))
            else:
                self.collected.update(buttons)
                if not mask and self.collected:
                    action, names = self.capture, [name for name, bit in self.api['BUTTONS'] if name in self.collected]
                    self.abort()
                    self.set_binding(action, '+'.join(names))
            return True
        if activity and now >= self.message_until:
            self.widgets['status'].text = 'Input Detected: Controller %d' % (activity[0] + 1)
        elif not pads and now >= self.message_until:
            self.widgets['status'].text = 'No Controller Connected'
        return detecting

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.abort()
        if self.cls.__dict__.get('ConstructTreeData') is self.tree_hook:
            self.cls.ConstructTreeData = self.original_tree
        if self.cls.__dict__.get('LoadPanel') is self.load_hook:
            self.cls.LoadPanel = self.original_load
        if self.native_selection.get() == PANEL_ID:
            self.native_selection.set(self.fallback)
        for menu, panel in self.panels:
            if not getattr(panel, 'destroyed', False) and getattr(menu, 'display', False):
                self.reconstruct(menu)
            elif not getattr(panel, 'destroyed', False):
                menu.panelsByID.pop(PANEL_ID, None)
                panel.Close()
        self.panels = []


def install(controller, api):
    return ControllerSettings(controller, api)
