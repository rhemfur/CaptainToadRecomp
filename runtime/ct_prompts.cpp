// PlayStation button prompts for Captain Toad (Settings > Controls > Button prompts, as in the
// reference). The game draws its A/B/X/Y prompts, in text and on the episode book, with the glyphs
// U+E000..U+E003 of MessageFont38.bffnt in LocalizedData/<language>/LayoutData/FontData.szs: a disc with
// a ring and the letter, two grey levels that the text colours tint. In the PlayStation style the game
// reads a copy of that archive whose four glyphs show the cross, circle, square and triangle of the
// button each Wii U button is bound to, drawn here as plain geometry (button_glyph_art.h): no artwork
// is shipped, the copy is made from the player's own file into the user folder. The Xbox style keeps
// the letters (its colours do not fit a one-channel font), and the font is read once, at start.
// Built only into the full reference runtime (CT_EXTRA_SOURCES); hle/fs.cpp read_path asks font_for.
#include "cemu_shim.h"  // the vendored Cemu headers' base types, as the GX2 sources get them

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <mutex>
#include <string>
#include <vector>

#include "Cafe/HW/Latte/LatteAddrLib/LatteAddrLib.h"
#include "button_glyph_art.h"
#include "input_map.h"
#include "mods/item_icons.h"
#include "mods/lyt_build.h"
#include "platform/host.h"
#include "runtime.h"

namespace ct_prompts {
namespace {
using Bytes = std::vector<uint8_t>;

uint32_t be16(const uint8_t* p) { return uint32_t(p[0]) << 8 | p[1]; }
uint32_t be32(const uint8_t* p) { return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3]; }

// ---------------------------------------------------------------- BC4 blocks
void bc4_decode(const uint8_t* b, uint8_t out[16]) {
    const uint8_t r0 = b[0], r1 = b[1];
    uint8_t pal[8] = {r0, r1};
    if (r0 > r1) for (int i = 1; i < 7; i++) pal[i + 1] = uint8_t(((7 - i) * r0 + i * r1) / 7);
    else { for (int i = 1; i < 5; i++) pal[i + 1] = uint8_t(((5 - i) * r0 + i * r1) / 5); pal[6] = 0; pal[7] = 255; }
    uint64_t bits = 0;
    for (int i = 0; i < 6; i++) bits |= uint64_t(b[2 + i]) << (8 * i);
    for (int i = 0; i < 16; i++) out[i] = pal[(bits >> (3 * i)) & 7];
}
void bc4_encode(const uint8_t in[16], uint8_t* b) {
    uint8_t lo = 255, hi = 0;
    for (int i = 0; i < 16; i++) { lo = std::min(lo, in[i]); hi = std::max(hi, in[i]); }
    if (hi == lo) { b[0] = hi; b[1] = lo; std::memset(b + 2, 0, 6); return; }
    uint8_t pal[8] = {hi, lo};  // eight-value mode: r0 > r1
    for (int i = 1; i < 7; i++) pal[i + 1] = uint8_t(((7 - i) * hi + i * lo) / 7);
    uint64_t bits = 0;
    for (int i = 0; i < 16; i++) {
        int best = 0;
        for (int k = 1; k < 8; k++) if (std::abs(pal[k] - in[i]) < std::abs(pal[best] - in[i])) best = k;
        bits |= uint64_t(best) << (3 * i);
    }
    b[0] = hi; b[1] = lo;
    for (int i = 0; i < 6; i++) b[2 + i] = uint8_t(bits >> (8 * i));
}

// ---------------------------------------------------------------- the font
struct Sheet {  // one BC4 sheet, GX2 2D tiled (thin1), glyph rows stored bottom up
    uint8_t* data;
    uint32_t width, height;
    uint32_t addr(uint32_t bx, uint32_t by) const {
        return LatteAddrLib::ComputeSurfaceAddrFromCoordMacroTiled(bx, by, 0, 0, 64, width / 4, height / 4, 1,
                                                                   Latte::E_HWTILEMODE::TM_2D_TILED_THIN1, false, 0, 0);
    }
    // pixels with y counted from the top of the glyph grid
    uint8_t get(uint32_t x, uint32_t y) const {
        const uint32_t sy = height - 1 - y;
        uint8_t px[16];
        bc4_decode(data + addr(x / 4, sy / 4), px);
        return px[(sy % 4) * 4 + x % 4];
    }
};

// Redraws one disc glyph (cell at x0, y0, size w x h) with PlayStation shape `shape` (button_glyphs order:
// 0 cross, 1 circle, 2 square, 3 triangle); the ring and the disc stay the game's.
void redraw(Sheet& s, uint32_t x0, uint32_t y0, uint32_t w, uint32_t h, int shape) {
    std::vector<uint8_t> px(w * h);
    for (uint32_t y = 0; y < h; y++) for (uint32_t x = 0; x < w; x++) px[y * w + x] = s.get(x0 + x, y0 + y);
    // the ring: the bounding box of the bright pixels gives the centre and the outer radius
    int minx = w, maxx = -1, miny = h, maxy = -1;
    for (uint32_t y = 0; y < h; y++) for (uint32_t x = 0; x < w; x++)
        if (px[y * w + x] >= 200) { minx = std::min<int>(minx, x); maxx = std::max<int>(maxx, x); miny = std::min<int>(miny, y); maxy = std::max<int>(maxy, y); }
    if (maxx < 0) return;
    const float cx = (minx + maxx) / 2.0f, cy = (miny + maxy) / 2.0f, outer = (maxx - minx + maxy - miny) / 4.0f;
    // ring thickness: bright run inwards from the outer edge, the median over 24 directions
    std::vector<float> runs;
    for (int k = 0; k < 24; k++) {
        const float a = k * float(M_PI) / 12, dx = std::cos(a), dy = std::sin(a);
        float r = outer + 0.5f;
        while (r > 1) {
            const int x = int(std::lround(cx + dx * r)), y = int(std::lround(cy + dy * r));
            if (x >= 0 && y >= 0 && x < int(w) && y < int(h) && px[y * w + x] >= 200) break;
            r -= 0.5f;
        }
        const float edge = r;
        while (r > 1) {
            const int x = int(std::lround(cx + dx * r)), y = int(std::lround(cy + dy * r));
            if (x < 0 || y < 0 || x >= int(w) || y >= int(h) || px[y * w + x] < 200) break;
            r -= 0.5f;
        }
        runs.push_back(edge - r);
    }
    std::sort(runs.begin(), runs.end());
    const float inner = outer - runs[runs.size() / 2] - 0.5f;
    // the disc's own level, just inside the ring
    std::vector<uint8_t> fills;
    for (uint32_t y = 0; y < h; y++) for (uint32_t x = 0; x < w; x++) {
        const float d = std::hypot(x - cx, y - cy);
        if (d > inner - 2.5f && d < inner - 0.5f && px[y * w + x] < 200 && px[y * w + x] > 40) fills.push_back(px[y * w + x]);
    }
    if (fills.empty()) return;
    std::sort(fills.begin(), fills.end());
    const float fill = fills[fills.size() / 2], ink = 255;
    // the shape, sized like the reference's dialog disc (half-size 0.55 and stroke 0.22 of the disc)
    const float size = inner * 0.55f, stroke = inner * 0.22f;
    constexpr int kSamples = 4;
    for (uint32_t y = 0; y < h; y++) for (uint32_t x = 0; x < w; x++) {
        if (std::hypot(x + 0.5f - cx, y + 0.5f - cy) > inner - 0.5f) continue;
        int covered = 0;
        for (int sy = 0; sy < kSamples; sy++) for (int sx = 0; sx < kSamples; sx++) {
            const float px_ = x + (sx + 0.5f) / kSamples - cx, py_ = y + (sy + 0.5f) / kSamples - cy;
            if (button_glyphs::art::shape_distance(shape, px_, py_, size) <= stroke * 0.5f) covered++;
        }
        px[y * w + x] = uint8_t(std::lround(fill + (ink - fill) * covered / float(kSamples * kSamples)));
    }
    // write back the blocks the cell touches (cells do not share blocks with their glyph interiors;
    // blocks are decoded first so the neighbours' pixels are kept)
    const uint32_t sy0 = s.height - (y0 + h), sy1 = s.height - 1 - y0;
    for (uint32_t by = sy0 / 4; by <= sy1 / 4; by++) for (uint32_t bx = x0 / 4; bx <= (x0 + w - 1) / 4; bx++) {
        uint8_t* block = s.data + s.addr(bx, by);
        uint8_t v[16];
        bc4_decode(block, v);
        for (int i = 0; i < 16; i++) {
            const uint32_t x = bx * 4 + i % 4, sy = by * 4 + i / 4, y = s.height - 1 - sy;
            if (x >= x0 && x < x0 + w && y >= y0 && y < y0 + h) v[i] = px[(y - y0) * w + (x - x0)];
        }
        bc4_encode(v, block);
    }
}

// Patches U+E000..E003 of a BFFNT (version 3, Wii U) in place; false if it has no such glyphs.
bool patch_font(uint8_t* f, size_t size, const std::array<int, 4>& shapes) {
    if (size < 20 || std::memcmp(f, "FFNT", 4) || be16(f + 4) != 0xFEFF) return false;
    uint32_t tglp = 0;
    std::array<int, 4> glyph = {-1, -1, -1, -1};
    for (uint32_t p = be16(f + 6); p + 8 <= size;) {
        const uint32_t block = be32(f + p + 4);
        if (!std::memcmp(f + p, "TGLP", 4)) tglp = p;
        if (!std::memcmp(f + p, "CMAP", 4) && p + 20 <= size) {
            const uint32_t lo = be16(f + p + 8), hi = be16(f + p + 10), method = be16(f + p + 12), body = p + 20;
            for (int i = 0; i < 4; i++) {
                const uint32_t c = 0xE000 + i;
                if (method == 0 && c >= lo && c <= hi) glyph[i] = int(be16(f + body) + c - lo);
                else if (method == 1 && c >= lo && c <= hi && body + 2 * (c - lo) + 2 <= size) {
                    const uint32_t g = be16(f + body + 2 * (c - lo));
                    if (g != 0xFFFF) glyph[i] = int(g);
                } else if (method == 2) {
                    const uint32_t n = be16(f + body);
                    for (uint32_t k = 0; k < n && body + 6 + 4 * k <= size; k++)
                        if (be16(f + body + 2 + 4 * k) == c) glyph[i] = int(be16(f + body + 4 + 4 * k));
                }
            }
        }
        if (!block) break;
        p += block;
    }
    if (!tglp || glyph[0] < 0) return false;
    const uint8_t* t = f + tglp;
    const uint32_t cw = t[8], ch = t[9], sheets = t[10], sheet_size = be32(t + 12), format = be16(t + 18);
    const uint32_t cols = be16(t + 20), rows = be16(t + 22), sw = be16(t + 24), sh = be16(t + 26), data = be32(t + 28);
    if (format != 12 || sw * sh / 2 != sheet_size || uint64_t(data) + uint64_t(sheets) * sheet_size > size) return false;  // BC4 only
    for (int i = 0; i < 4; i++) {
        if (glyph[i] < 0) continue;
        const uint32_t g = uint32_t(glyph[i]), per_sheet = cols * rows, sheet = g / per_sheet, cell = g % per_sheet;
        if (sheet >= sheets) continue;
        Sheet s{f + data + sheet * sheet_size, sw, sh};
        redraw(s, (cell % cols) * (cw + 1) + 1, (cell / cols) * (ch + 1) + 1, cw, ch, shapes[i]);
    }
    return true;
}

// Patches every font of a SARC (big endian) in place; true if one changed.
bool patch_archive(Bytes& a, const std::array<int, 4>& shapes) {
    if (a.size() < 0x20 || std::memcmp(a.data(), "SARC", 4) || be16(&a[6]) != 0xFEFF) return false;
    const uint32_t data = be32(&a[0x0C]), nodes = be16(&a[0x1A]), names = 0x20 + 16 * nodes + 8;
    bool changed = false;
    for (uint32_t i = 0; i < nodes; i++) {
        const uint8_t* n = &a[0x20 + 16 * i];
        const uint32_t attr = be32(n + 4), start = be32(n + 8), end = be32(n + 12);
        const std::string name((const char*)&a[names + (attr & 0xFFFF) * 4]);
        if (name.size() < 6 || name.compare(name.size() - 6, 6, ".bffnt") || uint64_t(data) + end > a.size()) continue;
        changed |= patch_font(&a[data + start], end - start, shapes);
    }
    return changed;
}
}  // namespace

std::string font_for(const std::string& guest, const std::string& host_path) {
    static const std::string kName = "/LayoutData/FontData.szs";
    if (guest.size() < kName.size() || guest.compare(guest.size() - kName.size(), kName.size(), kName)) return {};
    const auto look = input_map::prompt_style(input_map::current(), input_map::pad_family());
    if (look.face != input_map::FaceStyle::kPlayStation) return {};
    // each Wii U button shows the shape of the host button bound to it (button_glyph_art.h order)
    std::array<int, 4> shapes;
    std::string key;
    for (int i = 0; i < 4; i++) { shapes[i] = look.buttons[i] & 3; key += char('0' + shapes[i]); }
    // the language folder names the copy (LocalizedData/<language>/LayoutData/FontData.szs)
    std::string language = guest.substr(0, guest.size() - kName.size());
    language = language.substr(language.find_last_of('/') + 1);
    const std::filesystem::path out = std::filesystem::path(host::config_dir()) / "prompts" / ("playstation-" + key) / language / "FontData.szs";
    static std::mutex mutex;
    std::lock_guard lock(mutex);
    std::error_code ec;
    if (std::filesystem::exists(out, ec)) return out.string();
    try {
        std::ifstream in(host_path, std::ios::binary);
        Bytes szs((std::istreambuf_iterator<char>(in)), {});
        if (szs.empty()) return {};
        Bytes archive = item_icons::yaz0_decode(szs);
        if (!patch_archive(archive, shapes)) return {};
        std::filesystem::create_directories(out.parent_path(), ec);
        const auto tmp = std::filesystem::path(out).concat(".tmp");
        Bytes packed = lyt_build::yaz0_store(archive);
        // the game aligns the unpacked archive as the Yaz0 header says (0x2000 here): the GPU reads
        // the font sheets in place, so they must keep the original alignment
        if (packed.size() >= 16 && szs.size() >= 16) std::copy(szs.begin() + 8, szs.begin() + 12, packed.begin() + 8);
        {
            std::ofstream o(tmp, std::ios::binary | std::ios::trunc);
            o.write((const char*)packed.data(), (std::streamsize)packed.size());
            if (!o) return {};
        }
        std::filesystem::rename(tmp, out, ec);
        if (ec) return {};
        LOG("[prompts] PlayStation shapes in %s (%s)", out.string().c_str(), key.c_str());
        return out.string();
    } catch (const std::exception& e) {
        LOG("[prompts] %s: %s", host_path.c_str(), e.what());
        return {};
    }
}

}  // namespace ct_prompts
