#include "runtime.h"
#include <filesystem>
#include <fstream>

int ct_filesystem_test(const std::string& directory) {
    std::filesystem::path root=std::filesystem::absolute(directory);
    std::filesystem::create_directories(root/"content");
    { std::ofstream file(root/"content/MiXeD.bin",std::ios::binary); file << "CTFS1234"; }
    config::game_dir=root.string();
    config::save_dir=(root/"save").string();
    mem::init();
    threads::init(LoadedModule{});
    Cpu* cpu=threads::make_service_cpu("fs-test");
    threads::ensure_core();
    auto path=mem::runtime_alloc(256), mode=mem::runtime_alloc(16), handle=mem::runtime_alloc(4);
    auto buffer=mem::runtime_alloc(32), stat=mem::runtime_alloc(0x68);
    auto invoke=[&](const char* name,std::initializer_list<uint32_t> arguments) {
        auto fn=hle_find("coreinit",name);
        if (!fn) fatal("[ct-test] missing filesystem export %s",name);
        unsigned index=3;
        for (auto arg:arguments) cpu->r[index++]=arg;
        fn(cpu);
        return int32_t(cpu->r[3]);
    };
    mem::write_cstr(path,"/vol/content/mixed.bin",256);
    mem::write_cstr(mode,"rb",16);
    bool ok=invoke("FSOpenFile",{0,0,path,mode,handle,0})==0;
    auto file=ld32(handle);
    memset(mem::ptr(buffer),0xAA,32);
    ok=ok && invoke("FSReadFile",{0,0,buffer,2,4,file,0,0})==4 &&
       std::memcmp(mem::ptr(buffer),"CTFS1234",8)==0 && ld8(buffer+8)==0xAA;
    ok=ok && invoke("FSReadFile",{0,0,0xFFFFFFF0,8,4,file,0,0})==-10;
    st32(stat+0x64,0xDEADBEEF);
    ok=ok && invoke("FSGetStatFile",{0,0,file,stat,0})==0 && ld32(stat+0x10)==8 &&
       ld32(stat+0x64)==0xDEADBEEF;
    invoke("FSCloseFile",{0,0,file,0});
    mem::write_cstr(mode,"wb",16);
    ok=ok && invoke("FSOpenFile",{0,0,path,mode,handle,0})==-10;
    mem::write_cstr(path,"/vol/content/../../escape.bin",256);
    mem::write_cstr(mode,"rb",16);
    ok=ok && invoke("FSOpenFile",{0,0,path,mode,handle,0})==-6;
    mem::write_cstr(path,"/vol/save/user/test.bin",256);
    mem::write_cstr(mode,"wb",16);
    ok=ok && invoke("FSOpenFile",{0,0,path,mode,handle,0})==0;
    file=ld32(handle);
    ok=ok && invoke("FSWriteFile",{0,0,buffer,1,8,file,0,0})==8;
    invoke("FSCloseFile",{0,0,file,0});
    std::ifstream saved(root/"save/user/test.bin",std::ios::binary);
    std::string saved_bytes((std::istreambuf_iterator<char>(saved)),{});
    ok=ok && saved_bytes=="CTFS1234";
    threads::release_core();
    LOG("[ct-test] filesystem case/read/stat/bounds/content-readonly/save-roundtrip: %s",ok?"PASS":"FAIL");
    return ok?0:1;
}
