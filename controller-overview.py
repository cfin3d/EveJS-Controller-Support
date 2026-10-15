# Controller focus for the existing Overview. Python 2.7 compatible.
class _OverviewNavigation(object):
    def __init__(self, controller):
        self.c = controller
        self.window = self.last_window = self.returning = None
        self.previous_open = False
        self.item = self.tab = None
        self.edits, self.fonts, self.glyphs = {}, {}, []
        self.holds, self.fills = {}, {}
        self.serial = 0
        self.busy = None
        self.context_wait = self.right_pending = False
        self.reported = False
        self.padding_hook = None
        self.loading = self.first_pending = False
        self.wrapped = None
        self.footer = self.rail = None
        self.footer_groups = []
        self.icon_offset = self.shadow = None
        self.pointer = {}

    @property
    def active(self):
        return self.window is not None or self.returning is not None

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
                not getattr(c.native, 'pending', False) and not getattr(c.native, 'physical_buttons', None) and
                not getattr(c.ui, 'dragObject', None) and c.ui.registry.GetModalWindow() is None and
                not getattr(getattr(_ec_builtins, 'session', None), 'mutating', False) and self.stamp == self.identity())

    def nodes(self):
        if self.window is None:return []
        return [node for node in self.window.scroll.GetNodes()
                if getattr(node, 'itemID', None) is not None and not getattr(node, 'leavingOverview', False)]

    def selected(self):
        return next((node for node in self.nodes() if node.itemID == self.item), None)

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

    def add_glyphs(self):
        from carbonui.primitives.sprite import Sprite
        import carbonui.const as const
        window, group = self.window, self.window.tabGroup
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
        for tokens, text in ((('UP', 'DOWN'), 'Browse'), (('LB',), 'Hold: Menu'), (('B',), 'Hold: Exit')):
            group = Container(parent=self.footer, align=const.TOPLEFT, height=24, clipChildren=True, state=const.UI_DISABLED)
            icons = [Sprite(parent=group, align=const.CENTERLEFT, left=index*24, width=24, height=24,
                            color=(1., 1., 1., .8), state=const.UI_DISABLED) for index in range(len(tokens))]
            label = EveLabelSmall(parent=group, align=const.CENTERLEFT, left=len(tokens)*24+6,
                                 text=text, fontsize=13, maxLines=1, color=(1., 1., 1., .8), state=const.UI_DISABLED)
            self.footer_groups.append((group, icons, label, tokens))
        self.update_footer()

    def update_footer(self):
        if self.footer is None:return
        menu, context = self.c.menu, self.c.context
        in_menu = self.context_wait or context is not None and context.owner is self
        widths = []
        for index, (group, icons, label, tokens) in enumerate(self.footer_groups):
            if index == 1:
                tokens, text = (('RB',), 'Hold: Select') if in_menu else (('LB',), 'Hold: Menu')
                if label.text != text:label.text = text
            elif index == 2:
                text = 'Hold: Back' if in_menu else 'Hold: Exit'
                if label.text != text:label.text = text
            for icon, token in zip(icons, tokens):
                name = menu.icon_name(token) if menu else token.lower()
                path = getattr(menu, 'button_icons', {}).get(name)
                if path and getattr(icon, 'texturePath', None) != path:icon.texturePath = path
            group.opacity = .4 if index == 1 and not in_menu and self.selected() is None else 1.
            widths.append(len(icons)*24 + 6 + int(getattr(label, 'textwidth', len(label.text)*7)))
        width = max(0, self.footer.GetAbsolute()[2] - 24)
        stacked = sum(widths) + 24 > width
        # Include the native bottom gutter in the visible footer instead of
        # leaving it as extra empty space beneath otherwise centered prompts.
        wx, wy, ww, wh = self.window.GetAbsolute()
        cx, cy, cw, ch = self.window.content.GetAbsolute()
        padding = (0, 0, 0, -max(0, wy+wh-1-cy-ch))
        if getattr(self.footer, 'padding', None) != padding:self.footer.padding = padding
        self.footer.height = 84 if stacked else 32
        lefts = (0, (width-widths[1])/2., width-widths[2])
        for index, (group, icons, label, tokens) in enumerate(self.footer_groups):
            group.left = 12 if stacked else 12 + lefts[index]
            group.top = 4 + index*26 if stacked else (self.footer.height-group.height)/2.
            group.width = min(width, widths[index])

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
        panel = getattr(node, 'panel', None)
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
        self.add_glyphs()
        self.add_footer()
        nodes = self.nodes()
        self.first_pending = not bool(nodes)
        self.loading = False
        if nodes:self.focus(nodes[0], now)

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
                label.text = label.text
            self.fonts[key] = (label, base, size, panel)

    def restore_name(self):
        if self.wrapped is None:return
        panel, node, label, display, wrapped, opacity = self.wrapped
        if not getattr(wrapped, 'destroyed', False):wrapped.Close()
        if not getattr(label, 'destroyed', False) and not label.display:label.display = display
        self.wrapped = None

    def wrap_name(self, node):
        if not self.c.settings['overviewRowExpansion']:
            self.restore_name();return
        panel = getattr(node, 'panel', None)
        name = getattr(node, 'display_NAME', None)
        label = next((label for label in getattr(panel, 'columnLabels', ())
                      if name and label.text == name and getattr(label, 'columnWidth', 0) > 0), None)
        if self.wrapped and (self.wrapped[0] is not panel or self.wrapped[1] is not node or self.wrapped[2] is not label):self.restore_name()
        if label is None:return
        size = max(1, int(round(label.ReverseScaleDpi(label.measurer.fontSize))))
        lines = min(3, max(1, int((node.height - 4) / float(size + 2))))
        if lines < 2:
            self.restore_name();return
        if self.wrapped is None:
            from eve.client.script.ui.control.eveLabel import EveLabelSmall
            from carbonui import TextColor
            import carbonui.const as const
            wrapped = EveLabelSmall(parent=panel, name='controllerOverviewName', align=const.CENTERLEFT,
                                   state=const.UI_DISABLED, text='', maxLines=lines, fontsize=size,
                                   color=TextColor.HIGHLIGHT)
            self.wrapped = (panel, node, label, label.display, wrapped, label.opacity)
        wrapped = self.wrapped[4]
        wrapped.left, wrapped.width = label.columnPosition, label.columnWidth
        wrapped.fontsize, wrapped.maxLines = size, lines
        wrapped.text = name
        wrapped.opacity = self.wrapped[5]
        label.display = False

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
            panel = getattr(node, 'panel', None)
            if panel is not None and not getattr(panel, 'destroyed', False) and getattr(getattr(panel, 'sr', None), 'node', None) is node:
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
                    label.measurer.fontSize = base;label.text = label.text
                del self.fonts[key]
        if changed:
            scroll.UpdateNodesWidthAndPosition()
            scroll.UpdatePosition()
        if target is not None:
            index = list(scroll.GetNodes()).index(target)
            scroll.ShowNodeIdx(index)
        self.wrap_name(target)
        self.update_rail(target)
        self.update_footer()

    def restore_layout(self):
        self.restore_icon_offset()
        if self.shadow and not getattr(self.shadow[0], 'destroyed', False):self.shadow[0].Close()
        self.shadow = None
        if self.rail and not getattr(self.rail[2], 'destroyed', False):self.rail[2].Close()
        self.rail = None
        if self.footer is not None and not getattr(self.footer, 'destroyed', False):self.footer.Close()
        self.footer, self.footer_groups = None, []
        self.restore_name()
        self.restore_fonts()
        if self.window is not None and not getattr(self.window, 'destroyed', False):
            scroll = getattr(self.window, 'scroll', None)
            if scroll is not None and not getattr(scroll, 'destroyed', False):
                for node, base, fraction, started, goal in [edit[:5] for edit in self.edits.values()]:
                    node.height = self.base_height(node, base)
                scroll.UpdateNodesWidthAndPosition()
                scroll.UpdatePosition()
        self.edits = {}
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

    def cancel(self):
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

    def finish(self, now):
        origin, start = self.origin, self.c.native.position()
        self.cancel()
        self.c.custom_epoch += 1
        self.c.radial_gate = True
        self.returning = (now, start, origin)

    def focus(self, node, now):
        self.pointer.clear()
        self.item = node.itemID
        self.blocked |= self.previous & 0x300
        self.holds = {}
        self.transition = (now, self.c.native.position())

    def animate(self, now):
        node = self.selected()
        panel = getattr(node, 'panel', None)
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
        self.restore_fonts()
        self.item = None
        self.layout(now, immediate=True)
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
        panel = getattr(node, 'panel', None)
        if panel is None or not _ec_radial_visible(self.c.ui, panel):return
        self.c.context.observe(set((2,)), now, owner=self)
        self.c.native.buttons(set((2,)))
        self.context_wait = self.right_pending = True
        self.holds = {}

    def context_finished(self, now):
        self.context_wait = self.right_pending = False
        self.holds = {}
        self.blocked |= self.previous | 0x230f
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
                if getattr(c.native, 'pending', False) or getattr(c.native, 'physical_buttons', None):return False
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
                row = next((node for node in self.nodes() if getattr(node, 'panel', None) is not None and
                            _ec_radial_visible(self.c.ui, node.panel) and
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
                    self.blocked |= pad[0] & 0x300
                    self.holds.pop(0x100, None);self.holds.pop(0x200, None)
            raw = pad[0]
            self.blocked &= raw
            mask = raw & ~self.blocked
            if self.loading and not (getattr(self.window, '_ballparkDirty', False) or getattr(self.window, '_scrollEntriesDirty', False)):
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
            if mask & 0x2000:
                started = self.holds.setdefault('exit', now)
                progress = min(1., max(0., (now - started) * 1000. / self.c.settings['clickHoldMilliseconds']))
                self.fills[2] = progress
                if progress >= 1.:self.finish(now)
            else:self.holds.pop('exit', None)
            self.previous = mask
            return True
        except Exception as error:
            self.fail(error)
            return owned or rising
