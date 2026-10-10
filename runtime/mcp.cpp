// MCP region record layout follows Cemu coreinit_MCP.h/.cpp (MPL-2.0).
// This runtime exposes an EUR virtual console; other product/serial fields remain unknown/zero.
#include "runtime.h"
#include <mutex>
#include <unordered_set>

namespace {
std::mutex guard;
std::unordered_set<uint32_t> handles;
uint32_t next_handle=1;
}
HLE(coreinit, MCP_Open) {
    std::lock_guard<std::mutex> lock(guard);
    if (!next_handle) fatal("[ct-stop] MCP handle space exhausted");
    auto handle=next_handle++;
    handles.insert(handle);
    ret(c,handle);
}
HLE(coreinit, MCP_Close) {
    std::lock_guard<std::mutex> lock(guard);
    handles.erase(arg(c,0));
}
HLE(coreinit, MCP_GetSysProdSettings) {
    std::lock_guard<std::mutex> lock(guard);
    if (!handles.contains(arg(c,0))) fatal("[ct-stop] MCP settings requested through invalid handle");
    auto out=arg(c,1);
    if (out<0x10000 || uint64_t(out)+0x46>0x100000000ull) fatal("[ct-stop] invalid MCP settings buffer");
    memset(mem::ptr(out),0,0x46);
    st8(out+0x03,4); // Virtual platform region: Europe.
    st8(out+0x0B,4); // Foreground title region: Europe.
    ret(c,0);
}
