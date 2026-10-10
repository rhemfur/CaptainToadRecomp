// Texture/sampler and render-target register bindings adapted from ZeldaWWHDRecomp gx2_resources.cpp (MPL-2.0).
#include "runtime.h"
#include "gx2/gx2_cmd.h"
#include "gx2/gx2_regs.h"
#include "gx2/gx2.h"
#include "gx2_texture_regs.h"
using namespace Latte;
using gx2::set_reg;
using gx2::set_regs;
template<class T> static T* gp(uint32_t address) {
    if (address<0x10000 || (address&3) || uint64_t(address)+sizeof(T)>0x100000000ull)
        fatal("[ct-stop] invalid GX2 resource structure");
    return reinterpret_cast<T*>(mem::ptr(address));
}
static float fa(Cpu* c,int i) { return float(c->f[1+i].ps0); }
// ---------------------------------------------------------------- textures and samplers
HLE(gx2, GX2InitTextureRegs) { GX2::GX2InitTextureRegs(gp<GX2::GX2Texture>(arg(c, 0))); }

static void set_texture(uint32 texAddr, uint32 baseReg, uint32 unit) {
    auto* tex = gp<GX2::GX2Texture>(texAddr);
    uint32 image = tex->surface.imagePtr, mip = tex->surface.mipPtr;
    if (!mip) mip = image;
    uint32 swizzle = tex->surface.swizzle;
    if (TM_IsMacroTiled(tex->surface.tileMode)) {
        uint32 stop = (swizzle >> 16) & 0xFF;
        if (stop > 0) image ^= (swizzle & 0xFFFF);
        if (stop > 1) mip ^= (swizzle & 0xFFFF);
    }
    uint32 w[7] = {tex->regTexWord0.value().getRawValue(), tex->regTexWord1.value().getRawValue(), image >> 8, mip >> 8,
                   tex->regTexWord4.value().getRawValue(), tex->regTexWord5.value().getRawValue(),
                   tex->regTexWord6.value().getRawValue()};
    set_regs(baseReg + unit * 7, w, 7);
}
HLE(gx2, GX2SetPixelTexture) { set_texture(arg(c, 0), REGADDR::SQ_TEX_RESOURCE_WORD0_N_PS, arg(c, 1)); }
HLE(gx2, GX2SetVertexTexture) { set_texture(arg(c, 0), REGADDR::SQ_TEX_RESOURCE_WORD0_N_VS, arg(c, 1)); }
HLE(gx2, GX2SetGeometryTexture) { set_texture(arg(c, 0), REGADDR::SQ_TEX_RESOURCE_WORD0_N_GS, arg(c, 1)); }

using SW0 = LATTE_SQ_TEX_SAMPLER_WORD0_0;
HLE(gx2, GX2InitSampler) { GX2::GX2InitSampler(gp<GX2::GX2Sampler>(arg(c, 0)), (SW0::E_CLAMP)arg(c, 1), (SW0::E_XY_FILTER)arg(c, 2)); }
HLE(gx2, GX2InitSamplerXYFilter) {
    GX2::GX2InitSamplerXYFilter(gp<GX2::GX2Sampler>(arg(c, 0)), (SW0::E_XY_FILTER)arg(c, 1), (SW0::E_XY_FILTER)arg(c, 2), arg(c, 3));
}
HLE(gx2, GX2InitSamplerZMFilter) {
    GX2::GX2InitSamplerZMFilter(gp<GX2::GX2Sampler>(arg(c, 0)), (SW0::E_Z_FILTER)arg(c, 1), (SW0::E_Z_FILTER)arg(c, 2));
}
HLE(gx2, GX2InitSamplerLOD) { GX2::GX2InitSamplerLOD(gp<GX2::GX2Sampler>(arg(c, 0)), fa(c, 0), fa(c, 1), fa(c, 2)); }
HLE(gx2, GX2InitSamplerClamping) {
    GX2::GX2InitSamplerClamping(gp<GX2::GX2Sampler>(arg(c, 0)), (SW0::E_CLAMP)arg(c, 1), (SW0::E_CLAMP)arg(c, 2), (SW0::E_CLAMP)arg(c, 3));
}
HLE(gx2, GX2InitSamplerBorderType) { GX2::GX2InitSamplerBorderType(gp<GX2::GX2Sampler>(arg(c, 0)), (SW0::E_BORDER_COLOR_TYPE)arg(c, 1)); }
HLE(gx2, GX2InitSamplerDepthCompare) { GX2::GX2InitSamplerDepthCompare(gp<GX2::GX2Sampler>(arg(c, 0)), (SW0::E_DEPTH_COMPARE)arg(c, 1)); }

static void set_sampler(uint32 sampler, uint32 index) {
    uint32 w[3] = {ld32(sampler), ld32(sampler + 4), ld32(sampler + 8)};
    set_regs(REGADDR::SQ_TEX_SAMPLER_WORD0_0 + index * 3, w, 3);
}
HLE(gx2, GX2SetPixelSampler) { set_sampler(arg(c, 0), arg(c, 1) + SAMPLER_BASE_INDEX_PIXEL); }
HLE(gx2, GX2SetVertexSampler) { set_sampler(arg(c, 0), arg(c, 1) + SAMPLER_BASE_INDEX_VERTEX); }
HLE(gx2, GX2SetGeometrySampler) { set_sampler(arg(c, 0), arg(c, 1) + SAMPLER_BASE_INDEX_GEOMETRY); }

static void set_border(uint32 base, Cpu* c) {
    uint32 v[4] = {gx2::fbits(fa(c, 0)), gx2::fbits(fa(c, 1)), gx2::fbits(fa(c, 2)), gx2::fbits(fa(c, 3))};
    set_regs(base + arg(c, 0) * 4, v, 4);
}
HLE(gx2, GX2SetPixelSamplerBorderColor) { set_border(REGADDR::TD_PS_SAMPLER0_BORDER_RED, c); }
HLE(gx2, GX2SetVertexSamplerBorderColor) { set_border(REGADDR::TD_VS_SAMPLER0_BORDER_RED, c); }
HLE(gx2, GX2SetGeometrySamplerBorderColor) { set_border(REGADDR::TD_GS_SAMPLER0_BORDER_RED, c); }


// ---------------------------------------------------------------- render targets
HLE(gx2, GX2InitColorBufferRegs) { GX2::GX2InitColorBufferRegs(gp<GX2::GX2ColorBuffer>(arg(c, 0))); }
HLE(gx2, GX2InitDepthBufferRegs) { GX2::GX2InitDepthBufferRegs(gp<GX2::GX2DepthBuffer>(arg(c, 0))); }

namespace gx2 {
uint32 color_buffer_address(const GX2::GX2ColorBuffer* cb) {
    uint32 mip = cb->viewMip;
    uint32 base = cb->surface.imagePtr;
    if (mip == 1) base = cb->surface.mipPtr;
    else if (mip > 1) base = cb->surface.mipPtr + cb->surface.mipOffset[mip - 1];
    uint32 swizzle = cb->surface.swizzle;
    if (TM_IsMacroTiled(cb->surface.tileMode) && mip < ((swizzle >> 16) & 0xFF)) base ^= (swizzle & 0xFFFF);
    return base;
}
}  // namespace gx2

HLE(gx2, GX2SetColorBuffer) {
    auto* cb = gp<GX2::GX2ColorBuffer>(arg(c, 0));
    uint32 target = arg(c, 1) & 7;
    set_reg(mmCB_COLOR0_BASE + target, gx2::color_buffer_address(cb));  // full address; our renderer's convention
    set_reg(mmCB_COLOR0_SIZE + target, cb->reg_size);
    set_reg(mmCB_COLOR0_VIEW + target, cb->reg_view);
    set_reg(mmCB_COLOR0_INFO + target, cb->reg_info);
    // our convention (gx2.h kColorTarget3D): the unused TILE/FRAG registers carry the view's real width
    // (| slices << 16 | volume flag) and height. A volume's slices are its depth at the view's mip.
    auto dim = cb->surface.dim.value();
    bool volume = dim == Latte::E_DIM::DIM_3D;
    uint32 slices = dim == Latte::E_DIM::DIM_2D_ARRAY ? std::max<uint32>(cb->surface.depth, 1)
                    : volume                          ? std::max<uint32>(cb->surface.depth >> cb->viewMip, 1)
                                                      : 1;
    set_reg(mmCB_COLOR0_TILE + target, std::max<uint32>(cb->surface.width >> cb->viewMip, 1) | (std::min<uint32>(slices, 0x7FFF) << 16) |
                                           (volume ? gx2::kColorTarget3D : 0));
    set_reg(mmCB_COLOR0_FRAG + target, std::max<uint32>(cb->surface.height >> cb->viewMip, 1));
}

HLE(gx2, GX2SetDepthBuffer) {
    auto* db = gp<GX2::GX2DepthBuffer>(arg(c, 0));
    uint32 info = ((uint32)db->surface.tileMode.value() & 0xF) << 15;
    switch (db->surface.format.value()) {
    case E_GX2SURFFMT::D16_UNORM: info |= 1; break;
    case E_GX2SURFFMT::D24_S8_UNORM: info |= 3; break;
    case E_GX2SURFFMT::D24_S8_FLOAT: info |= 5; break;
    case E_GX2SURFFMT::D32_FLOAT: info |= 6; break;
    case E_GX2SURFFMT::D32_S8_FLOAT: info |= 7; break;
    default: break;
    }
    uint32 view = (db->viewFirstSlice & 0x7FF) | (((db->viewNumSlices + db->viewFirstSlice - 1) & 0x7FF) << 13);
    set_reg(mmDB_DEPTH_SIZE, db->reg_size);
    set_reg(mmDB_DEPTH_BASE, db->surface.imagePtr);  // full address; our renderer's convention
    set_reg(mmDB_DEPTH_INFO, info);
    set_reg(mmDB_DEPTH_VIEW, view);
    set_reg(mmDB_HTILE_DATA_BASE, (uint32)db->surface.width << 16 | (db->surface.height & 0xFFFF));  // our convention
    // our convention: unused register 0xA002 (between DB_DEPTH_VIEW and DB_DEPTH_BASE) = array slices
    set_reg(gx2::kDepthSlicesReg, db->surface.dim.value() == Latte::E_DIM::DIM_2D_ARRAY ? std::max<uint32>(db->surface.depth, 1) : 1);
}


HLE(gx2, GX2InitDepthBufferHiZEnable) {
    gp<GX2::GX2DepthBuffer>(arg(c,0));
    if (arg(c,1)) { LOG("[ct-stop] HiZ acceleration requires implementation"); std::_Exit(78); }
    // HiZ is an optional acceleration path. Disabled requests use ordinary depth evaluation.
    LOG("[ct-gx2] HiZ acceleration disabled for depth buffer %08X",arg(c,0));
}
