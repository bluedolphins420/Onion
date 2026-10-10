"""Validate generated geometry/assets and execute the actual migration shell."""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess,tempfile,zlib
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'static/build/.tmp_update/res/display'
SCRIPT=ROOT/'static/build/.tmp_update/script/mini_flip_display.sh'
geometry=json.loads((ASSETS/'geometry.json').read_text())
allowed={'video_crop_overscan','video_scale_integer','video_dingux_ipu_filter_type','video_filter','video_shader_enable','input_overlay_enable','input_overlay','input_overlay_opacity','input_overlay_auto_scale','input_overlay_auto_rotate','input_overlay_hide_in_menu','video_dingux_ipu_keep_aspect'}
def parse(s): return dict((a.strip(),b.strip().strip('"')) for a,b in (l.split('=',1) for l in s.splitlines() if '=' in l and not l.lstrip().startswith('#')))
count=0
for res,items in geometry.items():
    w,h=map(int,res.split('x'))
    for kind,(x,y,vw,vh,scale) in items.items():
        data=(ASSETS/'overlays'/res/(kind+'.png')).read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II',data[16:24])==(w,h)
        at=8;compressed=b''
        while at<len(data):
            n=struct.unpack('>I',data[at:at+4])[0];tag=data[at+4:at+8];body=data[at+8:at+8+n]
            assert zlib.crc32(tag+body)&0xffffffff==struct.unpack('>I',data[at+8+n:at+12+n])[0]
            if tag==b'IDAT': compressed+=body
            at+=n+12
        raw=zlib.decompress(compressed);assert len(raw)==h*(w*4+1)
        for py in range(h):
            assert raw[py*(w*4+1)]==0
            for px in range(w):
                a=raw[py*(w*4+1)+1+px*4+3]
                if kind=='tv': assert a==(14 if py%2 else 0)
                elif x<=px<x+vw and y<=py<y+vh:
                    assert a==(22 if (px-x)%scale==scale-1 or (py-y)%scale==scale-1 else 0)
                else: assert a==255
        if kind!='tv':
            sw,sh={'gb':(160,144),'gba':(240,160),'ngp':(160,152)}[kind]
            factor=min(w//sw,h//sh)
            assert [x,y,vw,vh,scale]==[((w-sw*factor)//2)&~1,(h-sh*factor)//2,sw*factor,sh*factor,factor]
        count+=1
for f in (ASSETS/'profiles').rglob('*.cfg'):
    cfg=parse(f.read_text());assert set(cfg)<=allowed
    assert cfg['video_filter'] in ['', '/mnt/SDCARD/RetroArch/.retroarch/filters/video/Offset_Custom/Offset_up10px.filt']
    assert cfg['video_shader_enable']=='false'
    if cfg['video_filter']:
        assert '752x560/balanced' in f.as_posix() and '/gba/gba.cfg' in cfg['input_overlay']
    if cfg['input_overlay_enable']=='true':
        p=ROOT/'static/build'/cfg['input_overlay'].removeprefix('/mnt/SDCARD/')
        assert p.exists() and p.with_suffix('.png').exists()
    count+=1
print(f'PASS {count} geometry/PNG/profile checks; every overlay alpha and grid coordinate verified.')

# Pin original artwork, configs, readmes and CRT binary byte-for-byte.
oz=ASSETS/'ozboss'
def rgba_rows(data):
    w,h=struct.unpack('>II',data[16:24]);compressed=b'';at=8
    while at<len(data):
        n=struct.unpack('>I',data[at:at+4])[0];tag=data[at+4:at+8];body=data[at+8:at+8+n]
        assert zlib.crc32(tag+body)&0xffffffff==struct.unpack('>I',data[at+8+n:at+12+n])[0]
        if tag==b'IDAT': compressed+=body
        at+=n+12
    raw=zlib.decompress(compressed);stride=w*4;prev=bytearray(stride);rows=[]
    assert len(raw)==h*(stride+1)
    for y in range(h):
        start=y*(stride+1);method=raw[start];row=bytearray(raw[start+1:start+1+stride])
        for i in range(stride):
            a=row[i-4] if i>=4 else 0;b=prev[i];c=prev[i-4] if i>=4 else 0
            if method==4:
                p=a+b-c;dist=[abs(p-a),abs(p-b),abs(p-c)];predict=[a,b,c][dist.index(min(dist))]
            else: predict=[0,a,b,(a+b)//2][method]
            row[i]=(row[i]+predict)&255
        rows.append(row);prev=row
    return rows

for name,digest in json.loads((oz/'SHA256.json').read_text()).items():
    data=(oz/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest,name
    if name.endswith('.png'): assert struct.unpack('>II',data[16:24])==(752,560)
    if name.endswith('.cfg'):
        cfg=parse(data.decode());assert (oz/name).with_name(cfg['overlay0_overlay']).is_file()
# The transparent game apertures must coincide with the driver's even-x
# RGB565 placement; do not assume a generic 750px-wide/custom viewport.
for kind,bounds in [('gb',(64,0,686,560)),('gbc',(64,0,686,560)),('gba',(16,10,736,490))]:
    rows=rgba_rows((oz/kind/(kind+'.png')).read_bytes())
    points=[(x,y) for y,row in enumerate(rows) for x in range(752) if row[x*4+3]<255]
    assert (min(x for x,y in points),min(y for x,y in points),max(x for x,y in points)+1,max(y for x,y in points)+1)==bounds
elf=(oz/'crt/filter/crt.so').read_bytes()
assert elf[:6]==b'\x7fELF\x01\x01' and int.from_bytes(elf[18:20],'little')==40
native=ASSETS/'profiles/752x560/balanced'
for system in ['GB','GBC']:
    cfg=parse((native/f'Gambatte/{system}.cfg').read_text())
    assert cfg['video_scale_integer']=='false' and cfg['video_dingux_ipu_keep_aspect']=='true'
    assert cfg['video_dingux_ipu_filter_type']=='0' and cfg['input_overlay'].endswith(f'/{system.lower()}/{system.lower()}.cfg')
    opt=parse((native/f'Gambatte/{system}.opt').read_text())
    assert opt['gambatte_mix_frames']=='mix' and opt['gambatte_dark_filter_level']==('0' if system=='GB' else '15')
assert parse((native/'gpSP/gpSP.opt').read_text())['gpsp_drc']=='enabled'
assert parse((native/'gpSP/gpSP.opt').read_text())['gpsp_frame_mixing']=='enabled'
print('PASS original OzBoss assets, native resolution, separate GB/GBC profiles, offset selection and stock dynarec retention.')

def dependencies(sd):
    filters=sd/'RetroArch/.retroarch/filters/video/Offset_Custom';filters.mkdir(parents=True)
    (filters/'Offset_up10px.filt').write_text('filter = offset_up\noffset_up_px = 10\n')
    (filters/'offset_up.so').write_bytes(b'fixture; actual package checked separately')

def exercise(shell):
    with tempfile.TemporaryDirectory(prefix='display reset test ') as td:
        sd=Path(td);profile=sd/'Saves/CurrentProfile';config=profile/'config';config.mkdir(parents=True)
        shutil.copytree(ASSETS,sd/'.tmp_update/res/display')
        dependencies(sd)
        target=config/'Gambatte/Gambatte.cfg';target.parent.mkdir();original='audio_latency = "99"\nvideo_filter = "old.filt"\ninput_player1_a = "9"\n';target.write_text(original)
        game=target.parent/'My Game.cfg';game.write_text('input_overlay = "custom.cfg"\n')
        directory=target.parent/'GB.cfg';directory.write_text('video_scale_integer = "false"\n')
        extra=config/'Unknown Core/nested/Old Game.cfg';extra.parent.mkdir(parents=True);extra.write_text('old = "yes"\n')
        (target.parent/'Gambatte.opt').write_text('old options')
        (target.parent/'My Game.opt').write_text('old game options')
        protected={extra.parent/'Unknown.opt':'other core options',target.parent/'controls.rmp':'old remap',profile/'game.srm':'save data'}
        for f,text in protected.items(): f.write_text(text)
        state=profile/'.mini-flip-display-v3'
        oldstate=profile/'.mini-flip-display-v2';oldstate.mkdir();(oldstate/'active').write_text('1')
        oldsnapshot=oldstate/'snapshot-1';oldsnapshot.mkdir();(oldsnapshot/'complete').write_text('752x560/balanced')
        env=dict(os.environ,DEVICE_ID='285',MINIFLIP_SD=str(sd),MINIFLIP_RES='752x560',MINIFLIP_LOCK=str(sd/'display.lock'))
        def run(action,code=0,**changes):
            result=subprocess.run(shell+[str(SCRIPT),action],env=dict(env,**changes),capture_output=True,text=True,timeout=30)
            assert result.returncode==code,(action,result.stdout,result.stderr)
        run('boot',DEVICE_ID='354');assert target.read_text()==original and not state.exists()
        run('boot');session=state/'snapshot-1';cfg=parse(target.read_text())
        assert cfg['video_filter']=='' and 'input_player1_a' not in cfg and 'audio_latency' not in cfg
        assert (session/'archive/Gambatte/Gambatte.cfg').read_text()==original
        assert not game.exists() and directory.exists() and not extra.exists()
        assert (session/'archive/Gambatte/Gambatte.opt').read_text()=='old options'
        assert not (target.parent/'My Game.opt').exists()
        assert (oldsnapshot/'complete').read_text()=='752x560/balanced'
        assert (session/'archive/Unknown Core/nested/Old Game.cfg').read_text()=='old = "yes"\n'
        for f,text in protected.items(): assert f.read_text()==text
        assert parse((config/'PCSX-ReARMed/PCSX-ReARMed.cfg').read_text())['audio_driver']=='sdl'
        gba=config/'gpSP/gpSP.cfg';assert parse(gba.read_text())['video_scale_integer']=='true'
        assert parse((config/'mGBA/mGBA.cfg').read_text())['input_overlay_enable']=='false'
        assert parse((config/'TGB Dual/TGB Dual.cfg').read_text())['input_overlay_enable']=='false'
        assert parse((config/'mGBA/GBA.cfg').read_text())['input_overlay_enable']=='true'
        first=target.read_bytes();run('boot');assert target.read_bytes()==first
        game.write_text('manual = "new"\n')
        target.write_text(target.read_text()+'user_note = "preserve"\n');edited=target.read_bytes()
        run('boot');assert target.read_bytes()==edited and game.read_text()=='manual = "new"\n'
        run('boot',MINIFLIP_RES='640x480');assert target.read_bytes()==edited and '640x480' in gba.read_text()
        run('clean');assert parse(target.read_text())['input_overlay_enable']=='false' and 'user_note' in target.read_text()
        run('balanced');assert parse(target.read_text())['input_overlay_enable']=='true'
        run('restore',1);assert target.read_text()==original and not gba.exists()
        assert (target.parent/'Gambatte.opt').read_text()=='old options'
        assert (target.parent/'My Game.opt').read_text()=='old game options'
        assert game.read_text()=='manual = "new"\n' and directory.exists() and extra.exists()
        run('boot');assert target.read_text()==original and not gba.exists()
        run('restore',1);assert target.read_text()==original
        # Explicit re-enable after restore takes another snapshot and resets again.
        run('balanced');assert (state/'active').read_text().strip()=='2' and not game.exists()
        assert (state/'snapshot-2/archive/Gambatte/My Game.cfg').read_text()=='manual = "new"\n'
        target.write_text(target.read_text()+'later = "edit"\n');edited=target.read_bytes()
        run('restore',1);assert target.read_bytes()==edited
        # Live-lock, argument and asset failures do not mutate existing config.
        (sd/'display.lock').mkdir();(sd/'display.lock/pid').write_text(str(os.getpid()))
        run('clean',1);(sd/'display.lock/pid').unlink();(sd/'display.lock').rmdir()
        run('bad',2);run('boot',2,MINIFLIP_RES='bad')
        before=target.read_bytes();(sd/'.tmp_update/res/display/overlays/752x560/gba.png').unlink()
        run('clean',1);assert target.read_bytes()==before
        for f,text in protected.items(): assert f.read_text()==text
    # Simulate interruption after one atomic archive move, before reset completion.
    with tempfile.TemporaryDirectory() as td:
        sd=Path(td);profile=sd/'Saves/CurrentProfile';config=profile/'config';config.mkdir(parents=True)
        shutil.copytree(ASSETS,sd/'.tmp_update/res/display')
        dependencies(sd)
        state=profile/'.mini-flip-display-v3';session=state/'snapshot-1';archive=session/'archive';archive.mkdir(parents=True)
        (state/'active').write_text('1\n');(session/'reset-files').write_text('already.cfg\npending.cfg\n')
        (archive/'already.cfg').write_text('saved');(config/'pending.cfg').write_text('pending')
        result=subprocess.run(shell+[str(SCRIPT),'boot'],env=dict(os.environ,DEVICE_ID='285',MINIFLIP_SD=str(sd),MINIFLIP_RES='752x560',MINIFLIP_LOCK=str(sd/'display.lock')),capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stderr
        assert (archive/'already.cfg').read_text()=='saved' and (archive/'pending.cfg').read_text()=='pending' and not (config/'pending.cfg').exists()
    print('PASS reset migration under '+ ' '.join(shell)+': all old CFG overrides archived, stock core requirements seeded, options/remaps/saves intact, manual edits persist, repeated boot/restore, resolution fallback, snapshot cycles, interruption recovery and failure guards.')
exercise(['sh'])
if shutil.which('busybox'): exercise(['busybox','sh'])
else: raise RuntimeError('BusyBox target-shell validation required')
# Runtime must apply only after resolution detection has run.
runtime=(ROOT/'static/build/.tmp_update/runtime.sh').read_text()
assert runtime.index('    init_system\n')<runtime.index('mini_flip_display.sh')<runtime.index('    update_time\n')
print('Display validation complete.')
