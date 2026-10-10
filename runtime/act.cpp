// nn_act startup behavior follows Cemu nn_act.cpp (MPL-2.0).
// This runtime exposes one local account in slot 1; slot 0 is invalid on the console.
#include "runtime.h"
#include <atomic>

namespace {
std::atomic<uint32_t> initialize_count{0};
}
HLE(nn_act, Initialize__Q2_2nn3actFv) {
    if (initialize_count.fetch_add(1)==UINT32_MAX) fatal("[ct-stop] nn_act initialize count overflow");
    ret(c,0);
}
HLE(nn_act, GetSlotNo__Q2_2nn3actFv) { ret(c,1); }
