// CPU-backed surface transfers adapted from ZeldaWWHDRecomp Vulkan surfaces.cpp (MPL-2.0).
// Game render targets are not GPU-written by this diagnostic; drawing remains unsupported.
#include "runtime.h"
#include "gx2/gx2_cmd.h"
#include "gx2_surface_calc.h"
#include "write_watch.h"
#include <atomic>
using namespace Latte;
namespace {
uint32_t level_address(const GX2Surface& surface,uint32_t level) {
    uint64_t address=level==0?uint32_t(surface.imagePtr):uint32_t(surface.mipPtr);
    if (level>1) address+=surface.mipOffset[level-1];
    if (address<0x10000 || address>=0x100000000ull) fatal("[ct-stop] invalid surface image address");
    return uint32_t(address);
}
uint32_t element(const LatteAddrLib::AddrSurfaceInfo_OUT& info,uint32_t x,uint32_t y,uint32_t slice,
                 uint32_t bits,bool depth,LatteAddrLib::CachedSurfaceAddrInfo& cached) {
    auto tile=info.hwTileMode;
    if (tile==E_HWTILEMODE::TM_LINEAR_GENERAL || tile==E_HWTILEMODE::TM_LINEAR_ALIGNED)
        return LatteAddrLib::ComputeSurfaceAddrFromCoordLinear(x,y,slice,0,bits,info.pitch,info.height,info.depth);
    if (!TM_IsMacroTiled(tile)) return LatteAddrLib::ComputeSurfaceAddrFromCoordMicroTiled(x,y,slice,bits,info.pitch,info.height,tile,depth);
    return LatteAddrLib::ComputeSurfaceAddrFromCoordMacroTiledCached(x,y,&cached);
}
void prepare(const GX2Surface& surface,const LatteAddrLib::AddrSurfaceInfo_OUT& info,uint32_t slice,bool depth,
             LatteAddrLib::CachedSurfaceAddrInfo& cached) {
    if (TM_IsMacroTiled(info.hwTileMode))
        LatteAddrLib::SetupCachedSurfaceAddrInfo(&cached,slice,0,info.bpp,info.pitch,info.height,info.depth,1,
            info.hwTileMode,depth,(uint32_t(surface.swizzle)>>8)&1,(uint32_t(surface.swizzle)>>9)&3);
}
void copy(GX2Surface& source,uint32_t src_mip,uint32_t src_slice,GX2Surface& destination,uint32_t dst_mip,uint32_t dst_slice) {
    if (src_mip>=source.numLevels || dst_mip>=destination.numLevels || src_mip>13 || dst_mip>13 || source.aa || destination.aa)
        fatal("[ct-stop] unsupported surface mip/sample selection");
    LatteAddrLib::AddrSurfaceInfo_OUT si{},di{};
    gx2calc::CalculateSurfaceInfo(&source,src_mip,&si);
    gx2calc::CalculateSurfaceInfo(&destination,dst_mip,&di);
    bool compressed=IsCompressedFormat(source.format),dst_compressed=IsCompressedFormat(destination.format);
    if (!si.bpp || si.bpp>128 || si.bpp%8 || si.bpp!=di.bpp || compressed!=dst_compressed ||
        src_slice>=si.depth || dst_slice>=di.depth) fatal("[ct-stop] unsupported CPU surface copy layout");
    uint32_t width=std::min(std::max(uint32_t(source.width)>>src_mip,1u),std::max(uint32_t(destination.width)>>dst_mip,1u));
    uint32_t height=std::min(std::max(uint32_t(source.height)>>src_mip,1u),std::max(uint32_t(destination.height)>>dst_mip,1u));
    if (compressed) { width=(width+3)/4; height=(height+3)/4; }
    uint32_t bytes=si.bpp/8,src_base=level_address(source,src_mip),dst_base=level_address(destination,dst_mip);
    if (uint64_t(src_base)+si.surfSize>0x100000000ull || uint64_t(dst_base)+di.surfSize>0x100000000ull ||
        di.surfSize>UINT32_MAX || uint64_t(width)*height*bytes>(64u<<20)) fatal("[ct-stop] surface copy bounds exceeded");
    bool source_depth=(uint32_t(source.format.value())&0x800)!=0,dest_depth=(uint32_t(destination.format.value())&0x800)!=0;
    LatteAddrLib::CachedSurfaceAddrInfo sc{},dc{};
    prepare(source,si,src_slice,source_depth,sc); prepare(destination,di,dst_slice,dest_depth,dc);
    std::vector<uint8_t> gathered(size_t(width)*height*bytes);
    for (uint32_t y=0;y<height;++y) for (uint32_t x=0;x<width;++x) {
        auto offset=element(si,x,y,src_slice,si.bpp,source_depth,sc);
        if (uint64_t(offset)+bytes>si.surfSize) fatal("[ct-stop] source texel outside surface");
        memcpy(gathered.data()+(size_t(y)*width+x)*bytes,mem::ptr(src_base+offset),bytes);
    }
    wwatch::HostWrite write(dst_base,uint32_t(di.surfSize));
    for (uint32_t y=0;y<height;++y) for (uint32_t x=0;x<width;++x) {
        auto offset=element(di,x,y,dst_slice,di.bpp,dest_depth,dc);
        if (uint64_t(offset)+bytes>di.surfSize) fatal("[ct-stop] destination texel outside surface");
        memcpy(mem::ptr(dst_base+offset),gathered.data()+(size_t(y)*width+x)*bytes,bytes);
    }
    static std::atomic<unsigned> copies{0};
    if (++copies<=4) LOG("[ct-gx2] CPU surface copy %ux%u, %u-bit elements, tiling %u -> %u",
        width,height,si.bpp,unsigned(si.hwTileMode),unsigned(di.hwTileMode));
}
}
void ct_gx2_copy_encoded(const uint32_t* payload,uint32_t count) {
    if (count!=62) fatal("[ct-stop] invalid surface-copy command");
    GX2Surface source{},destination{};
    memcpy(&source,payload,0x74); memcpy(&destination,payload+31,0x74);
    copy(source,payload[29],payload[30],destination,payload[60],payload[61]);
}
HLE(gx2, GX2CopySurface) {
    auto src=arg(c,0),dst=arg(c,3);
    if (src<0x10000 || dst<0x10000 || (src&3) || (dst&3) ||
        uint64_t(src)+0x74>0x100000000ull || uint64_t(dst)+0x74>0x100000000ull)
        fatal("[ct-stop] invalid surface-copy structures");
    uint32_t payload[62];
    memcpy(payload,mem::ptr(src),0x74); payload[29]=arg(c,1); payload[30]=arg(c,2);
    memcpy(payload+31,mem::ptr(dst),0x74); payload[60]=arg(c,4); payload[61]=arg(c,5);
    gx2::emit(gx2::OP_COPY_SURFACE,payload,62);
}
