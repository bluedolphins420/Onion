"""Pin existing bundled apps, themes, libraries, installer layout and settings ABI."""
from pathlib import Path
import json
import subprocess

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'tests/onion_compatibility.json').read_text())
for path, expected in manifest.items():
    actual=subprocess.check_output(['git','rev-parse','HEAD:'+path],cwd=root,text=True).strip()
    assert actual==expected, f'Compatibility surface changed: {path}'
    print(f'PASS unchanged compatibility surface: {path}')
print('These source identity checks do not replace testing third-party apps on hardware.')
