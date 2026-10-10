// Generic surface size/alignment calculation from the reference Cemu-derived AddrLib (MPL-2.0).
#include "runtime.h"
#include "gx2_surface_calc.h"
HLE(gx2, GX2CalcSurfaceSizeAndAlignment) {
    auto address=arg(c,0);
    if (address<0x10000 || (address&3) || uint64_t(address)+sizeof(GX2Surface)>0x100000000ull)
        fatal("[ct-stop] invalid GX2 surface pointer");
    auto surface=reinterpret_cast<GX2Surface*>(mem::ptr(address));
    if (!surface->width || !surface->height || surface->width>16384 || surface->height>16384 ||
        surface->depth>2048 || surface->numLevels>16)
        fatal("[ct-stop] invalid GX2 surface dimensions");
    gx2calc::CalcSurfaceSizeAndAlignment(surface);
}

void cemu_shim_log(const std::string& message) { LOG("[ct-gx2-reference] %s",message.c_str()); }
