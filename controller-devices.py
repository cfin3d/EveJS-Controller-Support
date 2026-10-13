# In-process SDL3 gamepads and controller-specific prompts. Python 2.7 compatible.
import ctypes as _dev_ctypes
import os as _dev_os

EXTRA_BUTTONS=[('R4',1<<18),('L4',1<<19),('R5',1<<20),('L5',1<<21),('TOUCHPAD',1<<22),
               ('MISC1',1<<23),('MISC2',1<<24),('MISC3',1<<25),('MISC4',1<<26),('MISC5',1<<27),('MISC6',1<<28),('GUIDE',1<<29)]
BASE_ICONS={'A':'a','B':'b','X':'x','Y':'y','LB':'lb','RB':'rb','LT':'lt','RT':'rt',
            'LS':'left-stick','RS':'right-stick','LEFT_STICK':'left-stick','RIGHT_STICK':'right-stick',
            'LEFT_STICK_Y':'left-stick','RIGHT_STICK_Y':'right-stick','UP':'dpad-up','DOWN':'dpad-down',
            'LEFT':'dpad-left','RIGHT':'dpad-right','VIEW':'view','MENU':'menu'}
BASE_ICONS.update((name,name.lower()) for name,bit in EXTRA_BUTTONS)
PS_ICONS=dict(BASE_ICONS,A='playstation/cross',B='playstation/circle',X='playstation/square',Y='playstation/triangle',
              LB='playstation/l1',RB='playstation/r1',LT='playstation/l2',RT='playstation/r2',
              LS='playstation/l3',RS='playstation/r3',VIEW='playstation/create',MENU='playstation/options',
              GUIDE='playstation/ps',TOUCHPAD='playstation/touchpad')
ICON_FILES=set(BASE_ICONS.values()) | set(PS_ICONS.values()) | set(('playstation/share','playstation/select','playstation/start'))


def _ec_controller_style(controller):
    choice=controller.settings.get('controllerIcons','auto')
    if choice in ('ps4','ps5'):return 'playstation'
    if choice!='auto':return choice
    information=getattr(controller.native,'device_info',lambda: {})()
    return information.get('style','xbox')


def _ec_controller_kind(controller):
    choice=controller.settings.get('controllerIcons','auto')
    return choice if choice in ('ps4','ps5') else getattr(controller.native,'device_info',lambda:{})().get('kind','')


def _ec_button_icon(controller,token):
    style=_ec_controller_style(controller)
    if style=='playstation':
        kind=_ec_controller_kind(controller)
        if token=='VIEW' and kind=='ps4':return 'playstation/share'
        if token=='VIEW' and kind=='ps3':return 'playstation/select'
        if token=='MENU' and kind=='ps3':return 'playstation/start'
        return PS_ICONS.get(token,token.lower())
    return BASE_ICONS.get(token,token.lower())


def _ec_button_name(controller,value):
    style=_ec_controller_style(controller)
    names={'LEFT_STICK':'Left Stick','RIGHT_STICK':'Right Stick','LEFT_STICK_Y':'Left Stick Up/Down',
           'RIGHT_STICK_Y':'Right Stick Up/Down','UP':'D-Pad Up','DOWN':'D-Pad Down','LEFT':'D-Pad Left',
           'RIGHT':'D-Pad Right','VIEW':'Select / View','MENU':'Menu','TOUCHPAD':'Touchpad Click',
           'GUIDE':'Guide','MISC1':'Extra 1','MISC2':'Extra 2','MISC3':'Extra 3','MISC4':'Extra 4','MISC5':'Extra 5','MISC6':'Extra 6'}
    if style=='playstation':
        kind=_ec_controller_kind(controller)
        names.update(A='Cross',B='Circle',X='Square',Y='Triangle',LB='L1',RB='R1',LT='L2',RT='R2',LS='L3',RS='R3',
                     VIEW='Share' if kind=='ps4' else 'Select' if kind=='ps3' else 'Create',MENU='Start' if kind=='ps3' else 'Options',GUIDE='PS')
    elif style=='steam':names.update(VIEW='View',MENU='Menu',GUIDE='Steam',TOUCHPAD='Trackpad Click',MISC1='Quick Access')
    return ' + '.join(names.get(token,token) for token in value.split('+')) if value else 'Disabled'


class _Gamepads(object):
    # SDL3 is loaded by absolute path and runs on the client's polling thread.
    # All devices normalize to the same positional button/axis contract.
    def __init__(self,directory,library=None):
        self.library=library or _dev_ctypes.CDLL(_dev_os.path.join(directory,'runtime','SDL3.dll'))
        self.handles,self.metadata,self.last_read={},{},{}
        self.selected,self.last_instance=-1,None
        self.closed,self.initialized=False,False
        self.hints=[]
        self.event_state=None
        c=_dev_ctypes
        signatures={
            'SDL_SetHint':([c.c_char_p,c.c_char_p],c.c_bool),
            'SDL_GetHint':([c.c_char_p],c.c_char_p),'SDL_ResetHint':([c.c_char_p],c.c_bool),
            'SDL_InitSubSystem':([c.c_uint32],c.c_bool),'SDL_QuitSubSystem':([c.c_uint32],None),
            'SDL_SetGamepadEventsEnabled':([c.c_bool],None),'SDL_SetJoystickEventsEnabled':([c.c_bool],None),
            'SDL_GamepadEventsEnabled':([],c.c_bool),'SDL_JoystickEventsEnabled':([],c.c_bool),
            'SDL_UpdateGamepads':([],None),'SDL_GetGamepads':([c.POINTER(c.c_int)],c.POINTER(c.c_uint32)),
            'SDL_free':([c.c_void_p],None),'SDL_OpenGamepad':([c.c_uint32],c.c_void_p),
            'SDL_CloseGamepad':([c.c_void_p],None),'SDL_GamepadConnected':([c.c_void_p],c.c_bool),
            'SDL_GetGamepadButton':([c.c_void_p,c.c_int],c.c_bool),'SDL_GetGamepadAxis':([c.c_void_p,c.c_int],c.c_int16),
            'SDL_GetRealGamepadType':([c.c_void_p],c.c_int),'SDL_GetGamepadPlayerIndex':([c.c_void_p],c.c_int),
            'SDL_GetGamepadName':([c.c_void_p],c.c_char_p),'SDL_GetGamepadVendor':([c.c_void_p],c.c_uint16),
            'SDL_GetGamepadProduct':([c.c_void_p],c.c_uint16)}
        for name,(args,result) in signatures.items():
            function=getattr(self.library,name);function.argtypes=args;function.restype=result
        for hint in ('SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS','SDL_JOYSTICK_HIDAPI','SDL_JOYSTICK_HIDAPI_PS4',
                     'SDL_JOYSTICK_HIDAPI_PS5','SDL_JOYSTICK_HIDAPI_STEAM','SDL_JOYSTICK_HIDAPI_STEAMDECK'):
            key=hint.encode('ascii');old=self.library.SDL_GetHint(key)
            self.hints.append((key,old))
            self.library.SDL_SetHint(key,b'1')
        try:
            if not self.library.SDL_InitSubSystem(0x2000):raise RuntimeError('SDL Gamepad Initialization Failed')
            self.initialized=True
            self.event_state=(self.library.SDL_GamepadEventsEnabled(),self.library.SDL_JoystickEventsEnabled())
            self.library.SDL_SetGamepadEventsEnabled(False)
            self.library.SDL_SetJoystickEventsEnabled(False)
            self.scan()
        except Exception:
            self.close()
            raise

    def describe(self,handle):
        kind=self.library.SDL_GetRealGamepadType(handle)
        vendor=self.library.SDL_GetGamepadVendor(handle);product=self.library.SDL_GetGamepadProduct(handle)
        raw=self.library.SDL_GetGamepadName(handle) or b'Controller'
        name=raw.decode('utf-8','replace').replace('<','').replace('>','').replace('&','')[:80]
        family='playstation' if kind in (4,5,6) else 'steam' if kind==12 or vendor==0x28de else 'xbox'
        return dict(name=name,style=family,kind={4:'ps3',5:'ps4',6:'ps5'}.get(kind,'steamdeck' if vendor==0x28de and product==0x1205 else family),backend='SDL3')

    def scan(self):
        if self.closed:return {}
        self.library.SDL_UpdateGamepads()
        count=_dev_ctypes.c_int()
        array=self.library.SDL_GetGamepads(_dev_ctypes.byref(count))
        try:
            if count.value<0 or count.value>128:raise RuntimeError('Invalid Gamepad Enumeration')
            instances=[int(array[i]) for i in range(count.value)] if array else []
        finally:
            if array:self.library.SDL_free(array)
        for instance,(slot,handle) in list(self.handles.items()):
            if instance not in instances or not self.library.SDL_GamepadConnected(handle):
                self.library.SDL_CloseGamepad(handle)
                del self.handles[instance];self.metadata.pop(slot,None);self.last_read.pop(instance,None)
        for instance in instances:
            if instance in self.handles or len(self.handles)>=16:continue
            handle=self.library.SDL_OpenGamepad(instance)
            if not handle:continue
            try:
                taken=set(slot for slot,old in self.handles.values())
                player=self.library.SDL_GetGamepadPlayerIndex(handle)
                slot=player if 0<=player<16 and player not in taken else next(i for i in range(16) if i not in taken)
                self.metadata[slot]=self.describe(handle)
                self.handles[instance]=(slot,handle)
            except Exception:
                self.library.SDL_CloseGamepad(handle)
                raise
        samples={}
        buttons=[0x1000,0x2000,0x4000,0x8000,0x20,1<<29,0x10,0x40,0x80,0x100,0x200,1,2,4,8,
                 1<<23,1<<18,1<<19,1<<20,1<<21,1<<22,1<<24,1<<25,1<<26,1<<27,1<<28]
        for instance,(slot,handle) in self.handles.items():
            if not self.library.SDL_GamepadConnected(handle):continue
            mask=sum(bit for button,bit in enumerate(buttons) if self.library.SDL_GetGamepadButton(handle,button))
            axis=[int(self.library.SDL_GetGamepadAxis(handle,i)) for i in range(6)]
            # SDL Y grows downward; the existing runtime uses upward-positive Y.
            samples[slot]=(mask,axis[0],max(-32768,min(32767,-axis[1])),axis[2],max(-32768,min(32767,-axis[3])),
                           max(0,min(255,int(round(axis[4]*255./32767.)))),max(0,min(255,int(round(axis[5]*255./32767.)))))
        return samples

    def read(self,index):
        samples=self.scan()
        by_slot=dict((slot,instance) for instance,(slot,handle) in self.handles.items())
        active=[]
        for slot,sample in samples.items():
            instance=by_slot[slot];old=self.last_read.get(instance,(0,0,0,0,0,0,0))
            if sample[0] & ~old[0] or any(abs(sample[i]-old[i])> (12 if i>=5 else 2000) and abs(sample[i])>(20 if i>=5 else 8000) for i in range(1,7)):
                active.append(slot)
            self.last_read[instance]=sample
        if index>=0:slot=index if index in samples else -1
        elif self.selected in active:slot=self.selected
        elif active:slot=sorted(active,key=lambda i:(self.metadata[i]['style']=='xbox',i))[0]
        else:slot=self.selected if self.selected in samples else min(samples) if samples else -1
        instance=by_slot.get(slot)
        changed=slot!=self.selected or instance!=self.last_instance
        self.selected,self.last_instance=slot,instance
        return samples.get(slot),changed

    def device_info(self):
        return self.metadata.get(self.selected,dict(name='No Controller Connected',style='xbox',kind='',backend='SDL3'))

    def close(self):
        if self.closed:return
        self.closed=True
        try:
            for slot,handle in self.handles.values():self.library.SDL_CloseGamepad(handle)
        finally:
            self.handles={};self.metadata={};self.last_read={}
            if self.initialized:
                if self.event_state is not None:
                    self.library.SDL_SetGamepadEventsEnabled(self.event_state[0])
                    self.library.SDL_SetJoystickEventsEnabled(self.event_state[1])
                self.library.SDL_QuitSubSystem(0x2000)
                self.initialized=False
            for key,old in self.hints:
                if self.library.SDL_GetHint(key)==b'1':
                    if old is None:self.library.SDL_ResetHint(key)
                    else:self.library.SDL_SetHint(key,old)
            self.hints=[]
