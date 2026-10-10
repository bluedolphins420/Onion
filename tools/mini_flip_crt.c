/* SPDX-License-Identifier: GPL-3.0-or-later
 * Mini Flip normalizer for OzBoss's 224-line CRT artwork.
 * Artwork remains the original author's; this filter is independently written.
 */
#include "../tests/fixtures/softfilter.h"
#include <stdlib.h>
#include <string.h>
struct crt {
    unsigned fmt,max_w,w,h;
    void *out;
    const void *in;
    size_t os,is;
};
static unsigned formats(void){return SOFTFILTER_FMT_RGB565|SOFTFILTER_FMT_XRGB8888;}
static unsigned outputs(unsigned f){return f&formats();}
static unsigned crop(unsigned w){return w==256?3:(w==512?6:0);}
static unsigned width(struct crt*c,unsigned w){
    unsigned result=w-2*crop(w),limit=c->max_w-2*crop(c->max_w);
    return result<limit?result:limit;
}
static void *create(const struct softfilter_config *cfg,unsigned in,unsigned out,
    unsigned mw,unsigned mh,unsigned threads,softfilter_simd_mask_t simd,void*u){
    if(!mw||!mh||!threads||in!=out||(in!=1&&in!=2))return NULL;
    struct crt*c=calloc(1,sizeof(*c));if(c){c->fmt=in;c->max_w=mw;}return c;
}
static unsigned threads(void*c){return 1;}
static void size(void*v,unsigned*ow,unsigned*oh,unsigned w,unsigned h){
    *ow=width(v,w);*oh=224;
}
static void process(void*v,void*unused){
    struct crt*c=v;
    unsigned ow=width(c,c->w),bpp=c->fmt==1?2:4,left=crop(c->w),sw=c->w-2*left;
    unsigned top=0,sh=c->h,step=1,pad=0;
    if(c->h==239||c->h==240){top=8;sh=224;}
    else if(c->h==448){step=2;sh=224;}
    else if(c->h==478||c->h==480){top=16;step=2;sh=224;}
    else if(sh<224)pad=(224-sh)/2;
    for(unsigned y=0;y<224;y++){
        unsigned char*out=(unsigned char*)c->out+y*c->os;
        if(!sh||y<pad||(sh<224&&y>=pad+sh)){memset(out,0,ow*bpp);continue;}
        unsigned sy=top+(sh<=224?(y-pad)*step:(unsigned)((uint64_t)y*sh/224));
        const unsigned char*src=(const unsigned char*)c->in+sy*c->is+left*bpp;
        if(step==1&&sw==ow){memcpy(out,src,ow*bpp);continue;}
        for(unsigned x=0;x<ow;x++){
            unsigned sx=sw==ow?x:(unsigned)((uint64_t)x*sw/ow);
            if(bpp==2){
                uint16_t a;memcpy(&a,src+sx*2,2);
                if(step==2){uint16_t b;memcpy(&b,src+c->is+sx*2,2);a=(uint16_t)(((a&0xf7de)+(b&0xf7de))>>1);}
                memcpy(out+x*2,&a,2);
            }else{
                uint32_t a;memcpy(&a,src+sx*4,4);
                if(step==2){uint32_t b;memcpy(&b,src+c->is+sx*4,4);a=((a&0xfefefe)+(b&0xfefefe))>>1;}
                memcpy(out+x*4,&a,4);
            }
        }
    }
}
static void packets(void*v,struct softfilter_work_packet*p,void*out,size_t os,
    const void*in,unsigned w,unsigned h,size_t is){
    struct crt*c=v;c->out=out;c->in=in;c->os=os;c->is=is;c->w=w;c->h=h;
    p[0].work=process;p[0].thread_data=NULL;
}
static const struct softfilter_implementation implementation={
    formats,outputs,create,free,threads,size,packets,SOFTFILTER_API_VERSION,
    "Mini Flip CRT normalizer","mini_flip_crt"
};
const struct softfilter_implementation *softfilter_get_implementation(softfilter_simd_mask_t simd){return &implementation;}
