// Captain Toad boot diagnostic: generic Cafe components, no renderer or Zelda hooks.
#include "runtime.h"
#include "recomp_table.h"
#include "platform/host.h"
#include "sha256.h"
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <thread>

int g_ppc_trace = 1;
static std::atomic<uint64_t> calls{0};
static std::atomic<uint32_t> last_function{0};
extern "C" void ppc_trace_enter(uint32_t addr) {
    last_function = addr;
    auto n = ++calls;
    if (n <= 30) LOG("[ct-trace] #%llu function=%08X", (unsigned long long)n, addr);
    if (n > 10000000) fatal("[ct-stop] diagnostic function-entry budget exceeded, last=%08X", addr);
}
namespace perf_hint { void add_current_thread() {} } // Host optimization disabled in headless diagnostic.
namespace rprof {
uint64_t thread_cpu_ns() {
#ifdef _WIN32
    FILETIME created, exited, kernel, user;
    if (!GetThreadTimes(GetCurrentThread(), &created, &exited, &kernel, &user)) return 0;
    auto value = [](FILETIME t) { return (uint64_t(t.dwHighDateTime) << 32) | t.dwLowDateTime; };
    return (value(kernel) + value(user)) * 100;
#else
    timespec t{};
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t);
    return uint64_t(t.tv_sec) * 1000000000 + t.tv_nsec;
#endif
}
}
namespace ss {
uint32_t snap_ld32(uint32_t) { fatal("[ct-stop] snapshots are unavailable in the boot diagnostic"); }
}
void mem_setup_heaps(uint32_t data_end);
void mem_init_data_imports(uint32_t, uint32_t, uint32_t);
int ct_vulkan_probe();
int ct_mutex_test();
int ct_filesystem_test(const std::string&);
int ct_system_test();

static bool hash_test() {
    std::vector<uint8_t> abc{'a','b','c'};
    std::vector<uint8_t> million(1000000, 'a');
    return ct::sha256({}) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" &&
           ct::sha256(abc) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" &&
           ct::sha256(million) == "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0";
}

static bool verify_image(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file || file.tellg() < 52 || file.tellg() > (64 << 20)) return false;
    auto length = size_t(file.tellg());
    file.seekg(0);
    std::vector<uint8_t> image(length);
    if (!file.read(reinterpret_cast<char*>(image.data()), length)) return false;
    if (ct::sha256(image) != "3e867817ff4cfbefcd1f3323fe1e97919852cd86aee3738bd8d44e6e460a0464") return false;
    return image[0]==0x7f && image[1]=='E' && image[2]=='L' && image[3]=='F' &&
           image[4]==1 && image[5]==2 && image[18]==0 && image[19]==20;
}

static void data_imports() {
    uint32_t alloc=0, alloc_ex=0, free_=0;
    for (unsigned i=0; i<g_recomp_import_count; ++i) {
        const auto& im = g_recomp_imports[i];
        if (im.is_func) continue;
        std::string name(im.name);
        if (name=="MEMAllocFromDefaultHeap") alloc=im.addr;
        else if (name=="MEMAllocFromDefaultHeapEx") alloc_ex=im.addr;
        else if (name=="MEMFreeToDefaultHeap") free_=im.addr;
        else if (name=="__gh_FOPEN_MAX") st32(im.addr,20);
        else if (name=="__atexit_cleanup" || name=="__cpp_exception_cleanup_ptr" ||
                 name=="__cpp_exception_init_ptr") {
            // These are nullable callback variables, not functions returning success.
            st32(im.addr,0);
        } else if (name=="_iob") {
            // Do not fabricate an unverified FILE ABI. Fail if a stream service is called.
            LOG("[ct-import-data] _iob storage remains zero; stream ABI requires implementation");
        } else fatal("[ct-stop] unknown data import %s.%s",im.lib,im.name);
    }
    mem_init_data_imports(alloc,alloc_ex,free_);
}

int main(int argc, char** argv) {
#ifdef __ANDROID__
    log_set_sink([](const char* line,size_t size) { std::fwrite(line,1,size,stderr); std::fputc('\n',stderr); });
#endif
    if (argc==2 && std::string(argv[1])=="--self-test") {
        bool ok=hash_test();
        LOG("[ct-test] SHA-256 known vectors: %s",ok?"PASS":"FAIL");
        return ok?0:1;
    }
    if (argc==2 && std::string(argv[1])=="--vulkan-probe") return ct_vulkan_probe();
    if (argc==2 && std::string(argv[1])=="--mutex-self-test") return ct_mutex_test();
    if (argc==2 && std::string(argv[1])=="--system-self-test") return ct_system_test();
    if (argc==3 && std::string(argv[1])=="--fs-self-test") return ct_filesystem_test(argv[2]);
    std::string game="game";
    int seconds=10;
    bool verify_only=false;
    for (int i=1;i<argc;++i) {
        std::string option(argv[i]);
        if (option=="--game" && i+1<argc) game=argv[++i];
        else if (option=="--seconds" && i+1<argc) seconds=std::atoi(argv[++i]);
        else if (option=="--verify-only") verify_only=true;
        else { std::fprintf(stderr,"usage: ct-diagnostic [--game DIR] [--seconds 1..60] [--verify-only]\n"); return 2; }
    }
    if (seconds<1 || seconds>60) return 2;
    auto rpx=game+"/code/Kinopio.rpx";
    if (!verify_image(rpx)) {
        LOG("[ct-stop] executable does not match the Captain Toad EUR v16 SHA-256 profile");
        return 3;
    }
    LOG("[ct-profile] verified CT-EUR-v16, %u generated functions, %u imports",
        g_recomp_func_count,g_recomp_import_count);
    if (verify_only) return 0;
    config::game_dir=game;
    config::save_dir=game+"/save-diagnostic";
    mem::init();
    LoadedModule module{};
    if (!load_rpx(rpx,module) || module.entry!=g_recomp_entry_point) fatal("[ct-stop] entry point mismatch");
    LOG("[ct-boot] loaded Kinopio.rpx entry=%08X sda=%08X sda2=%08X data_end=%08X",
        module.entry,module.sda_base,module.sda2_base,module.data_end);
    dispatch::init();
    data_imports();
    mem_setup_heaps(module.data_end);
    threads::init(module);
    uint32_t args=mem::runtime_alloc(16), arg0=mem::runtime_alloc(16);
    mem::write_cstr(arg0,"Kinopio.rpx",16);
    st32(args,arg0);
    std::thread([seconds] {
        std::this_thread::sleep_for(std::chrono::seconds(seconds));
        LOG("[ct-stop] diagnostic deadline reached, entries=%llu last=%08X",
            (unsigned long long)calls.load(),last_function.load());
        std::_Exit(124);
    }).detach();
    LOG("[ct-boot] executing recompiled entry; no renderer or audio backend attached");
    threads::run_main(module,1,args);
    LOG("[ct-boot] guest main returned, entries=%llu",(unsigned long long)calls.load());
    return 0;
}
