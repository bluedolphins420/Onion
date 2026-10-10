"""Community integration tests: real fbmode source, mocked driver, real shell routing."""
import ast
from pathlib import Path
import os
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=''
for node in ast.parse((ROOT/'tests/mini_flip_regression.py').read_text()).body:
    if isinstance(node,ast.FunctionDef) and node.name=='check':
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<runner>','exec'))
mock=r'''
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
int scenario,closed,puts_count,maps,gets,pan_count;
unsigned long long ticks;
struct fb_var_screeninfo driver;
int mock_open(const char*p,int flags,...){return scenario==1?-1:7;}
int mock_close(int fd){assert(fd==7);closed++;return 0;}
int mock_clock(clockid_t c,struct timespec*t){ticks+=10;t->tv_sec=ticks/1000;t->tv_nsec=(ticks%1000)*1000000;return 0;}
int mock_sleep(useconds_t n){return 0;}
void*mock_mmap(void*a,size_t n,int p,int f,int fd,off_t o){maps++;if(scenario==4)return MAP_FAILED;assert(n<=6000000);void*r=malloc(n);assert(r);memset(r,0xaa,n);return r;}
int mock_msync(void*a,size_t n,int f){unsigned char*p=a;for(size_t i=0;i<n;i++)assert(p[i]==0);return 0;}
int mock_munmap(void*a,size_t n){free(a);return 0;}
int mock_ioctl(int fd,unsigned long req,...){
 va_list ap;va_start(ap,req);void*p=va_arg(ap,void*);va_end(ap);
 if(req==FBIOGET_VSCREENINFO){
   gets++;if(scenario==3)return -1;
   memcpy(p,&driver,sizeof driver);
   if(puts_count && scenario==2)((struct fb_var_screeninfo*)p)->yres_virtual+=1;
   if(puts_count && scenario==8)((struct fb_var_screeninfo*)p)->bits_per_pixel=16;
 }else if(req==FBIOGET_FSCREENINFO){
   struct fb_fix_screeninfo*f=p;memset(f,0,sizeof *f);
   f->line_length=driver.xres*4+16;f->smem_len=scenario==5?100:6000000;
 }else if(req==FBIOPUT_VSCREENINFO){
   puts_count++;if(scenario==6)return -1;memcpy(&driver,p,sizeof driver);
 }else if(req==FBIOPAN_DISPLAY){pan_count++;if(scenario==9)return -1;}
 return 0;
}
#define open mock_open
#define close mock_close
#define clock_gettime mock_clock
#define usleep mock_sleep
#define mmap mock_mmap
#define msync mock_msync
#define munmap mock_munmap
#define ioctl mock_ioctl
#define main fbmode_main
'''
code=mock+(ROOT/'src/fbmode/fbmode.c').read_text()+r'''
#undef main
int main(int argc,char**argv){
 scenario=atoi(argv[1]);driver.xres=752;driver.yres=560;
 driver.xres_virtual=752;driver.yres_virtual=1680;driver.bits_per_pixel=32;
 char*args[]={"fbmode","640x480","--pages","3","--preclear","--timeout","30",NULL};
 int n=7;if(scenario==7)args[3]="1";
 if(scenario==10){args[1]="--probe";n=2;}
 if(scenario==11){args[1]="752x560";args[3]="2";}
 int rc=fbmode_main(n,args);
 assert(rc==((scenario==0 || scenario==10 || scenario==11)?0:(scenario==2 || scenario==8)?3:2));
 assert(closed==(scenario==1?0:1));
 if(scenario==0 || scenario==11){assert(puts_count==1&&maps==2&&pan_count==1);assert(driver.yres_virtual==driver.yres*(scenario==0?3:2));}
 if(scenario==10)assert(puts_count==0&&maps==0&&pan_count==0);
 if(scenario==7)assert(puts_count==0&&maps==0);
 puts("driver geometry, pitch, timeout, errors and read-only probe checked");
}
'''
check('framebuffer',code,range(12))

runtime=(ROOT/'static/build/.tmp_update/runtime.sh').read_text()
def shell_function(name):
    start=runtime.index(name+'() {')
    return runtime[start:runtime.index('\n}',start)+2]
selection=shell_function('select_main_ui')
recovery=shell_function('recover_main_ui').replace('/tmp/cmd_to_run.sh','"$sysdir/handoff"')
for case in range(8):
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);(root/'config').mkdir();(root/'bin').mkdir()
        if case!=0:(root/'config/.openMainUI').touch()
        if case==4:(root/'config/.showExpert').touch()
        if case!=2:
            exe=root/'bin/MainUI-open';exe.write_text('#!/bin/sh\nexit 0\n');exe.chmod(0o755)
        (root/'handoff').touch()
        device='354' if case==3 else '285'
        status=139 if case==5 else 127 if case==6 else 0
        script=selection+'\n'+recovery+r'''
log(){ :; }
select_main_ui
printf '%s\n' "$mainui_srcname"
recover_main_ui "$STATUS"
'''
        result=subprocess.run(['sh','-c',script],env=dict(os.environ,sysdir=folder,DEVICE_ID=device,STATUS=str(status)),text=True,capture_output=True,check=True)
        expected='MainUI-285-clean' if case in (0,2) else 'MainUI-354-clean' if case==3 else 'MainUI-open'
        assert result.stdout.strip()==expected,(case,result.stdout)
        assert (root/'handoff').exists()==(case not in (5,6))
        assert (root/'config/.openMainUI').exists()==(case not in (0,5,6))
        print(f'PASS launcher/{case}: selection and crash fallback')
print('12 framebuffer sanitizer scenarios and 8 shell routing cases passed.')
