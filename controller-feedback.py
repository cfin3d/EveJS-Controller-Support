# In-process combat feedback. Python 2.7 compatible.
import array as _fb_array
import ctypes as _fb_c
import math as _fb_math
import time as _fb_time
try:
    import __builtin__ as _fb_builtins
except ImportError:
    import builtins as _fb_builtins

FEEDBACK_KEYS = ('vibrationEnabled','vibrationStrength','damageVibration','destructionVibration',
                 'damageVibrationStrength','destructionVibrationStrength','dualsenseHaptics')
# Duration, low/high motor intensity, two waveform frequencies.
_FB_PATTERNS = {'laser':(.12,.14,.30,170.,205.), 'projectile':(.19,.42,.32,85.,145.),
                'missile':(.36,.78,.45,55.,95.), 'generic':(.18,.32,.27,100.,150.),
                'destruction':(1.15,1.,.85,48.,83.)}


def _fb_envelope(kind, age):
    duration = _FB_PATTERNS[kind][0]
    if age < 0. or age >= duration:return 0.
    attack = min(1.,age/.006)
    tail = max(0.,1.-age/duration)
    if kind=='destruction':return attack * tail * (.45+.55*_fb_math.exp(-age*3.))
    if kind=='missile':return attack * tail**1.3
    if kind=='projectile':return attack * tail**2. * (.65+.35*_fb_math.exp(-((age-.045)/.012)**2))
    return attack * tail**1.5


def _fb_levels(effects, now, strength):
    low = high = 0.
    for kind,start,gain in effects:
        weight = _fb_envelope(kind,now-start)*gain*strength
        low=max(low,_FB_PATTERNS[kind][1]*weight)
        high=max(high,_FB_PATTERNS[kind][2]*weight)
    return min(1.,low),min(1.,high)


def _fb_pcm(effects, start, duration, strength, rate=8000):
    # The controller's first two channels carry audible sound; keep them silent.
    # Only channels three/four receive independently authored haptic waveforms.
    samples = _fb_array.array('h')
    for index in range(int(duration*rate)):
        now=start+index/float(rate)
        left=right=0.
        for kind,stamp,gain in effects:
            age=now-stamp
            weight=_fb_envelope(kind,age)*gain*strength
            if not weight:continue
            pattern=_FB_PATTERNS[kind]
            left += pattern[1]*weight*(_fb_math.sin(2.*_fb_math.pi*pattern[3]*age)*.8 + _fb_math.sin(2.*_fb_math.pi*pattern[4]*age)*.2)
            right += pattern[2]*weight*_fb_math.sin(2.*_fb_math.pi*pattern[4]*age)
        # Headroom for layered hits, with a hard limit even under heavy combat.
        samples.extend((0,0,int(max(-.45,min(.45,left*.35))*32767),int(max(-.45,min(.45,right*.35))*32767)))
    if __import__('sys').byteorder!='little':samples.byteswap()
    return samples.tobytes() if hasattr(samples,'tobytes') else samples.tostring()


class _FeedbackAudioSpec(_fb_c.Structure):
    _fields_=[('format',_fb_c.c_uint32),('channels',_fb_c.c_int),('freq',_fb_c.c_int)]


class _FeedbackVibration(_fb_c.Structure):
    _fields_=[('left',_fb_c.c_uint16),('right',_fb_c.c_uint16)]


class _FeedbackOutput(object):
    def __init__(self,native):
        self.native=native
        self.pads=getattr(native,'devices',None)
        self.library=getattr(self.pads,'library',None)
        self.key,self.handle,self.slot=None,None,-1
        self.stream,self.audio_owned,self.audio_device=None,False,None
        self.audio_until,self.last_rumble,self.rumbling=0.,-1.,False
        self.enhanced_failed,self.rumble_failed=False,False
        self.status='No Controller Connected'
        self.functions={}
        self.set_state=None
        c=_fb_c
        signatures={
            'SDL_RumbleGamepad':([c.c_void_p,c.c_uint16,c.c_uint16,c.c_uint32],c.c_bool),
            'SDL_GetGamepadProperties':([c.c_void_p],c.c_uint32),
            'SDL_GetBooleanProperty':([c.c_uint32,c.c_char_p,c.c_bool],c.c_bool),
            'SDL_GetGamepadConnectionState':([c.c_void_p],c.c_int),
            'SDL_SendGamepadEffect':([c.c_void_p,c.c_void_p,c.c_int],c.c_bool),
            'SDL_GetAudioPlaybackDevices':([c.POINTER(c.c_int)],c.POINTER(c.c_uint32)),
            'SDL_GetAudioDeviceName':([c.c_uint32],c.c_char_p),
            'SDL_GetAudioDeviceFormat':([c.c_uint32,c.POINTER(_FeedbackAudioSpec),c.POINTER(c.c_int)],c.c_bool),
            'SDL_OpenAudioDeviceStream':([c.c_uint32,c.POINTER(_FeedbackAudioSpec),c.c_void_p,c.c_void_p],c.c_void_p),
            'SDL_GetAudioStreamFormat':([c.c_void_p,c.POINTER(_FeedbackAudioSpec),c.POINTER(_FeedbackAudioSpec)],c.c_bool),
            'SDL_GetAudioStreamDevice':([c.c_void_p],c.c_uint32),
            'SDL_ResumeAudioStreamDevice':([c.c_void_p],c.c_bool),
            'SDL_PauseAudioStreamDevice':([c.c_void_p],c.c_bool),
            'SDL_PutAudioStreamData':([c.c_void_p,c.c_void_p,c.c_int],c.c_bool),
            'SDL_GetAudioStreamQueued':([c.c_void_p],c.c_int),
            'SDL_ClearAudioStream':([c.c_void_p],c.c_bool),
            'SDL_DestroyAudioStream':([c.c_void_p],None)}
        if self.library:
            for name,(arguments,result) in signatures.items():
                function=getattr(self.library,name,None)
                if function:
                    function.argtypes=arguments;function.restype=result
                    self.functions[name]=function
        elif getattr(native,'xinput',None) is not None:
            for name in ('xinput1_4','xinput9_1_0'):
                try:
                    self.set_state=c.WinDLL(name).XInputSetState
                    self.set_state.argtypes=[c.c_uint32,c.POINTER(_FeedbackVibration)]
                    self.set_state.restype=c.c_uint32
                    break
                except (OSError,AttributeError):pass

    def current(self):
        if self.pads:
            instance=self.pads.last_instance
            entry=self.pads.handles.get(instance)
            return ('sdl',instance),entry[1] if entry else None,entry[0] if entry else -1
        slot=getattr(self.native,'selected',-1)
        return ('xinput',slot),None,slot

    def refresh(self):
        key,handle,slot=self.current()
        if key!=self.key or handle!=self.handle:
            self.stop()
            self.key,self.handle,self.slot=key,handle,slot
            self.enhanced_failed,self.rumble_failed=False,False
        return bool(self.handle if self.pads else 0<=self.slot<4)

    def valid_handle(self):
        entry=self.pads.handles.get(self.key[1]) if self.pads and self.key and self.key[0]=='sdl' else None
        return bool(self.handle and entry and entry[1]==self.handle)

    def rumble(self,low,high,duration=100):
        low,high=int(max(0.,min(1.,low))*65535),int(max(0.,min(1.,high))*65535)
        if self.library and self.valid_handle():
            function=self.functions.get('SDL_RumbleGamepad')
            success=bool(function and function(self.handle,low,high,duration))
        elif self.set_state and 0<=self.slot<4:
            vibration=_FeedbackVibration(low,high)
            success=self.set_state(self.slot,_fb_c.byref(vibration))==0
        else:success=False
        self.rumbling=success and bool(low or high)
        return success

    def open_audio(self):
        # SDL 3.4 has no stable HID-to-audio identity API. Fail closed if more
        # than one Sony controller or controller audio endpoint is present.
        # Never choose the default audio device or change its channel layout.
        required=('SDL_GetGamepadConnectionState','SDL_SendGamepadEffect','SDL_GetAudioPlaybackDevices',
                  'SDL_GetAudioDeviceName','SDL_GetAudioDeviceFormat','SDL_OpenAudioDeviceStream',
                  'SDL_GetAudioStreamFormat','SDL_GetAudioStreamDevice','SDL_ResumeAudioStreamDevice',
                  'SDL_PauseAudioStreamDevice','SDL_PutAudioStreamData','SDL_GetAudioStreamQueued',
                  'SDL_ClearAudioStream','SDL_DestroyAudioStream')
        if not self.valid_handle() or not all(name in self.functions for name in required):return False
        sony=[handle for slot,handle in self.pads.handles.values() if self.library.SDL_GetGamepadVendor(handle)==0x054c]
        if len(sony)!=1 or self.library.SDL_GetGamepadVendor(self.handle)!=0x054c:return False
        if self.library.SDL_GetRealGamepadType(self.handle)!=6 or self.library.SDL_GetGamepadProduct(self.handle) not in (0x0ce6,0x0df2):return False
        if self.functions['SDL_GetGamepadConnectionState'](self.handle)!=1:return False
        if not self.audio_owned:
            if not self.library.SDL_InitSubSystem(0x10):return False
            self.audio_owned=True
        count=_fb_c.c_int()
        devices=self.functions['SDL_GetAudioPlaybackDevices'](_fb_c.byref(count))
        candidates=[]
        try:
            if not 0<=count.value<=128:return False
            for index in range(count.value if devices else 0):
                identifier=int(devices[index])
                name=(self.functions['SDL_GetAudioDeviceName'](identifier) or b'').decode('utf-8','replace').lower()
                spec=_FeedbackAudioSpec()
                if ('dualsense' in name or 'wireless controller' in name) and self.functions['SDL_GetAudioDeviceFormat'](identifier,_fb_c.byref(spec),None) and spec.channels==4:
                    candidates.append(identifier)
        finally:
            if devices:self.library.SDL_free(devices)
        if len(candidates)!=1:return False
        spec=_FeedbackAudioSpec(0x8010,4,8000) # S16LE; SDL resamples, preserving four channels.
        stream=self.functions['SDL_OpenAudioDeviceStream'](candidates[0],_fb_c.byref(spec),None,None)
        if not stream:return False
        output=_FeedbackAudioSpec()
        if not self.functions['SDL_GetAudioStreamFormat'](stream,None,_fb_c.byref(output)) or output.channels!=4:
            self.functions['SDL_DestroyAudioStream'](stream)
            return False
        self.stream,self.audio_device=stream,candidates[0]
        # Stop emulated rumble before enabling the dedicated audio-haptic path.
        self.rumble(0.,0.)
        packet=_fb_c.create_string_buffer(47)
        if not self.functions['SDL_SendGamepadEffect'](self.handle,packet,47):
            self.close_audio()
            return False
        self.audio_until=0.
        return True

    def close_audio(self):
        if self.stream:
            try:
                self.functions['SDL_PauseAudioStreamDevice'](self.stream)
                self.functions['SDL_ClearAudioStream'](self.stream)
            finally:
                self.functions['SDL_DestroyAudioStream'](self.stream)
                self.stream,self.audio_device=None,None
        self.audio_until=0.

    def render(self,effects,now,strength,enhanced):
        if not self.refresh():self.status='No Controller Connected';return False
        dualsense=bool(self.valid_handle() and self.library.SDL_GetGamepadVendor(self.handle)==0x054c and self.library.SDL_GetRealGamepadType(self.handle)==6)
        if enhanced and dualsense and not self.enhanced_failed:
            try:
                if not self.stream and not self.open_audio():self.enhanced_failed=True
                if self.stream:
                    output=_FeedbackAudioSpec()
                    if not self.functions['SDL_GetAudioDeviceFormat'](self.audio_device,_fb_c.byref(output),None) or output.channels!=4:raise RuntimeError('Controller Audio Disconnected')
                    if not self.functions['SDL_GetAudioStreamFormat'](self.stream,None,_fb_c.byref(output)) or output.channels!=4:raise RuntimeError('Haptic Output Format Changed')
                    queued=self.functions['SDL_GetAudioStreamQueued'](self.stream)
                    if queued<0 or queued>6400:raise RuntimeError('Haptic Queue Unavailable')
                    # Maintain a short horizon rather than queuing whole hits.
                    if self.audio_until<now:
                        self.functions['SDL_ClearAudioStream'](self.stream)
                        self.audio_until=now
                    duration=max(0.,now+.045-self.audio_until)
                    if duration:
                        data=_fb_pcm(effects,self.audio_until,duration,strength)
                        buffer=_fb_c.create_string_buffer(data)
                        if not self.functions['SDL_PutAudioStreamData'](self.stream,buffer,len(data)):raise RuntimeError('Haptic Queue Failed')
                        self.audio_until+=duration
                    if not self.functions['SDL_ResumeAudioStreamDevice'](self.stream):raise RuntimeError('Haptic Stream Failed')
                    self.status='Enhanced DualSense Haptics (USB)'
                    return True
            except Exception:
                self.close_audio();self.enhanced_failed=True
        if self.stream:self.close_audio()
        low,high=_fb_levels(effects,now,strength)
        if now-self.last_rumble>=.030:
            self.last_rumble=now
            success=not self.rumble_failed and self.rumble(low,high)
            if not success and (low or high):self.rumble_failed=True
            self.status=('Standard Vibration (Enhanced Unavailable)' if enhanced and self.enhanced_failed else 'Standard Vibration') if success else 'Vibration Unavailable'
        return self.rumbling or low==high==0.

    def stop(self):
        try:self.close_audio()
        finally:
            if self.rumbling:
                try:self.rumble(0.,0.)
                except Exception:pass
            self.rumbling=False;self.last_rumble=-1.

    def close(self):
        try:self.stop()
        finally:
            if self.audio_owned:
                self.library.SDL_QuitSubSystem(0x10)
                self.audio_owned=False


class _CombatFeedback(object):
    __notifyevents__=['OnDamageMessage','OnDamageMessages','OnObjectExplode']

    def __init__(self,controller,output=None,clock=None):
        self.controller=controller
        self.output=output or _FeedbackOutput(controller.native)
        self.clock=clock or _fb_time.time
        self.effects,self.pending,self.seen=[],[],{}
        self.identity=None;self.previous_ship=None;self.previous_until=0.
        self.destroyed={};self.last_hit={}
        self.categories,self.weapon_groups={},None
        self.eligible,self.preview,self.registered,self.closed=False,False,False,False
        self.configuration=None
        self.status='Not Tested'
        self.manager=None

    def listen(self):
        self.manager=getattr(_fb_builtins,'sm',None)
        if self.manager:
            self.manager.RegisterNotify(self)
            self.registered=True

    def context(self):
        session=getattr(_fb_builtins,'session',None)
        return tuple(getattr(session,key,None) for key in ('charid','shipid','solarsystemid','stationid','structureid'))

    def category(self,weapon):
        try:
            if weapon in self.categories:return self.categories[weapon]
            cfg=getattr(_fb_builtins,'cfg')
            group=cfg.invtypes.Get(weapon).groupID
            if self.weapon_groups is None:
                const=getattr(_fb_builtins,'const')
                names={'groupEnergyWeapon':'laser','groupProjectileWeapon':'projectile','groupHybridWeapon':'projectile'}
                missiles=('groupRocket','groupLightMissile','groupHeavyMissile','groupHeavyAssaultMissile','groupCruiseMissile','groupTorpedo')
                names.update((name,'missile') for name in dir(const) if name.startswith('groupMissileLauncher') or name in missiles)
                self.weapon_groups=dict((getattr(const,name),kind) for name,kind in names.items() if getattr(const,name,None) is not None)
            kind=self.weapon_groups.get(group,'generic')
            if len(self.categories)>=128:self.categories={}
            self.categories[weapon]=kind
            return kind
        except Exception:pass
        return 'generic'

    def OnDamageMessage(self,message):
        # Notifications only enqueue bounded records. Device I/O stays on tick.
        try:
            if self.closed or not self.eligible or self.preview or not self.controller.settings['damageVibration']:return
            identity=self.context()
            if not identity[0] or not identity[1] or not identity[2] or identity[3] or identity[4]:return
            if not hasattr(message,'get') or message.get('target')!=identity[1] or message.get('observed'):return
            damage=float(message.get('damage',0.))
            if damage<=0. or _fb_math.isnan(damage) or _fb_math.isinf(damage):return
            now=self.clock()
            signature=tuple(message.get(key) for key in ('source','target','weapon','damage','hitQuality'))
            try:
                if now-self.seen.get(signature,-10.)<.05:return
                self.seen[signature]=now
                if len(self.seen)>64:self.seen=dict(sorted(self.seen.items(),key=lambda item:item[1])[-64:])
            except TypeError:pass
            kind=self.category(message.get('weapon'))
            self.pending=(self.pending+[(kind,now,identity[1])])[-16:]
        except Exception:pass

    def OnDamageMessages(self,messages):
        if isinstance(messages,(tuple,list)):
            for message in messages[:64]:self.OnDamageMessage(message)

    def OnObjectExplode(self,type_id,item_id):
        try:
            if self.closed or not self.eligible or self.preview or not self.controller.settings['destructionVibration']:return
            identity=self.context();now=self.clock()
            same_space=self.identity and identity[0]==self.identity[0] and identity[2]==self.identity[2] and not identity[3] and not identity[4]
            own_ship=item_id==identity[1] or same_space and (item_id==self.identity[1] or item_id==self.previous_ship and now<=self.previous_until)
            if not own_ship or not identity[0] or not identity[2] or identity[3] or identity[4] or item_id in self.destroyed:return
            self.destroyed[item_id]=now
            if len(self.destroyed)>32:self.destroyed=dict(sorted(self.destroyed.items(),key=lambda item:item[1])[-32:])
            self.pending=[('destruction',now,item_id)]
        except Exception:pass

    def cancel_gameplay(self):
        self.eligible=False
        if not self.preview:self.stop()

    def stop(self):
        self.effects,self.pending=[],[]
        self.preview=False;self.eligible=False
        try:self.output.stop()
        except Exception:self.status='Vibration Unavailable'

    def test(self):
        self.stop()
        settings=self.controller.settings
        if not settings['vibrationEnabled'] or settings['vibrationStrength']<=0.:return 'Vibration Is Disabled'
        if not self.controller.native.foreground():return 'Focus EVE To Test Vibration'
        if not self.output.refresh():return 'No Controller Connected'
        now=self.clock()
        self.output.enhanced_failed,self.output.rumble_failed=False,False
        delay=0.
        if settings['damageVibration'] and settings['damageVibrationStrength']>0.:
            gain=settings['damageVibrationStrength']
            self.effects=[('laser',now,gain),('projectile',now+.25,gain),('missile',now+.55,gain)]
            delay=1.
        if settings['destructionVibration']:self.effects.append(('destruction',now+delay,settings['destructionVibrationStrength']))
        if not any(gain>0 for kind,stamp,gain in self.effects):self.effects=[];return 'No Feedback Events Enabled'
        self.configuration=tuple(settings[key] for key in FEEDBACK_KEYS)
        self.identity=self.context()
        self.preview=True
        return 'Testing Vibration'

    def tick(self,now,active,foreground,pad,detecting=False):
        settings=self.controller.settings
        configuration=tuple(settings[key] for key in FEEDBACK_KEYS)
        identity=self.context()
        if self.configuration is not None and configuration!=self.configuration:
            self.stop()
            self.output.enhanced_failed,self.output.rumble_failed=False,False
        self.configuration=configuration
        if identity!=self.identity:
            old=self.identity
            same_space=old and old[0]==identity[0] and old[2]==identity[2] and not identity[3] and not identity[4]
            if same_space and old[1]!=identity[1]:
                self.previous_ship,self.previous_until=old[1],now+2.
                self.effects=[effect for effect in self.effects if effect[0]=='destruction']
                self.pending=[event for event in self.pending if event[0]=='destruction']
            else:
                self.stop();self.previous_ship=None;self.destroyed={}
            self.identity=identity
        if not foreground or pad is None or detecting or not settings['vibrationEnabled'] or settings['vibrationStrength']<=0.:
            self.stop();return
        if self.preview:
            menu=getattr(self.controller,'menu',None)
            if menu is None or not menu.visible():self.stop();return
        elif not active or not identity[0] or not identity[1] or not identity[2] or identity[3] or identity[4]:
            self.stop();return
        self.eligible=active and not self.preview
        events,self.pending=self.pending,[]
        for kind,stamp,ship in events:
            if now-stamp>.25:continue
            if kind=='destruction':
                self.effects=[(kind,now,settings['destructionVibrationStrength'])]
                break
            if ship!=identity[1] or any(effect[0]=='destruction' for effect in self.effects):continue
            if now-self.last_hit.get(kind,-10.)<.070:continue
            self.last_hit[kind]=now
            self.effects=(self.effects+[(kind,now,settings['damageVibrationStrength'])])[-8:]
        self.effects=[effect for effect in self.effects if now<effect[1]+_FB_PATTERNS[effect[0]][0]]
        if not self.effects:
            try:self.output.stop()
            except Exception:self.status='Vibration Unavailable'
            self.preview=False;return
        try:
            self.output.render(self.effects,now,settings['vibrationStrength'],settings['dualsenseHaptics'])
            self.status=self.output.status
        except Exception:
            self.stop();self.status='Vibration Unavailable'

    def close(self):
        if self.closed:return
        self.closed=True
        try:
            if self.registered:
                self.manager.UnregisterNotify(self)
                self.registered=False
        finally:
            self.effects,self.pending=[],[]
            try:self.output.close()
            except Exception:pass
