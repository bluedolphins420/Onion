"""Package the validated Community4 add-on without touching the OS installer."""
from pathlib import Path
import zipfile,hashlib,json,subprocess
repo=Path(__file__).resolve().parents[1]
root=repo.parent
out=root/'releases/Onion-Mini-Flip-Community4-All-Overlays'
out.mkdir(parents=True,exist_ok=True)
provenance=json.loads((root/'research/overlay-filter-build.json').read_text())
binary=repo/'static/build/App/AllOverlays/filters/mini_flip_crt.so'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==provenance['sha256']
readme="""MINI FLIP / COMMUNITY4 - ALL SYSTEM OVERLAYS

INSTALL
1. Close the game and fully shut down the device. Back up the SD card.
2. Extract this ZIP into the SD card root, merging App and .tmp_update.
   Include the hidden .tmp_update directory and replace the supplied files.
3. Boot and run Apps > All system overlays once, then launch a game.
This is an add-on for our Community4 build, not a full OS installer.

COVERAGE
NES (FCEUmm), SNES (Supafaust/Snes9x), Mega Drive/Genesis and Sega CD/32X
(PicoDrive), Master System (Gearsystem), and PC Engine/SuperGrafx receive
OzBoss's matching CRT artwork at native 752x560. Other installed supported
RetroArch cores receive gentle fullscreen scanlines by default.
Other handheld cores use a subtle LCD grid. The already-tested GB/GBC/GBA
and Neo Geo Pocket profiles are preserved. Game Gear stays on the LCD grid.
Installed DraStic gets its native grid enabled; its layout is unchanged.
PS1 overlays are explicitly disabled, including PCSX-ReARMed/SwanStation.
Standalone ports have no universal overlay interface and are not changed.
No emulator cores are installed; availability does not guarantee every game
on a system runs full speed. Existing vivid handheld color options remain.

CRT ADAPTATION
The original OzBoss artwork is unchanged. This add-on uses an independently
written CPU filter instead of the original CRT binary. It produces 224 rows:
240/239-line sources crop eight top overscan rows; 192-line sources are
centered; double-height SNES frames average adjacent rows. 256/512-pixel
sources lose 3/6 pixels on each side. Other tall sizes are resampled.
This is deliberate TV overscan presentation, not preservation of every edge
pixel. Bilinear fullscreen scaling aligns the artwork. At 640x480 the artwork
falls back to light scanlines. No GPU shader or overclock is introduced.
Snes9x's extra overscan crop is disabled. Custom crops in other core options
may need manual adjustment. Hardware performance is not benchmarked.

RESTORE / MANUAL CHANGES
Run Apps > Restore system overlays to undo this add-on's configuration
changes. Backups are in Saves/CurrentProfile/.mini-flip-all-overlays-v1.
Later manual edits are retained and reported in /tmp/mini_flip_all_overlays.log.
Use this restore before the older Display Restore app. Display Clean only
covers known templates; use Restore system overlays for a complete undo.
Re-running All system overlays reapplies its defaults. Ordinary boot only
refreshes native-resolution assets and preserves manual overrides.

SOURCE AND CREDITS
CRT artwork: OzBoss. See App/AllOverlays/CREDITS.txt and the original readme.
The original readme describes the author's filter; our adapter replaces it.
Our normalizer source and GPL-3.0 license are included under Source.
Source commit and successful validation run are in BUILD-INFO.json.
"""
files={}
for folder in ['App/AllOverlays','App/RestoreAllOverlays']:
 for p in (repo/'static/build'/folder).rglob('*'):
  if p.is_file() and 'current' not in p.parts:files[p.relative_to(repo/'static/build').as_posix()]=p.read_bytes()
key='.tmp_update/script/mini_flip_display.sh'
files[key]=(repo/'static/build'/key).read_bytes()
files['INSTALL.txt']=readme.encode()
files['Source/BUILD.txt']=b'From Source: arm-linux-gnueabihf-gcc -O2 -fPIC -shared tools/mini_flip_crt.c -o mini_flip_crt.so\nGPL-3.0-or-later. This license applies to the filter code, not OzBoss artwork.\n'
for src,dst in [('tools/mini_flip_crt.c','Source/tools/mini_flip_crt.c'),('tests/fixtures/softfilter.h','Source/tests/fixtures/softfilter.h'),('LICENSE','Source/LICENSE')]:files[dst]=(repo/src).read_bytes()
provenance['package_source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
files['BUILD-INFO.json']=(json.dumps(provenance,indent=2)+'\n').encode()
for name,data in list(files.items()):
 if name.endswith(('.sh','.cfg','.filt','.txt','.json','.c','.h','.md')):files[name]=data.replace(b'\r\n',b'\n')
archive=out/'Community4-All-System-Overlays.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name,data in sorted(files.items()):
  entry=zipfile.ZipInfo(name,(2026,10,10,0,0,0));entry.create_system=3
  entry.external_attr=(0o100755 if name.endswith(('.sh','.so')) else 0o100644)<<16
  entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,data)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and set(z.namelist())==set(files)
 for name,data in files.items():assert z.read(name)==data
assert b'filter = mini_flip_crt' in files['App/AllOverlays/filters/crt.filt']
assert 'App/AllOverlays/filters/mini_flip_crt.so' in files
(out/'INSTALL.txt').write_text(readme)
(out/'SHA256SUMS.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
(out/'BUILD-INFO.json').write_bytes(files['BUILD-INFO.json'])
print(json.dumps({'path':str(archive),'files':len(files),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
