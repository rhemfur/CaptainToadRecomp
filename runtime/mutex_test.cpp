// Exercise recursion, guest ABI, ownership and contention on the same emulated core.
#include "runtime.h"
#include <atomic>
#include <future>
#include <thread>

int ct_mutex_test() {
    std::thread([] { std::this_thread::sleep_for(std::chrono::seconds(10)); std::_Exit(124); }).detach();
    mem::init();
    threads::init(LoadedModule{});
    Cpu* owner=threads::make_service_cpu("mutex-test-owner");
    threads::set_service_core(1);
    threads::ensure_core();
    auto address=mem::runtime_alloc(0x30);
    st32(address+0x2C,0x12345678);
    auto invoke=[address](Cpu* cpu,const char* name) {
        auto fn=hle_find("coreinit",name);
        if (!fn) fatal("[ct-test] missing test export %s",name);
        cpu->r[3]=address; cpu->r[4]=0x11223344;
        fn(cpu);
        return cpu->r[3];
    };
    invoke(owner,"OSFastMutex_Init");
    bool ok=ld32(address)==0x664D7458 && ld32(address+4)==0x11223344 && ld32(address+0x2C)==0x12345678;
    invoke(owner,"OSFastMutex_Lock");
    ok=ok && invoke(owner,"OSFastMutex_TryLock")==1 && ld32(address+0x20)==2 &&
       ld32(address+0x1C)==threads::current_thread();
    std::promise<bool> tried,acquired;
    auto try_result=tried.get_future(), acquire_result=acquired.get_future();
    std::atomic<bool> entered_wait{false};
    std::thread competitor([&] {
        Cpu* other=threads::make_service_cpu("mutex-test-waiter");
        threads::set_service_core(1);
        threads::ensure_core();
        bool unavailable=invoke(other,"OSFastMutex_TryLock")==0;
        invoke(other,"OSFastMutex_Unlock");
        unavailable=unavailable && ld32(address+0x20)==2;
        tried.set_value(unavailable);
        entered_wait=true;
        invoke(other,"OSFastMutex_Lock");
        bool owns=ld32(address+0x1C)==threads::current_thread() && ld32(address+0x20)==1;
        invoke(other,"OSFastMutex_Unlock");
        acquired.set_value(owns);
        threads::release_core();
        threads::service_end();
    });
    threads::release_core();
    if (try_result.wait_for(std::chrono::seconds(2))!=std::future_status::ready)
        fatal("[ct-test] competitor did not reach TryLock");
    ok=ok && try_result.get();
    threads::ensure_core();
    invoke(owner,"OSFastMutex_Unlock");
    ok=ok && ld32(address+0x20)==1 && acquire_result.wait_for(std::chrono::milliseconds(0))!=std::future_status::ready;
    invoke(owner,"OSFastMutex_Unlock");
    threads::release_core();
    if (acquire_result.wait_for(std::chrono::seconds(2))!=std::future_status::ready)
        fatal("[ct-test] waiter could not acquire mutex after final unlock");
    ok=ok && acquire_result.get();
    competitor.join();
    ok=ok && entered_wait && ld32(address+0x1C)==0 && ld32(address+0x20)==0 && ld32(address+0x2C)==0x12345678;
    LOG("[ct-test] fast mutex ABI/recursion/non-owner/TryLock/same-core contention: %s",ok?"PASS":"FAIL");
    return ok?0:1;
}
