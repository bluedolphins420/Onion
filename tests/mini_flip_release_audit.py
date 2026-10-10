"""Run exact upstream C functions with simulated hardware; no device access.

These are defect reproductions, not release acceptance tests. A PASS means the
observed behavior matches the documented defect (or named healthy control).
Run on Linux with Python 3 and GCC. Source remains unmodified.
"""
from pathlib import Path
import subprocess
import tempfile
import os

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'src/keymon/keymon.c').read_text()

def function(signature):
    start = SOURCE.index(signature + '\n{')
    end = SOURCE.index('\n}', start) + 2
    return SOURCE[start:end]

def run_c(name, code, args=(), overflow=False):
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / 'audit.c'
        binary = Path(folder) / 'audit'
        source.write_text(code)
        flags = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-g'] if overflow else []
        subprocess.run(['gcc', '-std=gnu11', '-O0', *flags, str(source), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary), *args], capture_output=True, text=True,
                                timeout=10, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        if overflow:
            assert result.returncode != 0 and 'global-buffer-overflow' in result.stderr, result.stderr
            print('PASS:', name, '(AddressSanitizer global-buffer-overflow)')
            print('\n'.join(result.stderr.splitlines()[:14]))
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            print('PASS:', name, result.stdout.strip())

SLEEP_STUBS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <poll.h>
#include <linux/input.h>
#define MIYOO285 285
#define RELEASED 0
#define PRESSED 1
#define REPEAT 2
#define HW_BTN_POWER KEY_POWER
#define HW_BTN_MENU KEY_MENU
#define REPEAT_SEC(x) 100
#define print_debug(x) ((void)0)
int DEVICE_ID=285, input_fd=0;
struct input_event ev;
struct pollfd fds[1];
struct {int brightness, volume; bool mute;} settings={5,10,false};
int scenario, polls, lid_reads, shutdowns, resumed, power_offs;
int read_lid_state(void) {
    int n=lid_reads++;
    if(scenario==2 || scenario==6) return 1;
    if(scenario==3) return n==0?0:(n==1?-1:1);
    if(scenario==5) return 0;
    return n==0?0:1;
}
int audit_poll(struct pollfd *p, unsigned long count, int timeout) {
    assert(++polls<=5);
    return polls==5 || scenario==4 ? 1 : 0;
}
int audit_read(int fd, void *p, unsigned long count) {
    ev.type=polls==5?EV_KEY:EV_SYN;
    ev.code=HW_BTN_POWER; ev.value=RELEASED; return sizeof(ev);
}
bool battery_isCharging(void) {return scenario==1;}
int getMilliseconds(void) {return polls*500;}
void keyinput_disable(void) {}
void keyinput_enable(void) {}
int audit_system(const char *s) {return 0;}
bool temp_flag_get(const char *s) {return false;}
int suspend(uint32_t mode) {return 0;}
void setVolume(int n) {}
void rumble(int n) {}
void display_setBrightnessRaw(int n) {}
void display_setBrightness(int n) {}
void display_off(void) {}
void display_on(void) {}
void system_powersave_on(void) {}
void system_powersave_off(void) {power_offs++;}
void short_pulse(void) {}
void takeScreenshot(void) {}
void resume(void) {resumed++;}
void deepsleep(void) {shutdowns++;} /* check_autosave refusal */
int audit_usleep(unsigned int n) {return 0;}
#define poll audit_poll
#define read audit_read
#define system audit_system
#define usleep audit_usleep
'''
SLEEP_MAIN = r'''
int main(int argc,char **argv) {
    scenario=atoi(argv[1]);
    suspend_exec(scenario==5?500:-1);
    assert(polls==(scenario==0?1:5));
    if(scenario==1 || scenario==4) assert(lid_reads==1);
    if(scenario==5) {assert(shutdowns==4); assert(resumed==5);}
    printf("polls=%d lid_reads=%d shutdown_attempts=%d resume_calls=%d\n",
           polls,lid_reads,shutdowns,resumed);
}
'''
for scenario, name in enumerate([
    'control: ordinary unplugged lid opening wakes',
    'defect: charging suppresses lid wake until power release',
    'defect: reopening before initial sleep sample loses wake',
    'defect: one failed lid read discards closed state',
    'defect: continuous input events starve lid wake checks',
    'defect: rejected autosave shutdown repeatedly resumes behind black screen',
    'control: power-button sleep with open lid waits for power release',
]):
    run_c(name, SLEEP_STUBS + function('void suspend_exec(int timeout)') + SLEEP_MAIN, [str(scenario)])

PARSER_STUBS = r'''
#include <stdio.h>
#include <assert.h>
#include <string.h>
#define MIYOO285 285
int DEVICE_ID=285;
const char *sample;
FILE *audit_fopen(const char *path,const char *mode) {
    FILE *f=tmpfile(); fputs(sample,f); rewind(f); return f;
}
#define fopen audit_fopen
'''
run_c('defect: invalid sensor data is treated as closed', PARSER_STUBS + function('int read_lid_state(void)') + r'''
int main(void) {
    sample="1\n"; assert(read_lid_state()==1);
    sample="0\n"; assert(read_lid_state()==0);
    sample=""; assert(read_lid_state()==-1);
    sample="x\n"; assert(read_lid_state()==0);
    puts("open/closed/empty controls pass; x incorrectly becomes closed");
}
''')

PROC_STUBS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <dirent.h>
#include <signal.h>
#include <unistd.h>
#define PF_KTHREAD 0x00200000
#define PIDMAX 32
uint32_t suspendpid[PIDMAX];
int count, total, missing, signals;
DIR *audit_opendir(const char *p) {return (DIR*)1;}
struct dirent *audit_readdir(DIR *p) {
    static struct dirent d;
    if(count==total) return NULL;
    d.d_type=DT_DIR; sprintf(d.d_name,"%d",100+count++); return &d;
}
FILE *audit_fopen(const char *p,const char *m) {
    if(missing && count==2) return NULL;
    FILE *f=tmpfile(); fputs("100 (game) S 10 0 0 0 0 0",f); rewind(f); return f;
}
int audit_closedir(DIR *p) {return 0;}
pid_t audit_getpid(void) {return 999;}
void audit_sync(void) {}
int audit_kill(pid_t p,int sig) {signals++;return 0;}
void screenshot_system(void) {}
void terminate_retroarch(void) {}
void terminate_drastic(void) {}
void display_reset(void) {}
#define opendir audit_opendir
#define readdir audit_readdir
#define fopen audit_fopen
#define closedir audit_closedir
#define getpid audit_getpid
#define sync audit_sync
#define kill audit_kill
'''
proc_function = function('int suspend(uint32_t mode)')
run_c('defect: failed proc read reuses previous process metadata', PROC_STUBS + proc_function + r'''
int main(void) {total=2;missing=1;suspend(0);assert(signals==2);puts("unreadable second process still receives SIGSTOP");}
''')
run_c('defect: 32nd stopped process overruns PID array', PROC_STUBS + proc_function + r'''
int main(void) {total=32;suspend(0);}
''', overflow=True)
print('All 10 audit scenarios reproduced against exact source functions.')
