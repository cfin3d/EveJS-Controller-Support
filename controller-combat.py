# Native combat HUD integration for EVE client build 3396210. Python 2.7 compatible.
import hashlib
import json
import math
import os
try:
    import __builtin__ as _ch_builtins
except ImportError:
    import builtins as _ch_builtins

_CH_BUTTONS = (1, 8, 2, 4, 0x8000, 0x2000, 0x1000, 0x4000)
_CH_NAMES = ('UP', 'RIGHT', 'DOWN', 'LEFT', 'Y', 'B', 'A', 'X')
_CH_DIGITAL = 0xf00f
_CH_GUID = 'evejs.ControllerCombatAssignment'


def _ch_value(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _ch_id(value):
    result = str(value)
    if not result.isdigit() or int(result) <= 0:
        raise ValueError('Invalid Item Identity')
    return str(int(result))


def _ch_alive(node):
    try:return node is not None and not getattr(node, 'destroyed', False)
    except ReferenceError:return False


class _CombatLayoutStore(object):
    """Ship shortcuts in native character settings, separate from input presets."""
    def __init__(self, settings, namespace):
        self.settings, self.key = settings, namespace
        source = settings.Get(namespace, {})
        self.ships = {}
        if isinstance(source, dict) and source.get('schemaVersion') == 1:
            ships = source.get('ships', {})
            for ship, slots in (ships.items() if isinstance(ships, dict) else []):
                try:
                    ship = _ch_id(ship)
                    if not isinstance(slots, list) or len(slots) != 16:
                        continue
                    clean, used = [], set()
                    for value in slots:
                        if value is None:
                            clean.append(None)
                            continue
                        item, kind = _ch_id(value['itemID']), int(value['typeID'])
                        if kind <= 0 or item in used:
                            raise ValueError('Invalid Module Assignment')
                        used.add(item)
                        clean.append(dict(itemID=item, typeID=kind))
                    self.ships[ship] = clean
                except (ValueError, TypeError, KeyError):
                    continue

    def layout(self, ship):
        return [dict(value) if value else None for value in self.ships.get(_ch_id(ship), [None] * 16)]

    def save(self, ship, slots):
        # Publish a new settings value rather than mutating the stored object.
        revised = dict(self.ships)
        revised[_ch_id(ship)] = [dict(value) if value else None for value in slots]
        value = dict(schemaVersion=1, ships=revised)
        self.settings.Set(self.key, value)
        self.ships = revised

    def assign(self, ship, index, item, kind):
        if index not in range(16) or int(kind) <= 0:
            raise ValueError('Invalid Module Slot')
        slots, item = self.layout(ship), _ch_id(item)
        for previous, value in enumerate(slots):
            if value and value['itemID'] == item:
                slots[previous] = None
        slots[index] = dict(itemID=item, typeID=int(kind))
        self.save(ship, slots)

    def clear(self, ship, index):
        slots = self.layout(ship)
        if slots[index] is not None:
            slots[index] = None
            self.save(ship, slots)

    def reconcile(self, ship, fitted, complete):
        slots = self.layout(ship)
        if complete:
            changed = False
            for index, value in enumerate(slots):
                if value and (value['itemID'] not in fitted or
                              int(_ch_value(fitted[value['itemID']], 'typeID', 0)) != value['typeID']):
                    slots[index], changed = None, True
            if changed:
                self.save(ship, slots)
        return slots


class _CombatGestures(object):
    """Pure recognition: short release versus one consumed overload hold."""
    def __init__(self):
        self.previous, self.context, self.holds = 0, None, {}

    def reset(self, mask=0):
        self.previous, self.context, self.holds = mask, None, {}

    def step(self, mask, now, context, target, blocked=False):
        old, self.previous = self.previous, mask
        lt, rt = bool(mask & 0x10000), bool(mask & 0x20000)
        bank = 0 if lt and not rt else 1 if rt and not lt else None
        if blocked or context != self.context or lt and rt:
            self.holds = {}
            self.context = context
            # A context change never turns a held button into a fresh press.
            if blocked or lt and rt or old & _CH_DIGITAL:
                return []
        actions = []
        for bit, gesture in list(self.holds.items()):
            started, token, original_bank, consumed = gesture
            index = original_bank * 8 + _CH_BUTTONS.index(bit)
            current = target(index)
            same_release = not mask & bit and not mask & 0x30000
            if current != token or bank != original_bank and not same_release:
                del self.holds[bit]
                continue
            elapsed = now - started
            if not mask & bit:
                if not consumed:
                    actions.append((token, 'overload' if elapsed >= 1. - 1e-9 else 'toggle'))
                del self.holds[bit]
            elif not consumed and elapsed >= 1. - 1e-9:
                actions.append((token, 'overload'))
                self.holds[bit] = (started, token, original_bank, True)
        if bank is not None:
            for offset, bit in enumerate(_CH_BUTTONS):
                if mask & bit and not old & bit and bit not in self.holds:
                    token = target(bank * 8 + offset)
                    if token is not None:
                        self.holds[bit] = (now, token, bank, False)
        return actions

    def progress(self, now):
        return dict((value[1][2], min(1., max(0., now - value[0])))
                    for value in self.holds.values() if not value[3])


class _CombatOwnedNode(object):
    """Restore only geometry and instance handlers owned by this component."""
    def __init__(self, node, geometry=True):
        self.node, self.parent = node, node.parent
        siblings = list(getattr(self.parent, 'children', []))
        self.index = siblings.index(node) if node in siblings else 0
        self.geometry = dict((name, getattr(node, name)) for name in
                             ('align', 'left', 'top', 'width', 'height', 'display', 'state')) if geometry else {}
        if geometry:
            self.geometry.update((name, getattr(node, name)) for name in
                                 ('padLeft', 'padTop', 'padRight', 'padBottom') if hasattr(node, name))
        self.handlers = []

    def hook(self, name, function):
        own = name in getattr(self.node, '__dict__', {})
        previous = getattr(self.node, name, None)
        setattr(self.node, name, function)
        self.handlers.append((name, function, own, previous))

    def restore(self):
        if not _ch_alive(self.node):
            return
        errors = []
        for name, function, own, previous in reversed(self.handlers):
            try:
                if getattr(self.node, name, None) is function:
                    if own:setattr(self.node, name, previous)
                    else:delattr(self.node, name)
            except Exception as error:errors.append(error)
        if self.geometry and _ch_alive(self.parent):
            try:self.node.SetParent(self.parent, idx=self.index)
            except Exception as error:errors.append(error)
            for name, value in self.geometry.items():
                try:setattr(self.node, name, value)
                except Exception as error:errors.append(error)
        if errors:raise errors[0]


class _CombatTapCycle(object):
    """Advance from observed native states, never from an attempted command."""
    def __init__(self):
        self.steps = {}

    def observe(self, key, online, active):
        step = self.steps.get(key, 'activate')
        if not online:step = 'online'
        elif active:step = 'deactivate'
        elif step == 'deactivate':step = 'offline'
        elif step == 'online':step = 'activate'
        self.steps[key] = step
        return step


class _CombatHUD(object):
    def __init__(self, controller, api=None):
        self.c, self.api = controller, api
        self.root, self.ship, self.stock = None, None, None
        self.owned, self.moved, self.created = [], {}, []
        self.cells, self.prompts, self.arcs = [], [], []
        self.bank_prompts = []
        self.identity, self.store, self.assignments, self.fitted = None, None, [None] * 16, {}
        self.gestures = _CombatGestures()
        self.tap_cycle, self.actions_pending = _CombatTapCycle(), set()
        self.epoch, self.last_scan, self.retry_at = 0, -1., 0.
        self.ready, self.dragging, self.failed = False, None, False
        self.signature = None
        self.reserved = 0
        self.parent_orders = {}
        self.utilities, self.hidden = [], []
        self.center, self.hud_parent = None, None
        self.pending_owners, self.retired_roots = [], []
        self.cleanup_failed = False
        self.viewport = None
        self.focus_bank, self.focus_started = None, 0.
        self.focus, self.focus_from = (0., 0.), (0., 0.)

    def session_identity(self):
        session = getattr(_ch_builtins, 'session', None)
        return tuple(getattr(session, key, None) for key in
                     ('charid', 'shipid', 'solarsystemid', 'stationid', 'structureid'))

    def native_api(self):
        if self.api is None:
            import carbonui.const as const
            from carbonui.primitives.container import Container
            from carbonui.primitives.sprite import Sprite
            from carbonui.primitives.transform import Transform
            from carbonui.primitives.vectorlinetrace import VectorLineTrace
            from eve.client.script.ui.control.eveLabel import EveLabelSmall
            from eve.client.script.ui.inflight.shipHud.shipSlot import ShipSlot
            from eve.client.script.ui.inflight.shipModuleButton.shipmodulebutton import ModuleButton
            from util import KeyVal
            self.api = dict(const=const, Container=Container, Sprite=Sprite, Transform=Transform,
                            Line=VectorLineTrace, Label=EveLabelSmall,
                            ShipSlot=ShipSlot, ModuleButton=ModuleButton, KeyVal=KeyVal)
        return self.api

    def blocked(self):
        ui = self.c.ui
        if self.c.neocom or self.c.radial or self.c.radial_hold or self.c.radial_gate:
            return True
        close = getattr(self.c, 'window_close', None)
        if close and (close.target or close.returning or close.pending):
            return True
        if ui.registry.GetModalWindow() is not None or getattr(ui, 'dragObject', None) is not None:
            return True
        for name in ('menu', 'utilmenu', 'systemmenu'):
            layer = getattr(ui.layer, name, None)
            if _ch_alive(layer) and getattr(layer, 'display', False) and any(
                    _ch_alive(child) and getattr(child, 'display', False) for child in layer.children):
                return True
        return bool(getattr(getattr(_ch_builtins, 'session', None), 'mutating', False))

    def snapshot(self):
        session = getattr(_ch_builtins, 'session', None)
        ship = getattr(self.c.ui.layer, 'shipui', None)
        if not _ch_alive(ship) or not getattr(ship, 'display', False) or not getattr(ship, 'shipuiReady', False):
            return None
        if not session or not getattr(session, 'charid', None) or not getattr(session, 'shipid', None) or not getattr(session, 'solarsystemid', None):
            return None
        if getattr(session, 'mutating', False) or getattr(session, 'stationid', None) or getattr(session, 'structureid', None):
            return None
        native = getattr(ship, 'controller', None)
        if native is None or not native.IsLoaded() or not native._IsShipItemReady() or getattr(ship, 'initing', False):
            return None
        if native.GetItemID() != session.shipid or native.IsControllingStructure() or native.IsControllingTurret():
            return None
        stock = getattr(ship, 'slotsContainer', None)
        if not _ch_alive(stock) or getattr(stock, 'initSlotsDelayedTimer', None) is not None:
            return None
        fitted = {}
        for item in native.GetModules():
            if _ch_value(item, 'categoryID') != 7 or _ch_value(item, 'locationID') != session.shipid:
                continue
            if _ch_value(item, 'flagID') not in stock.slotsByFlag:
                continue
            fitted[_ch_id(_ch_value(item, 'itemID'))] = item
        return ship, stock, fitted

    def profile(self, identity):
        settings = getattr(_ch_builtins, 'settings', None)
        if settings is None:
            raise ValueError('Character Settings Unavailable')
        namespace = os.path.normcase(os.path.abspath(self.c.directory)) + ':' + str(identity[0])
        encoded = namespace if isinstance(namespace, bytes) else namespace.encode('utf-8')
        digest = hashlib.sha256(encoded).hexdigest()[:24]
        return _CombatLayoutStore(settings.char.ui, 'evejsControllerCombatLayoutsV1_' + digest)

    def icon(self, token):
        resolver = self.c.helpers.get('_ec_button_icon')
        names = dict(UP='dpad-up', RIGHT='dpad-right', DOWN='dpad-down', LEFT='dpad-left')
        name = resolver(self.c, token) if resolver else names.get(token, token.lower())
        return getattr(self.c.menu, 'button_icons', {}).get(name)

    def viewport_layout(self):
        # Carbon reports logical UI dimensions; its renderer applies UI/DPI
        # scaling. Never apply Windows or EVE scaling a second time here.
        x, y, width, height = self.c.ui.desktop.GetAbsolute()
        if width >= 1280 and height >= 356:return min(1280, int(width)-16), 340, False
        if width >= 768 and height >= 616:return min(800, int(width)-16), 600, True
        return None

    def button_prompt(self, token, cx, cy, icon_size):
        api, k = self.native_api(), self.api['const']
        size = icon_size + 6
        prompt = api['Container'](parent=self.root, name='evejsCombatPrompt'+token,
                    align=k.TOPLEFT, left=cx-size/2., top=cy-size/2.,
                    width=size, height=size, state=k.UI_DISABLED, opacity=1.)
        # Native slot centers are RGB 64. Keep this solid backing independent
        # of bank emphasis so bright scenery cannot show through the glyph.
        trigger = token in ('LT', 'RT')
        background = self.c.menu.button_icons['combat-trigger-backdrop'] if trigger else (
                     'res:/UI/Texture/classes/ShipUI/slotSolidBackground.png')
        placement = dict(align=k.TOPLEFT, left=3, top=3, width=icon_size, height=icon_size) if trigger else dict(align=k.TOALL)
        prompt.backdrop = api['Sprite'](parent=prompt, texturePath=background,
                    color=(64/255., 64/255., 64/255., 1.), opacity=1., state=k.UI_DISABLED, **placement)
        path = self.icon(token)
        if token in ('UP', 'RIGHT', 'DOWN', 'LEFT') and path:
            # One raster sprite shares the face icons' exact ring pixels,
            # white strokes and filtering instead of mixing line renderers.
            path = self.c.menu.button_icons['combat-dpad-'+token.lower()]
        prompt.glyph = api['Sprite'](parent=prompt, align=k.TOPLEFT, left=3, top=3,
                    width=icon_size, height=icon_size, texturePath=path,
                    color=(1., 1., 1., 1.), state=k.UI_DISABLED, idx=0) if path else api['Label'](
                    parent=prompt, align=k.TOPLEFT, left=(size-16)/2., top=(size-14)/2.,
                    text=token, state=k.UI_DISABLED, idx=0)
        return prompt

    def build(self, ship, stock, viewport):
        api, ui = self.native_api(), self.c.ui
        k, Container, Sprite = api['const'], api['Container'], api['Sprite']
        width, height, compact = viewport
        self.viewport = viewport
        self.ship, self.stock = ship, stock
        self.hud_parent = ship.hudContainer
        self.root = Container(parent=self.hud_parent, name='evejsControllerCombatHUD', align=k.TOPLEFT,
                              width=width, height=height, top=0, state=k.UI_PICKCHILDREN, idx=0)
        # The existing 185x200 center owns the real gauges, compass and speed UI.
        center = self.own(ship.centerParent)
        self.center = center.node
        center.node.SetParent(self.root)
        center.node.align = k.TOPLEFT
        center.node.left, center.node.top = (width - center.node.width) / 2., 28
        self.utility_strip(ship, width)
        # Reserve the native sensor compass's 200px footprint, even when it is
        # hidden. Slot positions stay fixed when the sensor overlay toggles.
        inner, cluster_step = 236., 260.
        outer = inner + cluster_step
        cluster_x = (-inner, -inner, inner, inner) if compact else (-outer, -inner, inner, outer)
        cluster_y = (128., 388., 128., 388.) if compact else (128.,)*4
        for index in range(16):
            cluster, direction = index // 4, index % 4
            dx, dy = ((0, -62.5), (62.5, 0), (0, 62.5), (-62.5, 0))[direction]
            cx, cy = width / 2. + cluster_x[cluster] + dx, cluster_y[cluster] + dy
            cell = api['Transform'](parent=self.root, name='evejsCombatSlot%d' % index,
                             align=k.TOPLEFT, left=cx-32, top=cy-32, width=64, height=64,
                             state=k.UI_NORMAL, pickRadius=26, idx=0,
                             scale=(1., 1.), scalingCenter=(.5, .5))
            Sprite(parent=cell, align=k.TOALL, state=k.UI_DISABLED,
                   texturePath='res:/UI/Texture/classes/ShipUI/slotMainCombined.png')
            frame = api['Line'](parent=cell, align=k.TOPLEFT, width=64, height=64,
                                lineWidth=1, color=(.35, .39, .42, 1.), state=k.UI_DISABLED)
            for point in range(49):
                angle = point * 2 * math.pi / 48.
                frame.AddPoint((32+25*math.cos(angle),32+25*math.sin(angle)), color=(.35,.39,.42,1.))
            cell._controller_combat_slot = index
            cell.OnDropData = lambda source, nodes, slot=index: self.drop(slot, source, nodes)
            cell.VerifyDrop = lambda source, nodes: self.can_drop(source, nodes)
            cell.isDropLocation = True
            self.cells.append(cell)
            token = _CH_NAMES[index % 8]
            vx, vy = ((0, -1), (1, 0), (0, 1), (-1, 0))[direction]
            self.prompts.append(self.button_prompt(token, cx+vx*51, cy+vy*51, 26))
            arc = api['Line'](parent=cell, name='evejsCombatHold', align=k.TOPLEFT,
                              width=64, height=64, state=k.UI_DISABLED, lineWidth=2,
                              color=(.91, .64, .29, 1.), idx=0)
            arc.display = False
            self.arcs.append(arc)
        for bank, offset in enumerate((-inner, inner) if compact else (-(inner+cluster_step/2.), inner+cluster_step/2.)):
            path = self.icon('LT' if bank == 0 else 'RT')
            if path:
                if compact:offset += -100 if bank==0 else 100
                self.bank_prompts.append(self.button_prompt('LT' if bank == 0 else 'RT',
                                         width/2.+offset, 30, 32))
        self.own(stock).node.display = False
        self.hidden.append(stock)
        toggle = getattr(ship, 'moduleToggleCont', None)
        if _ch_alive(toggle):
            self.own(toggle).node.display = False
            self.hidden.append(toggle)
        # Restore moved controls before native owners rebuild or flush them.
        self.own(stock, False).hook('InitSlots', self.rebuild_guard(stock.InitSlots))
        if callable(getattr(stock, 'Show', None)):
            self.own(stock, False).hook('Show', self.visibility_guard(stock.Show))
        self.own(ship, False).hook('ResetSelf', self.rebuild_guard(ship.ResetSelf))
        self.own(ship.hudButtons, False).hook('construct_buttons', self.rebuild_guard(ship.hudButtons.construct_buttons))
        if callable(getattr(ship, 'UpdateButtonPositions', None)):
            self.own(ship, False).hook('UpdateButtonPositions', self.position_guard(ship.UpdateButtonPositions))
        if callable(getattr(ship, 'UpdatePosition', None)):
            self.own(ship, False).hook('UpdatePosition', self.position_guard(ship.UpdatePosition))
        self.layout()
        self.epoch += 1

    def visibility_guard(self, native):
        def show(*args, **kwargs):
            result = native(*args, **kwargs)
            if _ch_alive(self.root):self.enforce_visibility()
            return result
        return show

    def position_guard(self, native):
        def position(*args, **kwargs):
            result = native(*args, **kwargs)
            if _ch_alive(self.root):
                if self.viewport_layout()!=self.viewport:self.detach(self.gestures.previous)
                else:self.layout()
            return result
        return position

    def enforce_visibility(self):
        for node in self.hidden:
            if _ch_alive(node):node.display = False

    def layout(self):
        # Follow the native HUD's camera/user offset as a single assembly. Clamp
        # only our presentation; never rewrite the native offset or preference.
        k, width = self.api['const'], self.root.width
        dx, dy, dw, dh = self.c.ui.desktop.GetAbsolute()
        px, py, pw, ph = self.hud_parent.GetAbsolute()
        x = px+(pw-width)/2.
        top_aligned = self.hud_parent.align == getattr(k, 'CENTERTOP', None)
        y = py if top_aligned else py+ph-self.root.height
        x = max(dx+8., min(dx+dw-8.-width, x))
        y = max(dy+8., min(dy+dh-8.-self.root.height, y))
        self.root.left, self.root.top = x-px, y-py
        self.center.align = k.TOPLEFT
        compact = self.viewport[2]
        self.center.left, self.center.top = (width-self.center.width)/2., 158 if compact else 28
        widgets = [widget for widget in self.utilities if self.utility_visible(widget)]
        total = sum(widget.width for widget in widgets) + max(0, len(widgets)-1)*12.
        left = (width-total)/2.
        for widget in widgets:
            widget.align = k.TOPLEFT
            widget.left, widget.top = left, (552 if compact else 292)-widget.height/2.
            left += widget.width+12.
        self.enforce_visibility()

    def utility_visible(self, widget):
        if not _ch_alive(widget) or not getattr(widget, 'display', True):return False
        # Native grouping keeps its outer container displayed even when there
        # are no groupable weapons and its actual icon is hidden.
        if widget is getattr(self.stock, 'groupAllButton', None):
            icon = getattr(widget, 'groupAllIcon', None)
            return _ch_alive(icon) and getattr(icon, 'display', True)
        return True

    def rebuild_guard(self, native):
        def rebuild(*args, **kwargs):
            self.detach(self.gestures.previous)
            return native(*args, **kwargs)
        return rebuild

    def own(self, node, geometry=True):
        owner = self.capture(node, geometry)
        self.owned.append(owner)
        return owner

    def capture(self, node, geometry=True):
        owner = _CombatOwnedNode(node, geometry)
        if geometry:
            order = self.parent_orders.setdefault(id(node.parent), list(node.parent.children))
            for sibling in node.parent.children:
                if sibling not in order:
                    order.append(sibling)
            alive = [sibling for sibling in order if _ch_alive(sibling)]
            if node in alive:
                owner.index = alive.index(node)
        return owner

    def utility_strip(self, ship, width):
        api, controls = self.native_api(), ship.hudButtons
        k = api['const']
        children = list(controls.children)
        find = lambda word: next((child for child in children if word.lower() in type(child).__name__.lower()), None)
        cargo, scanner = find('cargo'), find('scanner')
        widgets = [cargo, scanner, getattr(controls, 'tacticalOverlay', None),
                   getattr(controls, 'cameraTactical', None), getattr(controls, 'cameraOrbit', None),
                   getattr(controls, 'cameraPov', None), getattr(controls, 'autopilotBtn', None),
                   getattr(ship, 'safetyButton', None), getattr(ship, 'optionsCont', None)]
        if not all(_ch_alive(widget) for widget in widgets):
            raise ValueError('Native Utility Controls Unavailable')
        mining = getattr(ship, 'mining_overlay_buttons', None)
        if _ch_alive(mining):
            # The integrated Mining Surveyor is a separate native container,
            # outside hudButtons. Move its existing control with the strip and
            # retain the container's native hull-dependent visibility.
            widgets.insert(widgets.index(controls.autopilotBtn), mining)
        # Include optional zoom controls and future native utility buttons;
        # keep the existing instances, enabled state, menus and tooltips.
        widgets.extend(child for child in children if child not in widgets and callable(getattr(child, 'OnClick', None)))
        grouping = getattr(self.stock, 'groupAllButton', None)
        if _ch_alive(grouping):widgets.append(grouping)
        self.utilities = list(widgets)
        for widget in widgets:
            self.own(widget)
            if widget is mining:
                for node in [widget] + list(widget.children):
                    if node is not widget:self.own(node)
                    for name in ('padLeft', 'padTop', 'padRight', 'padBottom'):
                        if hasattr(node, name):setattr(node, name, 0)
            widget.SetParent(self.root)
            widget.align = k.TOPLEFT
        self.own(controls).node.display = False
        self.hidden.append(controls)

    def native_button(self, item):
        button = self.stock.GetModule(int(item))
        if button is None:
            # A fitted slave resolves the current native weapon bank master.
            manager = getattr(_ch_builtins, 'sm', None)
            dogma = manager.GetService('clientDogmaIM').GetDogmaLocation() if manager else None
            master = dogma.GetMasterModuleID(self.identity[1], int(item)) if dogma else None
            button = self.stock.GetModule(master) if master else None
        return button if _ch_alive(button) else None

    def make_passive(self, item, cell):
        # Native passive controls may be filtered out of the original HUD.
        api, k = self.native_api(), self.api['const']
        slot = api['ShipSlot'](parent=cell, align=k.TOPLEFT, width=64, height=64,
                              state=k.UI_NORMAL, left=0, top=0)
        button = api['ModuleButton'](parent=slot, align=k.TOPLEFT, width=48, height=48,
                                    left=8, top=8, state=k.UI_NORMAL, idx=0)
        try:
            button.Setup(item)
        except Exception:
            slot.Close()
            raise
        self.created.append(slot)
        return button

    def refresh(self):
        self.restore_modules()
        if self.pending_owners:raise RuntimeError('Native module restoration incomplete')
        for slot in self.created:
            if _ch_alive(slot):
                slot.Close()
        self.created = []
        for cell in self.cells:
            cell.display = True
        used = set()
        for index, value in enumerate(self.assignments):
            if not value:
                continue
            button = self.native_button(value['itemID'])
            if button is None:
                item = self.fitted.get(value['itemID'])
                if item is None:
                    continue
                # Only construct a missing passive; never clone a weapon bank.
                effect = self.stock.GetDefaultEffect(item)
                if effect is not None:
                    continue
                button = self.make_passive(item, self.cells[index])
            if id(button) in used:
                continue
            used.add(id(button))
            slot = button.parent
            owner = self.capture(slot)
            self.moved[index] = owner
            slot.SetParent(self.cells[index], idx=0)
            slot.align = self.api['const'].TOPLEFT
            slot.left, slot.top, slot.width, slot.height, slot.display = 0, 0, 64, 64, True
            self.arcs[index].SetOrder(0)
            slot._controller_combat_slot = index
            owner.hook('OnDropData', lambda source, nodes, pos=index: self.drop(pos, source, nodes))
            owner.hook('VerifyDrop', lambda source, nodes: self.can_drop(source, nodes))
            control = _CombatOwnedNode(button, False)
            # Track ownership before replacing any handler so a partial
            # attachment can restore the native button on failure.
            owner.control = control
            owner.controls = [control]
            # Keep module owners, native menus, tooltip and animation methods.
            native_click = button.OnClick
            control.hook('OnClick', self.cursor_click(index, button, native_click))
            control.hook('GetMenu', self.cursor_menu(index, button, button.GetMenu))
            control.hook('OnDropData', lambda source, nodes, pos=index: self.drop(pos, source, nodes))
            control.hook('VerifyDrop', lambda source, nodes: self.can_drop(source, nodes))
            control.hook('GetDragData', lambda pos=index, obj=button: self.drag_data(pos, obj))
            control.hook('PrepareDrag', lambda drag, source, obj=button: self.prepare_drag(drag, obj))
            control.hook('VerifyDrag', lambda location, nodes: self.cell_index(location) is not None)
            control.hook('OnEndDrag', self.end_drag)
            overload = getattr(getattr(button, 'sr', None), 'overloadButton', None)
            if _ch_alive(overload) and callable(getattr(overload, 'OnClick', None)):
                overlay = _CombatOwnedNode(overload, False)
                owner.controls.append(overlay)
                overlay.hook('OnClick', self.cursor_click(index, button, overload.OnClick))
        self.epoch += 1
        self.gestures.reset(self.gestures.previous)

    def cursor_click(self, index, button, native):
        def click(*args):
            token = self.target(index)
            snapshot = self.snapshot()
            if token is not None and token[-1] == id(button) and not self.blocked() and snapshot is not None and token[3] in snapshot[2]:
                return native(*args)
        return click

    def cursor_menu(self, index, button, native):
        def menu(*args):
            token, snapshot = self.target(index), self.snapshot()
            if token is None or token[-1] != id(button) or snapshot is None or token[3] not in snapshot[2] or self.blocked_without_drag():
                return []
            self.gestures.reset(self.gestures.previous)
            return native(*args)
        return menu

    def action_target(self, index):
        token = self.target(index)
        if token is not None:
            button = self.moved[index].control.node
            if getattr(button, 'def_effect', None) is not None and getattr(button, 'isInActiveState', False):
                return token
        return None

    def tap_action(self, token, button):
        key = (token[1], token[3], token[-1])
        step = self.tap_cycle.observe(key, bool(getattr(button, 'online', True)),
                                      bool(getattr(button.def_effect, 'isActive', False)))
        if (not getattr(button, 'isInActiveState', False) or
                any(getattr(button, name, False) for name in
                    ('isDeactivating', 'effect_activating', 'waitingForActiveTarget', 'isPendingUnlockForDeactivate'))):
            return None
        return step

    def target(self, index):
        if not self.ready or self.identity != self.session_identity() or not self.assignments[index]:
            return None
        value = self.assignments[index]
        item = self.fitted.get(value['itemID'])
        if item is None or int(_ch_value(item, 'typeID', 0)) != value['typeID']:
            return None
        owner = self.moved.get(index)
        button = getattr(getattr(owner, 'control', None), 'node', None)
        if not _ch_alive(button):
            return None
        expected = self.native_button(value['itemID'])
        if expected is not None and expected is not button:
            return None
        if expected is None and (owner.node not in self.created or
                _ch_id(_ch_value(button.moduleinfo, 'itemID')) != value['itemID']):
            return None
        return (self.epoch, self.identity, index, value['itemID'], value['typeID'], id(button))

    def execute(self, token, action):
        import uthread
        if self.target(token[2]) != token or token in self.actions_pending:
            return
        button = self.moved[token[2]].control.node
        intended = self.tap_action(token, button) if action == 'toggle' else 'overload'
        if intended is None:return
        self.actions_pending.add(token)
        def send():
            try:
                if not self.c.active or self.c.mode.mode != 'controller' or not self.c.native.foreground():
                    return
                if getattr(self.c.native, 'pending', False):
                    return
                if self.blocked() or self.target(token[2]) != token:
                    return
                # Recheck authoritative fit and bank identity at deferred dispatch.
                snapshot = self.snapshot()
                if snapshot is None or token[3] not in snapshot[2]:
                    return
                if self.native_button(token[3]) not in (None, button):
                    return
                if getattr(button, 'def_effect', None) is None or not getattr(button, 'isInActiveState', False):
                    return
                if getattr(button, 'IsBeingDragged', lambda: False)():
                    return
                if intended == 'overload':
                    if not getattr(button, 'online', True):return
                    button.ToggleOverload()
                elif self.tap_action(token, button) != intended:
                    return
                elif intended in ('online', 'offline'):
                    # Already on a uthread: use the native handler directly so
                    # its confirmations and server request remain serialized.
                    button._ChangeOnline(intended == 'online')
                else:
                    button.Click(0)
                if self.target(token[2]) == token:self.tap_action(token, button)
            except Exception as error:
                print('EVEJS_CONTROLLER:Module action unavailable: ' + type(error).__name__)
            finally:
                self.actions_pending.discard(token)
        try:uthread.new(send)
        except Exception:
            self.actions_pending.discard(token)
            raise

    def source_item(self, source, nodes):
        if not self.ready or self.identity != self.session_identity() or self.blocked_without_drag():
            return None
        if not isinstance(nodes, (tuple, list)) or not nodes or len(nodes) > 16:
            return None
        node = nodes[0]
        if _ch_value(node, '__guid__') == _CH_GUID:
            if (len(nodes) != 1 or _ch_value(node, 'context') != self.identity or
                    _ch_value(node, 'epoch') != self.epoch or
                    _ch_value(node, 'owner') is not self):
                return None
            item_id = _ch_value(node, 'itemID')
        else:
            # Loaded charges may be the fitting window's drag nodes. Resolve
            # the installed module from its live fitting slot controller.
            controller = getattr(source, 'controller', None)
            if controller is None or not callable(getattr(controller, 'GetModule', None)):
                return None
            if not callable(getattr(controller, 'IsSimulated', None)) or controller.IsSimulated():
                return None
            item = controller.GetModule()
            if item is None:
                return None
            item_id = _ch_value(item, 'itemID')
        try:
            item_id = _ch_id(item_id)
        except (ValueError, TypeError):
            return None
        return self.fitted.get(item_id)

    def blocked_without_drag(self):
        ui = self.c.ui
        return (self.c.mode.mode != 'controller' or not self.c.native.foreground() or
                ui.registry.GetModalWindow() is not None or
                bool(getattr(getattr(_ch_builtins, 'session', None), 'mutating', False)))

    def can_drop(self, source, nodes):
        return self.source_item(source, nodes) is not None

    def drop(self, index, source, nodes):
        item = self.source_item(source, nodes)
        if item is None:
            return
        snapshot = self.snapshot()
        item_id = _ch_id(_ch_value(item, 'itemID'))
        if snapshot is None or item_id not in snapshot[2]:
            return
        slots = self.store.layout(self.identity[1])
        native = self.native_button(item_id)
        for previous, value in enumerate(slots):
            if value and (value['itemID'] == item_id or native is not None and self.native_button(value['itemID']) is native):
                slots[previous] = None
        slots[index] = dict(itemID=item_id, typeID=int(_ch_value(item, 'typeID')))
        self.store.save(self.identity[1], slots)
        self.assignments = self.store.layout(self.identity[1])
        self.signature = None
        self.gestures.reset(self.gestures.previous)
        self.epoch += 1

    def cell_index(self, location):
        for unused in range(16):
            if location is None or location is self.root:
                return None
            index = getattr(location, '_controller_combat_slot', None)
            if index is not None and location in self.cells:
                return index
            location = getattr(location, 'parent', None)
        return None

    def drag_data(self, index, button):
        token = self.target(index)
        if token is None:
            return []
        self.gestures.reset(self.gestures.previous)
        self.dragging = token
        return [self.native_api()['KeyVal'](__guid__=_CH_GUID, owner=self,
                context=self.identity, epoch=self.epoch, slot=index,
                itemID=token[3], typeID=token[4])]

    def prepare_drag(self, drag, button):
        api = self.native_api()
        drag.width, drag.height = 48, 48
        api['Sprite'](parent=drag, align=api['const'].TOPLEFT, width=48, height=48,
                      state=api['const'].UI_DISABLED, texturePath=button.icon.texturePath)
        return (24, 24)

    def end_drag(self, source, location, nodes):
        token, self.dragging = self.dragging, None
        if token is None or self.target(token[2]) != token or self.blocked_without_drag():
            return
        if self.cell_index(location) is not None:
            return
        # Other windows reject our custom drag type. They cannot unfit items.
        neutral = [self.c.ui.desktop, getattr(self.c.ui.layer, 'inflight', None),
                   getattr(self.c.ui.layer, 'viewstate', None), self.ship, self.root]
        if location not in neutral or self.c.ui.uilib.Key(self.api['const'].VK_ESCAPE):
            return
        self.store.clear(self.identity[1], token[2])
        self.assignments = self.store.layout(self.identity[1])
        self.signature = None
        self.epoch += 1

    def update_arcs(self, now, bank):
        progress = self.gestures.progress(now)
        for index, arc in enumerate(self.arcs):
            fraction = progress.get(index, 0.)
            arc.display = fraction > 0
            if fraction:
                arc.Flush()
                for step in range(max(2, int(fraction * 48) + 1)):
                    angle = -math.pi/2 + 2*math.pi*min(fraction, step/48.)
                    arc.AddPoint((32 + 23*math.cos(angle), 32 + 23*math.sin(angle)), color=(.91, .64, .29, 1.))

    def update_focus(self, now, bank):
        # Ease from the currently displayed emphasis, including rapid bank
        # changes. Scale the native slot assembly around its own center while
        # leaving logical slot bounds and outside prompts in place.
        elapsed = min(1., max(0., (now-self.focus_started)/.16))
        eased = elapsed*elapsed*(3.-2.*elapsed)
        target = tuple(1. if self.focus_bank == side else 0. for side in range(2))
        self.focus = tuple(start+(end-start)*eased for start, end in zip(self.focus_from, target))
        if bank != self.focus_bank:
            self.focus_bank, self.focus_started, self.focus_from = bank, now, self.focus
        for index, cell in enumerate(self.cells):
            selected, opposite = self.focus[index//8], self.focus[1-index//8]
            scale = 1.+.05*selected
            cell.scale = (scale, scale)
            cell.opacity = 1.-.4*opposite
            self.prompts[index].glyph.opacity = .65+.35*selected-.15*opposite
        for side, prompt in enumerate(self.bank_prompts):
            prompt.glyph.opacity = 1.-.4*self.focus[1-side]

    def route(self, pad, now, active=True):
        self.reserved &= pad[0]
        mask = pad[0] | (0x10000 if pad[5] >= self.c.settings['triggerThreshold'] else 0) | (0x20000 if pad[6] >= self.c.settings['triggerThreshold'] else 0)
        if not active or not self.c.settings.get('combatHudEnabled', False):
            self.detach(mask)
            return self.filtered(pad)
        if now < self.retry_at:
            self.gestures.reset(mask)
            return self.filtered(pad)
        stage = 'Native HUD Snapshot'
        try:
            self.cleanup()
            if self.pending_owners or self.retired_roots:
                self.gestures.reset(mask)
                return self.filtered(pad)
            snapshot = self.snapshot()
            if snapshot is None:
                self.detach(mask)
                return self.filtered(pad)
            ship, stock, fitted = snapshot
            identity = self.session_identity()
            viewport = self.viewport_layout()
            if viewport is None:
                self.detach(mask)
                return self.filtered(pad)
            if (self.identity != identity or self.ship is not ship or self.stock is not stock or
                    self.center is not ship.centerParent or self.hud_parent is not ship.hudContainer or
                    not _ch_alive(self.root) or self.viewport != viewport):
                self.detach(self.gestures.previous)
                if self.pending_owners or self.retired_roots:return self.filtered(pad)
                self.identity, self.store = identity, self.profile(identity)
                stage = 'Native HUD Attachment'
                self.build(ship, stock, viewport)
            self.fitted = fitted
            self.assignments = self.store.reconcile(identity[1], fitted, True)
            signature = tuple((value['itemID'], value['typeID'], id(self.native_button(value['itemID'])))
                              if value else None for value in self.assignments)
            if signature != self.signature:
                stage = 'Module Refresh'
                self.refresh()
                self.signature = signature
            self.ready = True
            # Notice natural cycle completion and cursor-driven native state
            # changes even when no controller button is being pressed.
            for index, owner in self.moved.items():
                token = self.target(index)
                if (token is not None and token not in self.actions_pending and
                        getattr(owner.control.node, 'def_effect', None) is not None):
                    self.tap_action(token, owner.control.node)
            stage = 'Layout And Input'
            self.layout()
            self.root.display = True
            blocked = self.blocked()
            for token, action in self.gestures.step(mask, now, (self.identity, self.epoch), self.action_target, blocked):
                self.execute(token, action)
            bank = 0 if mask & 0x30000 == 0x10000 else 1 if mask & 0x30000 == 0x20000 else None
            self.update_arcs(now, bank)
            self.update_focus(now, None if blocked else bank)
            self.failed = False
            # Reserve only the digital module controls in a trigger context.
            # Cursor clicks, sticks, camera zoom and other inputs keep working.
            if not blocked and mask & 0x30000:
                self.reserved |= pad[0] & _CH_DIGITAL
                pad = (pad[0] & ~_CH_DIGITAL,) + tuple(pad[1:])
            return self.filtered(pad)
        except Exception as error:
            self.detach(mask)
            self.retry_at = now + 2.
            if not self.failed:
                print('EVEJS_CONTROLLER:Combat HUD unavailable ('+stage+'); original HUD restored: ' + type(error).__name__)
                self.failed = True
            return self.filtered(pad)

    def filtered(self, pad):
        return (pad[0] & ~self.reserved,) + tuple(pad[1:])

    def restore_modules(self):
        # Restore ascending native sibling positions, regardless of HUD order.
        moved, self.moved = self.moved, {}
        for owner in sorted(moved.values(), key=lambda value: (id(value.parent), value.index)):
            for control in getattr(owner, 'controls', []):
                self.pending_owners.append(control)
            self.pending_owners.append(owner)
            try:delattr(owner.node, '_controller_combat_slot')
            except (AttributeError, TypeError):pass
        self.cleanup()

    def cleanup(self):
        # Clear ownership before invoking UI setters: native notifications may
        # re-enter cancellation while a HUD is being rebuilt during undocking.
        pending, self.pending_owners = self.pending_owners, []
        for owner in pending:
            try:owner.restore()
            except Exception as error:
                self.pending_owners.append(owner)
                if not self.cleanup_failed:
                    print('EVEJS_CONTROLLER:Combat HUD cleanup deferred ('+type(owner.node).__name__+'): '+type(error).__name__)
                    self.cleanup_failed = True
        retired, self.retired_roots = self.retired_roots, []
        for root in retired:
            if not _ch_alive(root):continue
            # Never destroy a borrowed native widget whose reparent operation
            # failed. Hide this old presentation until restoration can finish.
            occupied = False
            for owner in self.pending_owners:
                node = owner.node
                for unused in range(32):
                    if node is root:occupied = True;break
                    if not _ch_alive(node):break
                    node = getattr(node, 'parent', None)
            if occupied:
                self.retired_roots.append(root)
                continue
            try:root.Close()
            except Exception:self.retired_roots.append(root)
        if not self.pending_owners and not self.retired_roots:self.cleanup_failed = False

    def detach(self, mask=0):
        self.ready, self.dragging = False, None
        self.gestures.reset(mask)
        self.tap_cycle, self.actions_pending = _CombatTapCycle(), set()
        self.epoch += 1
        root, owned, created = self.root, self.owned, self.created
        self.root, self.ship, self.stock = None, None, None
        self.center, self.hud_parent = None, None
        self.viewport = None
        self.owned, self.created = [], []
        self.focus_bank, self.focus_started = None, 0.
        self.focus, self.focus_from = (0., 0.), (0., 0.)
        self.utilities, self.hidden = [], []
        self.cells, self.prompts, self.arcs = [], [], []
        self.bank_prompts = []
        self.parent_orders = {}
        self.signature = None
        if _ch_alive(root):
            root.display = False
            self.retired_roots.append(root)
        # Restore native owners before closing the old custom root.
        self.pending_owners.extend(sorted(owned, key=lambda value: (id(value.parent), value.index)))
        moved_roots, self.retired_roots = self.retired_roots, []
        self.restore_modules()
        self.retired_roots = moved_roots + self.retired_roots
        for slot in created:
            if _ch_alive(slot):
                try:slot.Close()
                except Exception:
                    slot.display = False
                    self.retired_roots.append(slot)
        self.cleanup()

    def close(self):
        self.detach()
