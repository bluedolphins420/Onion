/* Execute the distributed ARM filter under qemu-user, using RetroArch ABI. */
#include "fixtures/softfilter.h"
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int cfg_float(void *u,const char*k,float*v,float d){*v=d;return 0;}
static int cfg_int(void *u,const char*k,int*v,int d){*v=d;return 0;}
static int cfg_hex(void *u,const char*k,unsigned*v,unsigned d){*v=d;return 0;}
int main(int argc,char **argv) {
    assert(argc==2);
    void *lib=dlopen(argv[1],RTLD_NOW);if(!lib){puts(dlerror());return 1;}
    softfilter_get_implementation_t get=(softfilter_get_implementation_t)dlsym(lib,"softfilter_get_implementation");assert(get);
    const struct softfilter_implementation *f=get(0);assert(f&&f->api_version==2);
    printf("Filter: %s; formats=%u\n",f->ident,f->query_input_formats());
    struct softfilter_config cfg={.get_float=cfg_float,.get_int=cfg_int,.get_hex=cfg_hex,.free=free};
    const unsigned sizes[][2]={{256,240},{256,224},{256,239},{320,224},{320,240},{256,192},{512,224},{512,239},{512,448},{512,478},{256,242},{352,240},{320,192}};
    for(unsigned fmt=1;fmt<=2;fmt<<=1) {
        if(!(f->query_input_formats()&fmt)) continue;
        assert(f->query_output_formats(fmt)&fmt);
        void *ctx=f->create(&cfg,fmt,fmt,1024,512,1,0,NULL);assert(ctx);
        unsigned nt=f->query_num_threads(ctx);assert(nt>0&&nt<=1);
        for(unsigned t=0;t<sizeof(sizes)/sizeof(sizes[0]);t++) {
            unsigned w=sizes[t][0],h=sizes[t][1],ow=0,oh=0,bpp=fmt==1?2:4;
            f->query_output_size(ctx,&ow,&oh,w,h);
            assert(ow>0&&ow<=2048&&oh>0&&oh<=1024);
            size_t is=w*bpp+16,os=ow*bpp+16,total=os*oh;
            unsigned char *input=calloc(h+2,is),*raw=malloc(total+128),*output=raw+64;
            assert(input&&raw);memset(raw,0xa7,total+128);
            for(unsigned y=0;y<h;y++) for(unsigned x=0;x<w;x++) {
                if(bpp==2)((uint16_t*)(input+y*is))[x]=(uint16_t)(y+1);
                else ((uint32_t*)(input+y*is))[x]=y+1;
            }
            struct softfilter_work_packet packet[1]={{0}};
            f->get_work_packets(ctx,packet,output,os,input,w,h,is);assert(packet[0].work);packet[0].work(ctx,packet[0].thread_data);
            for(unsigned i=0;i<64;i++) assert(raw[i]==0xa7&&raw[64+total+i]==0xa7);
            unsigned first=0,last=0;
            for(unsigned y=0;y<oh;y++) for(unsigned x=0;x<ow;x++) {
                unsigned value=bpp==2?((uint16_t*)(output+y*os))[x]:((uint32_t*)(output+y*os))[x];
                assert(value<=h);if(value){if(!first)first=value;last=value;}
            }
            printf("fmt=%u %ux%u -> %ux%u rows=%u..%u\n",fmt,w,h,ow,oh,first,last);
            fflush(stdout);free(raw);free(input);
        }
        f->destroy(ctx);
    }
    dlclose(lib);return 0;
}
