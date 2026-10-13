# Native UI helpers for EVE client build 3396210.
# Python 2.7 compatible. Uses native hit-testing and reversible cursor masking.
# Does not modify client archives or replace input handlers.
# Explicit stick gestures call the existing client flight/stop functions.
import json as _ec_json
import os as _ec_os
import time as _ec_time
import math as _ec_math
try:
    import __builtin__ as _ec_builtins
except ImportError:
    import builtins as _ec_builtins


def _ec_hover_target(uicore):
    return _ec_target_bounds(uicore, getattr(getattr(uicore, 'uilib', None), 'mouseOver', None))


def _ec_custom_command(uicore, modifier, key):
    keys = dict([(chr(code), code) for code in range(65,91)] + [(str(i),48+i) for i in range(10)] + [('F%d'%i,111+i) for i in range(1,25)] + [('Space',32),('Tab',9),('Enter',13),('Escape',27),('Backspace',8),('Insert',45),('Delete',46),('Home',36),('End',35),('Page Up',33),('Page Down',34),('Up',38),('Down',40),('Left',37),('Right',39)])
    mods = {'CTRL':17,'ALT':18,'SHIFT':16}
    shortcut = tuple([mods[token] for token in modifier.split('+') if token != 'NONE'] + [keys[key]])
    mapping = uicore.cmd.commandMap
    command = mapping.GetCommandByShortcut(shortcut)
    if command is None:
        command = next((item for item in mapping.GetAllMappedCommands() if item.shortcut and item.shortcut[-1] == shortcut[-1] and set(item.shortcut[:-1]) == set(shortcut[:-1])), None)
    return command


def _ec_custom_execute(uicore, binding):
    if uicore.registry.GetModalWindow() is not None or getattr(getattr(_ec_builtins,'session',None),'mutating',False):
        return
    command = _ec_custom_command(uicore, binding['modifier'], binding['key'])
    if command is None or command.name != binding['command'] or not uicore.cmd.IsCommandEnabled(command):
        return
    uicore.cmd.ExecuteCommand(command)
    if getattr(command,'category',None) == 'combat' and getattr(uicore.cmd,'combatCmdLoaded',None) is command:
        # Native combat shortcuts load an action for an object. Use EVE's
        # selected object and clean up the loaded command after dispatch.
        from eve.client.script.parklife import states
        try:
            item_id = _ec_builtins.sm.GetService('stateSvc').GetExclState(states.selected)
            if item_id:
                uicore.cmd.ExecuteCombatCommand(item_id)
        finally:
            if getattr(uicore.cmd,'combatCmdLoaded',None) is command:
                uicore.cmd.UnloadCombatCommand()


def _ec_radial_record(item_id):
    from eve.client.script.parklife import targetMgr
    session = getattr(_ec_builtins, 'session', None)
    if session is None or not getattr(session, 'charid', None) or not getattr(session, 'solarsystemid', None) or any(getattr(session, key, None) for key in ('stationid', 'structureid', 'mutating')) or item_id == getattr(session, 'shipid', None):
        return None
    manager = getattr(_ec_builtins, 'sm', None)
    park = manager.GetService('michelle').GetBallpark() if manager else None
    slim = park.GetInvItem(item_id) if park else None
    if slim is None or park.GetBall(item_id) is None or getattr(slim, 'groupID', None) in targetMgr.const.nonTargetableGroups:
        return None
    if not getattr(slim, 'typeID', None) or not getattr(slim, 'groupID', None):
        return None
    return park, slim, tuple(getattr(session, key, None) for key in ('charid', 'shipid', 'solarsystemid'))


def _ec_radial_target(uicore):
    # Use the current native pick only. Never look through a window or fall
    # back to a selected object elsewhere on the screen.
    try:
        if uicore.registry.GetModalWindow() is not None or _ec_active_menus(uicore):
            return None
        unused, node = uicore.uilib.PickScreenPosition(int(uicore.ScaleDpi(uicore.uilib.x)), int(uicore.ScaleDpi(uicore.uilib.y)))
        for level in range(24):
            if node is None or node is uicore.desktop:
                return None
            if getattr(node, 'destroyed', False) or not getattr(node, 'display', True):
                return None
            node_class = getattr(node, '__class__', type(node))
            if any(part in node_class.__name__.lower() for part in ('button', 'checkbox', 'edit', 'slider', 'scrollbar', 'resize')):
                return None
            modules = [getattr(kind, '__module__', '') for kind in node_class.__mro__]
            surface = any(module.startswith(('eve.client.script.ui.inflight.bracket', 'eve.client.script.ui.inflight.overview.overviewScrollEntry')) for module in modules)
            if surface:
                if not _ec_radial_visible(uicore, node):
                    return None
                data = getattr(getattr(node, 'sr', None), 'node', None)
                item_id = getattr(node, 'itemID', None) or getattr(node, 'id', None) or getattr(data, 'itemID', None)
                record = _ec_radial_record(item_id) if item_id else None
                if record is not None:
                    park, slim, identity = record
                    return dict(itemID=item_id, typeID=slim.typeID, groupID=slim.groupID, park=park, session=identity, owner=node)
                return None
            # Some native bracket labels delegate events to their bracket.
            bracket = getattr(node, 'bracket', None)
            node = bracket if bracket is not None else getattr(node, 'parent', None)
    except Exception:
        return None
    return None


def _ec_radial_visible(uicore, node):
    for level in range(24):
        if node is uicore.desktop:
            return True
        if node is None or getattr(node, 'destroyed', False) or not getattr(node, 'display', True):
            return False
        node = getattr(node, 'parent', None)
    return False


def _ec_radial_valid(uicore, target):
    try:
        if uicore.registry.GetModalWindow() is not None or not _ec_radial_visible(uicore, target['owner']):
            return False
        record = _ec_radial_record(target['itemID'])
        return record is not None and record[0] is target['park'] and record[2] == target['session'] and record[1].typeID == target['typeID'] and record[1].groupID == target['groupID']
    except Exception:
        return False


def _ec_radial_install(controller):
    service = _ec_builtins.sm.GetService('radialmenu')
    original = service.TryExpandActionMenu
    def guarded(*args, **kwargs):
        native = controller.native
        if controller.active and controller.mode.mode == 'controller' and getattr(native, 'owned', set()) and not getattr(native, 'pending', False):
            return None
        return original(*args, **kwargs)
    service.TryExpandActionMenu = guarded
    def restore():
        if service.TryExpandActionMenu is guarded:
            service.TryExpandActionMenu = original
    return restore


def _ec_radial_open(uicore, target, controller):
    from eve.client.script.ui.shared.radialMenu.radialMenu import RadialMenuSpace
    from eve.client.script.ui.shared.radialMenu.radialMenuActions import RadialMenuRangeAction, RadialMenuActioSecondLevel
    from carbonui.primitives.container import Container
    from carbonui.primitives.vectorlinetrace import VectorLineTrace
    from carbonui.primitives.fill import Fill
    from eve.client.script.ui.control.eveLabel import EveLabelSmall
    from carbon.common.script.util.format import FmtDist
    import carbonui.const as constants

    class ControllerRadial(RadialMenuSpace):
        def InitializeCenterPoint(self, attributes):
            self.originalX = self.currentCenterX = attributes.get('x', uicore.uilib.x)
            self.originalY = self.currentCenterY = attributes.get('y', uicore.uilib.y)
            self.offsetX = self.offsetY = 0
            self.cursorClipped = False

        def SetPosition(self):
            margin = max(8, (320 - self.width) / 2. + 8)
            self.left = max(margin, min(uicore.desktop.width - self.width - margin, self.currentCenterX - self.width / 2.))
            self.top = max(52, min(uicore.desktop.height - self.height - 132, self.currentCenterY - self.height / 2.))
            self.currentCenterX, self.currentCenterY = self.left + self.width / 2., self.top + self.height / 2.

        def TryRepositionMouse(self, *args, **kwargs):
            pass

        def ResetCursor(self):
            pass

        def OnGlobalMove(self, *args):
            return True

        def OnMouseUp(self, *args):
            pass

        def OnMouseUpBlocker(self, *args):
            pass

        def IsRadialMenuButtonActive(self, *args):
            return True

    if not _ec_radial_valid(uicore, target):
        return None
    layer = uicore.layer.menu
    layer.Flush()
    try:
        view = ControllerRadial(parent=layer, name='evejsControllerRadial', itemID=target['itemID'], typeID=target['typeID'],
                                slimItem=_ec_radial_record(target['itemID'])[1], clickedObject=target['owner'],
                                x=uicore.uilib.x, y=uicore.uilib.y, updateDisplayName=True, state=constants.UI_NORMAL)
    except Exception:
        for child in list(layer.children):
            if getattr(child, 'name', None) == 'evejsControllerRadial':
                child.Close()
        raise
    layer.radialMenu = view
    activation = controller.settings['bindings']['leftClick'].split('+')
    range_axis = 'UP' in activation or 'DOWN' in activation
    cancel_glyph, cancel_mask = next((name, bit) for name, bit in (('B',0x2000),('A',0x1000),('X',0x4000),('Y',0x8000),('LS',0x40)) if name not in activation)
    try:
        wheel_cursor = Container(parent=view, name='evejsControllerRadialCursor', align=constants.TOPLEFT,
                                 width=32, height=32, state=constants.UI_DISABLED, idx=0)
        for line_width, color in ((4.5,(1.,1.,1.,1.)),(2.,(1.,1.,1.,1.))):
            ring = VectorLineTrace(parent=wheel_cursor, width=32, height=32, lineWidth=line_width,
                                  state=constants.UI_DISABLED)
            for index in range(49):
                angle = index * _ec_math.pi / 24.
                ring.AddPoint((16 + 13 * _ec_math.cos(angle),16 + 13 * _ec_math.sin(angle)),color=color)
        Fill(parent=wheel_cursor, align=constants.TOPLEFT, left=14.5, top=14.5, width=3, height=3,
             state=constants.UI_DISABLED, color=(1.,1.,1.,1.))
        wheel_cursor.left, wheel_cursor.top = view.width / 2. - 16, view.height / 2. - 16
        hints = Container(parent=view, align=constants.TOPLEFT, left=(view.width - 320) / 2., top=view.height + 12,
                          width=320, height=108, state=constants.UI_DISABLED)
        for index, (glyph, label) in enumerate((('LS', 'Select'), ('RS' if range_axis else '', 'Range'), (cancel_glyph, 'Cancel'), (controller.settings['bindings']['leftClick'], 'Release'))):
            x = index * 80 + 40
            line = VectorLineTrace(parent=hints, width=320, height=30, lineWidth=1.5, state=constants.UI_DISABLED)
            if index == 1 and not range_axis:
                points = [(x-5,9),(x,4),(x+5,9),(x,4),(x,23),(x-5,18),(x,23),(x+5,18)]
            elif index == 3:
                points = [(x-18,5),(x+18,5),(x+20,7),(x+20,23),(x+18,25),(x-18,25),(x-20,23),(x-20,7),(x-18,5)]
            else:
                points = [(x + 12 * _ec_math.cos(i * _ec_math.pi / 16.), 15 + 12 * _ec_math.sin(i * _ec_math.pi / 16.)) for i in range(33)]
            for point in points:
                line.AddPoint(point, color=(1., 1., 1., .85))
            if glyph:
                EveLabelSmall(parent=hints, text='<center>' + glyph + '</center>', align=constants.TOPLEFT, left=x-19, top=7, width=38, maxLines=1,
                              state=constants.UI_DISABLED, color=(1.,1.,1.,1.))
            EveLabelSmall(parent=hints, text='<center>' + label + '</center>', align=constants.TOPLEFT, left=index*80+5, top=32, width=70,
                          state=constants.UI_DISABLED, color=(1.,1.,1.,.85))
        range_name = EveLabelSmall(parent=hints, name='evejsControllerRangeAction', text='', align=constants.TOPLEFT,
                                  left=62, top=49, width=116, maxLines=2, state=constants.UI_DISABLED, color=(1.,1.,1.,.85))
        range_value = EveLabelSmall(parent=hints, name='evejsControllerRangeValue', text='', align=constants.TOPLEFT,
                                   left=62, top=79, width=116, maxLines=1, state=constants.UI_DISABLED, color=(1.,1.,1.,1.))
    except Exception:
        view.Close()
        raise

    class RadialSession(object):
        def __init__(self):
            self.view, self.target = view, target
            self.cancel_mask = cancel_mask
            self.range_axis = range_axis
            self.finished, self.confirmed = False, False
            self.button, self.degree, self.more_started, self.expansion_degree = None, None, None, None
            self.button_key = None
            self.range_direction, self.next_range = 0, 0.
            self.range_values = {}
            self.last_range_vector, self.range_focus = None, False
            self.cursor = wheel_cursor
            self.range_name,self.range_value=range_name,range_value

        def valid(self):
            return not getattr(view, 'destroyed', False) and layer.radialMenu is view and _ec_radial_valid(uicore, target)

        def close(self):
            self.finished, self.confirmed = True, False
            if not getattr(view, 'destroyed', False):
                view.Close()

        def update(self, x, y, range_direction, now):
            if self.finished or not self.valid():
                return
            centered = _ec_math.hypot(x,y) < .04
            expanded = view.secondLayerCont.isExpanded
            if centered and self.last_range_vector and self.last_range_vector[2] == expanded and (range_direction or self.range_focus):
                x,y,unused = self.last_range_vector
                self.range_focus = True
            # The wheel owns a local cursor: absolute stick position inside a
            # circle, rather than accumulated desktop cursor movement. No OS
            # clipping or capture is installed, so physical input can take over.
            magnitude = _ec_math.hypot(x, y)
            divisor = max(1., magnitude)
            radius = max(0., min(view.width, view.height) / 2. - 18)
            wheel_cursor.left = view.width / 2. + x / divisor * radius - 16
            wheel_cursor.top = view.height / 2. - y / divisor * radius - 16
            if _ec_math.hypot(x, y) < .04:
                self.button, self.degree, self.more_started, self.expansion_degree = None, None, None, None
                self.button_key = None
                view.ResetFromCenter()
                return
            degree = _ec_math.degrees(_ec_math.atan2(x, y)) % 360
            button_layer = view.secondLayerCont if expanded else view.firstLayerCont
            if expanded and self.expansion_degree is not None:
                if abs((degree - self.expansion_degree + 180) % 360 - 180) < view.stepSize / 2. + 6:
                    return
                self.expansion_degree = None
            if self.degree is not None and abs((degree - self.degree + 180) % 360 - 180) < view.stepSize / 2. + 6:
                degree = self.degree
            button = view.FindMyButton(degree, button_layer, view.stepSize)
            button_key = (expanded,button.degree,getattr(button.actionButton,'labelPath',button.actionButton.labelText)) if button else None
            changed = button_key != self.button_key
            if changed:
                self.range_focus = False
            self.button_key = button_key
            self.button = button
            self.degree = button.degree if button else None
            view.HiliteOneButton(button, button_layer)
            view.SelectButton(None)
            if button is None:
                self.last_range_vector, self.range_focus = None, False
                view.ClearOptionRangeText()
                return
            action = button.actionButton
            if isinstance(action, RadialMenuActioSecondLevel):
                self.last_range_vector, self.range_focus = None, False
                if changed:
                    self.more_started = now
                if not expanded and self.more_started is not None and now - self.more_started >= .25:
                    view.UpdateSecondLevel(button, animate=True)
                    self.expansion_degree, self.button, self.degree = button.degree, None, None
                return
            self.more_started = None
            if isinstance(action, RadialMenuRangeAction):
                self.last_range_vector = (x,y,expanded)
                if range_direction:
                    self.range_focus = True
                ranges = list(action.rangeList)
                if not ranges:
                    return
                range_key = (expanded, button.degree, getattr(action, 'labelPath', action.labelText))
                action.currentRange = max(min(ranges), min(max(ranges), self.range_values.get(range_key, action.defaultRange)))
                if changed:
                    self.range_direction, self.next_range = 0, now
                index = min(range(len(ranges)), key=lambda i: abs(ranges[i] - action.currentRange))
                if range_direction and (range_direction != self.range_direction or now >= self.next_range):
                    index = max(0, min(len(ranges)-1, index + range_direction))
                    action.currentRange = ranges[index]
                    self.next_range = now + (.35 if range_direction != self.range_direction else .15)
                self.range_direction = range_direction
                self.range_values[range_key] = action.currentRange
                action.percOfAllRange = float(index) / max(1, len(ranges)-1)
                range_name.text='<center>'+action.labelText+'</center>'
                range_value.text='<center>'+FmtDist(action.currentRange)+'</center>'
                view.rangeCont.display = True
                view.SetOptionRangeText(FmtDist(action.currentRange), True)
                view.SetRangeCircle(button.degree, action.percOfAllRange)
                view.MoveMouseRangeCallback(True, action.currentRange, action.percOfAllRange)
            else:
                self.last_range_vector, self.range_focus = None, False
                view.ClearOptionRangeText()
                view.MoveMouseRangeCallback(False)
            view.SelectButton(button)

        def finish(self, confirm):
            selected = view.selectedBtn
            if not confirm or self.finished or not self.valid() or selected is None:
                self.close()
                return
            label = selected.actionButton.labelText
            range_value = getattr(selected.actionButton, 'currentRange', None)
            range_fraction = getattr(selected.actionButton, 'percOfAllRange', None)
            view.UpdateOptions()
            button_layer = view.secondLayerCont if view.secondLayerCont.isExpanded else view.firstLayerCont
            current = view.FindMyButton(selected.degree, button_layer, view.stepSize)
            if current is None or current.actionButton.labelText != label:
                self.close()
                return
            action = current.actionButton
            if range_value is not None:
                if not isinstance(action, RadialMenuRangeAction) or not action.rangeList or range_value < min(action.rangeList) or range_value > max(action.rangeList):
                    self.close()
                    return
                action.currentRange, action.percOfAllRange = range_value, range_fraction
            original = action.OnButtonClick
            range_callback = action.func if range_value is not None else None
            range_target = action.funcArgs if range_value is not None else None
            self.finished, self.confirmed = True, True
            def guarded_action(*args, **kwargs):
                if self.confirmed and controller.active and _ec_radial_valid(uicore, target):
                    if range_callback is not None:
                        # Native refresh/closing can replace range controls.
                        # Pin the validated native callback and selected values
                        # instead of reading a mutable action after queuing.
                        return range_callback(range_target,range_value,range_fraction)
                    return original(*args, **kwargs)
            action.OnButtonClick = guarded_action
            view.ClickButton(current)

    return RadialSession()


def _ec_neocom_open(uicore,controller,pad):
    from eve.client.script.ui.shared.neocom.neocom import neocomPanelEntries as entries
    service = _ec_builtins.sm.GetService('neocom')
    session=getattr(_ec_builtins,'session',None)
    if uicore.registry.GetModalWindow() is not None or not getattr(session,'charid',None) or getattr(session,'mutating',False):
        return None

    class NeocomSession(object):
        def __init__(self):
            self.closed=False
            self.stack=[]
            self.hooks=[]
            self.previous_mask=pad[0] | (0x10000 if pad[5]>=controller.settings['triggerThreshold'] else 0) | (0x20000 if pad[6]>=controller.settings['triggerThreshold'] else 0)
            self.direction,self.next_repeat=0,0.
            self.transition=None
            self.holds,self.fills={},{}
            self.blocked=set(button for button in (0x1000,0x2000) if pad[0] & button)
            self.epoch=controller.custom_epoch
            self.identity=self.session_identity()
            # Pause native mouse-hover expansion while controller focus moves.
            # Restore only the methods this session still owns when it ends.
            for cls in set(value for value in vars(entries).values() if isinstance(value,type) and issubclass(value,entries.PanelEntryBase)):
                for name in ('OnMouseEnter','OnMouseExit'):
                    original=cls.__dict__.get(name)
                    if original is None:continue
                    def guarded(row,*args,**kwargs):
                        return None
                    self.hooks.append((cls,name,original,guarded))
                    setattr(cls,name,guarded)

        def session_identity(self):
            return tuple(getattr(getattr(_ec_builtins,'session',None),key,None) for key in ('charid','shipid','solarsystemid','stationid','structureid'))

        def valid(self):
            return not self.closed and controller.active and controller.custom_epoch==self.epoch and self.session_identity()==self.identity and not getattr(getattr(_ec_builtins,'session',None),'mutating',False) and controller.mode.mode=='controller' and controller.native.foreground() and uicore.registry.GetModalWindow() is None and self.stack and all(not getattr(panel,'destroyed',False) and getattr(panel,'display',True) and panel in service.currPanels for panel,index in self.stack)

        def close(self):
            if self.closed:return
            self.closed=True
            try:
                service.CloseAllPanels()
            finally:
                for cls,name,original,guarded in self.hooks:
                    if cls.__dict__.get(name) is guarded:setattr(cls,name,original)
                self.hooks=[]
                self.stack=[]
                self.transition=None

        def rows(self,panel):
            rows=[]
            pending=list(getattr(getattr(panel,'main',panel),'children',[]))
            while pending and len(rows)<256:
                row=pending.pop(0)
                if getattr(row,'destroyed',False) or not getattr(row,'display',True):continue
                if isinstance(row,entries.PanelEntryBase):
                    if getattr(row,'state',0) in (1,2):continue
                    enabled=getattr(row,'IsEnabled',None)
                    if callable(enabled) and not enabled():continue
                    x,y,w,h=row.GetAbsolute()
                    if w>0 and h>0:rows.append(row)
                else:pending.extend(list(getattr(row,'children',[])))
            return sorted(rows,key=lambda row:row.GetAbsolute()[1])

        def focus(self,index,now):
            panel,old_index=self.stack[-1]
            rows=self.rows(panel)
            if not rows:return False
            index=max(0,min(len(rows)-1,index))
            for row in rows:row.SetDeselected()
            row=rows[index]
            row.SetSelected()
            self.stack[-1]=(panel,index)
            self.transition=(now,controller.native.position(),row)
            return True

        def selected(self):
            panel,index=self.stack[-1]
            rows=self.rows(panel)
            return rows[index] if 0<=index<len(rows) else None

        def is_group(self,row):
            data=getattr(row,'btnData',None)
            return isinstance(row,(entries.PanelEntryGroup,entries.PanelEntryBookmarks)) or callable(getattr(row,'ToggleNeocomPanel',None)) and not hasattr(data,'wnd') and len(getattr(data,'children',[]))>1

        def enter(self,now):
            row=self.selected()
            if row is None or not self.is_group(row):return
            row.ToggleNeocomPanel()
            panel=getattr(row,'_openNeocomPanel',None)
            if panel is not None and not getattr(panel,'destroyed',False):
                self.stack.append((panel,0))
                if not self.focus(0,now):
                    self.stack.pop()
                    service.ClosePanel(panel)
                    self.focus(self.stack[-1][1],now)

        def back(self,now):
            if len(self.stack)>1:
                panel,index=self.stack.pop()
                if panel in service.currPanels:service.ClosePanel(panel)
                self.focus(self.stack[-1][1],now)

        def animate(self,now):
            if not self.transition:return
            started,start,row=self.transition
            if getattr(row,'destroyed',False):return
            dx,dy,dw,dh=uicore.desktop.GetAbsolute()
            x,y,w,h=row.GetAbsolute()
            left,top,sw,sh=controller.native.bounds()
            target=(left+(x+w/2.-dx)*sw/dw,top+(y+h/2.-dy)*sh/dh)
            panel,index=self.stack[-1]
            px,py,pw,ph=panel.GetAbsolute()
            limits=(left+(px-dx)*sw/dw,top+(py-dy)*sh/dh,left+(px+pw-dx)*sw/dw-1,top+(py+ph-dy)*sh/dh-1)
            t=max(0.,min(1.,(now-started)/.14))
            ease=t*t*(3.-2.*t)
            start=(max(limits[0],min(limits[2],start[0])),max(limits[1],min(limits[3],start[1])))
            controller.native.move(max(limits[0],min(limits[2],start[0]+(target[0]-start[0])*ease)),max(limits[1],min(limits[3],start[1]+(target[1]-start[1])*ease)))
            if t>=1.:self.transition=None

        def step(self,pad,now):
            if not self.valid():return False
            mask=pad[0] | (0x10000 if pad[5]>=controller.settings['triggerThreshold'] else 0) | (0x20000 if pad[6]>=controller.settings['triggerThreshold'] else 0)
            rising=mask & ~self.previous_mask
            self.previous_mask=mask
            if rising & 4:self.back(now)
            elif rising & 8:self.enter(now)
            direction=(1 if mask & 2 else 0)-(1 if mask & 1 else 0)
            if direction and (direction!=self.direction or now>=self.next_repeat):
                self.focus(self.stack[-1][1]+direction,now)
                self.next_repeat=now+(.35 if direction!=self.direction else .12)
            self.direction=direction
            if not self.valid():return False
            self.fills={}
            for button,indicator in ((0x2000,2),(0x1000,1)):
                if button==0x1000 and mask & 0x2000:
                    self.holds.pop(button,None)
                    continue
                if not mask & button:
                    self.blocked.discard(button)
                    self.holds.pop(button,None)
                    continue
                if button in self.blocked:continue
                row=self.selected()
                key=(id(self.stack[-1][0]),id(row)) if button==0x1000 else None
                hold=self.holds.get(button)
                if hold is None or hold[1]!=key:
                    hold=(now,key)
                    self.holds[button]=hold
                progress=min(1.,max(0.,(now-hold[0])*1000./controller.settings['clickHoldMilliseconds']))
                self.fills[indicator]=progress
                if progress>=1.:
                    self.blocked.add(button)
                    self.holds.pop(button,None)
                    if button==0x2000:return False
                    if row is not None:
                        if self.is_group(row):self.enter(now)
                        else:
                            # Use the row's native command/window/bookmark callback.
                            row.OnClick()
                            return False
            self.animate(now)
            return True

    navigation=NeocomSession()
    try:
        service.CloseAllPanels()
        panel=service.ShowEveMenu()
        navigation.stack=[(panel,0)]
        if not navigation.valid() or not navigation.focus(0,_ec_time.time()):
            navigation.close()
            return None
        return navigation
    except Exception:
        navigation.close()
        raise


def _ec_active_menus(uicore):
    layers = getattr(uicore, 'layer', None)
    menus = [getattr(layers, name, None) for name in ('menu', 'utilmenu')]
    menus = [menu for menu in menus if menu is not None and getattr(menu, 'display', False) and
             any(getattr(child, 'display', False) and not getattr(child, 'destroyed', False) for child in getattr(menu, 'children', []))]
    # Neocom panels are maintained separately from context-menu layers.
    service = getattr(getattr(_ec_builtins, 'sm', None), 'services', {}).get('neocom')
    for panel in getattr(service, 'currPanels', []):
        if panel is not None and getattr(panel, 'display', False) and not getattr(panel, 'destroyed', False) and panel not in menus:
            menus.append(panel)
    return menus


def _ec_target_bounds(uicore, node):
    desktop = getattr(uicore, 'desktop', None)
    uilib = getattr(uicore, 'uilib', None)
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
        # Keep attraction inside open menu layers, including their submenus.
        menus = _ec_active_menus(uicore)
        if menus and not any(menu in chain for menu in menus):
            return None
        # Native mouseOver supplies EVE's hit-test result, respecting occlusion.
        # Take the nearest enabled clickable ancestor, never a nearby guessed box.
        if any(getattr(ancestor, 'destroyed', False) or not getattr(ancestor, 'display', True) for ancestor in chain):
            return None
        for candidate in chain:
            if getattr(candidate, 'destroyed', False) or not getattr(candidate, 'display', True):
                return None
            kind = type(candidate).__name__.lower()
            if any(part in kind for part in ('edit', 'slider', 'scrollbar', 'resize')):
                return None
            has_handler = getattr(candidate, 'HasEventHandler', None)
            entry = getattr(candidate, 'menuEntryData', None)
            neocom = getattr(type(candidate), '__module__', '').endswith('.neocomPanelEntries') and getattr(candidate, 'btnData', None) is not None
            # Native context-menu rows execute on mouse-up rather than OnClick.
            if not callable(has_handler) or not (has_handler('OnClick') or (entry is not None or neocom) and has_handler('OnMouseUp')):
                continue
            if entry is not None:
                enabled = getattr(entry, 'IsEnabled', None)
                interactable = getattr(candidate, 'IsInteractable', None)
                if callable(enabled) and not enabled() or callable(interactable) and not interactable():
                    continue
            if getattr(candidate, 'state', 0) in (1, 2):
                continue
            is_enabled = getattr(candidate, 'IsEnabled', None)
            if callable(is_enabled) and not is_enabled():
                return None
            x, y, w, h = candidate.GetAbsolute()
            if w < 6 or h < 6 or w > (min(dw, 960) if entry is not None or neocom else 480) or h > 128 or w * h > 72000:
                return None
            x, y = x - dx, y - dy
            if x < 0 or y < 0 or x + w > dw or y + h > dh:
                return None
            return {'id': str(id(candidate)), 'x': float(x) / dw, 'y': float(y) / dh,
                    'w': float(w) / dw, 'h': float(h) / dh}
    except Exception:
        return None
    return None


_ec_snap_cache = None


def _ec_snap_targets(uicore, radius):
    global _ec_snap_cache
    try:
        px, py = uicore.ScaleDpi(uicore.uilib.x), uicore.ScaleDpi(uicore.uilib.y)
        now = _ec_time.time()
        modal_id = (id(uicore), radius, id(uicore.registry.GetModalWindow()), uicore.desktop.GetAbsolute(), tuple((id(menu), tuple(id(child) for child in getattr(menu, 'children', []) if getattr(child, 'display', False) and not getattr(child, 'destroyed', False))) for menu in _ec_active_menus(uicore)))
        if _ec_snap_cache and _ec_snap_cache[4] == modal_id and now - _ec_snap_cache[0] < .04 and _ec_math.hypot(px - _ec_snap_cache[1], py - _ec_snap_cache[2]) < 2:
            return _ec_snap_cache[3]
        targets, neighbors = {}, {}
        points = [(px, py)]
        for distance in (radius * .25, radius * .5, radius):
            for index in range(8):
                angle = index * _ec_math.pi / 4.
                points.append((px + _ec_math.cos(angle) * distance, py + _ec_math.sin(angle) * distance))
        for x, y in points:
            unused, node = uicore.uilib.PickScreenPosition(int(x), int(y))
            target = _ec_target_bounds(uicore, node)
            if target is not None:
                targets[target['id']] = target
            # Recover small adjacent controls between sample rays. Enumerate
            # only local siblings and confirm each through native picking.
            for level in range(3):
                if node is None or node is uicore.desktop:
                    break
                for child in list(getattr(getattr(node, 'parent', None), 'children', []))[:128]:
                    neighbors[id(child)] = child
                node = getattr(node, 'parent', None)
        dx, dy, dw, dh = uicore.desktop.GetAbsolute()
        for node in list(neighbors.values())[:256]:
            target = _ec_target_bounds(uicore, node)
            if target is None or target['id'] in targets:
                continue
            tx, ty = uicore.ScaleDpi(dx + target['x'] * dw), uicore.ScaleDpi(dy + target['y'] * dh)
            tw, th = uicore.ScaleDpi(target['w'] * dw), uicore.ScaleDpi(target['h'] * dh)
            if _ec_math.hypot(max(tx - px, 0., px - tx - tw), max(ty - py, 0., py - ty - th)) > radius:
                continue
            unused, picked = uicore.uilib.PickScreenPosition(int(max(tx + 1, min(tx + tw - 1, px))), int(max(ty + 1, min(ty + th - 1, py))))
            visible = _ec_target_bounds(uicore, picked)
            if visible is not None and visible['id'] == target['id']:
                targets[target['id']] = target
        result = []
        for target in targets.values():
            cx = uicore.ScaleDpi(dx + (target['x'] + target['w'] / 2.) * dw)
            cy = uicore.ScaleDpi(dy + (target['y'] + target['h'] / 2.) * dh)
            unused, picked = uicore.uilib.PickScreenPosition(int(cx), int(cy))
            visible = _ec_target_bounds(uicore, picked)
            if visible is not None and visible['id'] == target['id']:
                result.append(target)
        result.sort(key=lambda target: target['id'])
        _ec_snap_cache = (now, px, py, result, modal_id)
        return result
    except Exception:
        return []


def _ec_snap_target(uicore, radius):
    targets = _ec_snap_targets(uicore, radius)
    if not targets:
        return None
    dx, dy, dw, dh = uicore.desktop.GetAbsolute()
    return min(targets, key=lambda target: _ec_math.hypot(dx + (target['x'] + target['w'] / 2.) * dw - uicore.uilib.x,
                                                        dy + (target['y'] + target['h'] / 2.) * dh - uicore.uilib.y))


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


class _QueuedPark(object):
    def __init__(self, original, dispatch):
        self.original, self.dispatch = original, dispatch

    def __getattr__(self, name):
        return getattr(self.original, name)

    def CmdGotoDirection(self, *args):
        steer = getattr(self.original, 'CmdSteerDirection', None)
        if callable(steer) and _ec_predict_heading(args):
            self.dispatch(steer, *args)
        else:
            self.dispatch(self.original.CmdGotoDirection, *args)


def _ec_predict_heading(direction):
    # Reuse native manual-flight rotation prediction on its private simulation
    # ball. Do not change the authoritative ship ball or emit repeat steering.
    try:
        manager = getattr(_ec_builtins, 'sm', None)
        service = getattr(manager, 'services', {}).get('flightControls')
        if service is None and manager is not None:
            service = manager.GetService('flightControls')
        simulation = getattr(service, 'simulation', None)
        session = getattr(_ec_builtins, 'session', None)
        if simulation is None or not getattr(service, 'running', False) or getattr(getattr(simulation, 'ship', None), 'id', None) != getattr(session, 'shipid', None):
            return False
        if not simulation.CanControl():
            return False
        import blue
        simulation.AttachBalls()
        simulation.direction = tuple(direction)
        simulation.lastCalled = blue.os.GetSimTime()
        simulation.controlling = True
        try:
            simulation.UpdateDirection()
        finally:
            simulation.controlling = False
        return True
    except Exception:
        return False


class _QueuedMichelle(object):
    def __init__(self, original, dispatch):
        self.original, self.dispatch = original, dispatch

    def __getattr__(self, name):
        return getattr(self.original, name)

    def GetRemotePark(self):
        park = self.original.GetRemotePark()
        return _QueuedPark(park, self.dispatch) if park is not None else None


class _QueuedServices(object):
    def __init__(self, original, dispatch):
        self.original, self.dispatch = original, dispatch

    def __getattr__(self, name):
        return getattr(self.original, name)

    def GetService(self, name):
        service = self.original.GetService(name)
        return _QueuedMichelle(service, self.dispatch) if name == 'michelle' else service


def _ec_call_center_direction(native, camera, uicore, dispatch=None):
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
    if dispatch is not None:
        private['sm'] = _QueuedServices(namespace.get('sm', getattr(_ec_builtins, 'sm', None)), dispatch)
    centered = types.FunctionType(code, private, 'EveControllerCameraCenterFlight', defaults, closure)
    return centered(camera)


def _ec_navigation(action, uicore, dispatch=None):
    session = getattr(_ec_builtins, 'session', None)
    sm = getattr(_ec_builtins, 'sm', None)
    if sm is None or session is None or not getattr(session, 'charid', None) or not getattr(session, 'shipid', None):
        return 'Navigation unavailable: character not ready'
    if getattr(session, 'mutating', False) or not getattr(session, 'solarsystemid', None) or getattr(session, 'stationid', None) or getattr(session, 'structureid', None):
        return 'Navigation unavailable: not flying in space'
    if action == 'stop':
        if dispatch is None:
            uicore.cmd.CmdStopShip()
        else:
            dispatch(uicore.cmd.CmdStopShip)
        return 'Stop ship requested'
    if action != 'fly':
        return 'Navigation unavailable: unknown action'
    camera = sm.GetService('sceneManager').GetActiveSpaceCamera()
    if camera is None or sm.GetService('michelle').GetRemotePark() is None:
        return 'Navigation unavailable: space camera not ready'
    from eve.client.script.ui.camera.cameraUtil import SetShipDirection
    # Queue only the remote request. Native notification/prediction runs now,
    # without waiting for the server reply or blocking controller polling.
    _ec_call_center_direction(SetShipDirection, camera, uicore, dispatch)
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
