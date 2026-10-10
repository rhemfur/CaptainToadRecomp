// Shader resource queries follow Cemu GX2_Shader.cpp and ZeldaWWHDRecomp gx2_resources.cpp (MPL-2.0).
// Each GX2 shader begins with its SQ_PGM_RESOURCES_{VS,PS,GS} register: NUM_GPRS in bits 0-7,
// NUM_STACK_ENTRIES in bits 8-15.
#include "runtime.h"
#include "gx2/gx2_cmd.h"
#include "gx2/gx2_regs.h"
#include <algorithm>
using gx2::set_reg;
using gx2::set_regs;

// Games may keep shader headers at 2-byte offsets inside resource files; GX2 reads them without
// an alignment requirement.
static uint32_t program_resources(uint32_t shader) {
    if (shader<0x10000 || uint64_t(shader)+4>0x100000000ull)
        fatal("[ct-stop] invalid GX2 shader pointer %08X",shader);
    return ld32(shader);
}
HLE(gx2, GX2GetVertexShaderGPRs) { ret(c,program_resources(arg(c,0))&0xFF); }
HLE(gx2, GX2GetVertexShaderStackEntries) { ret(c,(program_resources(arg(c,0))>>8)&0xFF); }
HLE(gx2, GX2GetPixelShaderGPRs) { ret(c,program_resources(arg(c,0))&0xFF); }
HLE(gx2, GX2GetPixelShaderStackEntries) { ret(c,(program_resources(arg(c,0))>>8)&0xFF); }
HLE(gx2, GX2GetGeometryShaderGPRs) { ret(c,program_resources(arg(c,0))&0xFF); }
HLE(gx2, GX2GetGeometryShaderStackEntries) { ret(c,(program_resources(arg(c,0))>>8)&0xFF); }

// Shader binding adapted from ZeldaWWHDRecomp gx2_resources.cpp/gx2_shader_regs.cpp (MPL-2.0), whose
// structure layouts and register sequences follow Cemu GX2_Shader.cpp. Only registers the shader
// owns are forwarded, so display lists record the same sequence the console would emit.

static void check_structure(uint32_t shader,uint32_t size) {
    if (shader<0x10000 || uint64_t(shader)+size>0x100000000ull)
        fatal("[ct-stop] invalid GX2 shader structure %08X",shader);
}
static void check_program(const uint32_t* regs,uint32_t start,const char* stage) {
    if (!regs[start] || !regs[start+1]) fatal("[ct-stop] %s shader has no program",stage);
}
HLE(gx2, GX2SetVertexShader) {
    static thread_local uint32_t tmp[gx2::kNumRegs]; // display lists are recorded on several cores
    auto vs=arg(c,0);
    check_structure(vs,0x134);
    auto outputs=std::min<uint32_t>(ld32(vs+0x0C),10), semantics=std::min<uint32_t>(ld32(vs+0x40),32);
    gx2::bind_vertex_shader_regs(tmp,vs);
    if (ld32(vs+0xD8)==2) {
        check_program(tmp,mmSQ_PGM_START_ES,"vertex (export)");
        set_regs(mmSQ_PGM_START_ES,&tmp[mmSQ_PGM_START_ES],2);
        set_reg(mmSQ_PGM_RESOURCES_ES,tmp[mmSQ_PGM_RESOURCES_ES]);
    } else {
        check_program(tmp,mmSQ_PGM_START_VS,"vertex");
        set_regs(mmSQ_PGM_START_VS,&tmp[mmSQ_PGM_START_VS],2);
        set_reg(mmSQ_PGM_RESOURCES_VS,tmp[mmSQ_PGM_RESOURCES_VS]);
        set_reg(mmVGT_PRIMITIVEID_EN,tmp[mmVGT_PRIMITIVEID_EN]);
        set_reg(mmSPI_VS_OUT_CONFIG,tmp[mmSPI_VS_OUT_CONFIG]);
        set_reg(mmPA_CL_VS_OUT_CNTL,tmp[mmPA_CL_VS_OUT_CNTL]);
        if (outputs) set_regs(mmSPI_VS_OUT_ID_0,&tmp[mmSPI_VS_OUT_ID_0],outputs);
    }
    if (semantics) {
        set_reg(mmSQ_VTX_SEMANTIC_CLEAR,0xFFFFFFFF);
        set_regs(mmSQ_VTX_SEMANTIC_0,&tmp[mmSQ_VTX_SEMANTIC_0],semantics);
    }
}
HLE(gx2, GX2SetPixelShader) {
    static thread_local uint32_t tmp[gx2::kNumRegs];
    auto ps=arg(c,0);
    check_structure(ps,0xE8);
    auto inputs=std::min<uint32_t>(ld32(ps+0x10),0x20);
    gx2::bind_pixel_shader_regs(tmp,ps);
    check_program(tmp,mmSQ_PGM_START_PS,"pixel");
    set_regs(mmSQ_PGM_START_PS,&tmp[mmSQ_PGM_START_PS],2);
    set_reg(mmSQ_PGM_RESOURCES_PS,tmp[mmSQ_PGM_RESOURCES_PS]);
    set_regs(mmSPI_PS_IN_CONTROL_0,&tmp[mmSPI_PS_IN_CONTROL_0],2);
    if (inputs) set_regs(mmSPI_PS_INPUT_CNTL_0,&tmp[mmSPI_PS_INPUT_CNTL_0],inputs);
    set_reg(mmCB_SHADER_MASK,tmp[mmCB_SHADER_MASK]);
    set_reg(mmCB_SHADER_CONTROL,tmp[mmCB_SHADER_CONTROL]);
    set_reg(mmDB_SHADER_CONTROL,tmp[mmDB_SHADER_CONTROL]);
    set_reg(mmSPI_INPUT_Z,tmp[mmSPI_INPUT_Z]);
}
