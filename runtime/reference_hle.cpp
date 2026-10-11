// Captain Toad imports that the reference runtime does not export. Behavior follows Cemu
// (MPL-2.0): padscore.cpp, coreinit_Misc.cpp, snd_user.cpp, mic.cpp and nn_nfp.cpp.
// Built only into the full reference runtime (tools/patch_runtime.py, CT_EXTRA_SOURCES).
#include "runtime.h"
#include <atomic>

// ---------------------------------------------------------------- padscore
// The reference input layer has no Wii Remote pointer (DPD); enabling it changes no host state.
HLE(padscore, KPADEnableDPD) { LOG("[ct-pad] KPADEnableDPD(%d): no pointer input", (int32_t)arg(c, 0)); }
HLE(padscore, KPADDisableDPD) {}

// ---------------------------------------------------------------- coreinit
HLE(coreinit, COSWarn) {
    // (moduleId, format, ...): the format string alone; arguments are not expanded.
    LOG("[COSWarn-%d] %s", (int32_t)arg(c, 0), arg(c, 1) ? mem::read_cstr(arg(c, 1)).c_str() : "");
}
HLE(coreinit, OSCoherencyBarrier) {}  // host memory is coherent

// ---------------------------------------------------------------- snd_core / snd_user
HLE(snd_core, AXSetPpcLoadLimit) { ret(c, 0); }
// (device, deviceIndex, volume 0x8000 = 1.0): the reference mixer has no device master volume yet.
HLE(snd_core, AXSetDeviceVolume) {
    static std::atomic<bool> logged{false};
    if (!logged.exchange(true))
        LOG("[ct-ax] AXSetDeviceVolume(%u, %u, %04X) accepted; host output volume unchanged", arg(c, 0), arg(c, 1), arg(c, 2) & 0xFFFF);
    ret(c, 0);
}
namespace {
std::atomic<uint32_t> fx_alloc{0}, fx_free{0};
}
HLE(snd_user, AXFXSetHooks) { fx_alloc = arg(c, 0); fx_free = arg(c, 1); }
HLE(snd_user, AXFXGetHooks) {
    if (arg(c, 0)) st32(arg(c, 0), fx_alloc);
    if (arg(c, 1)) st32(arg(c, 1), fx_free);
}

// ---------------------------------------------------------------- nn_save
// Other titles' saves (Captain Toad looks for Super Mario 3D World, unique id 0x145D) are not
// installed: lookups report FS_STATUS_NOT_FOUND (-6) as Cemu does for an absent save.
constexpr uint32_t kFsNotFound = uint32_t(-6);
HLE(nn_save, SAVEGetStatOtherNormalApplication) {
    LOG("[ct-save] no save of title 00050000%08X: %s", (arg(c, 2) << 8) | 0x10000000u, arg(c, 4) ? mem::read_cstr(arg(c, 4)).c_str() : "");
    ret(c, kFsNotFound);
}
HLE(nn_save, SAVEOpenFileOtherNormalApplication) { ret(c, kFsNotFound); }
// (client, block, accountSlot, u64* freeSize, errHandling): a fixed 1 GiB of save space
HLE(nn_save, SAVEGetFreeSpaceSize) {
    if (arg(c, 3)) { st32(arg(c, 3), 0); st32(arg(c, 3) + 4, 0x40000000u); }
    ret(c, 0);
}

// ---------------------------------------------------------------- mic
// No GamePad microphone is connected: MICInit reports NOT_CONNECTED (-8) and returns -1.
HLE(mic, MICInit) {
    if (arg(c, 3)) st32(arg(c, 3), uint32_t(-8));
    ret(c, uint32_t(-1));
}

// ---------------------------------------------------------------- nn_nfp (amiibo)
// The reader initializes and searches but never detects a figure.
namespace {
constexpr uint32_t kNfpSuccess = 27u << 20;  // BUILD_NN_RESULT(SUCCESS, NN_NFP, 0)
std::atomic<bool> nfp_initialized{false}, nfp_detecting{false};
void init_auto_event(Cpu* c, uint32_t event) {
    static auto os_init_event = hle_find("coreinit", "OSInitEvent");
    if (!os_init_event) fatal("[ct-stop] OSInitEvent is unavailable for nn_nfp");
    Cpu call = *c;
    call.r[3] = event; call.r[4] = 0; call.r[5] = 1;  // not signaled, auto reset
    os_init_event(&call);
}
}
HLE(nn_nfp, Initialize__Q2_2nn3nfpFv) { nfp_initialized = true; nfp_detecting = false; ret(c, 0); }
HLE(nn_nfp, Finalize__Q2_2nn3nfpFv) { nfp_initialized = false; nfp_detecting = false; ret(c, 0); }
HLE(nn_nfp, GetNfpState__Q2_2nn3nfpFv) { ret(c, !nfp_initialized ? 0 : nfp_detecting ? 2 : 1); }
HLE(nn_nfp, SetActivateEvent__Q2_2nn3nfpFP7OSEvent) { if (arg(c, 0)) init_auto_event(c, arg(c, 0)); ret(c, 0); }
HLE(nn_nfp, SetDeactivateEvent__Q2_2nn3nfpFP7OSEvent) { if (arg(c, 0)) init_auto_event(c, arg(c, 0)); ret(c, 0); }
HLE(nn_nfp, StartDetection__Q2_2nn3nfpFv) { nfp_detecting = true; ret(c, kNfpSuccess); }
HLE(nn_nfp, StopDetection__Q2_2nn3nfpFv) { nfp_detecting = false; ret(c, kNfpSuccess); }
