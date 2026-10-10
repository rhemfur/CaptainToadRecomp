// Shader resource queries follow Cemu GX2_Shader.cpp and ZeldaWWHDRecomp gx2_resources.cpp (MPL-2.0).
// Each GX2 shader begins with its SQ_PGM_RESOURCES_{VS,PS,GS} register: NUM_GPRS in bits 0-7,
// NUM_STACK_ENTRIES in bits 8-15.
#include "runtime.h"

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
