// Native fetch-descriptor encoding adapted from ZeldaWWHDRecomp gx2_resources.cpp (MPL-2.0).
// The descriptor is consumed by the native renderer; it is not Latte shader microcode.
#include "runtime.h"
#include "gx2/gx2_cmd.h"
#include "gx2/gx2_regs.h"
using namespace Latte;

namespace {
void unsupported() { LOG("[ct-stop] tessellated fetch shaders require implementation"); std::_Exit(78); }
void check_range(uint32_t address,uint32_t bytes) {
    if (address<0x10000 || (address&3) || uint64_t(address)+bytes>0x100000000ull)
        fatal("[ct-stop] invalid native fetch descriptor range");
}
uint32_t program_size(uint32_t count) {
    if (count>128) fatal("[ct-stop] unsupported vertex attribute count %u",count);
    uint32_t control=(((((count+15)/16)+1)*8+15)&~15u);
    return std::max(control+count*16,16+count*16);
}
}
HLE(gx2, GX2CalcFetchShaderSizeEx) {
    if (arg(c,1) || arg(c,2)) unsupported();
    ret(c,program_size(arg(c,0)));
}
HLE(gx2, GX2InitFetchShaderEx) {
    auto shader=arg(c,0),program=arg(c,1),count=arg(c,2),attributes=arg(c,3);
    if (arg(c,4) || arg(c,5)) unsupported();
    check_range(shader,0x20); check_range(program,program_size(count));
    if (count) check_range(attributes,count*0x20);
    st32(program,0x57574653); // Existing native descriptor format identifier (WWFS).
    st32(program+4,count); st32(program+8,0); st32(program+12,0);
    for (uint32_t i=0;i<count;++i) {
        auto source=attributes+i*0x20,target=program+16+i*16;
        if (ld32(source)>255 || ld32(source+4)>=16 || ld32(source+0x10)>1 ||
            ld32(source+0x14)>0xFFFF || ld32(source+0x1C)>3)
            fatal("[ct-stop] invalid vertex attribute descriptor");
        st32(target,(ld32(source)&0xFF)|((ld32(source+4)&0xFF)<<8)|
             ((ld32(source+0x10)&0xFF)<<16)|((ld32(source+0x1C)&0xFF)<<24));
        st32(target+4,ld32(source+8));
        st32(target+8,(ld32(source+0x0C)&0xFFFF)|((ld32(source+0x14)&0xFFFF)<<16));
        st32(target+12,ld32(source+0x18));
    }
    memset(mem::ptr(shader),0,0x20);
    st32(shader+8,16+count*16); st32(shader+12,program); st32(shader+16,count);
}
HLE(gx2, GX2SetFetchShader) {
    auto shader=arg(c,0); check_range(shader,0x20);
    gx2::set_reg(mmSQ_PGM_START_FS,ld32(shader+12)>>8);
    gx2::set_reg(mmSQ_PGM_START_FS+1,ld32(shader+8)>>3);
}
