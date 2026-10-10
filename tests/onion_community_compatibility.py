from pathlib import Path
import json,subprocess
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'tests/onion_community_compatibility.json').read_text())
lines=subprocess.check_output(['git','ls-tree','-r','HEAD'],cwd=root,text=True).splitlines()
actual={line.split('\t',1)[1]:line.split('\t',1)[0].split()[2] for line in lines}
for path,sha in manifest['files'].items():
    assert actual.get(path)==sha,path
prefixes=('static/build/','static/packages/','static/configs/','static/dist/','lib/')
for path in actual:
    if path.startswith(prefixes):
        assert path in manifest['files'] or path in manifest['allowed'],path
print(f"PASS {len(manifest['files'])} original compatibility files unchanged; only explicit display/selector exceptions permitted.")
