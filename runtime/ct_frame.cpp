// Captain Toad's frame start. The profile's hook list (profiles/*.json "hooks", tools/recompile.py)
// routes the game's per-frame function through hook_<address>: USA v16 0x02420F10, which runs the game
// logic, draws and swaps the TV/GamePad buffers, and which the main loop calls once a frame. Its entry
// is the point where save states are made and loaded (savestate.cpp ss::ct_service): the main thread
// is there on every frame with the same call chain, and the other game threads can be parked.
// Built only into the full reference runtime (CT_EXTRA_SOURCES).
#include "runtime.h"
#include "aspect.h"

#include <cmath>
#include <cstdlib>

namespace ss { void ct_service(Cpu* c); }  // savestate.cpp, Captain Toad additions (tools/patch_runtime.py)

// weak: a build of another region has no such hook and no such function
extern "C" __attribute__((weak)) void f_02420F10_orig(Cpu* c);
// TV aspect ratio (Settings > Graphics > Aspect ratio, aspect.cpp): the runtime widens the screen-shaped
// render targets; the game's side is what Cemu's Resolution pack patches (KinopioAspectUWv16): three
// 16:9 constants in .rodata, written here at the start of each frame, and the camera aspect below.
static constexpr float kCtBaseAspect = 16.0f / 9.0f;
static void ct_aspect_constants() {
    static const uint32_t addresses[] = {0x100A2D38u, 0x100C0164u, 0x100D982Cu};
    static float written = kCtBaseAspect;
    static bool usable = [] {
        for (uint32_t a : addresses)
            if (u32_as_f32(ld32(a)) != kCtBaseAspect) {
                LOG("[aspect] constant at %08X is not 16:9: Captain Toad's aspect stays 16:9", a);
                return false;
            }
        return true;
    }();
    const float want = aspect::game();
    if (!usable || want == written) return;
    for (uint32_t a : addresses) st32(a, f32_as_u32(want));
    written = want;
}

extern "C" void hook_02420F10(Cpu* c) {
    ss::ct_service(c);
    ct_aspect_constants();
    f_02420F10_orig(c);
}

// USA v16 0x023734F8 (r3 renderer, r4 viewport {left, top, right, bottom}, r5 layer: 0 TV, 1 GamePad)
// stores the viewport's width / height as the layer camera's projection aspect (+0x130). For the TV's
// 1280x720 and the GamePad's 854x480 the picture shape replaces it: the runtime widens both screens'
// buffers (tools/patch_runtime.py, screen_shaped).
extern "C" __attribute__((weak)) void f_023734F8_orig(Cpu* c);
extern "C" void hook_023734F8(Cpu* c) {
    const uint32_t rect = c->r[4], layer = c->r[5];
    const float w = u32_as_f32(ld32(rect + 8)) - u32_as_f32(ld32(rect)),
                h = u32_as_f32(ld32(rect + 12)) - u32_as_f32(ld32(rect + 4));
    f_023734F8_orig(c);
    const float want = aspect::game();
    if (h > 0 && std::fabs(w / h - kCtBaseAspect) < 0.01f && want != kCtBaseAspect) st32(c->r[3] + 0x130, f32_as_u32(want));
    static const bool log_cameras = std::getenv("CT_LOG_ASPECT") != nullptr;  // each camera's viewport and aspect
    if (log_cameras) LOG("[aspect] camera: viewport %.0fx%.0f, layer %u, aspect %.4f", w, h, layer,
                 u32_as_f32(ld32(c->r[3] + 0x130)));
}

// Return addresses that continue the same way, for the save-state check that a parked thread is where
// the state saved it (threads.cpp same_chain). sead::Thread::run (USA v16 0x022DA820) waits on its
// message queue first before its loop (returning to 0x022DA840) and then in the loop (0x022DA870); both
// test the message for quit, call calc and wait again. A thread that has not yet had a message, as in a
// game started afresh, can so load a state saved after it had one (sead::MicConnectThread).
// The polling loop at USA v16 0x0241EBC4 has four branches that end in OSSleepTicks (returning to
// 0x0241EC68, 0x0241ECB4, 0x0241ED18 and 0x0241ED74); each reloads the same registers and then tests r11
// to loop or leave. Every pair was checked in the generated code to reload the same register set.
extern "C" uint32_t ct_equivalent_return(uint32_t lr) {
    switch (lr) {
    case 0x022DA840u: return 0x022DA870u;
    case 0x0241EC68u: case 0x0241ECB4u: case 0x0241ED18u: return 0x0241ED74u;
    default: return lr;
    }
}
