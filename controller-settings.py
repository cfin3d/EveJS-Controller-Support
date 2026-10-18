# Native System Menu integration for EVE client build 3396210.
# -*- coding: utf-8 -*-
import ctypes
import json
import os
import sys
import time

PANEL_ID = 'evejs-controller'
BINDING_BUTTON_WIDTH = 274
BINDING_BUTTON_HEIGHT = 40
SETTINGS_PAGES = (('General', 'general'), ('Overview', 'overview'), ('Bindings', 'bindings'), ('Profiles', 'profiles'))
BINDING_CATEGORIES = (('General Actions', 'general'), ('Custom Shortcuts', 'custom'),
                      ('Overview', 'overview'), ('Neocom', 'neocom'), ('Context Menus', 'context'),
                      ('Target Radial', 'radial'), ('Combat Modules', 'combat'))
# Group presentation separately from the runtime's action registry. New actions
# remain visible in Other Actions until they receive a more specific group.
BINDING_GROUPS = (('Cursor And Clicks', ('cursor', 'leftClick', 'rightClick')),
                  ('Camera And Flight', ('cameraPan', 'cameraZoom', 'fly', 'stop')),
                  ('Menus And Windows', ('neocom', 'overview', 'closeWindow')))
BUTTON_ICONS = dict(A='a', B='b', X='x', Y='y', LB='lb', RB='rb', LT='lt', RT='rt',
                    LS='left-stick', RS='right-stick', LEFT_STICK='left-stick', RIGHT_STICK='right-stick',
                    LEFT_STICK_Y='left-stick', RIGHT_STICK_Y='right-stick',
                    UP='dpad-up', DOWN='dpad-down', LEFT='dpad-left', RIGHT='dpad-right', VIEW='view', MENU='menu')
BUTTON_ICONS.update((name,name.lower()) for name in ('R4','L4','R5','L5','TOUCHPAD','MISC1','MISC2','MISC3','MISC4','MISC5','MISC6','GUIDE'))
PS_ICON_FILES=('cross','circle','square','triangle','l1','r1','l2','r2','l3','r3','create','share','select','start','options','ps','touchpad')
PROFILE_KEYS = ('bindings', 'customBindings', 'controllerIcons', 'controllerModeLocked', 'overviewRowExpansion', 'overviewAnimations', 'deadzone', 'cursorSpeed', 'cameraSpeed', 'cameraZoomSpeed',
                'invertCameraPan', 'cursorRing', 'cursorSnap', 'snapRadius', 'snapMaxSpeed',
                'clickHoldMilliseconds', 'rightStickStopMilliseconds', 'windowCloseHoldMilliseconds', 'triggerThreshold',
                'vibrationEnabled','vibrationStrength','damageVibration','destructionVibration',
                'damageVibrationStrength','destructionVibrationStrength','dualsenseHaptics')


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


def write_preferences(directory, patch, validate, expected=None):
    path = os.path.join(directory, 'preferences.json')
    with open(path, 'rb') as stream:
        content = stream.read(65537)
    if len(content) > 65536:
        raise ValueError('Configuration Is Too Large')
    document = json.loads(content)
    if expected is not None:
        current = validate(document)
        if any(current[key] != value for key,value in expected.items()):
            raise ValueError('Bindings Changed; Try Again')
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


def prepare_button_icons(directory):
    import blue
    icons = {}
    combat_icons = {'combat-trigger-backdrop'} | set('combat-dpad-'+direction for direction in ('up','right','down','left'))
    for name in set(BUTTON_ICONS.values()) | set('playstation/'+name for name in PS_ICON_FILES) | combat_icons:
        resource = 'cache:/evejs-controller/buttons/' + name + '.png'
        destination = blue.paths.ResolvePathForWriting(resource)
        folder = os.path.dirname(destination)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        with open(os.path.join(directory, 'assets', 'buttons', 'native', name + '.png'), 'rb') as stream:
            content = stream.read(32769)
        if len(content) > 32768 or not content.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Invalid Controller Button Icon')
        with open(destination, 'wb') as stream:
            stream.write(content)
        icons[name] = resource
    return icons


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
        from carbonui.primitives.sprite import Sprite
        from eve.client.script.ui.control.eveLabel import EveLabelSmall
        from eve.client.script.ui.shared.systemMenu.systemMenuHeader import SystemMenuHeader
        import carbonui.const as const
        class SizedButton(Button):
            # Current native Button recomputes intrinsic dimensions and ignores
            # legacy fixedwidth/fixedheight. Keep normal styling and behavior,
            # but reserve the full frame for our composite icon contents.
            def __init__(self, *args, **kwargs):
                self.controller_width = kwargs.get('width', 120)
                self.controller_height = kwargs.get('height', 36)
                Button.__init__(self, *args, **kwargs)

            def get_intrinsic_width(self):
                return self.controller_width

            def get_intrinsic_height(self):
                return self.controller_height

        self.controller, self.api, self.cls, self.const = controller, api, SystemMenu, const
        self.native_selection, self.fallback = system_menu_selected_tab_setting, PANELID_CAMERA
        self.icon = prepare_icon(controller.directory)
        self.button_icons = prepare_button_icons(controller.directory)
        self.Sprite = Sprite
        self.Scroll, self.Combo, self.Checkbox, self.Slider = ScrollContainer, Combo, Checkbox, Slider
        self.Button, self.Edit, self.Container, self.Label, self.Header = SizedButton, SingleLineEditText, Container, EveLabelSmall, SystemMenuHeader
        self.panels, self.widgets, self.connected, self.previous = [], {}, {}, {}
        self.callbacks = {}
        self.capture, self.identifying, self.ready, self.collected = None, False, False, set()
        self.deadline, self.last_scan, self.message_until = 0., -1., 0.
        self.selected_profile, self.closed, self.rendered_settings = None, False, None
        self.selected_page, self.selected_binding_category = 'general', 'general'
        self.pages, self.binding_categories = {}, {}
        self.rendered_style=None
        self.custom_draft = dict(id=None, command='', controller='')
        self.custom_category, self.custom_search = 'all', ''
        self.command_catalog, self.default_shortcuts, self.catalog_map = [], {}, None
        self.confirming = False
        self.selection_options = None
        options = getattr(self.native_selection, 'options', None)
        if isinstance(options, (tuple, list)) and PANEL_ID not in options:
            self.selection_options = options
            self.native_selection.options = type(options)(list(options) + [PANEL_ID])
        self.original_tree, self.original_load = SystemMenu.__dict__['ConstructTreeData'], SystemMenu.__dict__['LoadPanel']
        manager = self

        def construct(menu, *args, **kwargs):
            result = manager.original_tree(menu, *args, **kwargs)
            if not manager.closed:
                previous = menu.panelsByID.get(PANEL_ID)
                if previous is not None and not getattr(previous, 'destroyed', False):
                    previous.Close()
                panel = manager.Container(name=PANEL_ID, parent=menu.panelCont, align=manager.const.TOALL, display=False)
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
        tree = getattr(menu, 'menuTreeData', None)
        if callable(getattr(tree, 'RemoveChild', None)):
            for child in list(tree.children):tree.RemoveChild(child)
        menu.ReconstructLayout(selected)

    def visible(self):
        return any(not getattr(panel, 'destroyed', False) and getattr(menu, 'display', False) and getattr(panel, 'display', False) for menu, panel in self.panels)

    def message(self, text):
        self.message_until = time.time() + 3.
        status = self.widgets.get('status')
        if status is not None and not getattr(status, 'destroyed', False):
            status.text = text

    def save(self, patch, rebuild=False, expected=None):
        try:
            result = write_preferences(self.controller.directory, patch, self.api['preferences'], expected)
            self.controller.cancel()
            self.controller.mode.reset()
            self.controller.settings = result
            if getattr(self.controller,'feedback',None):self.controller.feedback.stop()
            self.rendered_settings = result
            if rebuild:
                self.rebuild()
            else:
                self.refresh_binding_details()
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
        return self.Container(parent=parent, align=self.const.TOTOP, height=height, padBottom=8)

    def pair(self, panel, fields):
        row = self.row(panel, 54)
        cells = [self.Container(parent=row, align=self.const.TOLEFT_PROP, width=.5, padRight=12),
                 self.Container(parent=row, align=self.const.TOALL, padLeft=12)]
        for cell, field in zip(cells, fields):
            self.slider(cell, *field)

    def button(self, parent, label, func, **kwargs):
        width = kwargs.pop('width', max(64, min(184, len(label) * 7 + 24)))
        height = kwargs.pop('height', 36)
        cell = self.Container(parent=parent, align=self.const.TORIGHT, width=width+6)
        return self.Button(parent=cell, label=label, func=func, align=self.const.CENTER,
                           width=width, height=height, **kwargs)

    def choose_controller(self, combo, label, value):
        self.abort()
        self.save({'controllerIndex': value})

    def controller_options(self):
        selected = self.controller.settings['controllerIndex']
        devices=getattr(getattr(self.controller.native,'devices',None),'metadata',{})
        return [('Auto-Detect', -1)] + [('%s%s' % (('Controller %d: '%(slot+1)+devices[slot]['name']) if slot in devices else 'Controller %d'%(slot+1), ' (Connected)' if slot in self.connected else ' (Disconnected)'), slot)
                                      for slot in range(16) if slot in self.connected or slot == selected]

    def current_style(self):
        function=self.controller.helpers.get('_ec_controller_style')
        return (function(self.controller) if function else 'xbox',getattr(self.controller.native,'device_info',lambda:{})().get('kind',''))

    def binding_title(self,value):
        function=self.controller.helpers.get('_ec_button_name')
        return function(self.controller,value) if function else display_binding(value)

    def icon_name(self,token):
        function=self.controller.helpers.get('_ec_button_icon')
        return function(self.controller,token) if function else BUTTON_ICONS[token]

    def build(self, panel):
        panel._controller_loaded = True
        settings = self.controller.settings
        self.widgets = {}
        self.callbacks = {}
        self.rendered_settings = settings
        self.rendered_style=self.current_style()
        self.pages, self.binding_categories = {}, {}
        self.navigation(panel, 'Settings Page', SETTINGS_PAGES, self.selected_page, self.choose_page, 'page_selector')
        # Activity and capture cancellation stay reachable above every page's
        # independent scroll area, even when editing a long list of shortcuts.
        self.widgets['status'] = self.Label(parent=panel, align=self.const.TOTOP, text='Use A Controller Input To Identify Activity', padBottom=10)
        cancel_row = self.row(panel)
        self.widgets['cancel'] = cancel_row
        cancel_row.display = bool(self.capture or self.identifying)
        self.button(cancel_row, 'Cancel Input Detection', self.abort, width=184)
        root = panel
        for title, identity in SETTINGS_PAGES:
            self.pages[identity] = self.Container(parent=root, align=self.const.TOALL, display=identity == self.selected_page)
        # Each scroll owns only its page; hidden pages reserve no layout space.
        def page(identity):
            return self.Scroll(parent=self.pages[identity], align=self.const.TOALL)
        panel = page('general')
        self.Header(parent=panel, text='Input Device', padTop=0)
        row = self.row(panel)
        self.widgets['selector'] = self.Combo(parent=row, align=self.const.TOLEFT, width=230, options=self.controller_options(), select=settings['controllerIndex'], callback=self.choose_controller)
        self.button(row, 'Identify Controller', self.identify)
        row=self.row(panel)
        self.Label(parent=row,align=self.const.CENTERLEFT,text='Button Icons',state=self.const.UI_DISABLED)
        self.Combo(parent=row,align=self.const.TORIGHT,width=230,options=[('Auto-Detect','auto'),('Xbox','xbox'),('PlayStation 4','ps4'),('PlayStation 5','ps5'),('Steam','steam')],select=settings.get('controllerIcons','auto'),callback=lambda combo,label,value:self.save({'controllerIcons':value},rebuild=True))
        self.check(panel, 'controllerModeLocked', 'Lock Controller Mode',
                   'Keep Controller Mode, Navigation Focus And Holds Active During Mouse Or Keyboard Use')
        backend=getattr(self.controller.native,'device_info',lambda:{})().get('backend','XInput')
        self.Label(parent=panel,align=self.const.TOTOP,text='Input Backend: '+backend,padBottom=8,state=self.const.UI_DISABLED)
        self.Header(parent=panel, text='Camera', padTop=12)
        self.pair(panel, [('cameraSpeed','Pan / Scroll Speed',100,4000,50),('cameraZoomSpeed','Zoom Speed',.1,3.,.1)])
        self.check(panel, 'invertCameraPan', 'Invert Camera Pan', 'Reverse Vertical Panning; Cursor Movement And Zoom Keep Their Direction')
        self.Header(parent=panel, text='Cursor', padTop=12)
        self.pair(panel, [('deadzone','Stick Deadzone',.05,.5,.01),('cursorSpeed','Cursor Speed (px/s)',100,4000,50)])
        self.check(panel, 'cursorRing', 'Circular Cursor')
        self.check(panel, 'cursorSnap', 'UI Attraction')
        self.pair(panel, [('snapRadius','Attraction Radius (px)',8,64,1),('snapMaxSpeed','Attraction Speed Limit (px/s)',50,600,10)])
        self.Header(parent=panel, text='Hold Timing', padTop=12)
        self.pair(panel, [('clickHoldMilliseconds','Click / Activation Hold (ms)',200,2000,50),('rightStickStopMilliseconds','Stop Hold (ms)',500,3000,100)])
        self.pair(panel, [('triggerThreshold','Trigger Activation',10,240,5),('windowCloseHoldMilliseconds','Window Close Hold (ms)',500,3000,100)])
        self.Header(parent=panel,text='Vibration',padTop=12)
        self.check(panel,'vibrationEnabled','Enable Vibration','Turn All Controller Feedback On Or Off')
        self.pair(panel,[('vibrationStrength','Overall Strength',0.,1.,.05)])
        self.check(panel,'damageVibration','Incoming Damage Feedback')
        self.check(panel,'destructionVibration','Ship Destruction Feedback')
        self.pair(panel,[('damageVibrationStrength','Damage Strength',0.,1.,.05),('destructionVibrationStrength','Destruction Strength',0.,1.,.05)])
        self.check(panel,'dualsenseHaptics','Enhanced DualSense Haptics (USB)','Connect A DualSense Directly By USB For Detailed Feedback; Uses Standard Vibration If Enhanced Output Is Unavailable')
        row=self.row(panel)
        self.button(row,'Stop Vibration',self.stop_vibration,width=120)
        self.button(row,'Test Vibration',self.test_vibration,width=120)
        self.widgets['feedback_status']=self.Label(parent=panel,align=self.const.TOTOP,text=self.feedback_status(),padBottom=8,state=self.const.UI_DISABLED)
        panel = page('overview')
        self.Header(parent=panel, text='Overview', padTop=0)
        self.pair(panel, [('overviewRowExpansion','Focused Row Extra Height',0,64,2)])
        self.check(panel, 'overviewAnimations', 'Smooth Overview Transitions', 'Disable For Immediate Row And Cursor Movement')
        self.build_bindings(self.pages['bindings'])
        panel = page('profiles')
        self.Header(parent=panel, text='Profiles', padTop=0)
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
        self.Header(parent=panel, text='Defaults', padTop=12)
        self.button(self.row(panel), 'Restore Defaults', self.restore_defaults)

    def navigation(self, panel, title, options, selected, callback, key):
        row = self.row(panel)
        self.Label(parent=row, align=self.const.CENTERLEFT, text=title, state=self.const.UI_DISABLED)
        self.widgets[key] = self.Combo(parent=row, align=self.const.TORIGHT, width=274,
                                       options=list(options), select=selected, callback=callback)

    def choose_page(self, combo, label, value):
        self.abort()
        feedback = getattr(self.controller, 'feedback', None)
        if feedback: feedback.stop()
        self.selected_page = value
        for identity, panel in self.pages.items():
            panel.display = identity == value
        if value == 'bindings' and self.selected_binding_category == 'custom': self.refresh_catalog()

    def choose_binding_category(self, combo, label, value):
        self.abort()
        self.selected_binding_category = value
        for identity, panel in self.binding_categories.items():
            panel.display = identity == value
        if value == 'custom': self.refresh_catalog()

    def binding_headings(self, panel):
        headings = self.row(panel, 20)
        action = self.Container(parent=headings, align=self.const.TOLEFT_PROP, width=.43, padRight=12)
        self.Label(parent=action, align=self.const.TOTOP, text='<b>Function</b>')
        self.Label(parent=headings, align=self.const.TOALL, text='<b>Controller Input</b>')

    def action_detail(self, action):
        hold = self.controller.settings['clickHoldMilliseconds']
        return dict(cursor='Move Freely; Also Moves Within Focused Menus',
                    leftClick='Hold %d ms: Click / Drag Or Open A Target Radial' % hold,
                    rightClick='Hold %d ms: Open A Native Context Menu' % hold,
                    cameraPan='Pan Camera, Scroll Windows Or Pan Map / Ship Tree',
                    cameraZoom='Up: Zoom In; Down: Zoom Out',
                    fly='Short Press, Then Release; Paused In Focused Menus',
                    stop='Hold %d ms; Paused In Focused Menus' % self.controller.settings['rightStickStopMilliseconds'],
                    neocom='Press To Open; Press Again To Close',
                    overview='Press To Focus The Existing Overview',
                    closeWindow='Hold %d ms, Then Release To Close' % self.controller.settings['windowCloseHoldMilliseconds']).get(action, '')

    def refresh_binding_details(self):
        for action, title in self.api['ACTIONS']:
            label = self.widgets.get('binding:'+action+':detail')
            if label is not None:
                label.text = label.hint = self.action_detail(action)
        for title, category in BINDING_CATEGORIES[2:]:
            for key, title, value, detail in self.context_bindings(category):
                label = self.widgets.get('reference:'+category+':'+key+':detail')
                if label is not None:
                    label.text = label.hint = detail

    def build_bindings(self, root):
        self.navigation(root, 'Binding Category', BINDING_CATEGORIES, self.selected_binding_category,
                        self.choose_binding_category, 'binding_category')
        for title, identity in BINDING_CATEGORIES:
            self.binding_categories[identity] = self.Scroll(parent=root, align=self.const.TOALL,
                                                            display=identity == self.selected_binding_category)
        panel = self.binding_categories['general']
        self.Label(parent=panel, align=self.const.TOTOP,
                   text='Select An Input To Rebind. Hold Modifiers While Entering A Combination.', padBottom=12)
        self.binding_headings(panel)
        actions = dict(self.api['ACTIONS'])
        groups = list(BINDING_GROUPS)
        remaining = tuple(action for action, title in self.api['ACTIONS'] if not any(action in keys for title, keys in groups))
        if remaining: groups.append(('Other Actions', remaining))
        for title, keys in groups:
            self.Header(parent=panel, text=title, padTop=12)
            for action in keys:
                if action not in actions: continue
                self.binding_row(panel, actions[action], self.controller.settings['bindings'][action],
                                 self.capture_callback(action), self.clear_callback(action), 'binding:'+action,
                                 detail=self.action_detail(action))
        panel = self.binding_categories['custom']
        self.Header(parent=panel, text='Custom Shortcuts', padTop=0)
        self.Label(parent=panel, align=self.const.TOTOP,
                   text='Choose An EVE Action Or Keyboard Shortcut, Then Assign A Controller Input. Up To 32 Bindings.', padBottom=12)
        self.binding_headings(panel)
        settings = self.controller.settings
        if not settings['customBindings']:
            self.Label(parent=panel, align=self.const.TOTOP, text='No Custom Shortcuts Yet', padBottom=12)
        for item in settings['customBindings']:
            try:command=self.resolve_custom(item)
            except Exception:command=None
            title=command.GetDescription() if command and command.name==item['command'] else item['command']
            self.binding_row(panel,title,item['controller'],self.edit_custom_callback(item),
                             self.remove_custom_callback(item['id']),'custom:'+item['id'],'Remove',
                             detail=('EVE Action' if 'modifier' not in item else self.shortcut_title(item))+'; Select The Input To Edit')
        self.Header(parent=panel, text='Edit Shortcut' if self.custom_draft['id'] else 'Add Shortcut', padTop=12)
        self.build_custom_editor(panel)
        self.Label(parent=panel, align=self.const.TOTOP, text='Rear Buttons And Touchpad Clicks Can Be Bound When Exposed As Independent Inputs.', padBottom=8)
        for title, identity in BINDING_CATEGORIES[2:]:
            panel = self.binding_categories[identity]
            self.Header(parent=panel, text=title, padTop=0)
            self.Label(parent=panel, align=self.const.TOTOP,
                       text='Context Controls Are Fixed Unless Marked As A Shared General Action. / Means Either Input.', padBottom=12)
            if identity == 'combat':
                self.Label(parent=panel, align=self.const.TOTOP,
                           text='Assigned Slots Only. Tap: Activate / Deactivate / Offline / Online. Hold 1,000 ms: Toggle Overload. Assign Modules By Dragging From Fitting.', padBottom=12)
            self.binding_headings(panel)
            for key, title, value, detail in self.context_bindings(identity):
                if identity == 'combat' and key in ('slot-1', 'slot-9'):
                    self.Header(parent=panel, text='Left Trigger Bank' if key == 'slot-1' else 'Right Trigger Bank', padTop=12)
                self.reference_row(panel, title, value, detail, 'reference:'+identity+':'+key)

    def context_bindings(self, category):
        settings = self.controller.settings
        bindings = settings['bindings']
        hold = 'Hold %d ms' % settings['clickHoldMilliseconds']
        cursor = ('cursor', 'Move Cursor / Leave Focus', bindings['cursor'],
                  'Shared Move Cursor Action; Move Outside The Window Or Menu To Leave Focus')
        browse = ('browse', 'Browse Items', 'UP/DOWN', 'Press Immediately; Hold To Repeat')
        enter = ('enter', 'Enter Submenu', 'RIGHT', 'Press')
        back = ('back', 'Return To Parent Menu', 'LEFT', 'Press')
        select = ('select', 'Select Highlighted Item', 'RB', hold)
        cancel = ('cancel', 'Close Menu', 'B', hold)
        if category == 'overview':
            return [('focus', 'Focus Overview', bindings['overview'], 'Shared Focus Overview Action; Press'),
                    browse, ('tabs', 'Previous / Next Tab', 'LB/RB', 'Tap, Then Release'),
                    ('menu', 'Open Object Context Menu', 'LB', hold),
                    ('lock', 'Lock Target', 'X', 'Hold 500 ms; Requires An Available Native Action'),
                    ('orbit', 'Orbit Object', 'Y', 'Hold 500 ms; Requires An Available Native Action'),
                    ('approach', 'Approach Object', 'A', 'Hold 500 ms; Requires An Available Native Action'),
                    ('track', 'Track Object', 'B', 'Hold 500 ms, Then Release Before 1,000 ms'),
                    ('exit', 'Exit Overview Focus', 'B', 'Hold 1,000 ms'), cursor]
        if category == 'neocom':
            return [('open', 'Open / Close Neocom', bindings['neocom'], 'Shared Open Neocom Action; Press'),
                    browse, enter, back, select, cancel, cursor]
        if category == 'context':
            return [browse, enter, back, select, cancel, cursor]
        if category == 'radial':
            activation = bindings['leftClick'].split('+')
            cancel_input = next(name for name in ('B', 'A', 'X', 'Y', 'LS') if name not in activation)
            axis = 'UP' in activation or 'DOWN' in activation
            return [('open', 'Open Target Radial', bindings['leftClick'], 'Shared Left-Click Action; '+hold+' Over A Valid Target'),
                    ('wedge', 'Choose Wedge / More', 'LEFT_STICK', 'Move Toward An Action; Hold Toward More For Additional Options'),
                    ('range', 'Increase / Decrease Range', 'RIGHT_STICK_Y' if axis else 'UP/DOWN',
                     'Uses Right Stick When The Activation Binding Includes D-Pad Up Or Down' if axis else 'Adjust The Highlighted Range Action'),
                    ('confirm', 'Execute Highlighted Action', bindings['leftClick'], 'Release The Activation Input; No Selection Cancels'),
                    ('cancel', 'Cancel Radial', cancel_input, 'Press Immediately; Adapts To The Activation Binding')]
        if category == 'combat':
            return [('slot-%d' % (bank*8+index+1), 'Module Slot %d' % (bank*8+index+1), trigger+'+'+button,
                     'Tap: Cycle State; Hold 1,000 ms: Overload')
                    for bank, trigger in enumerate(('LT', 'RT'))
                    for index, button in enumerate(('UP', 'RIGHT', 'DOWN', 'LEFT', 'Y', 'B', 'A', 'X'))]
        return []

    def clear_callback(self, action):
        return lambda *args: self.set_binding(action, '')

    def feedback_status(self):
        feedback=getattr(self.controller,'feedback',None)
        if not self.controller.settings['vibrationEnabled']:return 'Vibration: Disabled'
        return 'Vibration: '+(feedback.status if feedback else 'Unavailable')

    def test_vibration(self,*args):
        if self.capture or self.identifying:self.message('Finish Input Detection Before Testing');return
        feedback=getattr(self.controller,'feedback',None)
        self.message(feedback.test() if feedback else 'Vibration Unavailable')

    def stop_vibration(self,*args):
        feedback=getattr(self.controller,'feedback',None)
        if feedback:feedback.stop()
        self.message('Vibration Stopped')

    def capture_callback(self, action):
        return lambda *args: self.begin_capture(action)

    def binding_label(self, panel, title, detail, widget_key):
        label_cell = self.Container(parent=panel, align=self.const.TOLEFT_PROP, width=.43, padRight=12)
        self.Label(parent=label_cell, align=self.const.TOTOP, padTop=4, maxLines=2, text=title,
                   hint=title, state=self.const.UI_DISABLED)
        if detail:
            self.widgets[widget_key+':detail'] = self.Label(parent=label_cell, align=self.const.TOTOP, padTop=3, maxLines=2, text=detail,
                                                           hint=detail, fontsize=11, color=(1.,1.,1.,.65), state=self.const.UI_DISABLED)

    def binding_row(self, panel, title, value, capture, clear, widget_key, clear_label='Clear', detail=''):
        row = self.row(panel, 76 if detail else 48)
        self.binding_label(row, title, detail, widget_key)
        inputs = self.Container(parent=row, align=self.const.TOALL)
        self.button(inputs, clear_label, clear, width=56 if clear_label=='Clear' else 68,height=BINDING_BUTTON_HEIGHT)
        self.widgets[widget_key] = self.input_button(inputs, value, capture)

    def reference_row(self, panel, title, value, detail, widget_key):
        row = self.row(panel, 76)
        self.binding_label(row, title, detail, widget_key)
        inputs = self.Container(parent=row, align=self.const.TOALL)
        hint = ' / '.join(self.binding_title(part) for part in value.split('/')) if value else 'Disabled'
        control = self.Container(parent=inputs, align=self.const.CENTERLEFT, width=BINDING_BUTTON_WIDTH,
                                 height=BINDING_BUTTON_HEIGHT, hint=hint)
        self.widgets[widget_key] = control
        self.input_contents(control, value, 'Disabled', '/' if '/' in value else '+')

    def input_button(self, parent, value, callback, empty='Disabled'):
        control = self.Button(parent=parent, align=self.const.CENTERLEFT, width=BINDING_BUTTON_WIDTH, height=BINDING_BUTTON_HEIGHT,
                              label='' if value else empty,
                              hint=self.binding_title(value) if value else empty, func=callback)
        if value:
            self.input_contents(control, value, empty)
        return control

    def input_contents(self, control, value, empty, separator='+'):
        tokens = value.split(separator) if value else []
        icon_size = 30
        width = len(tokens) * icon_size + max(0,len(tokens)-1) * 16 + (58 if tokens and tokens[-1].endswith('_Y') else 0)
        if not value:
            self.Label(parent=control, align=self.const.CENTER, text=empty, state=self.const.UI_DISABLED)
            return
        contents = self.Container(parent=control, align=self.const.CENTER, width=width, height=30,
                                  state=self.const.UI_DISABLED)
        left = 0
        for index, token in enumerate(tokens):
            if index:
                self.Label(parent=contents, align=self.const.CENTERLEFT, left=left, width=16,
                           text=separator, state=self.const.UI_DISABLED, color=(1.,1.,1.,1.))
                left += 16
            self.Sprite(parent=contents, align=self.const.CENTERLEFT, left=left, width=icon_size, height=icon_size,
                        texturePath=self.button_icons[self.icon_name(token)], state=self.const.UI_DISABLED,
                        color=(1.,1.,1.,1.))
            left += icon_size
            if token.endswith('_Y'):
                self.Label(parent=contents, align=self.const.CENTERLEFT, left=left+4, width=54,
                           text='Up/Down', state=self.const.UI_DISABLED, color=(1.,1.,1.,1.))

    def check(self, panel, key, title, hint=''):
        self.widgets[key] = self.Checkbox(parent=panel, align=self.const.TOTOP, text=title, checked=self.controller.settings[key], hint=hint,
                                         callback=lambda control: self.save({key: bool(control.GetValue())}), padBottom=6)

    def slider(self, panel, key, title, low, high, step):
        row = self.row(panel, 50)
        value = self.controller.settings[key]
        self.Label(parent=row, align=self.const.TOPLEFT, text=title, state=self.const.UI_DISABLED)
        track = self.Container(parent=row, align=self.const.TOTOP, height=24, padTop=22)
        label = self.Label(parent=track, align=self.const.TOPRIGHT, top=2, width=52, text=self.format_value(key,value), state=self.const.UI_DISABLED)
        def change(control):
            value = round(control.GetValue() / step) * step
            value = max(low, min(high, value))
            if step >= 1:
                value = int(value)
            else:
                value = round(value, 2)
            if self.save({key: value}):
                label.text = self.format_value(key,value)
                control.SetValue(value)
        # Native Signal stores functions weakly; retain each closure for this panel.
        self.callbacks[key] = change
        self.widgets[key] = self.Slider(parent=track, align=self.const.TOTOP, padTop=4, padRight=64, height=16, minValue=low, maxValue=high, value=value, isInteger=step >= 1, callback=change)

    def format_value(self,key,value):
        return '%d%%' % round(value*100) if key in ('deadzone','vibrationStrength','damageVibrationStrength','destructionVibrationStrength') else ('%.2f'%value).rstrip('0').rstrip('.')

    def shortcut_title(self,item):
        if 'modifier' not in item:
            try:command=self.resolve_custom(item)
            except Exception:command=None
            return command.GetDescription() if command else item['command']
        return (item['modifier'].replace('+',' + ')+' + ' if item['modifier']!='NONE' else '')+item['key']

    def build_custom_editor(self,panel):
        draft=self.custom_draft
        method = 'shortcut' if 'modifier' in draft else 'action'
        self.navigation(panel, 'Binding Method', (('EVE Action','action'),('Keyboard Shortcut (Advanced)','shortcut')),
                        method, self.custom_method, 'custom_method')
        if method == 'action':
            self.build_action_picker(panel)
        else:
            self.build_keyboard_picker(panel)
        self.widgets['custom_action']=self.Label(parent=panel,align=self.const.TOTOP,text='',padTop=4,padBottom=12)
        row=self.row(panel,48)
        self.button(row,'Save Binding' if draft['id'] else 'Add Binding',self.add_custom,width=112,height=BINDING_BUTTON_HEIGHT)
        self.widgets['custom_input']=self.input_button(row,draft['controller'],self.capture_callback('custom:draft'),'Choose Input')
        if draft['id']:
            self.button(self.row(panel),'Cancel Editing',self.reset_custom,width=128)
        self.refresh_custom_action()

    def build_keyboard_picker(self,panel):
        draft=self.custom_draft
        row=self.row(panel,58)
        left=self.Container(parent=row,align=self.const.TOLEFT_PROP,width=.5,padRight=12)
        right=self.Container(parent=row,align=self.const.TOALL,padLeft=12)
        self.Label(parent=left,align=self.const.TOTOP,text='Modifier',padBottom=6)
        self.Label(parent=right,align=self.const.TOTOP,text='Keyboard Key',padBottom=6)
        self.widgets['custom_modifier']=self.Combo(parent=left,align=self.const.TOTOP,options=[(title,value) for title,value,codes in self.api['SHORTCUT_MODIFIERS']],select=draft['modifier'],callback=self.custom_modifier)
        self.widgets['custom_key']=self.Combo(parent=right,align=self.const.TOTOP,options=[(key,key) for key,code in self.api['SHORTCUT_KEYS']],select=draft['key'],callback=self.custom_key)

    def load_catalog(self):
        service = getattr(self.controller.ui, 'cmd', None)
        mapping = getattr(service, 'commandMap', None)
        self.command_catalog = []
        if mapping is None: return
        # The native factories return fresh mappings. The service's existing
        # defaultShortcutMapping has already been mutated by player remaps.
        if mapping is not self.catalog_map:
            self.default_shortcuts = {}
            for factory in ('SetDefaultShortcutMappingCORE','SetDefaultShortcutMappingGAME'):
                try:
                    for command in getattr(service, factory)():
                        self.default_shortcuts[command.name] = command.GetShortcutAsString() or 'Unassigned'
                except Exception: pass
            self.catalog_map = mapping
        try:commands = mapping.GetAllCommands()
        except Exception:return
        categories = dict(window='Windows',combat='Combat',general='General',navigation='Navigation',
                          modules='Modules',drones='Drones',fighters='Fighters',charactercreator='Character Creation')
        try:
            from eve.client.script.ui.shared.systemMenu.systemMenuConst import NAME_BY_PANELID
            from localization import GetByLabel
            categories.update((key,GetByLabel(path)) for key,path in NAME_BY_PANELID.items() if key in categories)
        except Exception:pass
        for command in commands:
            name = command.name
            try:
                if not getattr(service,'IsCommandAllowed',lambda name:True)(name):continue
            except Exception:continue
            try:title = command.GetDescription() or name
            except Exception:title=name
            category = getattr(command,'category',None) or 'general'
            description = ''
            try:description = command.GetDetailedDescription() or ''
            except Exception:pass
            if not description and getattr(command,'hint',None):
                try:
                    from localization import GetByLabel
                    description = GetByLabel(command.hint)
                except Exception:pass
            try:current = command.GetShortcutAsString() or 'Unassigned'
            except Exception:current = 'Unavailable'
            self.command_catalog.append(dict(name=name,title=title,category=category,
                categoryTitle=categories.get(category,category.replace('_',' ').title()),
                description=description or self.describe_action(name,category,title),
                current=current,default=self.default_shortcuts.get(name,'Unavailable')))
        self.command_catalog.sort(key=lambda item:(item['categoryTitle'].lower(),item['title'].lower(),item['name']))

    def describe_action(self,name,category,title):
        descriptions=dict(
            CmdAlignToItem='Align The Ship Toward The Selected Object Without Entering Warp.',
            CmdApproachItem='Fly Toward The Selected Object.',
            CmdOrbitItem='Orbit The Selected Object At The Configured Orbit Distance.',
            CmdKeepItemAtRange='Keep The Configured Distance From The Selected Object.',
            CmdWarpToItem='Request Warp To The Selected Object When Available.',
            CmdDockOrJumpOrActivateGate='Use The Selected Station, Stargate Or Acceleration Gate.',
            CmdLockTargetItem='Request A Target Lock On The Selected Object.',
            CmdUnlockTargetItem='Unlock The Selected Target.',
            CmdUnlockTargetItems='Unlock All Currently Locked Targets.',
            CmdSelectTargetItem='Select The Highlighted Object As The Active Target.',
            CmdShowItemInfo='Show Information About The Selected Object.',
            CmdToggleLookAtItem='Move The Camera To Or From The Selected Object.',
            CmdRefreshDirectionalScan='Run A Directional Scan Using The Scanner Settings.',
            CmdRefreshProbeScan='Run A Probe Scan Using The Current Probe Setup.',
            CmdIncreaseProbeScanRange='Increase The Active Probe Formation Scan Range.',
            CmdDecreaseProbeScanRange='Decrease The Active Probe Formation Scan Range.',
            CmdDronesEngage='Order Drones To Engage The Selected Target.',
            CmdDronesReturnAndOrbit='Recall Drones To Orbit The Ship.',
            CmdDronesReturnToBay='Recall Drones Into The Ship Drone Bay.',
            CmdReconnectToDrones='Attempt To Reconnect To Lost Drones In Space.',
            CmdStopShip='Request That The Ship Stop.',
            CmdSetShipFullSpeed='Set The Ship To Full Speed.',
            CmdSelectNextTarget='Select The Next Locked Target.',
            CmdSelectPrevTarget='Select The Previous Locked Target.')
        if name in descriptions:return descriptions[name]
        if category=='window' and name.startswith(('Open','Toggle')):return 'Open Or Toggle: '+title+'.'
        if name.startswith('CmdActivate') and category=='modules':return 'Use The Native Module Activation Command For This Power Slot.'
        if name.startswith('CmdOverload'):return 'Toggle Overheating For This Module Slot Or Rack; Native Restrictions Apply.'
        if name.startswith('CmdTagItem_'):return 'Apply Or Clear The Named Overview Tag On The Selected Object.'
        if name.startswith(('CmdFleetBroadcast_','CmdSendBroadcast_')):return 'Send The Named Fleet Broadcast To The Current Recipients.'
        return 'Runs This EVE Function Once Per Controller Press; Native Availability Rules Apply.'

    def build_action_picker(self,panel):
        self.load_catalog()
        categories=sorted(set((item['categoryTitle'],item['category']) for item in self.command_catalog))
        if self.custom_category not in [key for title,key in categories]:self.custom_category='all'
        self.navigation(panel,'Action Category',[('All Categories','all')]+categories,
                        self.custom_category,self.custom_action_category,'custom_category')
        self.Label(parent=panel,align=self.const.TOTOP,text='Search Functions And Descriptions',padBottom=6)
        row=self.row(panel)
        self.button(row,'Search',self.search_custom,width=80)
        self.button(row,'Refresh',self.refresh_catalog,width=80)
        self.widgets['custom_search']=self.Edit(parent=row,align=self.const.TOALL,setvalue=self.custom_search,
                                               hint='Search Functions And Descriptions',maxLength=80)
        self.widgets['custom_search'].OnReturn=self.search_custom
        self.Label(parent=panel,align=self.const.TOTOP,text='EVE Function',padBottom=6)
        self.widgets['custom_function']=self.Combo(parent=panel,align=self.const.TOTOP,options=self.action_options(),
            select=self.custom_draft.get('command',''),callback=self.choose_custom_action,padBottom=8)
        self.widgets['custom_description']=self.Label(parent=panel,align=self.const.TOTOP,text='',padBottom=8)
        self.widgets['custom_shortcuts']=self.Label(parent=panel,align=self.const.TOTOP,text='',padBottom=8)
        self.widgets['custom_count']=self.Label(parent=panel,align=self.const.TOTOP,text='',padBottom=8)

    def action_options(self):
        query=self.custom_search.lower().split()
        self.filtered_actions=[item for item in self.command_catalog
            if (self.custom_category=='all' or item['category']==self.custom_category)
            and all(word in ' '.join((item['title'],item['description'],item['categoryTitle'],item['current'],item['default'],item['name'])).lower() for word in query)]
        options=[('Choose An EVE Function','')]+[(item['categoryTitle']+' / '+item['title'],item['name']) for item in self.filtered_actions]
        selected=self.custom_draft.get('command','')
        if selected and selected not in [value for title,value in options]:
            item=next((item for item in self.command_catalog if item['name']==selected),None)
            options.append(((item['title']+' (Selected)') if item else selected+' (Unavailable)',selected))
        return options

    def refresh_catalog(self,*args):
        if 'custom_function' not in self.widgets:return
        self.load_catalog()
        categories=sorted(set((item['categoryTitle'],item['category']) for item in self.command_catalog))
        if self.custom_category not in [key for title,key in categories]:self.custom_category='all'
        self.widgets['custom_category'].LoadOptions([('All Categories','all')]+categories,self.custom_category)
        self.refresh_action_options()

    def refresh_action_options(self):
        self.widgets['custom_function'].LoadOptions(self.action_options(),self.custom_draft.get('command',''))
        self.refresh_custom_action()

    def custom_action_category(self,combo,label,value):
        self.abort()
        self.custom_category=value
        self.refresh_action_options()

    def search_custom(self,*args):
        self.abort()
        self.custom_search=self.widgets['custom_search'].GetValue().strip()
        self.refresh_action_options()

    def choose_custom_action(self,combo,label,value):
        self.abort()
        self.custom_draft['command']=value
        self.refresh_custom_action()

    def custom_method(self,combo,label,value):
        self.abort()
        old=self.custom_draft
        self.custom_draft=dict(id=old['id'],controller=old['controller'])
        self.custom_draft.update(dict(modifier='NONE',key='F1') if value=='shortcut' else dict(command=''))
        self.rebuild()

    def custom_modifier(self,combo,label,value):
        self.custom_draft['modifier']=value
        self.refresh_custom_action()

    def custom_key(self,combo,label,value):
        self.custom_draft['key']=value
        self.refresh_custom_action()

    def resolve_custom(self,item):
        if 'modifier' not in item:
            service=self.controller.ui.cmd
            command=service.commandMap.GetCommandByName(item.get('command',''))
            return command if command and getattr(service,'IsCommandAllowed',lambda name:True)(command.name) else None
        function=self.controller.helpers.get('_ec_custom_command')
        return function(self.controller.ui,item['modifier'],item['key']) if function else None

    def refresh_custom_action(self):
        if 'modifier' not in self.custom_draft:
            item=next((item for item in self.command_catalog if item['name']==self.custom_draft.get('command')),None)
            self.widgets['custom_description'].text=item['description'] if item else 'Choose A Function To See Its Description'
            self.widgets['custom_shortcuts'].text=('Current Shortcut: '+item['current']+'    Default Shortcut: '+item['default']) if item else ''
            self.widgets['custom_count'].text='%d Matching Functions / %d Total; Includes Unassigned Shortcuts' % (len(self.filtered_actions),len(self.command_catalog))
            self.widgets['custom_action'].text='Action: '+item['title'] if item else 'Choose An Available EVE Function'
            return
        try:command=self.resolve_custom(self.custom_draft)
        except Exception:command=None
        self.widgets['custom_action'].text='Action: '+command.GetDescription() if command else 'Assign This Shortcut In Settings → Shortcuts First'

    def reset_custom(self,*args):
        self.abort()
        self.custom_draft=dict(id=None,command='',controller='')
        self.custom_search,self.custom_category='','all'
        self.rebuild()

    def edit_custom_callback(self,item):
        def edit(*args):
            self.abort()
            self.custom_draft=dict(item)
            self.custom_search,self.custom_category='','all'
            self.rebuild()
        return edit

    def remove_custom_callback(self,identity):
        def remove(*args):
            self.abort()
            if self.custom_draft['id']==identity:
                self.custom_draft=dict(id=None,command='',controller='')
            return self.save({'customBindings':[item for item in self.controller.settings['customBindings'] if item['id']!=identity]},rebuild=True)
        return remove

    def add_custom(self,*args):
        if self.capture or self.identifying:
            self.message('Finish Input Detection First')
            return False
        draft=dict(self.custom_draft)
        try:command=self.resolve_custom(draft)
        except Exception:command=None
        if command is None:
            self.message('Assign This Shortcut In Settings → Shortcuts First' if 'modifier' in draft else 'Choose An Available EVE Function')
            return False
        if not draft['controller']:
            self.message('Choose Controller Input First')
            return False
        draft['command']=command.name
        if self.commit_binding(None,draft['controller'],draft):
            self.reset_custom()
            return True
        return False

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
        if len(value.split('+'))>4:
            self.message('Use At Most Four Inputs Per Combination');return False
        try:value=self.api['binding'](value,action if action!='custom:draft' else 'custom')
        except ValueError as error:
            self.message(str(error));return False
        if action=='custom:draft':
            self.custom_draft['controller']=value
            self.rebuild()
            return True
        return self.commit_binding(action,value)

    def conflicts(self,state,action,value,item=None):
        found=[]
        for other,title in self.api['ACTIONS']:
            old=state['bindings'][other]
            if other==action or set((other,action))==set(('fly','stop')):
                continue
            collision=self.api['binding_overlap'](value,old) if item is not None else bool(value and old and value.replace('_Y','')==old.replace('_Y',''))
            if collision:found.append(('builtin',other,title,old))
        for old in state['customBindings']:
            if item is not None and old['id']==item.get('id'):
                continue
            if self.api['binding_overlap'](value,old['controller']):
                found.append(('custom',old['id'],self.shortcut_title(old),old['controller']))
        return found

    def confirm_override(self,conflicts,value,title):
        from eve.client.script.ui.shared.messagebox import MessageBox
        from player_messaging import PromptOptions, PromptIcon, PromptResult
        lines=['<b>'+old_title+'</b> ('+self.binding_title(old)+')' for kind,identity,old_title,old in conflicts]
        navigation_warning='<br><br>This also removes controller left-click and radial access. Use mouse/keyboard to assign a replacement.' if any(kind=='builtin' and identity=='leftClick' for kind,identity,old_title,old in conflicts) else ''
        self.confirming=True
        try:
            response=MessageBox.prompt_player(text='This input is already assigned to:<br><br>'+'<br>'.join(lines)+'<br><br>Replace these bindings with <b>'+title+'</b> on <b>'+self.binding_title(value)+'</b>? The existing assignments will be removed.'+navigation_warning,
                                              title='Replace Controller Binding?',buttons=PromptOptions.OKCANCEL,icon=PromptIcon.WARNING,
                                              default_response=PromptResult.CANCEL,modal=True,is_suppressable=False,
                                              ok_label='Replace Binding',cancel_label='Cancel')
            return (response[0] if isinstance(response,tuple) else response)==PromptResult.OK
        finally:self.confirming=False

    def commit_binding(self,action,value,item=None):
        if self.confirming or self.closed:
            return False
        value=self.api['binding'](value,action or 'custom')
        for attempt in range(3):
            with open(os.path.join(self.controller.directory,'preferences.json'),'rb') as stream:
                content=stream.read(65537)
            if len(content)>65536:
                self.message('Configuration Is Too Large');return False
            state=self.api['preferences'](json.loads(content))
            conflicts=self.conflicts(state,action,value,item)
            if conflicts:
                command=self.resolve_custom(item) if item is not None else None
                title=command.GetDescription() if command is not None else dict(self.api['ACTIONS']).get(action,'Custom Shortcut')
                if not self.confirm_override(conflicts,value,title):
                    self.message('Binding Change Canceled');return False
                if self.closed or not self.controller.active:
                    return False
                with open(os.path.join(self.controller.directory,'preferences.json'),'rb') as stream:
                    current_content=stream.read(65537)
                if len(current_content)>65536:
                    self.message('Configuration Is Too Large');return False
                current=self.api['preferences'](json.loads(current_content))
                if current['bindings']!=state['bindings'] or current['customBindings']!=state['customBindings']:
                    continue
            bindings=dict(state['bindings'])
            custom=[dict(old) for old in state['customBindings']]
            for kind,identity,title,old in conflicts:
                if kind=='builtin':bindings[identity]=''
                else:custom=[old for old in custom if old['id']!=identity]
            if item is None:
                bindings[action]=value
            else:
                item=dict(item)
                if item.get('id') is None:
                    item['id']='custom-%d'%(max([int(old['id'][7:]) for old in state['customBindings']]+[0])+1)
                custom=[old for old in custom if old['id']!=item['id']]
                custom.append(item)
                command=self.resolve_custom(item)
                if command is None or command.name!=item['command']:
                    self.message('Keyboard Shortcut Changed; Choose It Again');return False
            return self.save({'bindings':bindings,'customBindings':custom},rebuild=True,
                             expected={'bindings':state['bindings'],'customBindings':state['customBindings']})
        self.message('Bindings Changed; Try Again')
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
        feedback_status=self.widgets.get('feedback_status')
        if feedback_status is not None:feedback_status.text=self.feedback_status()
        pads = self.controller.native.scan()
        if set(pads) != set(self.connected):
            self.connected = pads
            self.widgets['selector'].LoadOptions(self.controller_options(), self.controller.settings['controllerIndex'])
        if (self.rendered_settings != self.controller.settings or self.rendered_style!=self.current_style()) and not detecting:
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
        if self.selection_options is not None:
            options = self.native_selection.options
            remaining = type(options)(value for value in options if value != PANEL_ID)
            self.native_selection.options = self.selection_options if remaining == self.selection_options else remaining
        for menu, panel in self.panels:
            if not getattr(panel, 'destroyed', False) and getattr(menu, 'display', False):
                self.reconstruct(menu)
            elif not getattr(panel, 'destroyed', False):
                menu.panelsByID.pop(PANEL_ID, None)
                panel.Close()
        self.panels = []
        self.callbacks.clear()


def install(controller, api):
    return ControllerSettings(controller, api)
