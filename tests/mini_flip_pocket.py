"""Exercise the actual suspend loop against closed-lid pocket button events."""
import ast
from pathlib import Path
import os
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT/'src/keymon/keymon.c').read_text()
for node in ast.parse((ROOT/'tests/mini_flip_regression.py').read_text()).body:
    if isinstance(node, ast.FunctionDef) and node.name in ('function', 'check'):
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<shared runner>', 'exec'))
for node in ast.parse((ROOT/'tests/mini_flip_release_audit.py').read_text()).body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id=='SLEEP_STUBS':
        stub=ast.literal_eval(node.value)
stub=stub.replace('#include <stdio.h>', '#include <stdio.h>\n#include <errno.h>')
stub=stub.replace('void keyinput_disable(void) {}','bool keyinput_disable(void) {return true;}')
stub=stub.replace('int scenario, polls,','int last_lid_state=-1;\nint scenario, polls,')
# Legacy fixture puts the opening brace on the signature line.
start=stub.index('int read_lid_state(void) {');end=stub.index('\n}',start)+2
stub=stub[:start]+r'''int read_lid_state(void) {
    lid_reads++;
    if(scenario==4) return 1;
    if(scenario==5 || scenario==6) return -1;
    if(scenario==7) return polls==0?1:(polls>=105?1:0);
    if(polls>=105) return 1;
    if(scenario==2 && polls>1) return -1;
    return 0;
}'''+stub[end:]
start=stub.index('int audit_poll(');end=stub.index('\n}',start)+2
stub=stub[:start]+r'''int audit_poll(struct pollfd *p, unsigned long count, int timeout) {
    assert(++polls<=105);
    p[0].revents=POLLIN;
    if(scenario==5 && polls==105) {p[0].revents=POLLHUP;}
    return 1;
}'''+stub[end:]
start=stub.index('int audit_read(');end=stub.index('\n}',start)+2
stub=stub[:start]+r'''int audit_read(int fd, void *p, unsigned long count) {
    ev.type=EV_KEY;
    ev.code=scenario==3?HW_BTN_MENU:HW_BTN_POWER;
    ev.value=(scenario==1)?(polls==1?PRESSED:REPEAT):RELEASED;
    return sizeof(ev);
}'''+stub[end:]
stub=stub.replace('return scenario==1;', 'return scenario==9;')
stub=stub.replace('void display_on(void) {}','void display_on(void) {assert(polls==105 || scenario==4 || scenario==6 || scenario==8 || scenario==10);}')
stub=stub.replace('int audit_usleep', '#define MODE_GAME 1\nint system_state=0;\nvoid system_state_update(void) {}\nbool check_autosave(void) {return true;}\nint audit_usleep')
check('pocket',stub+function('void suspend_exec(int timeout, bool lid_triggered)')+r'''
int main(int argc,char **argv) {
    scenario=atoi(argv[1]);
    if(scenario==10) DEVICE_ID=354;
    suspend_exec(scenario==8 || scenario==9?500:-1, scenario!=4 && scenario!=6 && scenario!=7 && scenario!=10);
    int expected=scenario==4 || scenario==6 || scenario==8 || scenario==10?1:105;
    assert(polls==expected);
    assert(shutdowns==(scenario==8?1:0));
    assert(resumed==(scenario==8?2:1));
    puts("closed-lid tap/hold/menu, sensor failure, opening, timeout and non-Flip controls");
}
''',range(11))
print('11 pocket-wake scenarios passed with ASan and UBSan.')
