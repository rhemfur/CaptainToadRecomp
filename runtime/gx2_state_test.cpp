#include "runtime.h"
#include <string>
#include "gx2/gx2_cmd.h"
#include "gx2/gx2_regs.h"
#include "gx2_texture_regs.h"

using namespace Latte;

int ct_gx2_test() {
    mem::init();
    Cpu cpu{};
    auto invoke=[&](const char* name,std::initializer_list<uint32_t> args={}) {
        auto fn=hle_find("gx2",name);
        if (!fn) fatal("[ct-test] missing GX2 export %s",name);
        unsigned i=3;
        for (auto arg:args) cpu.r[i++]=arg;
        fn(&cpu);
        return cpu.r[3];
    };
    invoke("GX2SetDefaultState");
    bool ok=gx2::regs()[REGADDR::CB_TARGET_MASK]==0xFFFFFFFF &&
            gx2::regs()[REGADDR::VGT_MULTI_PRIM_IB_RESET_INDX]==0xFFFFFFFF;
    cpu.f[1].ps0=10; cpu.f[2].ps0=20; cpu.f[3].ps0=200;
    cpu.f[4].ps0=100; cpu.f[5].ps0=0; cpu.f[6].ps0=1;
    invoke("GX2SetViewport");
    ok=ok && gx2::regs()[REGADDR::PA_CL_VPORT_XSCALE]==gx2::fbits(100) &&
       gx2::regs()[REGADDR::PA_CL_VPORT_XOFFSET]==gx2::fbits(110) &&
       gx2::regs()[REGADDR::PA_CL_VPORT_YSCALE]==gx2::fbits(-50) &&
       gx2::regs()[REGADDR::PA_CL_VPORT_YOFFSET]==gx2::fbits(70);
    auto list=mem::runtime_alloc(132,256);
    st32(list+128,0xDEADBEEF);
    invoke("GX2BeginDisplayListEx",{list,128,0});
    ok=ok && invoke("GX2GetDisplayListWriteStatus")==1;
    cpu.f[3].ps0=300;
    invoke("GX2SetViewport");
    ok=ok && gx2::regs()[REGADDR::PA_CL_VPORT_XSCALE]==gx2::fbits(100);
    auto bytes=invoke("GX2EndDisplayList",{list});
    ok=ok && bytes==72 && invoke("GX2GetDisplayListWriteStatus")==0;
    invoke("GX2CallDisplayList",{list,bytes});
    ok=ok && gx2::regs()[REGADDR::PA_CL_VPORT_XSCALE]==gx2::fbits(150) && ld32(list+128)==0xDEADBEEF;
    auto first=mem::runtime_alloc(0xA100,256),second=mem::runtime_alloc(0xA100,256);
    invoke("GX2SetupContextStateEx",{first,1});
    invoke("GX2SetContextState",{first});
    invoke("GX2SetTargetChannelMasks",{1,2,3,4,5,6,7,8});
    auto first_mask=gx2::regs()[REGADDR::CB_TARGET_MASK];
    invoke("GX2SetupContextStateEx",{second,1});
    invoke("GX2SetContextState",{second});
    invoke("GX2SetTargetChannelMasks",{8,7,6,5,4,3,2,1});
    auto second_mask=gx2::regs()[REGADDR::CB_TARGET_MASK];
    invoke("GX2SetContextState",{first});
    ok=ok && gx2::regs()[REGADDR::CB_TARGET_MASK]==first_mask && first_mask!=second_mask;
    auto out=mem::runtime_alloc(8);
    invoke("GX2GetContextStateDisplayList",{second,out,out+4});
    ok=ok && ld32(out)==second+0x9800 && ld32(out+4)==8;
    invoke("GX2CallDisplayList",{ld32(out),ld32(out+4)});
    ok=ok && gx2::regs()[REGADDR::CB_TARGET_MASK]==second_mask;
    auto scan_size=mem::runtime_alloc(12);
    st32(scan_size+8,0x12345678);
    invoke("GX2CalcTVSize",{3,0x41A,2,scan_size,scan_size+4});
    ok=ok && ld32(scan_size)==1280*720*4*2 && ld32(scan_size+4)==0 && ld32(scan_size+8)==0x12345678;
    auto surface=mem::runtime_alloc(0x78);
    st32(surface,1); st32(surface+4,64); st32(surface+8,32); st32(surface+12,1);
    st32(surface+16,1); st32(surface+20,0x1A); st32(surface+28,2); st32(surface+48,1);
    st32(surface+0x74,0xDEADBEEF);
    invoke("GX2CalcSurfaceSizeAndAlignment",{surface});
    auto alignment=ld32(surface+0x38),pitch=ld32(surface+0x3C);
    ok=ok && ld32(surface+0x20)>=64*32*4 && alignment && !(alignment&(alignment-1)) &&
       pitch>=64 && ld32(surface+0x74)==0xDEADBEEF;
    ok=ok && invoke("GX2CalcGeometryShaderInputRingBufferSize",{16})==262144 &&
       invoke("GX2CalcGeometryShaderOutputRingBufferSize",{16})==262144 &&
       invoke("GX2CalcFetchShaderSizeEx",{2,0,0})==48;
    auto fetch=mem::runtime_alloc(0x24),program=mem::runtime_alloc(52,256),attributes=mem::runtime_alloc(64);
    st32(fetch+0x20,0xAABBCCDD); st32(program+48,0x11223344);
    st32(attributes,3); st32(attributes+4,2); st32(attributes+8,8); st32(attributes+12,0x804);
    st32(attributes+16,1); st32(attributes+20,7); st32(attributes+24,0x00010203); st32(attributes+28,2);
    invoke("GX2InitFetchShaderEx",{fetch,program,2,attributes,0,0});
    ok=ok && ld32(fetch+8)==48 && ld32(fetch+12)==program && ld32(fetch+16)==2 &&
       ld32(program)==0x57574653 && ld32(program+4)==2 && ld32(program+16)==0x02010203 &&
       ld32(program+20)==8 && ld32(program+24)==0x00070804 && ld32(program+28)==0x00010203 &&
       ld32(fetch+0x20)==0xAABBCCDD && ld32(program+48)==0x11223344;
    auto depth=mem::runtime_alloc(0xA0),hiz=mem::runtime_alloc(12);
    st32(hiz+8,0xDEADBEEF);
    invoke("GX2CalcDepthBufferHiZInfo",{depth,hiz,hiz+4});
    invoke("GX2InitDepthBufferHiZEnable",{depth,1});
    ok=ok && ld32(hiz)==0x1000 && ld32(hiz+4)==0x100 && ld32(hiz+8)==0xDEADBEEF;
    auto shader=mem::runtime_alloc(8)+2; // Captain Toad passes a 2-byte-aligned vertex shader.
    st8(shader,0); st8(shader+1,0); st8(shader+2,0x0A); st8(shader+3,0x1F);
    for (auto kind:{"Vertex","Pixel","Geometry"}) {
        ok=ok && invoke((std::string("GX2Get")+kind+"ShaderGPRs").c_str(),{shader})==0x1F &&
           invoke((std::string("GX2Get")+kind+"ShaderStackEntries").c_str(),{shader})==0x0A;
    }
    auto sampler=mem::runtime_alloc(16);
    st32(sampler+12,0xDEADBEEF);
    invoke("GX2InitSampler",{sampler,2,1});
    auto sampler_struct=reinterpret_cast<GX2::GX2Sampler*>(mem::ptr(sampler));
    auto sampler_word=sampler_struct->word0.value();
    ok=ok && uint32_t(sampler_word.get_CLAMP_X())==2 && uint32_t(sampler_word.get_CLAMP_Y())==2 &&
       uint32_t(sampler_word.get_XY_MIN_FILTER())==1 && ld32(sampler+12)==0xDEADBEEF;
    invoke("GX2SetPixelSampler",{sampler,0});
    ok=ok && gx2::regs()[REGADDR::SQ_TEX_SAMPLER_WORD0_0+SAMPLER_BASE_INDEX_PIXEL*3]==ld32(sampler);
    auto tiled=mem::runtime_alloc(0x78),roundtrip=mem::runtime_alloc(0x78);
    memcpy(mem::ptr(tiled),mem::ptr(surface),0x74); st32(tiled+0x30,4);
    invoke("GX2CalcSurfaceSizeAndAlignment",{tiled});
    auto source_size=ld32(surface+0x20),target_size=ld32(tiled+0x20);
    auto allocation=std::max(source_size,target_size),source_data=mem::runtime_alloc(allocation+4,std::max(alignment,ld32(tiled+0x38)));
    auto tiled_data=mem::runtime_alloc(target_size+4,ld32(tiled+0x38));
    auto result_data=mem::runtime_alloc(source_size+4,alignment);
    st32(surface+0x24,source_data); st32(tiled+0x24,tiled_data);
    memcpy(mem::ptr(roundtrip),mem::ptr(surface),0x74); st32(roundtrip+0x24,result_data);
    for (uint32_t y=0;y<32;++y) for (uint32_t x=0;x<64;++x) {
        auto pixel=mem::ptr(source_data+(y*pitch+x)*4);
        pixel[0]=uint8_t(x); pixel[1]=uint8_t(y); pixel[2]=uint8_t(x^y); pixel[3]=255;
    }
    st32(source_data+allocation,0x01234567); st32(tiled_data+target_size,0x12345678); st32(result_data+source_size,0x23456789);
    auto verify_pixels=[&] {
        bool matches=true;
        for (uint32_t y=0;y<32;++y) for (uint32_t x=0;x<64;++x) {
            auto pixel=mem::ptr(result_data+(y*pitch+x)*4);
            matches=matches && pixel[0]==x && pixel[1]==y && pixel[2]==(x^y) && pixel[3]==255;
        }
        return matches;
    };
    invoke("GX2CopySurface",{surface,0,0,tiled,0,0});
    invoke("GX2CopySurface",{tiled,0,0,roundtrip,0,0});
    ok=ok && verify_pixels();
    st32(tiled+0x24,source_data); // The destination overlaps the original linear source.
    invoke("GX2CopySurface",{surface,0,0,tiled,0,0});
    invoke("GX2CopySurface",{tiled,0,0,roundtrip,0,0});
    ok=ok && verify_pixels() && ld32(source_data+allocation)==0x01234567 &&
       ld32(tiled_data+target_size)==0x12345678 && ld32(result_data+source_size)==0x23456789;
    LOG("[ct-test] GX2 state/resources/HiZ/shader-GPRs/tiled-copy/overlap/bounds: %s",ok?"PASS":"FAIL");
    return ok?0:1;
}
