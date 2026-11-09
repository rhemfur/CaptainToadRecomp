// Captain Toad cheats (Gameplay menu, Settings > Cheats, Android's menu button). tools/patch_runtime.py
// puts this file in place of the reference's mods/cheats.cpp, whose cheats edit Wind Waker HD's live
// save data.
//
// The game reads GameData.bin when it starts, so a cheat edits that file (ct_save.h) and restarts the
// game (on Android, where the app cannot relaunch itself, closes it): progress since the game last saved
// is lost, as the menu says. The file before the first cheat of a run is kept as
// GameData.bin.before-cheats. The course table comes from the player's own game
// (content/SystemData/StageList.szs).
//
// The reference's live switches (infinite health, magic and the like, the moon jump) read Wind Waker HD
// memory; here they are always off.
//
// Test aid: CT_CHEAT=unlock,clear,gems,bonus,times,pixel,complete applies those to the save once, early
// in the boot (runtime/mcp.cpp, the game's first MCP_Open), before the game reads it; no restart.
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <mutex>
#include <string>

#include "ct_save.h"
#include "gfx/renderer.h"
#include "mods.h"
#include "mods/item_icons.h"
#include "overlay/hostui.h"
#include "runtime.h"
#include "savestate.h"

namespace mods {
namespace {
std::mutex g_mutex;
bool g_backed_up = false;  // under g_mutex

ct_save::Bytes read_file(const std::filesystem::path& p) {
    std::ifstream f(p, std::ios::binary);
    return f ? ct_save::Bytes(std::istreambuf_iterator<char>(f), {}) : ct_save::Bytes();
}
bool write_file(const std::filesystem::path& p, const ct_save::Bytes& b) {
    // next to the save, then renamed over it: an interrupted write never leaves half a save
    const auto tmp = std::filesystem::path(p).concat(".cheat-tmp");
    {
        std::ofstream f(tmp, std::ios::binary | std::ios::trunc);
        if (!f.write((const char*)b.data(), (std::streamsize)b.size())) return false;
    }
    std::error_code ec;
    std::filesystem::rename(tmp, p, ec);
    return !ec;
}

const ct_save::Courses& courses(std::string& why) {
    static std::once_flag once;
    static ct_save::Courses table;
    static std::string error;
    std::call_once(once, [] {
        try {
            const auto szs = read_file(config::game_dir + "/content/SystemData/StageList.szs");
            if (szs.empty()) { error = "content/SystemData/StageList.szs is missing"; return; }
            const auto files = item_icons::read_sarc(item_icons::yaz0_decode(szs));
            const auto byml = files.find("StageList.byml");
            if (byml == files.end()) { error = "StageList.szs has no StageList.byml"; return; }
            table = ct_save::parse_stage_list(byml->second, error);
        } catch (const std::exception& e) {
            error = std::string("StageList.szs: ") + e.what();
        }
    });
    why = error;
    return table;
}

const char* name(int which) {
    switch (which) {
    case ct_save::kUnlockEpisodes: return "unlock every episode and course";
    case ct_save::kClearCourses: return "clear every course";
    case ct_save::kAllGems: return "every Super Gem";
    case ct_save::kAllBonus: return "every bonus objective";
    case ct_save::kAllTimes: return "every challenge time";
    case ct_save::kAllPixelToads: return "every Pixel Toad";
    case ct_save::kComplete: return "100% completion";
    default: return "cheats";
    }
}

// false and a notice when the save could not be changed
bool edit_save(int which) {
    std::lock_guard lock(g_mutex);
    std::string why;
    const auto& table = courses(why);
    if (table.empty()) {
        LOG("[cheats] %s", why.c_str());
        ss::notice("Cheats: the course list could not be read (" + why + ")");
        return false;
    }
    const std::filesystem::path save = config::save_dir + "/user/GameData.bin";
    auto data = read_file(save);
    if (data.empty()) {
        ss::notice("Cheats: no save yet. Start a course so the game saves once, then try again.");
        return false;
    }
    auto edited = data;
    if (!ct_save::apply(edited, which, table, why)) {
        LOG("[cheats] %s: %s", save.string().c_str(), why.c_str());
        ss::notice("Cheats: " + why);
        return false;
    }
    if (!g_backed_up) {
        const auto backup = std::filesystem::path(save).concat(".before-cheats");
        if (!write_file(backup, data)) {
            ss::notice("Cheats: could not keep a copy of the save; nothing changed");
            return false;
        }
        g_backed_up = true;
    }
    if (!write_file(save, edited)) {
        ss::notice("Cheats: could not write the save; nothing changed");
        return false;
    }
    LOG("[cheats] %s applied to %s (%zu courses in the game's list)", name(which), save.string().c_str(), table.size());
    return true;
}
}  // namespace

void apply_env_cheats() {
    const char* e = getenv("CT_CHEAT");
    if (!e || !*e) return;
    static const std::pair<const char*, int> names[] = {
        {"unlock", ct_save::kUnlockEpisodes}, {"clear", ct_save::kClearCourses}, {"gems", ct_save::kAllGems},
        {"bonus", ct_save::kAllBonus}, {"times", ct_save::kAllTimes}, {"pixel", ct_save::kAllPixelToads},
        {"complete", ct_save::kComplete}};
    int which = 0;
    for (const auto& [n, bit] : names)
        if (strstr(e, n)) which |= bit;
    if (which) edit_save(which);
}

void request_cheat(int which) {
    // The menu calls this on the main thread, the settings overlay on the render thread; the restart
    // runs on the main thread either way.
    hostui::post([which] {
        if (!edit_save(which)) return;
#ifdef __ANDROID__
        // the app cannot relaunch itself: it closes, and the next start reads the edited save
        hostui::quit();
#else
        if (!render::restart()) ss::notice(std::string("Cheats: ") + name(which) + " saved; restart Captain Toad to load it");
#endif
    });
}

bool infinite(int) { return false; }
void set_infinite(int, bool) {}
void moon_jump_input(const input::PadState&) {}
void moon_jump_camera(uint32_t) {}
void moon_jump_reset() {}
void moon_jump_step(Cpu*, uint32_t, bool) {}
bool moon_jump_move(uint32_t, float&, float&) { return false; }
void cheats_service() {}

}  // namespace mods
