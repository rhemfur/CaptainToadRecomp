#include "runtime.h"
int ct_system_test() {
    mem::init();
    Cpu cpu{};
    auto invoke=[&](const char* name,std::initializer_list<uint32_t> args={}) {
        auto fn=hle_find("coreinit",name);
        if (!fn) fatal("[ct-test] missing system export %s",name);
        unsigned i=3;
        for (auto arg:args) cpu.r[i++]=arg;
        fn(&cpu);
        return cpu.r[3];
    };
    auto first=invoke("MCP_Open"), second=invoke("MCP_Open");
    auto buffer=mem::runtime_alloc(0x50);
    st32(buffer+0x46,0x12345678);
    bool ok=first && second && first!=second && invoke("MCP_GetSysProdSettings",{first,buffer})==0 &&
            ld8(buffer+3)==4 && ld8(buffer+0x0B)==4 && ld32(buffer+0x46)==0x12345678;
    invoke("MCP_Close",{first}); invoke("MCP_Close",{second});
    auto info=invoke("OSGetSystemInfo");
    ok=ok && info && ld32(info)==248625000 && ld32(info+4)==1243125000 &&
       invoke("OSGetSystemInfo")==info && invoke("OSIsDebuggerInitialized")==0;
    auto uc=invoke("UCOpen"), record=mem::runtime_alloc(0x58), value=mem::runtime_alloc(8);
    mem::write_cstr(record,"cafe.language",64);
    st32(record+0x4C,4); st32(record+0x50,value);
    st32(value+4,0xAABBCCDD); st32(record+0x54,0x11223344);
    ok=ok && invoke("UCReadSysConfig",{uc,1,record})==0 && ld32(value)==1 &&
       ld32(value+4)==0xAABBCCDD && ld32(record+0x54)==0x11223344 && ld32(record+0x48)==0;
    invoke("UCClose",{uc});
    LOG("[ct-test] MCP/UC handles/EUR layout/bounds/system-info/debugger: %s",ok?"PASS":"FAIL");
    return ok?0:1;
}
