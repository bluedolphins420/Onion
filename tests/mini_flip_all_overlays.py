from pathlib import Path
import os,shlex,subprocess,tempfile,shutil,json,struct,zlib
REPO=Path(__file__).resolve().parents[1]
ROOT=REPO.parent
SHELL=shlex.split(os.environ.get('OVERLAY_TEST_SHELL','sh'))
SCRIPT=REPO/'static/build/App/AllOverlays/apply.sh'
BASE=ROOT/'research/all-overlay-tests';BASE.mkdir(parents=True,exist_ok=True)
def cfg(text):return dict((k.strip(),v.strip().strip('"')) for k,v in [l.split('=',1) for l in text.splitlines() if '=' in l])
with tempfile.TemporaryDirectory(dir=BASE,prefix='SD card ') as td:
 sd=Path(td)
 shutil.copytree(REPO/'static/build/App/AllOverlays',sd/'App/AllOverlays')
 shutil.copytree(REPO/'static/build/.tmp_update/res/display',sd/'.tmp_update/res/display')
 profile=sd/'Saves/CurrentProfile/config';profile.mkdir(parents=True)
 originals={}
 def put(rel,text):
  p=sd/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);originals[p]=p.read_bytes();return p
 globalcfg=put('RetroArch/.retroarch/retroarch.cfg','input_overlay_enable = "false"\nvideo_filter = "original.filt"\naudio_driver = "oss"\n')
 gb=put('Saves/CurrentProfile/config/Gambatte/GBC.cfg','input_overlay = "tested-ozboss.cfg"\ninput_overlay_enable = "true"\n')
 gba=put('Saves/CurrentProfile/config/mGBA/GBA.cfg','input_overlay = "tested-gba.cfg"\nvideo_filter = "offset.filt"\n')
 arcade=put('Saves/CurrentProfile/config/FinalBurn Neo/FinalBurn Neo.cfg','input_overlay_enable = "false"\nvideo_scale_integer = "true"\n')
 game=put('Saves/CurrentProfile/config/SwanStation/nested/Game.cfg','input_overlay_enable = "true"\nvideo_filter = ""\n')
 ws=put('Saves/CurrentProfile/config/Beetle WonderSwan/Portrait.cfg','video_rotation = "1"\n')
 gg=put('Saves/CurrentProfile/config/PicoDrive/GG.cfg','video_dingux_ipu_keep_aspect = "false"\n')
 opt=put('Saves/CurrentProfile/config/gpSP/gpSP.opt','gpsp_color_correction = "disabled"\n')
 snesopt=put('Saves/CurrentProfile/config/Snes9x/Game.opt','snes9x_overscan = "enabled"\naudio = "keep"\n')
 save=put('Saves/game.srm','SAVE');remap=put('Saves/CurrentProfile/config/controls.rmp','REMAP')
 nds=put('Emu/NDS/resources/settings.json',json.dumps(dict(overlay=0,mode=8,pen=3,maxcpu=1600)))
 for p in (sd/'.tmp_update/res/display/profiles').rglob('*'):
  if p.is_file():originals[p]=p.read_bytes()
 env=dict(os.environ,DEVICE_ID='285',MINIFLIP_SD=sd.as_posix(),MINIFLIP_RES='752x560',MINIFLIP_LOCK=(sd/'display.lock').as_posix(),MINIFLIP_JQ=shutil.which('jq'))
 def run(action,code=0,**changes):
  r=subprocess.run(SHELL+[SCRIPT.as_posix(),action],env=dict(env,**changes),capture_output=True,text=True,timeout=60);assert r.returncode==code,(r.stdout,r.stderr)
 run('apply',DEVICE_ID='354');assert globalcfg.read_bytes()==originals[globalcfg]
 run('apply')
 assert cfg(snesopt.read_text())=={'snes9x_overscan':'disabled','audio':'keep'}
 assert all(p.read_bytes()==originals[p] for p in [gb,gba,opt,save,remap])
 assert cfg(arcade.read_text())['input_overlay'].endswith('/tv.cfg') and cfg(arcade.read_text())['video_scale_integer']=='true'
 assert cfg(ws.read_text())['input_overlay'].endswith('/lcd.cfg') and cfg(ws.read_text())['video_rotation']=='1'
 assert cfg(gg.read_text())['input_overlay'].endswith('/lcd.cfg')
 assert cfg(globalcfg.read_text())['video_filter']=='original.filt'
 assert cfg(game.read_text())['input_overlay_enable']=='false'
 nes=cfg((profile/'FCEUmm/FCEUmm.cfg').read_text())
 assert nes['input_overlay'].endswith('/crt.cfg') and nes['video_filter'].endswith('/filters/crt.filt')
 assert nes['video_dingux_ipu_filter_type']=='1' and nes['video_scale_integer']=='false'
 for c in ['Supafaust','Snes9x','PicoDrive']:
  assert cfg((profile/c/(c+'.cfg')).read_text())['input_overlay'].endswith('/crt.cfg')
 for core in ['PCSX-ReARMed','SwanStation']:
  assert cfg((profile/core/(core+'.cfg')).read_text())['input_overlay_enable']=='false'
 assert json.loads(nds.read_text())==dict(overlay=1,mode=8,pen=3,maxcpu=1600)
 for resolution in ['752x560','640x480']:
  assert cfg((sd/f'.tmp_update/res/display/profiles/{resolution}/clean/Handy/Handy.cfg').read_text())['input_overlay_enable']=='false'
 first=arcade.read_bytes();run('apply');assert arcade.read_bytes()==first
 later=put('Saves/CurrentProfile/config/New Core/New Core.cfg','input_overlay_enable = "false"\n');run('apply');assert cfg(later.read_text())['input_overlay_enable']=='true'
 arcade.write_text(arcade.read_text()+'manual = "keep"\n');edited=arcade.read_bytes()
 run('boot',MINIFLIP_RES='640x480');assert arcade.read_bytes()==edited
 assert struct.unpack('>II',(sd/'App/AllOverlays/current/lcd.png').read_bytes()[16:24])==(640,480)
 run('restore',1);assert arcade.read_bytes()==edited and globalcfg.read_bytes()==originals[globalcfg]
 assert nds.read_bytes()==originals[nds] and not (profile/'SwanStation/SwanStation.cfg').exists()
 arcade.write_bytes(first);run('restore');assert all(p.read_bytes()==s for p,s in originals.items())
 run('apply');assert (sd/'Saves/CurrentProfile/.mini-flip-all-overlays-v1/active').read_text().strip()=='2'
 before=globalcfg.read_bytes();(sd/'display.lock').mkdir();run('apply',1);(sd/'display.lock').rmdir();assert globalcfg.read_bytes()==before
 run('bad',2);run('apply',2,MINIFLIP_RES='bad')
 (sd/'App/AllOverlays/assets/752x560/lcd.png').unlink();run('apply',1);assert globalcfg.read_bytes()==before
 print('PASS real shell: global/core/game/template coverage, PS1 exclusions, GB/GBC/GBA preservation, colors/remaps/saves intact, native resolutions, later edits, restore cycles, lock and invalid/missing-asset guards; actual jq changed only DraStic overlay.')
# Every grid pixel is transparent or faint, with no opaque mask clipping
# rotated games, unusual source resolutions, or standalone system artwork.
for p in (REPO/'static/build/App/AllOverlays/assets').rglob('*.png'):
 if p.stem=='crt':
  expected=REPO/'static/build/.tmp_update/res/display/ozboss/crt/crt.png' if p.parent.name=='752x560' else p.with_name('tv.png')
  assert p.read_bytes()==expected.read_bytes()
  continue
 data=p.read_bytes();w,h=struct.unpack('>II',data[16:24]);assert f'{w}x{h}'==p.parent.name
 at=8;compressed=b''
 while at<len(data):
  n=struct.unpack('>I',data[at:at+4])[0];tag=data[at+4:at+8];body=data[at+8:at+8+n]
  assert zlib.crc32(tag+body)&0xffffffff==struct.unpack('>I',data[at+8+n:at+12+n])[0]
  if tag==b'IDAT':compressed+=body
  at+=n+12
 raw=zlib.decompress(compressed);assert len(raw)==h*(w*4+1)
 for y in range(h):
  assert raw[y*(w*4+1)]==0
  for x in range(w):
   alpha=raw[y*(w*4+1)+1+x*4+3]
   assert alpha==(10 if x%2 or y%2 else 0) if p.stem=='lcd' else alpha==(14 if y%2 else 0)
print('PASS original CRT assets and native PNG integrity and every alpha coordinate; maximum added opacity 14/255.')
