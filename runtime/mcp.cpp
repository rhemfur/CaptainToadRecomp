// MCP region record layout follows Cemu coreinit_MCP.h/.cpp (MPL-2.0).
// The virtual console's region is the game's own (meta/meta.xml), so the game loads the message
// archives its disc carries (USA: USen/USfr/USes). Other product/serial fields remain unknown/zero.
#include "runtime.h"
#include <fstream>
#include <mutex>
#include <sstream>
#include <unordered_set>

namespace {
std::mutex guard;
std::unordered_set<uint32_t> handles;
uint32_t next_handle=1;

// Region bits as meta.xml and MCP use them: 1 Japan, 2 USA, 4 Europe. Without a readable single
// region, Europe (the first identified profile).
uint8_t game_region() {
    static const uint8_t region=[]{
        std::ifstream f(config::game_dir+"/meta/meta.xml");
        std::stringstream text;
        text<<f.rdbuf();
        const std::string xml=text.str();
        auto tag=xml.find("<region");
        auto start=tag==std::string::npos?tag:xml.find('>',tag);
        if (start==std::string::npos) return uint8_t(4);
        auto bits=std::strtoul(xml.c_str()+start+1,nullptr,16);
        return uint8_t(bits==1||bits==2||bits==4?bits:4);
    }();
    return region;
}
}
#ifdef CT_FOREIGN_GUEST
namespace mods { void apply_env_cheats(); }  // runtime/cheats.cpp (full runtime only)
#endif
HLE(coreinit, MCP_Open) {
#ifdef CT_FOREIGN_GUEST  // the full runtime (tools/build_runtime_macos.sh, build_game_*.ps1)
    static std::once_flag cheats;
    std::call_once(cheats, mods::apply_env_cheats);  // CT_CHEAT test aid, before the game reads its save
#endif
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
    st8(out+0x03,game_region()); // Virtual platform region
    st8(out+0x0B,game_region()); // Foreground title region
    ret(c,0);
}
