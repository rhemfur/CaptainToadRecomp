"""Captain Toad's exact-text changes to the reference runtime (tools/patch_runtime.py).

The settings overlay and the macOS and SDL host menus.
"""
from .common import _ct_end, _ct_only

REPLACEMENTS = {}
# Captain Toad cheats (runtime/cheats.cpp, runtime/ct_save.h) replace the Wind Waker HD ones: save edits
# applied with a restart, listed in the Gameplay menu and the settings overlay.
REPLACEMENTS['src/gfx/menu.mm'] = [
    ('#include "../mods/mods.h"\n', '#include "../mods/mods.h"\n#include "../mods/ct_save.h"\n#include <tuple>\n'),
    (('    [gp addItemWithTitle:@"Cheats (save in game to keep them)" action:nil keyEquivalent:@""].enabled = NO;\n'
         '    toggle(gp, @"    Give all items", ^BOOL { return NO; }, ^(BOOL) { mods::request_cheat(mods::kCheatItems); },\n'
         '           @"Every inventory item, light arrows, deluxe picto box, power bracelets, 4 bottles, 99 arrows and bombs");\n'
         '    toggle(gp, @"    Equip Master Sword and Mirror Shield (until reload)", ^BOOL { return NO; }, ^(BOOL) { mods::request_cheat(mods::kCheatSword); });\n'
         '    toggle(gp, @"    20 hearts, double magic, 5000 rupees", ^BOOL { return NO; }, ^(BOOL) { mods::request_cheat(mods::kCheatStats); },\n'
         '           @"Also refills hearts and magic");\n'
         '    toggle(gp, @"    Fill the bags (spoils and bait)", ^BOOL { return NO; }, ^(BOOL) { mods::request_cheat(mods::kCheatBags); },\n'
         '           @"Spoils bag and bait bag (if missing), every kind of spoils x99, empty bait slots filled");\n'
         '    for (auto [title, which] : {std::pair{@"    Infinite health", mods::kInfHealth}, {@"    Infinite magic", mods::kInfMagic},\n'
         '                                {@"    Infinite arrows and bombs", mods::kInfAmmo}, {@"    Infinite rupees", mods::kInfRupees},\n'
         '                                {@"    Infinite bait and spoils", mods::kInfBags}, {@"    Infinite swimming", mods::kInfBreath}}) {\n'
         '        int bit = which;  // (blocks cannot capture structured bindings)\n'
         '        toggle(gp, title, ^BOOL { return mods::infinite(bit); }, ^(BOOL on) { mods::set_infinite(bit, on); });\n'
         '    }\n'
         '    [gp addItem:[NSMenuItem separatorItem]];\n'
         '    NSString* story = @"Can change or break story events: the game may skip or repeat scenes that teach or check this. "\n'
         '                      @"Save to a different file first.";\n'
         '    [gp addItemWithTitle:@"⚠️ Story cheats (can break story events; use a spare save file)" action:nil keyEquivalent:@""].enabled = NO;\n'
         '    toggle(gp, @"    All songs", ^BOOL { return NO; }, ^(BOOL) { mods::request_cheat(mods::kCheatSongs); }, story);\n'
         '    toggle(gp, @"    All Triforce shards", ^BOOL { return NO; }, ^(BOOL) { mods::request_cheat(mods::kCheatTriforce); }, story);\n'
         '    toggle(gp, @"    Map, compass and boss key (this dungeon)", ^BOOL { return NO; }, ^(BOOL) { mods::request_cheat(mods::kCheatDungeon); }, story);\n'
         '    toggle(gp, @"    Add a small key (this dungeon)", ^BOOL { return NO; }, ^(BOOL) { mods::request_cheat(mods::kCheatKey); }, story);\n'),
     ('    [gp addItemWithTitle:@"Cheats (the game restarts; play since its last save is lost)" action:nil keyEquivalent:@""].enabled = NO;\n'
         '    for (auto [title, which, tip] : {\n'
         '             std::tuple{@"    Unlock every episode and course", (int)ct_save::kUnlockEpisodes, @"Episodes 2 and 3, the bonus episode and every course page"},\n'
         '             {@"    Clear every course", (int)ct_save::kClearCourses, @"Every course counts as cleared, with the ending seen; the episodes open"},\n'
         '             {@"    Every Super Gem", (int)ct_save::kAllGems, @"All 192 Super Gems"},\n'
         '             {@"    Every bonus objective", (int)ct_save::kAllBonus, @"The second Toad Stamp\'s task in every course that has one"},\n'
         '             {@"    Every challenge time", (int)ct_save::kAllTimes, @"Each course\'s best time set to its challenge time unless it is already faster"},\n'
         '             {@"    Every Pixel Toad", (int)ct_save::kAllPixelToads, @"Pixel Toad found in every course that hides one: the golden Pixel Toad on each episode"},\n'
         '             {@"    100% completion", (int)ct_save::kComplete, @"All of the above, every course 100%, Coins Galore and Mummy-Me Maze Forever: every Toad Stamp with glittering stars"}}) {\n'
         '        int bit = which;  // (blocks cannot capture structured bindings)\n'
         '        toggle(gp, title, ^BOOL { return NO; }, ^(BOOL) { mods::request_cheat(bit); }, tip);\n'
         '    }\n')),
]
REPLACEMENTS['src/overlay/overlay.cpp'] = [
    ('#include "../mods/mods.h"\n', '#include "../mods/mods.h"\n#include "../mods/ct_save.h"\n#include "../ct_touch_menu.h"\n'),
    (('void cheats() {\n'
         '    bool v;\n'
         '    note("Save in the game to keep them.");\n'
         '    auto cheat = [first = true](const char* label, int which) mutable {\n'
         '        if (!first) modsui::same_line_if_fits(label);\n'
         '        first = false;\n'
         '        if (ImGui::Button(label)) mods::request_cheat(which);\n'
         '    };\n'
         '    cheat("Give all items", mods::kCheatItems);\n'
         '    cheat("Equip Master Sword + Mirror Shield (until reload)", mods::kCheatSword);\n'
         '    cheat("20 hearts, double magic, 5000 rupees", mods::kCheatStats);\n'
         '    cheat("Fill the bags (spoils and bait)", mods::kCheatBags);\n'
         '    static const std::pair<const char*, int> inf[] = {{"Infinite health", mods::kInfHealth}, {"Infinite magic", mods::kInfMagic},\n'
         '                                                      {"Infinite arrows and bombs", mods::kInfAmmo},\n'
         '                                                      {"Infinite rupees", mods::kInfRupees},\n'
         '                                                      {"Infinite bait and spoils", mods::kInfBags},\n'
         '                                                      {"Infinite swimming", mods::kInfBreath},\n'
         '                                                      {"Moon jump (hold L; left stick steers)", mods::kMoonJump},\n'
         '                                                      {"No fall damage after moon jump", mods::kMoonNoFall}};\n'
         '    for (const auto& [label, which] : inf) {\n'
         '        int bit = which;\n'
         '        if (check(label, mods::infinite(bit), &v)) hostui::post([bit, v] { mods::set_infinite(bit, v); });\n'
         '    }\n'
         '    heading("Story cheats (can break story events; use a spare save file)");\n'
         '    auto story = [first = true](const char* label, int which) mutable {\n'
         '        if (!first) modsui::same_line_if_fits(label);\n'
         '        first = false;\n'
         '        if (ImGui::Button(label)) mods::request_cheat(which);\n'
         '    };\n'
         '    story("All songs", mods::kCheatSongs);\n'
         '    story("All Triforce shards", mods::kCheatTriforce);\n'
         '    story("Map, compass, boss key", mods::kCheatDungeon);\n'
         '    story("Small key", mods::kCheatKey);\n'
         '}\n'),
     ('void cheats() {\n'
         '#ifdef __ANDROID__\n'
         '    note("Each cheat changes the save and closes the game: open it again to play with it. Play since the game "\n'
         '         "last saved is lost. The save before the first cheat is kept as GameData.bin.before-cheats.");\n'
         '#else\n'
         '    note("Each cheat changes the save and restarts the game: play since the game last saved is lost. "\n'
         '         "The save before the first cheat is kept as GameData.bin.before-cheats.");\n'
         '#endif\n'
         '    auto cheat = [first = true](const char* label, int which) mutable {\n'
         '        if (!first) modsui::same_line_if_fits(label);\n'
         '        first = false;\n'
         '        if (ImGui::Button(label)) mods::request_cheat(which);\n'
         '    };\n'
         '    cheat("Unlock every episode and course", ct_save::kUnlockEpisodes);\n'
         '    cheat("Clear every course", ct_save::kClearCourses);\n'
         '    cheat("Every Super Gem", ct_save::kAllGems);\n'
         '    cheat("Every bonus objective", ct_save::kAllBonus);\n'
         '    cheat("Every challenge time", ct_save::kAllTimes);\n'
         '    cheat("Every Pixel Toad", ct_save::kAllPixelToads);\n'
         '    heading("Everything");\n'
         '    cheat("100% completion (every Toad Stamp, glittering stars, golden Pixel Toads)", ct_save::kComplete);\n'
         '}\n')),
]
REPLACEMENTS['src/overlay/overlay.cpp'] += [
    ('    heading("Frame rate");\n', _ct_only + '    heading("Frame rate");\n'),
    ('    // debug only, not saved (gx2::uncapped)\n', _ct_end + '    // debug only, not saved (gx2::uncapped)\n'),
    ('    float fovPercent=aspect::fov_scale()*100.0f;\n', _ct_only + '    float fovPercent=aspect::fov_scale()*100.0f;\n'),
    ('            post_changed([i] { aspect::set_mode(i); hostui::set("aspectMode", std::to_string(i)); });\n    }\n',
     '            post_changed([i] { aspect::set_mode(i); hostui::set("aspectMode", std::to_string(i)); });\n    }\n' + _ct_end),
    ('    float bloom = render::bloom_strength() * 100.0f;\n', _ct_only + '    float bloom = render::bloom_strength() * 100.0f;\n'),
    ('        post_changed([v] { render::set_ao_hires(v); });\n', '        post_changed([v] { render::set_ao_hires(v); });\n' + _ct_end),
]
REPLACEMENTS['src/overlay/mods_tab.h'] = [
    ('    int area = kBuiltin;     // remembered for the session (State lives as long as the game runs)\n',
     '#ifdef CT_FOREIGN_GUEST\n    int area = kCommunity;   // Captain Toad: no built-in mods\n#else\n'
     '    int area = kBuiltin;     // remembered for the session (State lives as long as the game runs)\n#endif\n'),
    ('            if (ImGui::BeginTabItem(kAreaNames[i], nullptr, f)) {\n',
     '#ifdef CT_FOREIGN_GUEST\n            if (i == kBuiltin) continue;  // Wind Waker HD\'s built-in mods\n#endif\n'
     '            if (ImGui::BeginTabItem(kAreaNames[i], nullptr, f)) {\n'),
    ('    if (h.file_picker && section("GameCube game for mods")) {',
     '    if (h.file_picker && !kCaptainToad && section("GameCube game for mods")) {'),
    ('    if (section("Save backups")) {\n', '    if (!kCaptainToad && section("Save backups")) {\n'),
    ('enum Area { kBuiltin, kCommunity, kMore, kAreas };\n',
     'enum Area { kBuiltin, kCommunity, kMore, kAreas };\n'
     '#ifdef CT_FOREIGN_GUEST\ninline constexpr bool kCaptainToad = true;  // CaptainToadRecomp: Wind Waker HD sections left out\n#else\n'
     'inline constexpr bool kCaptainToad = false;\n#endif\n'),
    ('inline const char* const kAreaNames[kAreas] = {"Built-in", "Community", "More"};\n',
     '#ifdef CT_FOREIGN_GUEST\ninline const char* const kAreaNames[kAreas] = {"Built-in", "Installed", "More"};\n#else\n'
     'inline const char* const kAreaNames[kAreas] = {"Built-in", "Community", "More"};\n#endif\n'),
]
REPLACEMENTS['src/overlay/overlay.cpp'] += [
    ('        h.code_mods = ext::features().code_mods;\n        h.mod_downloads = ext::features().mod_downloads;\n',
     '#ifdef CT_FOREIGN_GUEST  // no Wind Waker HD catalogue or code mods\n        h.code_mods = false;\n        h.mod_downloads = false;\n#else\n'
     '        h.code_mods = ext::features().code_mods;\n        h.mod_downloads = ext::features().mod_downloads;\n#endif\n'),
]
REPLACEMENTS['src/gfx/menu.mm'] += [
    ('    [g addItemWithTitle:@"Aspect ratio" action:nil keyEquivalent:@""].enabled = NO;\n',
     _ct_only + '    [g addItemWithTitle:@"Aspect ratio" action:nil keyEquivalent:@""].enabled = NO;\n'),
    ('    add(g, @"16x anisotropic filtering (N)", @selector(toggleAniso:), @"N");\n',
     _ct_end + '    add(g, @"16x anisotropic filtering (N)", @selector(toggleAniso:), @"N");\n'),
    ('    add(g, @"40 fps: frame interpolation (for 40, 80 and 120 Hz screens)", @selector(toggleInterpFps:), @"", 40);\n',
     _ct_only + '    add(g, @"40 fps: frame interpolation (for 40, 80 and 120 Hz screens)", @selector(toggleInterpFps:), @"", 40);\n'),
    ('    add(g, @"60 fps: true 60, game logic at 60 steps/s (7, experimental)", @selector(toggleInterp:), @"7", 2);\n',
     '    add(g, @"60 fps: true 60, game logic at 60 steps/s (7, experimental)", @selector(toggleInterp:), @"7", 2);\n' + _ct_end),
    ('    toggle(gp, @"Enable code mods (PowerPC mods)"', _ct_only + '    toggle(gp, @"Enable code mods (PowerPC mods)"'),
    ('    [gp addItem:[NSMenuItem separatorItem]];\n    [gp addItemWithTitle:@"Cheats (',
     '    [gp addItem:[NSMenuItem separatorItem]];\n' + _ct_end + '    [gp addItemWithTitle:@"Cheats ('),
]
REPLACEMENTS['src/gfx/menu.mm'] += [
    # -1: nothing chosen in the menu yet (0 is the Screen resolution)
    ('static float g_res_shown = 0;  // last value set from the UI (res_scale() lags a frame)\n'
     'static float current_res_scale() { return g_res_shown ? g_res_shown : render::res_scale(); }\n',
     '#ifdef CT_FOREIGN_GUEST\n'
     'static float g_res_shown = -1;  // last value set from the UI (res_scale() lags a frame); 0: Screen\n'
     'static float current_res_scale() { return g_res_shown >= 0 ? g_res_shown : render::res_scale(); }\n'
     '#else\n'
     'static float g_res_shown = 0;  // last value set from the UI (res_scale() lags a frame)\n'
     'static float current_res_scale() { return g_res_shown ? g_res_shown : render::res_scale(); }\n'
     '#endif  // Captain Toad screen resolution\n'),
    ('    NSString* res = current_res_scale() != 1.0f ? [NSString stringWithFormat:@" \\u00b7 %gx res", current_res_scale()] : @"";\n',
     '    NSString* res = current_res_scale() != 1.0f ? [NSString stringWithFormat:@" \\u00b7 %gx res", current_res_scale()] : @"";\n'
     '    if (current_res_scale() == 0) res = @" \\u00b7 screen res";  // Captain Toad screen resolution\n'),
    ('- (void)setRes:(NSMenuItem*)item { set_res(kResScales[item.tag]); update_title(); }\n',
     '- (void)setRes:(NSMenuItem*)item { set_res(kResScales[item.tag]); update_title(); }\n'
     '- (void)setResScreen:(NSMenuItem*)item { set_res(0); update_title(); }  // Captain Toad screen resolution\n'),
    ('    if (item.action == @selector(setRes:))\n',
     '    if (item.action == @selector(setResScreen:))\n'
     '        item.state = current_res_scale() == 0 ? NSControlStateValueOn : NSControlStateValueOff;\n'
     '    if (item.action == @selector(setRes:))\n'),
    ('    add(g, @"    3x (3840x2160)", @selector(setRes:), @"R", 3);\n',
     '    add(g, @"    3x (3840x2160)", @selector(setRes:), @"R", 3);\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    add(g, @"    Screen (the window\'s pixels)", @selector(setResScreen:), @"", 0).toolTip =\n'
     '        @"As many pixels as the picture covers in the window, up to 4x: GamePad only on a 4K screen draws at 4x";\n'
     '#endif  // Captain Toad screen resolution\n'),
]
# Settings > Display holds everything about the picture: the view and, for Captain Toad, its shape
# (aspect.cpp, runtime/ct_frame.cpp), which Wind Waker HD keeps under Graphics.
REPLACEMENTS['src/overlay/overlay.cpp'] += [
    ('        static const char* const modes[] = {"Separate window", "Picture-in-picture", "Automatic picture-in-picture", "Off", "GamePad only"};\n',
     '#ifdef CT_FOREIGN_GUEST\n'
     '        static const char* const modes[] = {"Separate window", "Picture-in-picture", "Automatic picture-in-picture", "TV only", "GamePad only"};\n'
     '#else\n'
     '        static const char* const modes[] = {"Separate window", "Picture-in-picture", "Automatic picture-in-picture", "Off", "GamePad only"};\n'
     '#endif\n'),
    ('        if (mode == 4)\n            note("Only the GamePad picture. In the game, Minus switches to Off-TV "\n'
     '                 "Play (the game on the GamePad).");\n    }\n',
     '        if (mode == 4)\n            note("Only the GamePad picture. In the game, Minus switches to Off-TV "\n'
     '                 "Play (the game on the GamePad).");\n    }\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    {  // Captain Toad: the TV picture\'s shape (aspect.cpp, runtime/ct_frame.cpp)\n'
     '        int shape = aspect::mode();\n'
     '        if (shape <= aspect::k32x9 &&\n'
     '#ifdef __ANDROID__\n'
     '            combo("Picture shape", &shape, "16:9 (original)\\0Match screen\\0" "16:10\\0" "21:9\\0" "32:9\\0"))\n'
     '#else\n'
     '            combo("Picture shape", &shape, "16:9 (original)\\0Match window\\0" "16:10\\0" "21:9\\0" "32:9\\0"))\n'
     '#endif\n'
     '            post_changed([shape] { aspect::set_mode(shape); hostui::set("aspectMode", std::to_string(shape)); });\n'
     '        help("The TV picture\'s shape. Wider shapes show more of the course at the sides; nothing is stretched.\\n"\n'
     '             "Match fills the screen (or window). The camera takes a new shape when the next course\\n"\n'
     '             "starts. The GamePad picture takes the same shape; touches reach its middle 16:9.");\n'
     '    }\n'
     '#endif  // Captain Toad picture shape\n'),
    ('        if (radio(names[i], std::fabs(cur - s) < 0.01f)) post_changed([s] { hostui::set_res_scale(s); });\n    }\n',
     '        if (radio(names[i], std::fabs(cur - s) < 0.01f)) post_changed([s] { hostui::set_res_scale(s); });\n    }\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    {  // 0 follows the window (gfx/metal_surfaces.mm, gfx/vulkan/surfaces.cpp)\n'
     '        flow::next(flow::check("Screen"));\n'
     '        if (radio("Screen", cur == 0)) post_changed([] { hostui::set_res_scale(0); });\n'
     '        help("Screen draws the game at the resolution of your screen, or of the game\'s window: as many pixels\\n"\n'
     '             "as the picture covers, up to 4x.");\n'
     '    }\n'
     '#endif  // Captain Toad screen resolution\n'),
    ('        ImGui::TextDisabled("%s  %gx  %s", render::api_name(render::active()), hostui::res_scale(), interp::mode_name());\n',
     '        if (hostui::res_scale() == 0)  // Captain Toad: the screen\'s resolution\n'
     '            ImGui::TextDisabled("%s  screen  %s", render::api_name(render::active()), interp::mode_name());\n'
     '        else\n'
     '        ImGui::TextDisabled("%s  %gx  %s", render::api_name(render::active()), hostui::res_scale(), interp::mode_name());\n'),
    # Window sizes (desktop): the TV window with this many pixels inside, those that fit its screen
    ('                                           : "The TV window (F11 or Alt+Enter); remembered for the next start");\n#endif\n',
     '                                           : "The TV window (F11 or Alt+Enter); remembered for the next start");\n#endif\n'
     '#ifndef __ANDROID__\n'
     '    {  // Captain Toad: window sizes (CaptainToadRecomp tools/patch_runtime.py)\n'
     '        static const int sizes[][2] = {{1280, 720}, {1600, 900}, {1920, 1080}, {2560, 1440}, {3840, 2160}};\n'
     '        int ww = 0, wh = 0;\n'
     '        hostui::window_size(ww, wh);\n'
     '        const bool windowed = !hostui::fullscreen();\n'
     '        ImGui::TextUnformatted("Window size");\n'
     '        bool first = true;\n'
     '        for (const auto& size : sizes) {\n'
     '            const int w = size[0], h = size[1];\n'
     '            if (!hostui::window_size_fits(w, h)) continue;\n'
     '            char label[32];\n'
     '            snprintf(label, sizeof label, "%dx%d##windowSize", w, h);\n'
     '            if (!first) flow::next(flow::check(label));\n'
     '            first = false;\n'
     '            if (radio(label, ww == w && wh == h, windowed)) hostui::post([w, h] { hostui::set_window_size(w, h); });\n'
     '        }\n'
     '        help(windowed ? "The game\'s window, in pixels inside it: the sizes that fit this screen. Drag the window\'s\\n"\n'
     '                        "edge for any other size."\n'
     '                      : "Leave full screen to choose a window size.");\n'
     '    }\n'
     '#endif  // Captain Toad window sizes\n'
     '#if defined(__ANDROID__) && defined(CT_FOREIGN_GUEST)\n'
     '    {  // Captain Toad: a punch-hole or notch camera (runtime/ct_touch_menu.cpp, WwhdActivity.java)\n'
     '        int cutout = ct_touch::cutout_clear() ? 1 : 0;\n'
     '        if (combo("Camera cutout", &cutout, "Use the area\\0Keep clear (black bar)\\0"))\n'
     '            hostui::post([cutout] { ct_touch::set_cutout_clear(cutout != 0); });\n'
     '        help("For phones with a punch-hole or notch camera at the edge of the screen. Use the area draws up to\\n"\n'
     '             "the edge, around the camera; Keep clear leaves a black bar along the camera\'s edge. Full screen only.");\n'
     '    }\n'
     '#endif  // Captain Toad camera cutout\n'),
    # Android: how opaque the on-screen controls are (runtime/ct_touch_menu.cpp)
    ('            hostui::set("touchControls", v ? "1" : "0");\n        });\n#endif\n',
     '            hostui::set("touchControls", v ? "1" : "0");\n        });\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    pip_percent("Controls opacity (%)", ct_touch::opacity(), ct_touch::kOpacityMin, 1.0f, ct_touch::set_opacity);\n'
     '    help("How opaque the on-screen controls are drawn.");\n'
     '#endif  // Captain Toad touch controls opacity\n'
     '#endif\n'),
]
REPLACEMENTS['src/overlay/hostui.h'] = [
    ('void set_fullscreen(bool on);\n',
     'void set_fullscreen(bool on);\n'
     '// Captain Toad (CaptainToadRecomp tools/patch_runtime.py): the TV window\'s size in pixels inside it, for\n'
     '// Settings > Display > Window size on desktop hosts\n'
     'void window_size(int& w, int& h);      // 0x0 when unknown\n'
     'bool window_size_fits(int w, int h);   // a window with this many pixels inside fits the TV window\'s screen\n'
     'void set_window_size(int w, int h);    // main thread; in a window only (full screen: nothing changes)\n'),
]
REPLACEMENTS['src/gfx/vulkan/overlay_sdl.cpp'] = [
    ('bool fullscreen() { return gfxvk::R.tv.window && (SDL_GetWindowFlags(gfxvk::R.tv.window) & SDL_WINDOW_FULLSCREEN); }\n',
     'bool fullscreen() { return gfxvk::R.tv.window && (SDL_GetWindowFlags(gfxvk::R.tv.window) & SDL_WINDOW_FULLSCREEN); }\n'
     '// Captain Toad window sizes: SDL sizes windows in its own units, the menu in pixels\n'
     'void window_size(int& w, int& h) {\n'
     '    w = h = 0;\n'
     '    if (SDL_Window* win = gfxvk::R.tv.window) SDL_GetWindowSizeInPixels(win, &w, &h);\n'
     '}\n'
     'bool window_size_fits(int w, int h) {\n'
     '    SDL_Window* win = gfxvk::R.tv.window;\n'
     '    SDL_Rect r{};\n'
     '    if (!win || !SDL_GetDisplayUsableBounds(SDL_GetDisplayForWindow(win), &r)) return false;\n'
     '    const float density = std::max(SDL_GetWindowPixelDensity(win), 0.1f);\n'
     '    return w / density <= r.w && h / density <= r.h;\n'
     '}\n'
     'void set_window_size(int w, int h) {\n'
     '    SDL_Window* win = gfxvk::R.tv.window;\n'
     '    if (!win || fullscreen()) return;\n'
     '    const float density = std::max(SDL_GetWindowPixelDensity(win), 0.1f);\n'
     '    if (!SDL_SetWindowSize(win, int(w / density + 0.5f), int(h / density + 0.5f)))\n'
     '        LOG("[display] TV window: size %dx%d failed: %s", w, h, SDL_GetError());\n'
     '    else\n'
     '        LOG("[display] TV window: %dx%d pixels inside", w, h);\n'
     '}\n'),
]
REPLACEMENTS['src/gfx/overlay_appkit.mm'] = [
    ('void set_fullscreen(bool on) { gfx::display_set_tv_fullscreen(on); }\n',
     'void set_fullscreen(bool on) { gfx::display_set_tv_fullscreen(on); }\n'
     '// Captain Toad window sizes: AppKit sizes windows in points, the menu in pixels\n'
     'void window_size(int& w, int& h) {\n'
     '    w = h = 0;\n'
     '    NSWindow* win = (__bridge NSWindow*)gfx::display_tv_window();\n'
     '    if (!win) return;\n'
     '    const NSRect r = [win convertRectToBacking:[win contentRectForFrameRect:win.frame]];\n'
     '    w = int(r.size.width + 0.5);\n'
     '    h = int(r.size.height + 0.5);\n'
     '}\n'
     'bool window_size_fits(int w, int h) {\n'
     '    NSWindow* win = (__bridge NSWindow*)gfx::display_tv_window();\n'
     '    NSScreen* screen = win.screen ?: NSScreen.mainScreen;\n'
     '    if (!win || !screen) return false;\n'
     '    const CGFloat scale = screen.backingScaleFactor;\n'
     '    const NSSize frame = [win frameRectForContentRect:NSMakeRect(0, 0, w / scale, h / scale)].size;\n'
     '    return frame.width <= screen.visibleFrame.size.width && frame.height <= screen.visibleFrame.size.height;\n'
     '}\n'
     'void set_window_size(int w, int h) {\n'
     '    NSWindow* win = (__bridge NSWindow*)gfx::display_tv_window();\n'
     '    if (!win || gfx::tv_fullscreen()) return;\n'
     '    const CGFloat scale = win.backingScaleFactor;\n'
     '    // the top left corner stays where it is, unless the window would leave the screen\n'
     '    NSRect frame = [win frameRectForContentRect:NSMakeRect(0, 0, w / scale, h / scale)];\n'
     '    frame.origin = NSMakePoint(NSMinX(win.frame), NSMaxY(win.frame) - frame.size.height);\n'
     '    [win setFrame:[win constrainFrameRect:frame toScreen:win.screen] display:YES];\n'
     '    LOG("[display] TV window: %dx%d pixels inside", w, h);\n'
     '}\n'),
]
REPLACEMENTS['src/overlay/gyro_popup.h'] = [
    ('    note("On the Wii U you aim in first person (bow, hookshot, boomerang, telescope, Picto Box, grappling hook) by "\n'
     '         "moving the GamePad. This works with the GamePad and the Pro Controller choice alike. The game\'s own "\n'
     '         "Options > Gyro switch still decides whether it uses the motion, and it ignores the motion while the right "\n'
     '         "stick is pushed.");\n',
     '#ifdef CT_FOREIGN_GUEST\n'
     '    note("Captain Toad reads the Wii U GamePad\'s motion: moving the GamePad turns the camera where the game "\n'
     '         "allows it, such as the first-person views. Controller gyro takes that motion from a controller\'s own "\n'
     '         "sensors (DualSense, DualShock 4, Switch Pro Controller, Joy-Con, Steam Deck and others), Cemuhook "\n'
     '         "from a DSU server app.");\n'
     '#else\n'
     '    note("On the Wii U you aim in first person (bow, hookshot, boomerang, telescope, Picto Box, grappling hook) by "\n'
     '         "moving the GamePad. This works with the GamePad and the Pro Controller choice alike. The game\'s own "\n'
     '         "Options > Gyro switch still decides whether it uses the motion, and it ignores the motion while the right "\n'
     '         "stick is pushed.");\n'
     '#endif\n'),
    ('    for (int i = 0; i < motion::kSourceCount; i++)\n',
     '    for (int i = 0; i < motion::kSourceCount; i++)\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '        if (i != motion::kMouse || g.source == motion::kMouse)  // it waits for Wind Waker HD\'s aiming\n'
     '#endif\n'),
]
