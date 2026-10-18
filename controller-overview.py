# Persistent controller-mode presentation for each native Overview window.
class _OverviewChrome(object):
    def __init__(self, navigation, window):
        self.nav, self.c, self.window = navigation, navigation.c, window
        self.group = window.tabGroup
        self.glyphs, self.footer_groups = [], []
        self.padding_hook = self.footer = None
        try:
            self.add_glyphs()
            self.add_footer()
        except Exception:
            self.close()
            raise

    def add_glyphs(self):
        from carbonui.primitives.sprite import Sprite
        import carbonui.const as const
        window, group = self.window, self.group
        original = window._get_tab_group_padding
        def padding():
            left, top, right, bottom = original()
            return (left + 52, top, right + 52, bottom)
        self.padding_hook = (window, original, padding, window.__dict__.get('_get_tab_group_padding'))
        window._get_tab_group_padding = padding
        window._update_tabs_padding()
        menu = self.c.menu
        for token, align in (('LB', const.CENTERLEFT), ('RB', const.CENTERRIGHT)):
            name = menu.icon_name(token) if menu else token.lower()
            path = getattr(menu, 'button_icons', {}).get(name)
            if path:
                self.glyphs.append(Sprite(name='controllerOverview'+token, parent=group, align=align,
                                         left=-42, width=32, height=32, texturePath=path,
                                         color=(1., 1., 1., .8), state=const.UI_DISABLED))

    def add_footer(self):
        from carbonui.primitives.container import Container
        from carbonui.primitives.fill import Fill
        from carbonui.primitives.sprite import Sprite
        from eve.client.script.ui.control.eveLabel import EveLabelSmall
        import carbonui.const as const
        # Dock before the native TOALL scroll, reserving real list space. The
        # window's own background, padding and resize handle remain native.
        self.footer = Container(name='controllerOverviewFooter', parent=self.window.content,
                                align=const.TOBOTTOM, height=32, idx=0, state=const.UI_DISABLED)
        Fill(parent=self.footer, align=const.TOTOP, height=1, color=(1., 1., 1., .15), state=const.UI_DISABLED)
        for tokens, text in ((('UP', 'DOWN'), 'Browse'), (('LB',), 'Hold: Menu'),
                             (('X',), '0.5s: Lock'), (('Y',), '0.5s: Orbit'), (('A',), '0.5s: Approach'),
                             (('B',), '0.5s: Track On Release'), (('B',), '1s: Exit')):
            group = Container(parent=self.footer, align=const.TOPLEFT, height=24, clipChildren=True, state=const.UI_DISABLED)
            icons = [Sprite(parent=group, align=const.CENTERLEFT, left=index*24, width=24, height=24,
                            color=(1., 1., 1., .8), state=const.UI_DISABLED) for index in range(4 if len(tokens) == 2 else len(tokens))]
            label = EveLabelSmall(parent=group, align=const.CENTERLEFT, left=len(tokens)*24+6,
                                 text=text, fontsize=13, maxLines=1, color=(1., 1., 1., .8), state=const.UI_DISABLED)
            self.footer_groups.append((group, icons, label, tokens))
        self.update_footer()

    def update_footer(self):
        if self.footer is None:return
        menu, context = self.c.menu, self.c.context
        focused = self.nav.window is self.window
        in_menu = focused and (self.nav.context_wait or context is not None and context.owner is self.nav)
        for glyph in self.glyphs:
            opacity = 1. if focused else .4
            if getattr(glyph, 'opacity', None) != opacity:glyph.opacity = opacity
        visible = []
        for index, (group, icons, label, tokens) in enumerate(self.footer_groups):
            group.display = not in_menu or index in (0, 1, 6)
            if not group.display:continue
            if index == 0:
                tokens, text = (('UP', 'DOWN'), 'Browse') if focused else (tuple(filter(None, self.c.settings['bindings']['overview'].split('+'))), 'Focus Overview')
                if label.text != text:label.text = text
            elif index == 1:
                tokens, text = (('RB',), 'Hold: Select') if in_menu else (('LB',), 'Hold: Menu')
                if label.text != text:label.text = text
            elif index == 6:
                text = 'Hold: Back' if in_menu else '1s: Exit'
                if label.text != text:label.text = text
            for slot, icon in enumerate(icons):
                icon.display = slot < len(tokens)
                if not icon.display:continue
                icon.left = slot*24
                token = tokens[slot]
                name = menu.icon_name(token) if menu else token.lower()
                path = getattr(menu, 'button_icons', {}).get(name)
                if path and getattr(icon, 'texturePath', None) != path:icon.texturePath = path
            if label.left != len(tokens)*24+6:label.left = len(tokens)*24+6
            enabled = focused and self.nav.selected() is not None
            if index in (2, 3, 4, 5):enabled = ('lock', 'orbit', 'approach', 'track')[index-2] in self.nav.actions
            group.opacity = .4 if (not focused and index != 0 or not in_menu and index in (1, 2, 3, 4, 5) and not enabled) else 1.
            width = len(tokens)*24 + 6 + int(getattr(label, 'textwidth', len(label.text)*7))
            visible.append((group, width))
        width = max(0, self.footer.GetAbsolute()[2] - 24)
        rows, row, used = [], [], 0
        for group, requested in visible:
            size = min(width, requested)
            if row and used + 12 + size > width:
                rows.append(row);row, used = [], 0
            row.append((group, size));used += size + (12 if len(row)>1 else 0)
        if row:rows.append(row)
        wx, wy, ww, wh = self.window.GetAbsolute()
        cx, cy, cw, ch = self.window.content.GetAbsolute()
        padding = (0, 0, 0, -max(0, wy+wh-1-cy-ch))
        if getattr(self.footer, 'padding', None) != padding:self.footer.padding = padding
        self.footer.height = 8 + len(rows)*24 + max(0, len(rows)-1)*4
        for index, row in enumerate(rows):
            total = sum(size for group, size in row)
            gap = (width-total)/float(len(row)-1) if len(row)>1 else 0
            left = 12 if len(row)>1 else 12+(width-total)/2.
            for group, size in row:
                group.left, group.top, group.width = left, 4+index*28, size
                left += size+gap

    def close(self):
        if self.footer is not None and not getattr(self.footer, 'destroyed', False):self.footer.Close()
        self.footer = None
        self.footer_groups = []
        for glyph in self.glyphs:
            if not getattr(glyph, 'destroyed', False):glyph.Close()
        self.glyphs = []
        if self.padding_hook:
            window, original, wrapper, previous = self.padding_hook
            if window.__dict__.get('_get_tab_group_padding') is wrapper:
                del window._get_tab_group_padding
                if previous is not None:window._get_tab_group_padding = previous
                if not getattr(window, 'destroyed', False):window._update_tabs_padding()
            self.padding_hook = None


# Controller focus for the existing Overview. Python 2.7 compatible.
class _OverviewNavigation(object):
    def __init__(self, controller):
        self.c = controller
        self.window = self.last_window = self.returning = None
        self.previous_open = False
        self.item = self.tab = None
        self.edits, self.fonts, self.views = {}, {}, {}
        self.holds, self.fills = {}, {}
        self.serial = 0
        self.busy = None
        self.context_wait = self.right_pending = False
        self.reported = False
        self.loading = self.first_pending = False
        self.wrapped = None
        self.name_detail = self.name_measure = None
        self.name_short = None
        self.name_offsets = {}
        self.rail = None
        self.row_hook = None
        self.icon_offset = self.shadow = None
        self.pointer = {}
        self.actions, self.action_holds = {}, {}
        self.action_query = None
        self.next_actions = 0.

    @property
    def active(self):
        return self.window is not None or self.returning is not None

    @property
    def view(self):
        return self.views.get(self.window) or self.views.get(self.last_window) or next(iter(self.views.values()), None)

    @property
    def footer(self):return self.view.footer if self.view else None

    @property
    def footer_groups(self):return self.view.footer_groups if self.view else []

    @property
    def glyphs(self):return self.view.glyphs if self.view else []

    def update_footer(self):
        for view in self.views.values():view.update_footer()

    def present(self):
        from eve.client.script.ui.inflight.overview.overviewWindow import OverviewWindow
        windows = [window for window in self.c.ui.registry.GetWindows()
                   if isinstance(window, OverviewWindow) and self.available(window)]
        for window, view in list(self.views.items()):
            if window not in windows or view.group is not window.tabGroup or getattr(view.footer, 'destroyed', False):
                view.close();del self.views[window]
        for window in windows:
            if window not in self.views:self.views[window] = _OverviewChrome(self, window)
        self.update_footer()

    def identity(self):
        session = getattr(_ec_builtins, 'session', None)
        return tuple(getattr(session, key, None) for key in ('charid', 'shipid', 'solarsystemid', 'stationid', 'structureid'))

    def available(self, window):
        return (window is not None and not getattr(window, 'destroyed', False) and
                _ec_radial_visible(self.c.ui, window) and not window.IsMinimized() and not window.IsCollapsed() and
                getattr(window, 'scroll', None) is not None and getattr(window, 'tabGroup', None) is not None)

    def safe(self):
        c = self.c
        return (c.active and c.mode.mode == 'controller' and c.native.foreground() and
                (c.settings.get('controllerModeLocked', False) or not getattr(c.native, 'pending', False) and not getattr(c.native, 'physical_buttons', None)) and
                not getattr(c.ui, 'dragObject', None) and c.ui.registry.GetModalWindow() is None and
                not getattr(getattr(_ec_builtins, 'session', None), 'mutating', False) and self.stamp == self.identity())

    def nodes(self):
        if self.window is None:return []
        return [node for node in self.window.scroll.GetNodes()
                if getattr(node, 'itemID', None) is not None and not getattr(node, 'leavingOverview', False)]

    def selected(self):
        return next((node for node in self.nodes() if node.itemID == self.item), None)

    def row_panel(self, node):
        panel = getattr(node, 'panel', None)
        if panel is not None and not getattr(panel, 'destroyed', False) and getattr(getattr(panel, 'sr', None), 'node', None) is node:
            return panel

    def reflow(self, target=None, rebuild=True, retired=()):
        scroll = self.window.scroll
        pending = getattr(scroll, 'updatePositionThread', None) is not None
        # BasicDynamicScroll's synchronous UpdatePosition clears its thread
        # handle. Cancel the old worker first, and prevent ShowNodeIdx from
        # creating another worker midway through the same layout transaction.
        with scroll.KillUpdateThreadAndBlock():
            if retired:scroll.RemoveNodes(retired, updateScroll=False)
            if rebuild or retired:scroll.UpdateNodesWidthAndPosition()
            before = scroll._position
            if target is not None:
                nodes = list(scroll.GetNodes())
                index = next((i for i, node in enumerate(nodes) if node is target), None)
                if index is not None:scroll.ShowNodeIdx(index)
            if rebuild or retired or pending or before != scroll._position:
                # Overview owns entry loading and dynamic data. Reflow only;
                # loading here can yield into tab/filter updates mid-layout.
                scroll.UpdatePosition(loadNodes=False)

    def context_valid(self):
        return (self.window is not None and self.safe() and self.available(self.window) and
                self.tab == self.window.GetSelectedTabID() and self.selected() is not None and self.busy is None)

    def choose_window(self):
        from eve.client.script.ui.inflight.overview.overviewWindow import OverviewWindow
        windows = [window for window in self.c.ui.registry.GetWindows()
                   if isinstance(window, OverviewWindow) and self.available(window)]
        # Honor the window under the pointer first, then the most recently used
        # Overview. Multiple Overview windows keep their own native tab sets.
        hover = getattr(self.c.ui.uilib, 'mouseOver', None)
        for window in windows:
            if _ec_ui_under(hover, window):return window
        if self.last_window in windows:return self.last_window
        active = getattr(self.c.ui.registry, 'GetActive', lambda:None)()
        for window in windows:
            if active is window or _ec_ui_under(active, window):return window
        return windows[0] if windows else None

    def restore_icon_offset(self):
        if self.icon_offset:
            icon, original, assigned = self.icon_offset
            if not getattr(icon, 'destroyed', False) and icon.left == assigned:icon.left = original
            self.icon_offset = None

    def update_shadow(self, panel):
        if self.shadow and (getattr(self.shadow[0], 'destroyed', False) or self.shadow[0].parent is not self.window.scroll.sr.clipper):
            if not getattr(self.shadow[0], 'destroyed', False):self.shadow[0].Close()
            self.shadow = None
        if panel is None or getattr(panel, 'destroyed', False):
            if self.shadow:self.shadow[0].display = False
            return
        if self.shadow is None:
            from carbonui.primitives.container import Container
            from carbonui.primitives.fill import Fill
            import carbonui.const as const
            # Overlay only the rows' outer three pixels, inside the native
            # scroll clipper. Separate one-pixel bands feather to transparent.
            root = Container(name='controllerOverviewShadow', parent=self.window.scroll.sr.clipper,
                             align=const.TOALL, idx=0, clipChildren=True, state=const.UI_DISABLED)
            strips = [Fill(parent=root, align=const.TOPLEFT, height=1, color=(0., 0., 0., alpha),
                           state=const.UI_DISABLED) for alpha in (.015, .04, .075, .10, .05, .02)]
            self.shadow = (root, strips)
        root, strips = self.shadow
        root.display = True
        cx, cy, cw, ch = root.GetAbsolute()
        x, y, width, height = panel.GetAbsolute()
        for index, strip in enumerate(strips):
            strip.left, strip.width = x-cx, width
            strip.top = y-cy-3+index if index < 3 else y-cy+height+index-3

    def update_rail(self, node):
        panel = self.row_panel(node)
        self.watch_row(panel)
        if self.rail and (self.rail[0] is not panel or self.rail[1] is not node or getattr(panel, 'destroyed', False)):
            if not getattr(self.rail[2], 'destroyed', False):self.rail[2].Close()
            self.rail = None
            self.restore_icon_offset()
        if panel is not None and not getattr(panel, 'destroyed', False) and self.rail is None:
            from carbonui.primitives.fill import Fill
            import carbonui.const as const
            # A disabled child follows the native row's animated height and
            # clipping; it never changes columns or captures mouse input.
            self.rail = (panel, node, Fill(name='controllerOverviewSelection', parent=panel, align=const.TOLEFT,
                                         width=2, padding=(0, 1, 0, 1), color=(1., 1., 1., .9),
                                         state=const.UI_DISABLED, idx=0))
        icon = getattr(panel, 'mainIcon', None)
        if self.icon_offset and self.icon_offset[0] is not icon:self.restore_icon_offset()
        if icon is not None and not getattr(icon, 'destroyed', False):
            if self.icon_offset is None or icon.left != self.icon_offset[2]:
                original = icon.left
                icon.left = original + 6
                self.icon_offset = (icon, original, icon.left)
        self.update_shadow(panel)

    def begin(self, window, pad, now):
        c = self.c
        self.window = self.last_window = window
        self.origin, self.stamp = c.native.position(), self.identity()
        self.tab, self.item = window.GetSelectedTabID(), None
        self.blocked, self.previous = pad[0], 0
        self.direction, self.next_repeat = 0, 0.
        self.holds, self.fills = {}, {}
        self.transition = None
        self.pointer.clear()
        c.custom_epoch += 1
        c.native.release();c.gestures.reset();c.magnet.reset();c.motion.reset();c.ui_navigation.clear()
        c.window_close.cancel()
        if c.combat:c.combat.suspend(pad)
        front = getattr(window, 'SetOrder', None)
        if callable(front):front(0)
        c.ui.registry.SetFocus(window)
        if window not in self.views:self.views[window] = _OverviewChrome(self, window)
        nodes = self.nodes()
        self.first_pending = not bool(nodes)
        self.loading = False
        if nodes:self.focus(nodes[0], now)
        self.update_footer()

    def base_height(self, node, fallback):
        fixed = getattr(node, 'fixedHeight', None)
        if fixed:return fixed
        dynamic = getattr(node, 'dynamicHeightFunction', None)
        if callable(dynamic):return dynamic(node, self.window.scroll.sr.clipper.GetAbsolute()[2])
        return fallback

    def restore_fonts(self, keep=None):
        for key, record in list(self.fonts.items()):
            label, base, assigned, panel = record
            if panel is keep and not getattr(label, 'destroyed', False):continue
            if not getattr(label, 'destroyed', False) and label.measurer.fontSize == assigned:
                label.measurer.fontSize = base
                label._columnWidthDirty = True
                label.text = label.text
            del self.fonts[key]

    def resize_fonts(self, panel, fraction):
        for label in getattr(panel, 'columnLabels', ()):
            if getattr(label, 'destroyed', False) or not hasattr(label, 'measurer'):continue
            key = id(label)
            record = self.fonts.get(key)
            current = label.measurer.fontSize
            base = record[1] if record and current == record[2] else current
            size = max(1, int(round(base * (1. + .17 * fraction))))
            if size != current:
                label.measurer.fontSize = size
                label._columnWidthDirty = True
                label.text = label.text
            self.fonts[key] = (label, base, size, panel)

    def restore_row_hook(self):
        if self.row_hook is None:return
        panel, previous, wrapper = self.row_hook
        if panel.__dict__.get('UpdateColumns') is wrapper:
            if previous is None:del panel.UpdateColumns
            else:panel.UpdateColumns = previous
        self.row_hook = None

    def watch_row(self, panel):
        if self.row_hook is not None and self.row_hook[0] is panel:return
        self.restore_row_hook()
        original = getattr(panel, 'UpdateColumns', None)
        if panel is None or getattr(panel, 'destroyed', False) or not callable(original):return
        def update(*args, **kwargs):
            result = original(*args, **kwargs)
            node = self.selected()
            if (self.window is not None and not getattr(panel, 'destroyed', False) and
                    getattr(node, 'panel', None) is panel and getattr(getattr(panel, 'sr', None), 'node', None) is node):
                fraction = self.edits.get(id(node), [None, None, 0.])[2]
                self.resize_fonts(panel, fraction)
                self.wrap_name(node)
                self.update_rail(node)
            return result
        self.row_hook = (panel, panel.__dict__.get('UpdateColumns'), update)
        panel.UpdateColumns = update

    def restore_name(self):
        for obj, original, assigned in self.name_offsets.values():
            if not getattr(obj, 'destroyed', False) and getattr(obj, 'top', 0) == assigned:obj.top = original
        self.name_offsets = {}
        if self.name_detail is not None and not getattr(self.name_detail, 'destroyed', False):self.name_detail.Close()
        self.name_detail = None
        if self.wrapped is not None:
            panel, node, label, display, wrapped, opacity = self.wrapped
            if not getattr(wrapped, 'destroyed', False):wrapped.Close()
            if not getattr(label, 'destroyed', False) and not label.display:label.display = display
        self.wrapped = None

    def offset_name_columns(self, panel, offset):
        objects = [obj for obj in list(getattr(panel, 'columnLabels', ())) + [getattr(panel, 'mainIcon', None)]
                   if obj is not None and not getattr(obj, 'destroyed', False)]
        for key, (obj, original, assigned) in list(self.name_offsets.items()):
            if obj not in objects:
                if not getattr(obj, 'destroyed', False) and getattr(obj, 'top', 0) == assigned:obj.top = original
                del self.name_offsets[key]
        for obj in objects:
            record = self.name_offsets.get(id(obj))
            current = getattr(obj, 'top', 0)
            original = record[1] if record and current == record[2] else current
            assigned = original + offset
            if current != assigned:obj.top = assigned
            self.name_offsets[id(obj)] = (obj, original, assigned)

    def wrap_name(self, node):
        if not self.c.settings['overviewRowExpansion']:
            self.restore_name();return
        panel = self.row_panel(node)
        name = getattr(node, 'display_NAME', None)
        label = next((label for label in getattr(panel, 'columnLabels', ())
                      if name and label.text == name and getattr(label, 'columnWidth', 0) > 0), None)
        if self.wrapped and (self.wrapped[0] is not panel or self.wrapped[1] is not node or self.wrapped[2] is not label):self.restore_name()
        if label is None:return
        from eve.client.script.ui.control.eveLabel import EveLabelSmall
        size = max(1, int(round(label.ReverseScaleDpi(label.measurer.fontSize))))
        style = getattr(EveLabelSmall, 'default_fontStyle', None)
        def measure(text):
            return self.c.ui.font.GetTextWidth(text, fontsize=size, font=style, fontStyle=style)
        measure_key = (name, size, style)
        if self.name_measure is None or self.name_measure[0] != measure_key:
            self.name_measure = (measure_key, measure(name))
        base = self.fonts.get(id(label), (None, label.measurer.fontSize))[1]
        detail_size = max(1, int(round(label.ReverseScaleDpi(base))))
        space = min(2*(detail_size+2), max(0, node.height-size-12))
        lines = max(1, min(2, int(space / float(detail_size+2))))
        if self.name_measure[1] <= label.columnWidth:
            self.restore_name();return
        short_key = (name, size, style, label.columnWidth)
        if self.name_short is None or self.name_short[0] != short_key:
            suffix = u'...'
            low, high = 0, len(name)
            while low < high:
                middle = (low+high+1)//2
                if measure(name[:middle]+suffix) <= label.columnWidth:low = middle
                else:high = middle-1
            short = name[:low].rstrip()+suffix if measure(suffix) <= label.columnWidth else ''
            self.name_short = (short_key, short)
        width = max(0, panel.GetAbsolute()[2])
        left = max(10, min(getattr(obj, 'columnPosition', label.columnPosition)
                           for obj in panel.columnLabels if not getattr(obj, 'destroyed', False)))
        detail_width = max(0, width-left-10)
        if detail_width < detail_size*3:
            self.restore_name();return
        if self.wrapped is None:
            from carbonui import TextColor
            import carbonui.const as const
            wrapped = EveLabelSmall(parent=panel, name='controllerOverviewName', align=const.CENTERLEFT,
                                   state=const.UI_NORMAL, text='', maxLines=1, fontsize=size,
                                   showEllipsis=False, autoFadeSides=False, color=TextColor.HIGHLIGHT)
            self.name_detail = EveLabelSmall(parent=panel, name='controllerOverviewNameDetail', align=const.CENTERLEFT,
                                            state=const.UI_NORMAL, text='', maxLines=lines, fontsize=detail_size,
                                            showEllipsis=True, color=TextColor.HIGHLIGHT)
            # Keep native row clicks, drags and object menus under the text.
            for target in (wrapped, self.name_detail):
                def get_hint(obj=target):return obj._controllerOverviewName
                target.GetHint = get_hint
                for event in ('GetMenu', 'OnMouseDown', 'OnMouseUp', 'OnClick', 'OnDblClick'):
                    handler = getattr(label, event, None)
                    if callable(handler):setattr(target, event, handler)
            self.wrapped = (panel, node, label, label.display, wrapped, label.opacity)
        wrapped = self.wrapped[4]
        # OverviewLabel uses a native text render object whose opacity does not
        # hide its measured glyphs. The scoped UpdateColumns hook reapplies
        # display before a native row refresh can reveal the original name.
        offset = -(space+min(3, space))/2.
        self.offset_name_columns(panel, offset)
        for target, values in ((wrapped, (('left', label.columnPosition), ('width', label.columnWidth),
                                         ('top', offset), ('fontsize', size), ('maxLines', 1),
                                         ('text', self.name_short[1]))),
                               (self.name_detail, (('left', left), ('width', detail_width), ('top', (size+7)/2.),
                                                   ('fontsize', detail_size), ('maxLines', lines),
                                                   ('display', space >= detail_size+2), ('text', name)))):
            for attr, value in values + (('_controllerOverviewName', name), ('opacity', self.wrapped[5])):
                if getattr(target, attr, None) != value:setattr(target, attr, value)
        if label.display:label.display = False

    def layout(self, now, immediate=False):
        if self.window is None:return
        scroll, nodes = self.window.scroll, self.nodes()
        live = dict((id(node), node) for node in nodes)
        target = self.selected()
        if target is not None and id(target) not in self.edits:
            self.edits[id(target)] = [target, target.height, 0., now, 0., 0.]
        changed, panels = False, set()
        for key, edit in list(self.edits.items()):
            node, fallback, fraction, started, goal_before, initial = edit
            goal = 1. if node is target else 0.
            if edit[4] != goal:
                # The fifth value is the requested endpoint; keep the current
                # height when reversing a transition during rapid navigation.
                edit[3], edit[4], edit[5] = now, goal, fraction
            t = 1. if immediate or not self.c.settings['overviewAnimations'] else min(1., max(0., (now - edit[3]) / .16))
            initial = edit[5]
            fraction = initial + (goal - initial) * t * t * (3. - 2. * t)
            edit[2] = fraction
            base = self.base_height(node, fallback)
            extra = min(self.c.settings['overviewRowExpansion'], max(0., scroll.sr.clipper.GetAbsolute()[3] - base))
            height = int(round(base + extra * fraction))
            if node.height != height:node.height = height;changed = True
            panel = self.row_panel(node)
            if panel is not None:
                panels.add(panel)
                self.resize_fonts(panel, fraction if extra else 0.)
            if key not in live or goal == 0. and t >= 1.:
                node.height = base
                del self.edits[key]
                changed = True
        for key, record in list(self.fonts.items()):
            if record[3] not in panels:
                label, base, assigned, panel = record
                if not getattr(label, 'destroyed', False) and label.measurer.fontSize == assigned:
                    label.measurer.fontSize = base;label._columnWidthDirty = True;label.text = label.text
                del self.fonts[key]
        self.reflow(target, rebuild=changed)
        self.wrap_name(target)
        self.update_rail(target)
        self.update_footer()

    def restore_layout(self):
        self.restore_row_hook()
        self.restore_icon_offset()
        if self.shadow and not getattr(self.shadow[0], 'destroyed', False):self.shadow[0].Close()
        self.shadow = None
        if self.rail and not getattr(self.rail[2], 'destroyed', False):self.rail[2].Close()
        self.rail = None
        self.restore_name()
        self.restore_fonts()
        if self.window is not None and not getattr(self.window, 'destroyed', False):
            scroll = getattr(self.window, 'scroll', None)
            if scroll is not None and not getattr(scroll, 'destroyed', False):
                for node, base, fraction, started, goal in [edit[:5] for edit in self.edits.values()]:
                    node.height = self.base_height(node, base)
                self.reflow()
        self.edits = {}
    def cancel(self, detach=False):
        self.actions, self.action_holds = {}, {}
        self.action_query = None
        try:self.restore_layout()
        finally:
            self.window = self.returning = None
            self.item = None
            self.serial += 1
            self.busy = None
            self.holds, self.fills = {}, {}
            self.context_wait = self.right_pending = False
            if self.c.context and self.c.context.owner is self:self.c.context.cancel()
            self.c.native.release()
            if detach:
                for view in self.views.values():view.close()
                self.views.clear()
            else:self.update_footer()

    def finish(self, now):
        origin, start = self.origin, self.c.native.position()
        self.cancel()
        self.c.custom_epoch += 1
        self.c.radial_gate = True
        self.returning = (now, start, origin)

    def focus(self, node, now):
        self.serial += 1
        self.actions, self.action_holds = {}, {}
        self.action_query = None
        self.next_actions = 0.
        self.pointer.clear()
        self.item = node.itemID
        self.blocked |= self.previous & 0xf300
        self.holds = {}
        self.transition = (now, self.c.native.position())

    def animate(self, now):
        node = self.selected()
        panel = self.row_panel(node)
        if panel is None or getattr(panel, 'destroyed', False) or not _ec_radial_visible(self.c.ui, panel):return
        dx, dy, dw, dh = self.c.ui.desktop.GetAbsolute()
        sx, sy, sw, sh = self.c.native.bounds()
        cx, cy, cw, ch = self.window.scroll.sr.clipper.GetAbsolute()
        x, y, w, h = panel.GetAbsolute()
        # Clip against the viewport and scroll clipper. Column widths and the
        # user's DPI remain native; Windows coordinates are converted here.
        left, right = max(dx, cx, x), min(dx + dw, cx + cw, x + w)
        top, bottom = max(dy, cy, y), min(dy + dh, cy + ch, y + h)
        if left >= right or top >= bottom:return
        target = (sx + ((left + right) / 2. - dx) * sw / float(dw),
                  sy + ((top + bottom) / 2. - dy) * sh / float(dh))
        t = 1.
        if self.transition and self.c.settings['overviewAnimations']:
            t = max(0., min(1., (now - self.transition[0]) / .14))
        ease = t * t * (3. - 2. * t)
        start = self.transition[1] if self.transition else target
        point = tuple(int(round(start[i] + (target[i] - start[i]) * ease)) for i in (0, 1))
        if self.c.native.position() != point:self.c.native.move(*point)
        if t >= 1.:self.transition = None

    def change_tab(self, direction, now):
        if self.busy is not None:return
        group = self.window.tabGroup
        tabs, index = list(group.GetTabs() or ()), group.GetSelectedIdx()
        if len(tabs) < 2 or index is None:return
        self.restore_layout()
        self.item = None
        self.serial += 1
        token, window, stamp = self.serial, self.window, self.stamp
        self.busy = token
        import uthread
        def select():
            try:
                if self.window is not window or self.busy != token or not self.safe() or not self.available(window):return
                if group is not window.tabGroup or tabs != list(group.GetTabs() or ()) or group.GetSelectedIdx() != index:return
                group.SelectByIdx((index + direction) % len(tabs))
                if self.window is not window or self.busy != token or not self.safe():return
                self.tab, self.item = window.GetSelectedTabID(), None
                self.loading = self.first_pending = True
                self.blocked |= self.previous
            except Exception as error:self.fail(error)
            finally:
                if self.busy == token:self.busy = None
        uthread.new(select)

    def open_context(self, now):
        if not self.context_valid() or self.c.context is None:return
        self.layout(now, immediate=True)
        self.transition = None
        self.animate(now)
        node = self.selected()
        panel = self.row_panel(node)
        if panel is None or not _ec_radial_visible(self.c.ui, panel):return
        self.c.context.observe(set((2,)), now, owner=self)
        self.c.native.buttons(set((2,)))
        self.context_wait = self.right_pending = True
        self.holds = {}
        self.action_holds = {}
        self.serial += 1

    def action_entries(self):
        from carbonui.control.contextMenu.menuDataFactory import CreateMenuDataFromRawTuples
        node = self.selected()
        panel = self.row_panel(node)
        if panel is None or not _ec_radial_visible(self.c.ui, panel):return {}
        getter = getattr(panel, 'GetMenu', None)
        if not callable(getter):return {}
        paths = {'UI/Inflight/LockTarget':'lock', 'UI/Inflight/OrbitObject':'orbit',
                 'UI/Inflight/ApproachObject':'approach', 'UI/Inflight/SetAsCameraInterest':'track'}
        entries = CreateMenuDataFromRawTuples(getter())
        return dict((paths[entry.GetLabelPath()], entry) for entry in entries or ()
                    if entry is not None and entry.GetLabelPath() in paths and entry.IsEnabled() and entry.HasFunction())

    def action_valid(self, stamp):
        return (self.context_valid() and not self.context_wait and not self.loading and
                stamp == (self.serial, self.window, self.item, self.tab))

    def refresh_actions(self, now):
        if now < self.next_actions or self.action_query is not None or self.selected() is None:return
        stamp = (self.serial, self.window, self.item, self.tab)
        if not self.action_valid(stamp):return
        self.action_query, self.next_actions = stamp, now+.5
        import uthread
        def query():
            try:
                if not self.action_valid(stamp):return
                entries = self.action_entries()
                if self.action_valid(stamp):self.actions = entries
            except Exception:
                if self.action_valid(stamp):self.actions = {}
            finally:
                if self.action_query == stamp:self.action_query = None
        uthread.new(query)

    def request_action(self, action):
        stamp = (self.serial, self.window, self.item, self.tab)
        if not self.action_valid(stamp):return
        import uthread
        def invoke():
            try:
                if not self.action_valid(stamp):return
                # Rebuild native availability at dispatch; the entry owns its
                # object ID, default range, safety checks and confirmations.
                entry = self.action_entries().get(action)
                if entry is not None and self.action_valid(stamp) and entry.IsEnabled():entry.ExecuteFunction()
            except Exception as error:
                print('EVEJS_CONTROLLER:Overview action unavailable: ' + type(error).__name__)
            finally:
                if self.action_valid(stamp):self.next_actions = 0.
        uthread.new(invoke)

    def face_step(self, raw, mask, now, pointed):
        face = mask & 0xf000
        if face & 0x2000:
            for button in (0x1000, 0x4000, 0x8000):self.action_holds.pop(button, None)
            self.blocked |= raw & 0xd000
        elif face and face & (face-1):
            self.blocked |= face
            self.action_holds.clear()
            return
        if mask & 0x2000:
            started = self.action_holds.setdefault(0x2000, now)
            elapsed = max(0., now-started)
            self.fills[1], self.fills[2] = min(1., elapsed/.5), min(1., elapsed)
            if elapsed+1e-6 >= 1.:
                self.finish(now)
                return
        elif 0x2000 in self.action_holds:
            elapsed = now-self.action_holds.pop(0x2000)
            if not raw & 0x2000:
                if elapsed+1e-6 >= 1.:self.finish(now);return
                if elapsed+1e-6 >= .5 and pointed:self.request_action('track')
        for button, action in ((0x4000, 'lock'), (0x8000, 'orbit'), (0x1000, 'approach')):
            if not mask & button or mask & 0x2000 or not pointed or not self.context_valid():
                self.action_holds.pop(button, None);continue
            started = self.action_holds.setdefault(button, now)
            progress = min(1., max(0., (now-started)/.5))
            self.fills[1] = progress
            if now-started+1e-6 >= .5:
                self.blocked |= button
                self.action_holds.pop(button, None)
                self.request_action(action)

    def context_finished(self, now):
        self.context_wait = self.right_pending = False
        self.holds = {}
        self.blocked |= self.previous | 0xf30f
        self.direction = 0
        self.transition = (now, self.c.native.position())
        if not self.context_valid():self.cancel()

    def context_cancelled(self):
        if self.window is not None:self.cancel()

    def fail(self, error):
        self.cancel()
        self.c.radial_gate = True
        if not self.reported:
            print('EVEJS_CONTROLLER:Overview navigation unavailable: ' + type(error).__name__)
            self.reported = True

    def step(self, pad, now, pressed, settings_open=False):
        owned = self.active
        rising, self.previous_open = pressed and not self.previous_open, pressed
        self.fills = {}
        try:
            self.present()
            if self.returning:
                if not self.safe() or settings_open:self.cancel();return True
                started, start, end = self.returning
                t = 1. if not self.c.settings['overviewAnimations'] else min(1., max(0., (now - started) / .14))
                ease = t * t * (3. - 2. * t)
                self.c.native.move(*(start[i] + (end[i] - start[i]) * ease for i in (0, 1)))
                if t >= 1.:self.returning = None
                return True
            if self.window is None:
                c = self.c
                if not rising or settings_open or c.radial_gate or c.neocom or c.radial or c.radial_hold or c.context and (c.context.active or c.context.pending):return False
                if c.context and c.context.roots():return False
                if not c.settings.get('controllerModeLocked', False) and (getattr(c.native, 'pending', False) or getattr(c.native, 'physical_buttons', None)):return False
                if c.ui.registry.GetModalWindow() is not None or getattr(c.ui, 'dragObject', None):return False
                window = self.choose_window()
                if window is None:return False
                self.begin(window, pad, now)
                return True
            if settings_open or not self.safe() or not self.available(self.window):
                self.cancel();self.c.radial_gate = True;return True
            if self.busy is None and self.tab != self.window.GetSelectedTabID():
                self.cancel();self.c.radial_gate = True;return True
            if self.c.context and (self.context_wait or self.c.context.owner is self):
                self.layout(now)
                if self.right_pending:
                    self.right_pending = False
                    self.c.context.observe(set(), now, owner=self)
                    self.c.native.buttons(set())
                self.c.context.step(pad, now, .016)
                self.fills = dict(self.c.context.fills)
                self.previous = pad[0]
                if self.context_wait and not self.c.context.active and self.c.context.pending is None:self.context_finished(now)
                return True
            if self.c.context and self.c.context.roots():
                self.cancel();self.c.radial_gate = True;return True
            manual = self.c.focus_pointer(pad, now, [self.window], self.pointer)
            if manual == 2:
                self.cancel()
                _ec_focus_release(self.c, pad)
                return True
            pointed = True
            if manual:
                self.transition = None
                row = next((node for node in self.nodes() if self.row_panel(node) is not None and
                            _ec_radial_visible(self.c.ui, self.row_panel(node)) and
                            _ec_focus_contains(self.c, self.window.scroll.sr.clipper) and
                            _ec_focus_contains(self.c, node.panel)), None)
                pointed = row is not None and row.itemID == self.item
                if row is not None and row.itemID != self.item and self.pointer['changed']:
                    pointer = dict(self.pointer)
                    self.focus(row, now)
                    self.pointer.update(pointer)
                    self.transition = None
                    pointed = True
                if self.pointer['moving']:
                    self.blocked |= pad[0] & 0xf300
                    self.action_holds.clear()
                    self.serial += 1
                    self.holds.pop(0x100, None);self.holds.pop(0x200, None)
            raw = pad[0]
            self.blocked &= raw
            mask = raw & ~self.blocked
            if self.loading and not (getattr(self.window, '_ballparkDirty', False) or getattr(self.window, '_scrollEntriesDirty', False)):
                # Native hover sorting can defer removal after a preset change.
                # The preset has already rejected these nodes; finish removing
                # them before focusing the new tab, using the scroll's own API.
                retired = [node for node in self.window.scroll.GetNodes() if getattr(node, 'leavingOverview', False)]
                if retired:self.reflow(retired=retired)
                self.loading = False
            if self.first_pending and not self.loading and self.busy is None:
                nodes = self.nodes()
                if nodes:self.focus(nodes[0], now);self.first_pending = False
            if self.item is not None and self.selected() is None:
                self.item = None
                self.holds = {}
                self.blocked |= raw
                mask = 0
            if self.busy is None and not self.loading:
                direction = (1 if mask & 2 else 0) - (1 if mask & 1 else 0)
                if direction and (direction != self.direction or now >= self.next_repeat):
                    nodes, current = self.nodes(), self.selected()
                    if nodes:
                        index = nodes.index(current) if current in nodes else (-1 if direction > 0 else len(nodes))
                        node = nodes[max(0, min(len(nodes) - 1, index + direction))]
                        if node is not current:self.focus(node, now)
                    self.next_repeat = now + (.35 if direction != self.direction else .12)
                self.direction = direction
            self.refresh_actions(now)
            self.layout(now)
            if not manual:self.animate(now)
            for button, direction in ((0x100, -1), (0x200, 1)):
                if mask & 0x2000 or self.busy is not None or mask & 0x300 == 0x300:
                    self.holds.pop(button, None);continue
                if mask & button:
                    if button not in self.holds:self.holds[button] = (now, self.item, self.tab)
                    started, item, tab = self.holds[button]
                    progress = min(1., max(0., (now - started) * 1000. / self.c.settings['clickHoldMilliseconds']))
                    if button == 0x100 and pointed and item == self.item and tab == self.tab and self.selected() is not None:
                        self.fills[2] = progress
                        if progress >= 1.:
                            self.blocked |= button
                            self.open_context(now)
                            break
                elif button in self.holds:
                    started, item, tab = self.holds.pop(button)
                    if not raw & button and now - started < self.c.settings['clickHoldMilliseconds'] / 1000.:self.change_tab(direction, now)
            if not self.context_wait:self.face_step(raw, mask, now, pointed)
            self.previous = mask
            return True
        except Exception as error:
            self.fail(error)
            return owned or rising
