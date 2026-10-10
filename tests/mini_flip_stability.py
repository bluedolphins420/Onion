"""Host regression tests for real source functions, including failure paths."""
import ast
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ''
# Share the sanitizer runner without executing the lid suite.
module = ast.parse((ROOT/'tests/mini_flip_regression.py').read_text())
for node in module.body:
    if isinstance(node, ast.FunctionDef) and node.name in ('function', 'check'):
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<shared runner>', 'exec'))
def extract(path, signature):
    return function(signature, (ROOT/path).read_text())

base = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
'''
check('command_output', base + extract('src/common/utils/process.h',
'int process_start_read_return(const char *cmdline, char *out_str, size_t out_size)') + r'''
int main(int argc,char **argv) {
 const char *commands[]={"printf 1200","printf '800\n1200\n'","true","printf 12345","printf 1000; exit 1","printf '\n'","printf 0"};
 const char *expected[]={"1200","1200","","","","","0"};
 int c=atoi(argv[1]); char out[5]="xxxx";
 int result=process_start_read_return(commands[c],out,sizeof out);
 assert(result==((c==2 || c==3 || c==4)?-1:0));
 assert(strcmp(out,expected[c])==0);
 assert(process_start_read_return("true",NULL,0)==-1);
 puts("bounded output, status, and final byte preserved");
}
''', range(7))

files=''.join(extract('src/common/utils/file.c', s) for s in (
'void file_readLastLine(const char *filename, char *out_str)',
'char *file_read(const char *path)',
'bool file_write(const char *path, const char *str, uint32_t len)',
'char *file_removeExtension(const char *myStr)'))
check('files', base + files + r'''
#include <dirent.h>
int fdcount(void){int n=0;DIR*d=opendir("/proc/self/fd");while(readdir(d))n++;closedir(d);return n;}
int main(int argc,char **argv){
 int c=atoi(argv[1]); char name[]="/tmp/onion-file-XXXXXX";
 int fd=mkstemp(name);assert(fd>=0);close(fd); char out[256]="stale";
 if(c==0){int before=fdcount();for(int i=0;i<1000;i++)file_readLastLine(name,out);assert(!*out);assert(fdcount()==before);}
 if(c==1){assert(file_write(name,"first\nlast",10));file_readLastLine(name,out);assert(!strcmp(out,"last"));}
 if(c==2){close(0);assert(file_write(name,"abc",3));char*p=file_read(name);assert(p&&!strcmp(p,"abc"));free(p);}
 if(c==3){unlink(name);assert(file_read(name)==NULL);assert(!file_write(name,"a",1));file_readLastLine(name,out);assert(!*out);}
 if(c==4){char*p=file_read(name);assert(p&&!p[0]);free(p);}
 if(c==5){char data[300];memset(data,'x',sizeof data);assert(file_write(name,data,sizeof data));file_readLastLine(name,out);assert(strlen(out)==254);}
 if(c==6){char*p=file_removeExtension("game.");assert(p&&!strcmp(p,"game."));free(p);p=file_removeExtension("game.zip");assert(!strcmp(p,"game"));free(p);}
 unlink(name);puts("file safety and descriptor lifecycle");
}
''', range(7))

check('input_grab', base + r'''
#include <linux/input.h>
int input_fd=1,calls,scenario;bool keyinput_disabled;
int mock_ioctl(int fd,unsigned long request,int value){
 calls++;
 if(scenario==0 || (scenario==2 && calls==3))return 0;
 errno=scenario==1?EBUSY:scenario==2?EINTR:ENODEV;return -1;
}
#define ioctl mock_ioctl
#define usleep(x) ((void)0)
''' + extract('src/keymon/input_fd.h','bool keyinput_disable(void)')+
extract('src/keymon/input_fd.h','void keyinput_enable(void)')+r'''
int main(int argc,char**argv){
 scenario=atoi(argv[1]); bool result=keyinput_disable();
 assert(result==(scenario==0 || scenario==2));
 assert(calls==(scenario==0?1:scenario==1?5:scenario==2?3:1));
 if(result){calls=0;scenario=0;assert(keyinput_disable());assert(calls==0);keyinput_enable();assert(calls==1&&!keyinput_disabled);}
 puts("bounded grab retries and idempotent release");
}
''',range(4))

check('power_restore',base+r'''
#define CPU_SCALING_GOVERNOR "governor"
#define CPU_SCALING_MIN_FREQ "min_freq"
#define file_get(fp,path,format,dest) {fp=fopen(path,"r");if(fp){fscanf(fp,format,dest);fclose(fp);}}
#define file_put(fp,path,format,value) {fp=fopen(path,"w");if(fp){fprintf(fp,format,value);fclose(fp);}}
int scenario,commands;
FILE* mock_popen(const char*c,const char*m){if(scenario==1)return NULL;FILE*f=tmpfile();fputs(scenario==2?"bad":scenario==3?"0":"1200\n",f);rewind(f);return f;}
int mock_system(const char*c){assert(!strcmp(c,"cpuclock 1200"));commands++;return 0;}
#define popen mock_popen
#define pclose fclose
#define system mock_system
''' + extract('src/common/system/system.h','void system_powersave(bool enabled)')+r'''
int main(int argc,char**argv){
 scenario=atoi(argv[1]);char folder[]="/tmp/onion-power-XXXXXX";assert(mkdtemp(folder));assert(!chdir(folder));
 FILE*f=fopen("governor","w");fputs("performance",f);fclose(f);
 if(scenario!=4){f=fopen("min_freq","w");fputs("400000",f);fclose(f);}
 system_powersave(false);assert(commands==0);
 system_powersave(true);system_powersave(true);system_powersave(false);system_powersave(false);
 assert(commands==(scenario==0?1:0));char b[32];f=fopen("governor","r");assert(fgets(b,sizeof b,f));fclose(f);assert(!strcmp(b,"performance"));
 if(scenario!=4){f=fopen("min_freq","r");assert(fgets(b,sizeof b,f));fclose(f);assert(!strcmp(b,"400000"));}
 unlink("governor");unlink("min_freq");chdir("/");rmdir(folder);
 puts("restore exact CPU state; malformed and unavailable readings skip changes");
}
''',range(5))

check('charging_cache',base+r'''
#define PLATFORM_MIYOOMINI
#define MIYOO283 283
#define GPIO_DIR1 "/mock/"
#define GPIO_DIR2 "/mock/"
#define IS_MIYOO_PLUS_OR_FLIP() (DEVICE_ID==285 || DEVICE_ID==354)
int DEVICE_ID=285,scenario,calls;
uint32_t now;uint32_t getMilliseconds(void){return now;}
void file_write(const char*p,const char*v,int n){}
FILE*mock_popen(const char*c,const char*m){calls++;FILE*f=tmpfile();fputs("{\"battery\":80, \"voltage\":4000, \"charging\":0}",f);rewind(f);return f;}
int mock_pclose(FILE*f){fclose(f);return scenario==1?1:0;}
#define popen mock_popen
#define pclose mock_pclose
'''+extract('src/common/system/battery.h','bool battery_isCharging(void)')+r'''
int main(int argc,char**argv){scenario=atoi(argv[1]);now=UINT32_MAX-200;
for(int i=0;i<1000;i++)assert(battery_isCharging()==(scenario==1));
assert(calls==1);now+=499;assert(battery_isCharging()==(scenario==1));assert(calls==1);
now++;assert(battery_isCharging()==(scenario==1));assert(calls==2);
puts("1000 calls share one sample; refresh at 500ms across clock wrap; failed command is unknown");}
''',range(2))

check('axp_transfer',base+r'''
#include <linux/i2c-dev.h>
#include <linux/i2c.h>
#include <stdarg.h>
#define AXPDEV "/mock/i2c"
#define AXPID 0x34
int scenario,closed;
int mock_open(const char*p,int mode){return scenario==0?-1:9;}
int mock_close(int fd){assert(fd==9);closed++;return 0;}
int mock_ioctl(int fd,unsigned long request,...){
 if(request!=I2C_RDWR)return 0;
 va_list ap;va_start(ap,request);struct i2c_rdwr_ioctl_data*p=va_arg(ap,void*);va_end(ap);
 if(scenario==1)return 0;
 if(scenario==2)return -1;
 if(p->nmsgs==2)p->msgs[1].buf[0]=123;
 return p->nmsgs;
}
#define open mock_open
#define close mock_close
#define ioctl mock_ioctl
'''+extract('src/common/system/axp.h','int axp_read(unsigned char address)')+
extract('src/common/system/axp.h','int axp_write(unsigned char address, unsigned char val)')+r'''
int main(int argc,char**argv){scenario=atoi(argv[1]);assert(axp_read(1)==(scenario==3?123:-1));assert(axp_write(1,2)==(scenario==3?0:-1));assert(closed==(scenario==0?0:2));puts("only complete I2C transfers accepted");}
''',range(4))
check('battery_percentage',base+r'''
int scenario,fail;
FILE*mock_popen(const char*c,const char*m){
 if(fail==1)return NULL;FILE*f=tmpfile();
 fputs(fail==2?"bad":fail==3?"{\"battery\":12345, \"voltage\":4000, \"charging\":0}":fail==4?"{\"battery\":80":"{\"battery\":73, \"voltage\":4000, \"charging\":0}",f);rewind(f);return f;
}
int mock_pclose(FILE*f){fclose(f);return fail==5?1:0;}
#define popen mock_popen
#define pclose mock_pclose
'''+extract('src/batmon/batmon.c','int getBatPercMMP(void)')+r'''
int main(int argc,char**argv){scenario=atoi(argv[1]);fail=scenario;assert(getBatPercMMP()==-1);fail=0;assert(getBatPercMMP()==73);fail=scenario;assert(getBatPercMMP()==73);unlink("/tmp/.axp_result");puts("missing, malformed and failed samples preserve last valid percentage");}
''',range(1,6))

check('battery_database',base+r'''
#include <sqlite3.h>
sqlite3*bat_log_db;int scenario,battery_current_state_duration=7,opens,closes;
#define DEVICE_SN "mini-flip"
int open_battery_log_db(void){
 opens++;if(scenario==4)return -1;
 assert(sqlite3_open(":memory:",&bat_log_db)==SQLITE_OK);
 if(scenario!=1){
 assert(sqlite3_exec(bat_log_db,"CREATE TABLE bat_activity(id INTEGER PRIMARY KEY,device_serial TEXT,duration INTEGER);CREATE TABLE device_specifics(id INTEGER PRIMARY KEY,device_serial TEXT,best_session INTEGER);",0,0,0)==SQLITE_OK);
 if(scenario!=2)assert(sqlite3_exec(bat_log_db,"INSERT INTO bat_activity VALUES(1,'mini-flip',10);INSERT INTO device_specifics VALUES(1,'mini-flip',1);INSERT INTO device_specifics VALUES(2,'other',99);",0,0,0)==SQLITE_OK);
 if(scenario==3)assert(sqlite3_exec(bat_log_db,"PRAGMA query_only=ON",0,0,0)==SQLITE_OK);
 }return 1;
}
void close_battery_log_db(void){
 assert(sqlite3_next_stmt(bat_log_db,NULL)==NULL);
 assert(sqlite3_close(bat_log_db)==SQLITE_OK);bat_log_db=NULL;closes++;
}
'''+extract('src/batmon/batmon.c','void update_current_duration(void)')+
extract('src/batmon/batmon.c','int set_best_session_time(int best_session)')+r'''
int main(int argc,char**argv){scenario=atoi(argv[1]);
 for(int i=0;i<100;i++){battery_current_state_duration=7;update_current_duration();assert(battery_current_state_duration==(scenario==0?0:7));assert(set_best_session_time(30)==(scenario==0?1:0));}
 assert(opens==200&&closes==(scenario==4?0:200));
 puts("200 database operations close all statements and preserve pending duration on failure");}
''',range(5),('-lsqlite3',))
print('39 additional stability scenarios passed with ASan and UBSan.')
