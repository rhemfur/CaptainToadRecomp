// Generic startup services adapted from ZeldaWWHDRecomp coreinit_misc.cpp (MPL-2.0).
#include "runtime.h"
#include <mutex>

// No guest debugger is installed by the diagnostic runtime.
HLE(coreinit, OSIsDebuggerInitialized) { ret(c,0); }
HLE(coreinit, OSIsDebuggerPresent) { ret(c,0); }

HLE(coreinit, OSGetSystemInfo) {
    static std::once_flag once;
    static uint32_t info=0;
    std::call_once(once,[] {
        info=mem::runtime_alloc(0x20);
        st32(info+0x00,248625000);
        st32(info+0x04,1243125000);
        st64(info+0x08,0);
        st32(info+0x10,0);
    });
    ret(c,info);
}
