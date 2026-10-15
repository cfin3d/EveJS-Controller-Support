# Native right-click menu navigation. Python 2.7 compatible.
class _ContextNavigation(object):
    def __init__(self, controller):
        self.c = controller
        self.pending = self.root = self.returning = None
        self.stack, self.hooks, self.holds = [], [], {}
        self.fills = {}
        self.right_down = False
        self.serial = 0
        self.busy = None
        self.transition = self.highlighted = None
        self.reported = False

    @property
    def active(self):
        return self.root is not None or self.returning is not None

    def snapshot(self):
        c = self.c
        session = getattr(_ec_builtins, 'session', None)
        return (tuple(getattr(session, key, None) for key in ('charid', 'shipid', 'solarsystemid', 'stationid', 'structureid')),
                c.custom_epoch, c.native.bounds(), c.ui.desktop.GetAbsolute(), c.ui.registry.GetModalWindow())

    def safe(self):
        c = self.c
        return (c.active and c.mode.mode == 'controller' and c.native.foreground() and
                not getattr(c.native, 'pending', False) and not getattr(c.native, 'physical_buttons', None) and
                not getattr(c.ui, 'dragObject', None) and not getattr(getattr(_ec_builtins, 'session', None), 'mutating', False) and
                self.stamp == self.snapshot())

    def roots(self):
        from carbonui.control.contextMenu.contextMenu import ContextMenu
        layer = getattr(self.c.ui.layer, 'menu', None)
        return [menu for menu in list(getattr(layer, 'children', ()))
                if isinstance(menu, ContextMenu) and not getattr(menu, 'parentEntry', None) and not getattr(menu, 'closing', False) and
                getattr(menu, 'state', 0) != 2 and _ec_radial_visible(self.c.ui, menu)]

    def observe(self, held, now):
        # Arm only for a synthetic right-click actually emitted by our gesture.
        # Physical mouse menus and existing popups never acquire controller focus.
        right = 2 in held
        try:
            if right and not self.right_down and not self.active:
                self.pending = dict(origin=self.c.native.position(), roots=self.roots(), deadline=None)
                self.stamp = self.snapshot()
            if self.pending:
                if right:self.pending['deadline'] = None
                elif self.pending['deadline'] is None:
                    self.pending['deadline'] = now + 1.25
                    self.pending['origin'] = self.c.native.position()
        except Exception as error:
            self.fail(error)
        self.right_down = right

    def owns(self, row):
        return self.root is not None and any(_ec_ui_under(row, panel) for panel, selected in self.stack)

    def install_hooks(self):
        from carbonui.control.contextMenu import menuEntryView as entries
        for cls in set(value for value in vars(entries).values() if isinstance(value, type) and issubclass(value, entries.BaseMenuEntryView)):
            for name in ('OnMouseEnter', 'OnMouseExit', 'CheckReconstructSubMenu', 'ReconstructSubMenuView'):
                original = cls.__dict__.get(name)
                if not callable(original):continue
                def wrap(original):
                    def guarded(row, *args, **kwargs):
                        if not self.owns(row):return original(row, *args, **kwargs)
                    return guarded
                guarded = wrap(original)
                self.hooks.append((cls, name, original, guarded))
                setattr(cls, name, guarded)

    def paint(self, row, selected):
        if row is None or getattr(row, 'destroyed', False):return
        if selected and getattr(row, 'underlay', None) is None:
            construct = getattr(row, 'ConstructUnderlay', None)
            if callable(construct):construct()
        for target, name in ((getattr(row, 'underlay', None), 'OnMouseEnter' if selected else 'OnMouseExit'),
                             (row, '_AnimMouseEnter' if selected else '_AnimMouseExit'),
                             (getattr(row, 'checkbox', None), 'OnMouseEnter' if selected else 'OnMouseExit')):
            method = getattr(target, name, None)
            if callable(method):method()

    def cleanup(self):
        self.serial += 1
        self.busy = None
        try:self.paint(self.highlighted, False)
        except Exception:pass
        finally:
            for cls, name, original, guarded in reversed(self.hooks):
                if cls.__dict__.get(name) is guarded:setattr(cls, name, original)
            self.hooks = []
            self.pending = self.root = self.returning = None
            self.stack, self.holds, self.fills = [], {}, {}
            self.transition = self.highlighted = None

    def cancel(self):
        # On physical takeover leave the native menu available to the mouse.
        self.cleanup()
        self.right_down = False

    def fail(self, error):
        owned = self.active
        self.cancel()
        if owned:self.c.radial_gate = True
        if not self.reported:
            print('EVEJS_CONTROLLER:Context navigation unavailable: ' + type(error).__name__)
            self.reported = True

    def valid(self):
        roots = self.roots() if self.root is not None else []
        return self.root is not None and self.safe() and self.root in roots and all(menu in self.menu_roots for menu in roots)

    def rows(self, panel):
        result = []
        for row in list(getattr(panel, 'entries', ()))[:256]:
            data = getattr(row, 'menuEntryData', None)
            if not _ec_ui_under(row, panel) or not _ec_radial_visible(self.c.ui, row) or getattr(row, 'state', 0) in (1, 2):continue
            if data is None or not data.IsEnabled():continue
            if not (data.HasFunction() or data.HasSubMenuData() or getattr(row, 'checkbox', None) is not None):continue
            x, y, w, h = row.GetAbsolute()
            if w > 0 and h > 0:result.append(row)
        return sorted(result, key=lambda row:row.GetAbsolute()[1])

    def selected(self):
        return self.stack[-1][1] if self.stack else None

    def focus(self, row, now):
        if row is not self.highlighted:
            self.paint(self.highlighted, False)
            self.paint(row, True)
        self.highlighted = row
        self.stack[-1] = (self.stack[-1][0], row)
        self.transition = (now, self.c.native.position())
        self.holds.pop(0x200, None)
        self.serial += 1
        self.busy = None

    def point(self, row):
        ui, native = self.c.ui, self.c.native
        dx, dy, dw, dh = ui.desktop.GetAbsolute()
        dw, dh = float(dw), float(dh)
        left, top, sw, sh = native.bounds()
        px, py, pw, ph = self.stack[-1][0].GetAbsolute()
        x, y, w, h = row.GetAbsolute()
        lo_x, hi_x = max(left, left + (px - dx) * sw / dw), min(left + sw - 1, left + (px + pw - dx) * sw / dw - 1)
        lo_y, hi_y = max(top, top + (py - dy) * sh / dh), min(top + sh - 1, top + (py + ph - dy) * sh / dh - 1)
        if lo_x > hi_x or lo_y > hi_y:raise ValueError('Context menu outside viewport')
        target = (max(lo_x, min(hi_x, left + (x + w / 2. - dx) * sw / dw)),
                  max(lo_y, min(hi_y, top + (y + h / 2. - dy) * sh / dh)))
        return target, (lo_x, lo_y, hi_x, hi_y)

    def animate(self, now):
        row = self.selected()
        if row is None:return
        target, limits = self.point(row)
        if self.transition:
            started, start = self.transition
            t = max(0., min(1., (now - started) / .14))
            ease = t * t * (3. - 2. * t)
            start = (max(limits[0], min(limits[2], start[0])), max(limits[1], min(limits[3], start[1])))
            point = tuple(start[i] + (target[i] - start[i]) * ease for i in (0, 1))
            if t >= 1.:self.transition = None
        else:point = target
        point = tuple(int(value) for value in point)
        if self.c.native.position() != point:self.c.native.move(*point)

    def begin(self, root, pad, now):
        c = self.c
        self.origin = self.pending['origin']
        self.pending = None
        self.root, self.stack = root, [(root, None)]
        self.menu_roots = self.roots()
        self.blocked, self.previous = pad[0] & 0x220f, pad[0]
        self.direction, self.next_repeat = 0, 0.
        c.custom_epoch += 1
        self.stamp = self.snapshot()
        c.custom_down = c.custom_pressed(pad)
        c.native.release()
        c.gestures.reset();c.magnet.reset();c.motion.reset();c.ui_navigation.clear()
        c.remainder_x = c.remainder_y = 0.
        self.install_hooks()
        rows = self.rows(root)
        if rows:self.focus(rows[0], now)

    def close_owned(self):
        if self.root is not None and self.root in self.roots():
            self.root.Collapse()
            scatter = getattr(getattr(_ec_builtins, 'sm', None), 'ScatterEvent', None)
            if callable(scatter):scatter('OnMenuClosed')

    def finish(self, now, restore=False, close=True):
        origin, start = self.origin, self.c.native.position()
        if close:self.close_owned()
        self.cleanup()
        self.c.radial_gate = True
        self.c.custom_epoch += 1
        self.stamp = self.snapshot()
        if restore:self.returning = (now, start, origin)

    def back(self, now):
        if len(self.stack) <= 1:return
        panel, row = self.stack.pop()
        panel.Collapse()
        parent = self.selected()
        if getattr(parent, 'subMenuView', None) is panel:parent.subMenuView = None
        self.focus(parent, now)

    def enter(self, now):
        row = self.selected()
        if self.busy is not None or len(self.stack) >= 32 or row is None or not row.menuEntryData.HasSubMenuData():return
        import uthread
        self.serial += 1
        token = self.serial
        self.busy = token
        panel = self.stack[-1][0]
        def build():
            submenu = None
            try:
                if not self.valid() or self.busy != token:return
                data = row.menuEntryData.GetSubMenuData()
                # Dynamic native data can yield. Never attach a late response
                # after takeover, cancellation, item changes or a session switch.
                if not self.valid() or self.busy != token or self.selected() is not row or self.stack[-1][0] is not panel or row not in self.rows(panel):return
                if not data:return
                from carbonui.control.contextMenu.contextMenu import ContextSubMenu
                row.Collapse()
                submenu = ContextSubMenu(parent=self.c.ui.layer.menu, parentEntry=row, menuData=data, idx=0)
                if not self.valid() or self.busy != token or self.selected() is not row:
                    submenu.Collapse();return
                row.subMenuView = submenu
                self.stack.append((submenu, None))
                rows = self.rows(submenu)
                if rows:self.focus(rows[0], _ec_time.time())
            except Exception as error:
                if submenu is not None and not getattr(submenu, 'destroyed', False):submenu.Collapse()
                if self.busy == token:self.fail(error)
            finally:
                if self.busy == token:self.busy = None
        uthread.new(build)

    def activate(self, now):
        row = self.selected()
        if self.busy is not None or row is None:return
        if not row.menuEntryData.HasFunction() and getattr(row, 'checkbox', None) is None:
            self.enter(now);return
        import uthread
        self.serial += 1
        token = self.serial
        self.busy = token
        def invoke():
            try:
                if not self.valid() or self.busy != token or self.selected() is not row or not row.menuEntryData.IsEnabled():return
                if getattr(row, 'checkbox', None) is not None:
                    row.OnClick()
                    self.finish(_ec_time.time())
                else:
                    # Native OnMouseUp dispatches the command, sound and flash,
                    # and closes the menu. Its exact-row hover test must reflect
                    # controller selection even before Windows processes a move.
                    sentinel = object()
                    previous = row.__dict__.get('IsMouseOverEntry', sentinel)
                    check = lambda:self.valid() and self.selected() is row
                    row.IsMouseOverEntry = check
                    try:row.OnMouseUp()
                    finally:
                        if row.__dict__.get('IsMouseOverEntry') is check:
                            if previous is sentinel:del row.IsMouseOverEntry
                            else:row.IsMouseOverEntry = previous
                    self.finish(_ec_time.time(), close=False)
            except Exception as error:
                if self.busy == token:self.fail(error)
            finally:
                if self.busy == token:self.busy = None
        uthread.new(invoke)

    def step(self, pad, now, dt):
        owned = self.active
        self.fills = {}
        try:
            if self.returning:
                if not self.safe():self.cancel();return True
                started, start, end = self.returning
                t = max(0., min(1., (now - started) / .14))
                ease = t * t * (3. - 2. * t)
                self.c.native.move(*(start[i] + (end[i] - start[i]) * ease for i in (0, 1)))
                if t >= 1.:self.returning = None
                return True
            if self.root is None:
                if self.pending is None:return False
                if not self.safe() or self.c.neocom or self.c.radial or self.c.radial_hold or self.c.radial_gate:
                    self.pending = None;return False
                deadline = self.pending['deadline']
                if deadline is not None and now > deadline:self.pending = None;return False
                roots = [root for root in self.roots() if root not in self.pending['roots']]
                if not roots:return False
                self.begin(roots[0], pad, now)
                return True
            if not self.valid():
                self.cancel();self.c.radial_gate = True;return True
            while len(self.stack) > 1:
                panel, row = self.stack[-1]
                parent = self.stack[-2][1]
                if _ec_radial_visible(self.c.ui, panel) and getattr(parent, 'subMenuView', None) is panel:break
                self.stack.pop();self.focus(self.selected(), now)
            # An already-running native hover task may finish after acquisition.
            # Retire only those extra branches of our own menu; preserve the
            # explicit D-pad path and never close another root's panels.
            for index, (panel, selected) in enumerate(self.stack):
                expected = self.stack[index + 1][0] if index + 1 < len(self.stack) else None
                for entry in list(getattr(panel, 'entries', ()))[:256]:
                    submenu = getattr(entry, 'subMenuView', None)
                    if submenu is not None and submenu is not expected:entry.Collapse()
            rows = self.rows(self.stack[-1][0])
            if self.selected() not in rows:
                if rows:self.focus(rows[0], now)
                elif self.selected() is not None:self.focus(None, now)
            raw = pad[0]
            self.blocked &= raw
            mask = raw & ~self.blocked
            rising = mask & ~self.previous
            self.previous = mask
            if rising & 4:self.back(now)
            elif rising & 8:self.enter(now)
            direction = (1 if mask & 2 else 0) - (1 if mask & 1 else 0)
            if direction and (direction != self.direction or now >= self.next_repeat):
                rows = self.rows(self.stack[-1][0])
                if rows:
                    index = rows.index(self.selected()) if self.selected() in rows else 0
                    row = rows[max(0, min(len(rows) - 1, index + direction))]
                    if row is not self.selected():self.focus(row, now)
                self.next_repeat = now + (.35 if direction != self.direction else .12)
            self.direction = direction
            self.animate(now)
            for button, indicator in ((0x2000, 2), (0x200, 1)):
                if not mask & button or button == 0x200 and mask & 0x2000:
                    self.holds.pop(button, None);continue
                if button == 0x200 and (self.selected() is None or self.busy is not None):continue
                if button not in self.holds:self.holds[button] = now
                progress = max(0., min(1., (now - self.holds[button]) * 1000. / self.c.settings['clickHoldMilliseconds']))
                self.fills[indicator] = progress
                if progress >= 1.:
                    self.blocked |= button;self.holds.pop(button, None)
                    if button == 0x2000:self.finish(now, restore=True);return True
                    self.activate(now)
            return True
        except Exception as error:
            owned = owned or self.active
            self.fail(error)
            return owned
