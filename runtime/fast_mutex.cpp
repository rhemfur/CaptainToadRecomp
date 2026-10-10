// OSFastMutex ABI/behavior follows Cemu coreinit_Thread.h and coreinit_Synchronization.cpp (MPL-2.0).
// Host wait objects are separate from the 0x2C-byte big-endian guest structure.
#include "runtime.h"
#include <condition_variable>
#include <memory>
#include <mutex>
#include <unordered_map>

namespace {
struct FastMutex {
    std::mutex guard;
    std::condition_variable changed;
    uint32_t owner=0, count=0;
};
std::mutex table_guard;
std::unordered_map<uint32_t,std::unique_ptr<FastMutex>> table;
FastMutex& lookup(uint32_t address) {
    if (address<0x10000 || uint64_t(address)+0x2C>0x100000000ull || (address&3))
        fatal("[ct-stop] invalid fast mutex address %08X",address);
    std::lock_guard<std::mutex> lock(table_guard);
    auto& item=table[address];
    if (!item) item=std::make_unique<FastMutex>();
    return *item;
}
uint32_t self() {
    auto id=threads::current_thread();
    if (!id) fatal("[ct-stop] fast mutex called outside a guest thread");
    return id;
}
void publish(uint32_t address,const FastMutex& mutex) {
    st32(address+0x1C,mutex.owner);
    st32(address+0x20,mutex.count);
}
}

HLE(coreinit, OSFastMutex_Init) {
    auto address=arg(c,0);
    auto& mutex=lookup(address);
    std::lock_guard<std::mutex> lock(mutex.guard);
    if (mutex.count) fatal("[ct-stop] reinitializing a locked fast mutex %08X",address);
    mutex.owner=0; mutex.count=0;
    memset(mem::ptr(address),0,0x2C);
    st32(address,0x664D7458); // fMtX
    st32(address+4,arg(c,1));
}
HLE(coreinit, OSFastMutex_Lock) {
    auto address=arg(c,0), id=self();
    auto& mutex=lookup(address);
    std::unique_lock<std::mutex> lock(mutex.guard);
    while (mutex.owner && mutex.owner!=id) {
        // Never reacquire the guest core while holding the host mutex: its owner may need that core.
        lock.unlock();
        threads::block_begin();
        lock.lock();
        mutex.changed.wait(lock,[&]{return !mutex.owner || mutex.owner==id;});
        lock.unlock();
        threads::block_end();
        lock.lock();
    }
    if (mutex.count==UINT32_MAX) fatal("[ct-stop] fast mutex recursion overflow");
    mutex.owner=id; ++mutex.count;
    publish(address,mutex);
}
HLE(coreinit, OSFastMutex_TryLock) {
    auto address=arg(c,0), id=self();
    auto& mutex=lookup(address);
    std::lock_guard<std::mutex> lock(mutex.guard);
    if (mutex.owner && mutex.owner!=id) { ret(c,0); return; }
    if (mutex.count==UINT32_MAX) fatal("[ct-stop] fast mutex recursion overflow");
    mutex.owner=id; ++mutex.count;
    publish(address,mutex);
    ret(c,1);
}
HLE(coreinit, OSFastMutex_Unlock) {
    auto address=arg(c,0), id=self();
    auto& mutex=lookup(address);
    bool wake=false;
    {
        std::lock_guard<std::mutex> lock(mutex.guard);
        // Cemu records titles relying on a non-owner unlock being ignored.
        if (mutex.owner!=id) return;
        if (!mutex.count) fatal("[ct-stop] inconsistent fast mutex count");
        if (--mutex.count==0) { mutex.owner=0; wake=true; }
        publish(address,mutex);
    }
    if (wake) mutex.changed.notify_one();
}
