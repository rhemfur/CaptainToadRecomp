// UC record layout follows ZeldaWWHDRecomp and Cemu coreinit_MCP.cpp (MPL-2.0).
#include "runtime.h"
#include <mutex>
#include <unordered_set>

namespace {
std::mutex guard;
std::unordered_set<uint32_t> handles;
uint32_t next_handle=1;
}
HLE(coreinit, UCOpen) {
    std::lock_guard<std::mutex> lock(guard);
    if (!next_handle) fatal("[ct-stop] UC handle space exhausted");
    auto handle=next_handle++;
    handles.insert(handle);
    ret(c,handle);
}
HLE(coreinit, UCClose) {
    std::lock_guard<std::mutex> lock(guard);
    handles.erase(arg(c,0));
    ret(c,0);
}
HLE(coreinit, UCReadSysConfig) {
    std::lock_guard<std::mutex> lock(guard);
    if (!handles.contains(arg(c,0))) fatal("[ct-stop] invalid UC handle");
    auto count=arg(c,1), entries=arg(c,2);
    if (count>1024 || entries<0x10000 || uint64_t(entries)+uint64_t(count)*0x54>0x100000000ull)
        fatal("[ct-stop] invalid UC record array");
    for (uint32_t i=0;i<count;++i) {
        auto entry=entries+i*0x54;
        auto name_ptr=reinterpret_cast<const char*>(mem::ptr(entry));
        size_t length=0;
        while (length<64 && name_ptr[length]) ++length;
        if (length==64) fatal("[ct-stop] unterminated UC setting name");
        std::string name(name_ptr,length);
        auto size=ld32(entry+0x4C), output=ld32(entry+0x50);
        uint32_t value=0;
        if (name=="cafe.language") value=1; // Explicit diagnostic default: English.
        else if (name=="cafe.initial_launch") value=2;
        else if (name=="parent.enable") value=0;
        else {
            LOG("[ct-stop] UC setting requires implementation: %s size=%u",name.c_str(),size);
            std::_Exit(78);
        }
        if (!output || output<0x10000 || uint64_t(output)+size>0x100000000ull ||
            (size!=1 && size!=2 && size!=4)) fatal("[ct-stop] invalid UC value buffer");
        if (size==1) st8(output,value);
        else if (size==2) st16(output,value);
        else st32(output,value);
        st32(entry+0x48,0);
        LOG("[ct-uc] %s=%u",name.c_str(),value);
    }
    ret(c,0);
}
