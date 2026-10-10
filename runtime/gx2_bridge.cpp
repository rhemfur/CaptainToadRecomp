// Generic GX2 state/display-list bridge. Default state follows ZeldaWWHDRecomp (MPL-2.0).
#include "runtime.h"
#include "gx2/gx2_cmd.h"
#include "gx2/gx2_regs.h"
#include "write_watch.h"
#include <atomic>
#include <array>
#include <mutex>
#include <unordered_map>

bool ct_gpu_initialize();
void ct_gpu_wait_idle();
void ct_gx2_copy_encoded(const uint32_t*,uint32_t);
namespace gx2 {
namespace {
std::recursive_mutex guard;
std::array<uint32_t,kNumRegs> registers{};
std::unordered_map<uint32_t,std::array<uint32_t,kNumRegs>> contexts;
uint32_t active_context=0;
struct Recording { uint32_t start=0,pos=0,end=0; };
thread_local Recording recording;
thread_local unsigned depth=0;
void checked_guest(uint32_t address,uint32_t bytes) {
    if (address<0x10000 || (address&3) || uint64_t(address)+bytes>0x100000000ull)
        fatal("[ct-stop] invalid GX2 guest range %08X+%X",address,bytes);
}
void stop(uint32_t op) {
    LOG("[ct-stop] GX2 command %u requires a rendering implementation",op);
    std::_Exit(78);
}
void apply(Op op,const uint32_t* payload,uint32_t count) {
    if (op==OP_SET_REGS) {
        if (count<2 || payload[0]>=kNumRegs || uint64_t(payload[0])+count-1>kNumRegs)
            fatal("[ct-stop] invalid GX2 register write");
        std::copy(payload+1,payload+count,registers.begin()+payload[0]);
        if (active_context) std::copy(payload+1,payload+count,contexts.at(active_context).begin()+payload[0]);
    } else if (op==OP_SET_CONTEXT) {
        if (count!=1 || (payload[0] && !contexts.contains(payload[0])))
            fatal("[ct-stop] unknown GX2 context");
        active_context=payload[0];
        if (active_context) registers=contexts.at(active_context);
    } else if (op==OP_CALL) {
        if (count!=2 || (payload[1]&3) || payload[1]>(64u<<20)) fatal("[ct-stop] invalid display list");
        checked_guest(payload[0],payload[1]);
        execute(reinterpret_cast<const uint32_t*>(mem::ptr(payload[0])),payload[1]/4);
    } else if (op==OP_COPY_SURFACE) {
        ct_gx2_copy_encoded(payload,count);
    } else if (op==OP_INVALIDATE) {
        if (count!=3) fatal("[ct-stop] invalid GX2 invalidate payload");
        wwatch::enable_hints();
        wwatch::hint(payload[1],payload[2]);
        std::atomic_thread_fence(std::memory_order_seq_cst);
    } else if (op==OP_FLUSH || op==OP_DRAW_DONE) {
        if (count) fatal("[ct-stop] invalid GX2 synchronization payload");
        ct_gpu_wait_idle();
    } else if (op==OP_NOP) {
        if (count) fatal("[ct-stop] malformed GX2 NOP");
    } else stop(op);
}
}
uint32_t* regs() { return registers.data(); }
void execute(const uint32_t* words,uint32_t count) {
    std::lock_guard<std::recursive_mutex> lock(guard);
    if (++depth>64) fatal("[ct-stop] display-list recursion limit");
    for (uint32_t offset=0;offset<count;) {
        auto header=words[offset++], size=header>>8;
        if (size>count-offset) fatal("[ct-stop] truncated GX2 command");
        apply(static_cast<Op>(header&0xFF),words+offset,size);
        offset+=size;
    }
    --depth;
}
void emit(Op op,const uint32_t* payload,uint32_t count) {
    if (recording.start) {
        uint64_t bytes=(uint64_t(count)+1)*4;
        if (bytes>uint64_t(recording.end)-recording.pos) fatal("[ct-stop] display-list buffer overflow");
        auto words=reinterpret_cast<uint32_t*>(mem::ptr(recording.pos));
        words[0]=uint32_t(op)|(count<<8);
        if (count) std::copy(payload,payload+count,words+1);
        recording.pos+=uint32_t(bytes);
    } else {
        std::lock_guard<std::recursive_mutex> lock(guard);
        apply(op,payload,count);
    }
}
void set_regs(uint32_t first,const uint32_t* values,uint32_t count) {
    if (!count) return;
    if (first>=kNumRegs || uint64_t(first)+count>kNumRegs) fatal("[ct-stop] GX2 register bounds");
    std::vector<uint32_t> payload(count+1);
    payload[0]=first;
    std::copy(values,values+count,payload.begin()+1);
    emit(OP_SET_REGS,payload.data(),count+1);
}
void set_reg(uint32_t reg,uint32_t value) { set_regs(reg,&value,1); }
using namespace Latte;
static void set_default_state() {
    // GX2SetShaderModeEx(UNIFORM_REGISTER, ...)
    LATTE_SQ_CONFIG sq;
    sq.set_DX9_CONSTS(true).set_ALU_INST_PREFER_VECTOR(true).set_PS_PRIO(3).set_VS_PRIO(2).set_GS_PRIO(1).set_ES_PRIO(0);
    set_reg(REGADDR::SQ_CONFIG, sq.getRawValue());
    set_reg(REGADDR::VGT_GS_MODE, 0);
    LATTE_PA_CL_VTE_CNTL vte{};
    vte.set_VPORT_X_OFFSET_ENA(true).set_VPORT_X_SCALE_ENA(true).set_VPORT_Y_OFFSET_ENA(true).set_VPORT_Y_SCALE_ENA(true);
    vte.set_VPORT_Z_OFFSET_ENA(true).set_VPORT_Z_SCALE_ENA(true).set_VTX_W0_FMT(true);
    set_reg(REGADDR::PA_CL_VTE_CNTL, vte.getRawValue());
    set_reg(REGADDR::DB_DEPTH_CONTROL, (1 << 1) | (1 << 2) | (1 << 4));  // z test + write, LESS
    LATTE_SX_ALPHA_TEST_CONTROL at;
    at.set_ALPHA_FUNC(LATTE_SX_ALPHA_TEST_CONTROL::E_ALPHA_FUNC::LESS).set_ALPHA_TEST_ENABLE(false);
    set_reg(REGADDR::SX_ALPHA_TEST_CONTROL, at.getRawValue());
    set_reg(REGADDR::SX_ALPHA_REF, 0);
    LATTE_PA_SU_SC_MODE_CNTL pm{};
    pm.set_FRONT_FACE(LATTE_PA_SU_SC_MODE_CNTL::E_FRONTFACE::CCW);
    pm.set_FRONT_POLY_MODE(LATTE_PA_SU_SC_MODE_CNTL::E_PTYPE::TRIANGLES).set_BACK_POLY_MODE(LATTE_PA_SU_SC_MODE_CNTL::E_PTYPE::TRIANGLES);
    set_reg(REGADDR::PA_SU_SC_MODE_CNTL, pm.getRawValue());
    set_reg(REGADDR::VGT_MULTI_PRIM_IB_RESET_INDX, 0xFFFFFFFF);
    set_reg(REGADDR::CB_TARGET_MASK, 0xFFFFFFFF);
    for (int i = 0; i < 4; i++) set_reg(REGADDR::CB_BLEND_RED + i, 0);
    set_reg(REGADDR::PA_SU_POINT_SIZE, LATTE_PA_SU_POINT_SIZE().set_WIDTH(8).set_HEIGHT(8).getRawValue());
    LATTE_CB_COLOR_CONTROL cc;
    cc.set_SPECIAL_OP(LATTE_CB_COLOR_CONTROL::E_SPECIALOP::NORMAL).set_ROP(LATTE_CB_COLOR_CONTROL::E_LOGICOP::COPY);
    set_reg(REGADDR::CB_COLOR_CONTROL, cc.getRawValue());
    LATTE_PA_CL_CLIP_CNTL clip{};
    clip.set_DX_LINEAR_ATTR_CLIP_ENA(true);
    set_reg(REGADDR::PA_CL_CLIP_CNTL, clip.getRawValue());
    set_reg(mmDB_DEPTH_CLEAR, fbits(1.0f));
}
}

HLE(gx2, GX2Init) {
    std::lock_guard<std::recursive_mutex> lock(gx2::guard);
    if (!ct_gpu_initialize()) { LOG("[ct-stop] Vulkan device initialization failed"); std::_Exit(80); }
    gx2::set_default_state();
    LOG("[ct-gx2] initialized register state and Vulkan device; game draw translation pending");
}
HLE(gx2, GX2SetDefaultState) { gx2::set_default_state(); }
HLE(gx2, GX2SetupContextStateEx) {
    auto context=arg(c,0);
    gx2::checked_guest(context,0xA100);
    std::lock_guard<std::recursive_mutex> lock(gx2::guard);
    gx2::contexts[context].fill(0);
    gx2::active_context=context;
    gx2::set_default_state();
    auto list=reinterpret_cast<uint32_t*>(mem::ptr(context+0x9800));
    list[0]=uint32_t(gx2::OP_SET_CONTEXT)|(1u<<8); list[1]=context;
}
HLE(gx2, GX2SetContextState) { gx2::emit(gx2::OP_SET_CONTEXT,{arg(c,0)}); }
HLE(gx2, GX2GetContextStateDisplayList) {
    if (arg(c,1)) st32(arg(c,1),arg(c,0)+0x9800);
    if (arg(c,2)) st32(arg(c,2),8);
}
HLE(gx2, GX2BeginDisplayListEx) {
    if (gx2::recording.start) fatal("[ct-stop] nested GX2 display-list recording");
    gx2::checked_guest(arg(c,0),arg(c,1));
    if (uint64_t(arg(c,0))+arg(c,1)>=0x100000000ull) fatal("[ct-stop] display list end overflow");
    gx2::recording={arg(c,0),arg(c,0),arg(c,0)+arg(c,1)};
}
HLE(gx2, GX2EndDisplayList) {
    auto size=gx2::recording.pos-gx2::recording.start;
    gx2::recording={}; ret(c,size);
}
HLE(gx2, GX2GetCurrentDisplayList) {
    if (arg(c,0)) st32(arg(c,0),gx2::recording.start);
    if (arg(c,1)) st32(arg(c,1),gx2::recording.start?gx2::recording.end-gx2::recording.start:0);
    ret(c,gx2::recording.start!=0);
}
HLE(gx2, GX2GetDisplayListWriteStatus) { ret(c,gx2::recording.start!=0); }
HLE(gx2, GX2CallDisplayList) { gx2::emit(gx2::OP_CALL,{arg(c,0),arg(c,1)}); }
HLE(gx2, GX2DirectCallDisplayList) { gx2::emit(gx2::OP_CALL,{arg(c,0),arg(c,1)}); }

HLE(gx2, GX2Invalidate) { gx2::emit(gx2::OP_INVALIDATE,{arg(c,0),arg(c,1),arg(c,2)}); }
HLE(gx2, GX2Flush) { gx2::emit(gx2::OP_FLUSH,{}); }
HLE(gx2, GX2DrawDone) { gx2::emit(gx2::OP_DRAW_DONE,{}); ret(c,1); }
