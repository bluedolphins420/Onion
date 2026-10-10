"""Generate original low-opacity overlays and matching Miyoo scaler defaults."""
from pathlib import Path
import json,struct,zlib
import shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'static/build/.tmp_update/res/display'
def png(path,w,h,pixels):
    def chunk(t,b): return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
    raw=b''.join(b'\0'+bytes(pixels[y*w*4:(y+1)*w*4]) for y in range(h))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b''))
TV=['FCEUmm','Nestopia','QuickNES','Mesen','Supafaust','Snes9x','Snes9x 2005','Snes9x 2005 Plus','Snes9x 2010','ChimeraSNES','PicoDrive','Genesis Plus GX','Beetle PCE','Beetle PCE Fast','Beetle SuperGrafx','Stella 2014','ProSystem','O2EM','FreeIntv','FreeChaF','Gearsystem']
CLEAN=['PCSX-ReARMed','FinalBurn Neo','FB Alpha','MAME 2003-Plus','MAME 2003-Xtreme','Beetle WonderSwan','Handy','PokeMini','Potator','SameDuck','VecX','blueMSX','Atari800','a5200','fuse','cap32','crocods','VICE x64','x1','DOSBox-pure','Hatari','PUAE','P-UAE Xtreme Amped','scummvm','scummvm_standalone','mGBA']
profiles={c+'/'+c+'.cfg':('tv',False,False) for c in TV}
profiles.update({c+'/'+c+'.cfg':('clean',None,False) for c in CLEAN})
profiles['PCSX-ReARMed/PCSX-ReARMed.cfg']=('clean',False,False)
profiles['Gambatte/Gambatte.cfg']=('gb',True,True)
profiles['TGB Dual/TGB Dual.cfg']=('clean',True,True)
for c in ['gpSP','Beetle GBA','VBA-M','VBA Next']: profiles[c+'/'+c+'.cfg']=('gba',True,True)
profiles['mGBA/GBA.cfg']=('gba',True,True)
profiles['Beetle NeoPop/Beetle NeoPop.cfg']=('ngp',True,True)
for c in ['Gearsystem','Genesis Plus GX','PicoDrive']: profiles[c+'/GG.cfg']=('clean',False,False)
baseline=ROOT/'static/configs/Saves/CurrentProfile/config'
for f in baseline.rglob('*.cfg'):
    dst=OUT/'baseline'/f.relative_to(baseline);dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(f.read_bytes())
geometry={}
for w,h in [(752,560),(640,480)]:
    res=f'{w}x{h}';d=OUT/'overlays'/res;d.mkdir(parents=True,exist_ok=True)
    geometry[res]={}
    for kind,sw,sh in [('gb',160,144),('gba',240,160),('ngp',160,152),('tv',w,h)]:
        scale=min(w//sw,h//sh);vw=sw*scale;vh=sh*scale;x=((w-vw)//2)&~1;y=(h-vh)//2
        geometry[res][kind]=[x,y,vw,vh,scale]
        pixels=bytearray(w*h*4)
        for py in range(h):
            for px in range(w):
                inside=x<=px<x+vw and y<=py<y+vh
                if kind=='tv': rgba=(0,0,0,14 if py%2 else 0)
                elif inside:
                    edge=(px-x)%scale==scale-1 or (py-y)%scale==scale-1
                    rgba=(0,0,0,22 if edge else 0)
                else:
                    rim=(x-2<=px<x+vw+2 and y-2<=py<y+vh+2)
                    rgba=(46,50,54,255) if rim else (12,14,17,255)
                at=(py*w+px)*4;pixels[at:at+4]=bytes(rgba)
        png(d/(kind+'.png'),w,h,pixels)
        (d/(kind+'.cfg')).write_text(f'overlays = 1\noverlay0_overlay = "{kind}.png"\noverlay0_full_screen = true\noverlay0_descs = 0\n')
    for mode in ['balanced','clean']:
        for rel,(kind,aspect,integer) in profiles.items():
            use_overlay=mode=='balanced' and kind!='clean'
            values={'video_scale_integer':str(integer).lower(),'video_dingux_ipu_filter_type':'2' if integer else ('0' if kind=='tv' else '1'),
                'video_filter':'','video_shader_enable':'false','input_overlay_enable':str(use_overlay).lower(),
                'input_overlay':f'/mnt/SDCARD/.tmp_update/res/display/overlays/{res}/{kind}.cfg' if use_overlay else '',
                'input_overlay_opacity':'1.0','input_overlay_auto_scale':'false','input_overlay_auto_rotate':'false','input_overlay_hide_in_menu':'true'}
            if aspect is not None: values['video_dingux_ipu_keep_aspect']=str(aspect).lower()
            target=OUT/'profiles'/res/mode/rel;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(''.join(f'{k} = "{v}"\n' for k,v in values.items()))
(OUT/'geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
(OUT/'README.txt').write_text('''Mini Flip display defaults v1. Original generated artwork; GPL-3.0-or-later,
matching the Onion project. Source: tools/generate_display_profiles.py.
No third-party bezel artwork is redistributed by this addition.

Balanced: GB/GBC, GBA and NGP use integer scaling, subtle aligned grids and
neutral bezels; TV cores use bicubic scaling and a subtle screen-space
scanline texture (not an emulation of a specific CRT). PS1/arcade/computers
use clean scaling without additional software filters. Clean removes the
overlays while retaining the scaling choices. Frame rate/battery improvement
is not measured. DraStic and standalone emulators retain their own defaults.

Driver constants verified at RetroArch 69a4f0ea: 0=bicubic, 1=bilinear,
2=nearest. Miyoo integer scaling uses the source dimensions; no custom
viewport settings or shader presets are assumed. 480p has separate assets.
GBA 560p viewport: 720x480 at 16,40. GB/GBC: 480x432 at 136,64.
NGP: 480x456 at 136,52. Core output changes/rotation/game overrides may require
an individual override; these are defaults, not universal game certification.
''')
print(f'Generated {len(profiles)} profiles in two modes at two resolutions.')
