// Captain Toad save data (GameData.bin) and the game's course table (content/SystemData/StageList.szs),
// for the cheats (cheats.cpp). Pure functions on bytes, so tests need no game.
//
// GameData.bin, Wii U (big-endian), 0x800C bytes: a sead stream whose first word is the CRC-32 of the
// rest. 0x1C: game data block (size, then progress flags at 0x20, lives at 0x30); then one block per
// episode (size, then its fields); then the course count and one 40-byte record per course id:
// flags, best coins, best time (seconds, -1 none), misses, last play time (u64), collected gems (bits).
// Layout as documented by the CTSe save editor (SunakazeKun, Captain-Toad-Save-editor); this code is
// written from that description and checked against a save the Wii U game wrote.
#pragma once
#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <vector>

namespace ct_save {

using Bytes = std::vector<uint8_t>;

constexpr uint32_t kFileSize = 0x800C;
constexpr uint32_t kGameData = 0x1C, kGameDataSize = 544;  // Wii U and 3DS size
constexpr uint32_t kSeasonSize = 60;

// game data progress flags
constexpr uint32_t kOpenSeason2 = 1u << 0, kOpenSeason3 = 1u << 1, kOpenBonusEpisode = 1u << 2,
                   kOpenCoinsGalore = 1u << 3, kShowEnding = 1u << 7, kOpenManeckForever = 1u << 13, kOpenPixelToad = 1u << 17;
// course flags
constexpr uint32_t kCourseOpen = 1u << 0, kCourseClear = 1u << 1, kCourseLock = 1u << 2, kCourseNew = 1u << 3,
                   kCourseBonusDone = 1u << 5, kCoursePixelToad = 1u << 8, kCourseComplete = 1u << 16;

enum Cheat : int {
    kUnlockEpisodes = 1 << 0,    // every episode and course page open
    kClearCourses = 1 << 1,      // every course cleared
    kAllGems = 1 << 2,           // every Super Gem
    kAllBonus = 1 << 3,          // every bonus objective
    kAllTimes = 1 << 4,          // every challenge time beaten
    kAllPixelToads = 1 << 5,     // Pixel Toad found in every course that has one
    kComplete = 1 << 6,          // all of the above, every course 100%, Coins Galore and Mummy-Me Maze Forever
};

// One course of the game's table: the gems it holds, its challenge time (0 none), a bonus objective.
// A course with gems also hides a Pixel Toad (update version 1.1 and later).
struct Course {
    uint32_t gems = 0, challenge_time = 0;
    bool bonus = false;
};
using Courses = std::map<uint32_t, Course>;  // by course id

inline uint32_t rd32(const Bytes& b, size_t o) { return uint32_t(b[o]) << 24 | uint32_t(b[o + 1]) << 16 | uint32_t(b[o + 2]) << 8 | b[o + 3]; }
inline void wr32(Bytes& b, size_t o, uint32_t v) {
    b[o] = uint8_t(v >> 24); b[o + 1] = uint8_t(v >> 16); b[o + 2] = uint8_t(v >> 8); b[o + 3] = uint8_t(v);
}

inline uint32_t crc32(const uint8_t* p, size_t n) {
    uint32_t c = 0xFFFFFFFFu;
    for (size_t i = 0; i < n; i++) {
        c ^= p[i];
        for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1)));
    }
    return ~c;
}

// Offset of course record 0, or 0 (with `why`) when the file is not a Wii U Captain Toad save.
inline uint32_t courses_offset(const Bytes& b, uint32_t& count, std::string& why) {
    if (b.size() != kFileSize) { why = "the save file has an unexpected size"; return 0; }
    if (rd32(b, 0x0C) != 7 || rd32(b, 0x08) != kFileSize) { why = "the save file is not Wii U Captain Toad save data"; return 0; }
    if (crc32(b.data() + 4, b.size() - 4) != rd32(b, 0)) { why = "the save file's checksum does not match"; return 0; }
    if (rd32(b, kGameData) != kGameDataSize) { why = "the save file's game data block is not the Wii U one"; return 0; }
    uint32_t p = kGameData + 4 + kGameDataSize;
    for (int season = 0; season < 5; season++) {  // the Wii U game's five episode blocks
        if (rd32(b, p) != kSeasonSize) { why = "the save file's episode blocks are not the Wii U ones"; return 0; }
        p += 4 + kSeasonSize;
    }
    count = rd32(b, p);
    if (count == 0 || p + 4 + uint64_t(count) * 40 > b.size()) { why = "the save file's course list is damaged"; return 0; }
    return p + 4;
}

// Applies the cheats to the save image and rewrites its checksum. Returns false (and `why`) without
// changing it when the file is not one this code understands.
inline bool apply(Bytes& b, int which, const Courses& courses, std::string& why) {
    uint32_t count = 0, base = courses_offset(b, count, why);
    if (!base) return false;
    if (which & kComplete) which |= kUnlockEpisodes | kClearCourses | kAllGems | kAllBonus | kAllTimes | kAllPixelToads;
    uint32_t game_flags = rd32(b, kGameData + 4);
    if (which & (kUnlockEpisodes | kClearCourses)) game_flags |= kOpenSeason2 | kOpenSeason3 | kOpenBonusEpisode;
    // the game sets this once the credits after episode 3's final course have played; a save with that course
    // cleared and the ending not seen makes the episode book fail (BossBird2Stage, course 88 in USA v16)
    if (which & kClearCourses) game_flags |= kShowEnding;
    if (which & kAllPixelToads) game_flags |= kOpenPixelToad;
    if (which & kComplete) game_flags |= kOpenCoinsGalore | kOpenManeckForever;
    wr32(b, kGameData + 4, game_flags);
    for (const auto& [id, course] : courses) {
        if (id >= count) continue;
        const size_t r = base + size_t(id) * 40;
        uint32_t flags = rd32(b, r), gems = rd32(b, r + 0x18);
        if (which & kUnlockEpisodes) flags = (flags | kCourseOpen) & ~kCourseLock;
        if (which & kClearCourses) flags = (flags | kCourseOpen | kCourseClear) & ~(kCourseLock | kCourseNew);
        if (which & kAllGems) gems |= (1u << course.gems) - 1;
        if ((which & kAllBonus) && course.bonus) flags |= kCourseBonusDone;
        if ((which & kAllPixelToads) && course.gems) flags |= kCoursePixelToad;
        if ((which & kAllTimes) && course.challenge_time) {
            const int32_t best = int32_t(rd32(b, r + 8));
            if (best < 0 || uint32_t(best) > course.challenge_time) wr32(b, r + 8, course.challenge_time);
        }
        if ((which & kComplete) && course.gems) flags |= kCourseComplete;
        wr32(b, r, flags);
        wr32(b, r + 0x18, gems);
    }
    wr32(b, 0, crc32(b.data() + 4, b.size() - 4));
    return true;
}

// ---------------------------------------------------------------- StageList.byml (BYML version 2)
namespace byml_detail {
inline uint32_t u24(const Bytes& d, size_t o) { return uint32_t(d[o]) << 16 | uint32_t(d[o + 1]) << 8 | d[o + 2]; }
struct Reader {
    const Bytes& d;
    std::vector<std::string> keys, strings;
    bool ok = true;
    bool in(size_t o, size_t n) const { return o + n <= d.size(); }
    std::vector<std::string> table(uint32_t off) {
        std::vector<std::string> out;
        if (!off || !in(off, 4) || d[off] != 0xC2) return out;
        const uint32_t n = u24(d, off + 1);
        for (uint32_t i = 0; i < n && in(off + 4 + 4 * i, 4); i++) {
            const size_t s = off + rd32(d, off + 4 + 4 * i);
            size_t e = s;
            while (e < d.size() && d[e]) e++;
            out.emplace_back((const char*)d.data() + s, e - s);
        }
        return out;
    }
    // children of a hash node: (key, type, value)
    template <class F> void hash(uint32_t off, F f) {
        if (!in(off, 4) || d[off] != 0xC1) { ok = false; return; }
        for (uint32_t i = 0, n = u24(d, off + 1); i < n && in(off + 4 + 8 * i, 8); i++) {
            const size_t p = off + 4 + 8 * i;
            const uint32_t k = u24(d, p);
            if (k < keys.size()) f(keys[k], d[p + 3], rd32(d, p + 4));
        }
    }
    template <class F> void array(uint32_t off, F f) {
        if (!in(off, 4) || d[off] != 0xC0) { ok = false; return; }
        const uint32_t n = u24(d, off + 1);
        const size_t values = off + 4 + ((n + 3) & ~3u);
        for (uint32_t i = 0; i < n && in(values + 4 * i, 4); i++) f(d[off + 4 + i], rd32(d, values + 4 * i));
    }
};
}  // namespace byml_detail

// The courses of StageList.byml: SeasonList[].StageList[] with CourseId, CollectItemNum, ChallengeTime
// and BadgeCondition1 ("無し", Shift-JIS, when the course has no bonus objective).
inline Courses parse_stage_list(const Bytes& d, std::string& why) {
    using namespace byml_detail;
    Courses out;
    if (d.size() < 16 || d[0] != 'B' || d[1] != 'Y') { why = "StageList is not BYML"; return out; }
    Reader r{d, {}, {}};
    r.keys = r.table(rd32(d, 4));
    r.strings = r.table(rd32(d, 8));
    static const std::string kNone("\x96\xB3\x82\xB5", 4);
    r.hash(rd32(d, 12), [&](const std::string& key, uint8_t type, uint32_t seasons) {
        if (key != "SeasonList" || type != 0xC0) return;
        r.array(seasons, [&](uint8_t, uint32_t season) {
            r.hash(season, [&](const std::string& key, uint8_t type, uint32_t stages) {
                if (key != "StageList" || type != 0xC0) return;
                r.array(stages, [&](uint8_t, uint32_t stage) {
                    uint32_t id = 0;
                    Course c;
                    r.hash(stage, [&](const std::string& key, uint8_t type, uint32_t v) {
                        if (key == "CourseId") id = v;
                        else if (key == "CollectItemNum") c.gems = v < 32 ? v : 0;
                        else if (key == "ChallengeTime") c.challenge_time = v;
                        else if (key == "BadgeCondition1" && type == 0xA0) c.bonus = v < r.strings.size() && r.strings[v] != kNone;
                    });
                    if (id) out[id] = c;
                });
            });
        });
    });
    if (!r.ok || out.empty()) why = "StageList has no courses";
    return out;
}

}  // namespace ct_save
