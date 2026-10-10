// Scan-buffer calculations adapted from ZeldaWWHDRecomp gx2_core.cpp (MPL-2.0).
#include "runtime.h"
#include <mutex>

namespace {
struct Scanout { uint32_t address=0,bytes=0,mode=0,format=0,buffers=0,width=0,height=0; bool enabled=false; };
std::mutex guard;
Scanout tv,drc;
uint32_t rgba_bytes(uint32_t format) {
    if (format==0x1A || format==0x41A) return 4;
    LOG("[ct-stop] scanout format requires implementation: %X",format); std::_Exit(78);
}
std::pair<uint32_t,uint32_t> tv_size(uint32_t mode) {
    if (mode==3) return {1280,720};
    LOG("[ct-stop] TV scan mode requires verification: %u",mode); std::_Exit(78);
}
uint32_t buffer_count(uint32_t mode) {
    if (mode>3) fatal("[ct-stop] unsupported scan buffering mode %u",mode);
    return std::max(mode,1u);
}
void checked_output(uint32_t address) {
    if (address<0x10000 || (address&3) || uint64_t(address)+4>0x100000000ull)
        fatal("[ct-stop] invalid scanout size output");
}
}
HLE(gx2, GX2CalcTVSize) {
    auto [width,height]=tv_size(arg(c,0));
    checked_output(arg(c,3)); checked_output(arg(c,4));
    st32(arg(c,3),width*height*rgba_bytes(arg(c,1))*buffer_count(arg(c,2)));
    st32(arg(c,4),0);
}
HLE(gx2, GX2CalcDRCSize) {
    checked_output(arg(c,3)); checked_output(arg(c,4));
    st32(arg(c,3),854*480*rgba_bytes(arg(c,1))*buffer_count(arg(c,2)));
    st32(arg(c,4),0);
}
HLE(gx2, GX2SetTVBuffer) {
    std::lock_guard<std::mutex> lock(guard);
    auto [width,height]=tv_size(arg(c,2));
    auto bytes=width*height*rgba_bytes(arg(c,3))*buffer_count(arg(c,4));
    if (arg(c,1)<bytes || arg(c,0)<0x10000 || uint64_t(arg(c,0))+arg(c,1)>0x100000000ull)
        fatal("[ct-stop] TV scan buffer is too small or out of range");
    tv={arg(c,0),arg(c,1),arg(c,2),arg(c,3),arg(c,4),width,height,tv.enabled};
    LOG("[ct-gx2] TV scan buffer configured %ux%u, %u bytes; presentation pending",width,height,tv.bytes);
}
HLE(gx2, GX2SetDRCBuffer) {
    std::lock_guard<std::mutex> lock(guard);
    auto bytes=854*480*rgba_bytes(arg(c,3))*buffer_count(arg(c,4));
    if (arg(c,1)<bytes || arg(c,0)<0x10000 || uint64_t(arg(c,0))+arg(c,1)>0x100000000ull)
        fatal("[ct-stop] DRC scan buffer is too small or out of range");
    drc={arg(c,0),arg(c,1),arg(c,2),arg(c,3),arg(c,4),854,480,drc.enabled};
}
HLE(gx2, GX2SetTVEnable) { std::lock_guard<std::mutex> lock(guard); tv.enabled=arg(c,0)!=0; }
HLE(gx2, GX2SetDRCEnable) { std::lock_guard<std::mutex> lock(guard); drc.enabled=arg(c,0)!=0; }
HLE(gx2, GX2SetTVScale) { std::lock_guard<std::mutex> lock(guard); tv.width=arg(c,0); tv.height=arg(c,1); }
HLE(gx2, GX2SetDRCScale) { std::lock_guard<std::mutex> lock(guard); drc.width=arg(c,0); drc.height=arg(c,1); }

namespace { uint32_t swap_interval=1; }
HLE(gx2, GX2SetSwapInterval) { std::lock_guard<std::mutex> lock(guard); swap_interval=std::max(arg(c,0),1u); }
HLE(gx2, GX2TempGetGPUVersion) { ret(c,2); }
HLE(gx2, GX2GetSwapStatus) {
    // No presentation is implemented or reported as completed by this diagnostic.
    if (arg(c,0)) st32(arg(c,0),0);
    if (arg(c,1)) st32(arg(c,1),0);
    if (arg(c,2)) st64(arg(c,2),0);
    if (arg(c,3)) st64(arg(c,3),timebase::guest_now());
}

// Ring allocation formulas follow Cemu GX2_shader_legacy.cpp; shader execution is not implied.
HLE(gx2, GX2CalcGeometryShaderInputRingBufferSize) { ret(c,arg(c,0)*4u*0x1000u); }
HLE(gx2, GX2CalcGeometryShaderOutputRingBufferSize) { ret(c,arg(c,0)*4u*0x1000u); }
