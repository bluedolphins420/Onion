"""Compile real patched C functions with mocked hardware and sanitizers."""
import ast
from pathlib import Path
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'src/keymon/keymon.c').read_text()
# Reuse only mock definitions, never execute the old defect expectations.
fixtures = {}
for node in ast.parse((ROOT / 'tests/mini_flip_release_audit.py').read_text()).body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id.endswith('_STUBS'):
            fixtures[node.targets[0].id] = ast.literal_eval(node.value)

def function(signature, source=SOURCE):
    start = source.index(signature + '\n{')
    return source[start:source.index('\n}', start) + 2]

def check(name, code, cases, link_flags=()):
    with tempfile.TemporaryDirectory() as folder:
        src = Path(folder) / 'test.c'
        exe = Path(folder) / 'test'
        src.write_text(code)
        subprocess.run(['gcc', '-std=gnu11', '-O1', '-g', '-no-pie',
                        '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                        str(src), '-o', str(exe), *link_flags], check=True)
        for case in cases:
            result = subprocess.run([str(exe), str(case)], text=True, capture_output=True,
                timeout=10, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
            assert result.returncode == 0, f'{name}/{case}: {result.stdout}\n{result.stderr}'
            print(f'PASS {name}/{case}: {result.stdout.strip()}', flush=True)

sleep = fixtures['SLEEP_STUBS'].replace('#include <stdio.h>', '#include <stdio.h>\n#include <errno.h>')
sleep = sleep.replace('void keyinput_disable(void) {}', 'bool keyinput_disable(void) {return true;}')
sleep = sleep.replace('int scenario, polls,', 'int last_lid_state=-1;\nint scenario, polls,')
sleep = sleep.replace('if(scenario==5) return 0;', 'if(scenario>=5 && scenario!=6) return polls>=5?1:0;')
sleep = sleep.replace('assert(++polls<=5);', '''assert(++polls<=5);
    fds[0].revents=POLLIN;
    if(scenario==11) {fds[0].revents=POLLHUP;return 1;}
    if(scenario==12) {errno=EBADF;return -1;}''')
sleep = sleep.replace('return scenario==1;', 'return scenario==1 || scenario==9;')
sleep = sleep.replace('int suspend(uint32_t mode) {return 0;}', 'int suspend(uint32_t mode) {return scenario==10?-1:0;}')
sleep = sleep.replace('int audit_usleep', '''#define MODE_GAME 1
int system_state=MODE_GAME;
void system_state_update(void) {}
bool check_autosave(void) {return scenario!=5 && scenario!=8;}
int audit_usleep''')
check('sleep', sleep + function('void suspend_exec(int timeout, bool lid_triggered)') + r'''
int main(int argc,char **argv) {
    scenario=atoi(argv[1]);
    if(scenario==7 || scenario==8) DEVICE_ID=354;
    int timeout=(scenario==5 || scenario==8 || scenario==9 || scenario==13)?500:-1;
    suspend_exec(timeout,scenario==2);
    int expected = scenario<=4 ? (scenario==3?2:1) : 5;
    if(scenario==10) expected=0;
    if(scenario==11 || scenario==12 || scenario==13) expected=1;
    assert(polls==expected);
    if(scenario<=4) assert(last_lid_state==1);
    assert(shutdowns==(scenario==13?1:0));
    if(scenario==5 || scenario==8) assert(resumed==1);
    printf("polls=%d lid_reads=%d shutdowns=%d resumes=%d\n", polls,lid_reads,shutdowns,resumed);
}
''', range(14))

check('sensor', fixtures['PARSER_STUBS'] + function('int read_lid_state(void)') + r'''
int main(void) {
    sample="1\n";assert(read_lid_state()==1);
    sample="0\n";assert(read_lid_state()==0);
    sample="";assert(read_lid_state()==-1);
    sample="x\n";assert(read_lid_state()==-1);
    sample="2\n";assert(read_lid_state()==-1);
    DEVICE_ID=354;assert(read_lid_state()==-1);
    puts("valid, empty, malformed and non-Flip readings");
}
''', [0])

proc = fixtures['PROC_STUBS'].replace('uint32_t suspendpid[PIDMAX];',
    re.search(r'uint32_t suspendpid\[[^;]+;', SOURCE)[0])
proc = proc.replace('int count, total, missing, signals;', 'int count, total, missing, signals, continued, failed, malformed, spaced, no_proc;\nvoid resume(void);')
proc = proc.replace('return (DIR*)1;', 'return no_proc?NULL:(DIR*)1;')
proc = proc.replace('fputs("100 (game) S 10 0 0 0 0 0",f);',
    'fputs(malformed && count==2?"invalid":(spaced?"100 (game ) title) S 10 0 0 0 0 0":"100 (game) S 10 0 0 0 0 0"),f);')
proc = proc.replace('signals++;return 0;', 'if(sig==SIGCONT){continued++;return 0;} if(failed && p==100)return -1; signals++;return 0;')
check('process', proc + function('int suspend(uint32_t mode)') + function('void resume(void)') + r'''
int main(int argc,char **argv) {
    int scenario=atoi(argv[1]);total=32;
    if(scenario==1) total=33;
    if(scenario==2) missing=1;
    if(scenario==3) malformed=1;
    if(scenario==4) spaced=1;
    if(scenario==5) failed=1;
    if(scenario==6) no_proc=1;
    int result=suspend(0);
    if(scenario==1){assert(result==-1);assert(suspendpid[0]==0);assert(continued==32);}
    else if(scenario==6){assert(result==-1);assert(signals==0);}
    else {
        int expected=(scenario==2 || scenario==3 || scenario==5)?31:32;
        assert(result==expected);assert(suspendpid[0]==expected);
        resume();assert(continued==expected);assert(suspendpid[0]==0);
    }
    printf("stops=%d continues=%d result=%d\n",signals,continued,result);
}
''', range(7))

battery_source=(ROOT/'src/common/system/battery.h').read_text()
check('charging', r'''
#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <assert.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#define PLATFORM_MIYOOMINI
#define MIYOO283 283
#define GPIO_DIR1 "/mock/"
#define GPIO_DIR2 "/mock/"
#define IS_MIYOO_PLUS_OR_FLIP() (DEVICE_ID==285 || DEVICE_ID==354)
int DEVICE_ID=285,scenario;
int getMilliseconds(void) {return 0;}
void file_write(const char *p,const char *v,int n) {}
FILE *audit_popen(const char *cmd,const char *mode) {
    if(scenario==0)return NULL;
    FILE *f=tmpfile();
    const char *text=scenario==1?"":scenario==2?"bad":scenario==3?
       "{\"battery\":80, \"voltage\":4000, \"charging\":3}":
       "{\"battery\":80, \"voltage\":4000, \"charging\":0}";
    fputs(text,f);rewind(f);return f;
}
#define popen audit_popen
#define pclose fclose
''' + function('bool battery_isCharging(void)', battery_source) + r'''
int main(int argc,char **argv) {scenario=atoi(argv[1]);assert(battery_isCharging()==(scenario!=4));puts("charge parse/failure policy correct");}
''', range(5))

# Exercise the actual lid dispatch block, including its outer state update.
start=SOURCE.index('        // Check lid state for Miyoo Mini Flip - poll')
end=SOURCE.index('\n        checkHeadphoneJack();',start)
check('lid_dispatch', r'''
#include <stdbool.h>
#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#define MIYOO285 285
#define printf_debug(...) ((void)0)
#define print_debug(...) ((void)0)
int DEVICE_ID=285,last_lid_state=1,current_lid_state,hibernate_start,closed_calls,shutdowns;
struct {int lid_close_action;bool disable_standby;} settings;
int read_lid_state(void){return 0;}
int getMilliseconds(void){return 123;}
void turnOffScreen(bool lid){assert(lid);closed_calls++;last_lid_state=1;}
void deepsleep(void){shutdowns++;}
void iteration(void){
''' + SOURCE[start:end] + r'''
}
int main(int argc,char **argv){
    settings.lid_close_action=atoi(argv[1]);settings.disable_standby=true;
    iteration();iteration();
    if(settings.lid_close_action==0){assert(closed_calls==2);assert(shutdowns==0);}
    if(settings.lid_close_action==1){assert(closed_calls==0);assert(shutdowns==1);}
    if(settings.lid_close_action==2){assert(closed_calls==0);assert(shutdowns==0);}
    puts("independent actions and repeated close tracking");
}
''', range(3))
print('30 regression scenarios passed with AddressSanitizer and UndefinedBehaviorSanitizer.')
