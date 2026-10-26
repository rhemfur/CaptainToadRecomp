"""Captain Toad's exact-text changes to the reference runtime (tools/patch_runtime.py).

Loader, guest threads, HLE, audio, save states, mods, aspect and the build.
"""
from .common import _ct_keep

REPLACEMENTS = {}
REPLACEMENTS['src/main.cpp'] = [
    ('std::string rpx = config::game_dir + "/code/cking.rpx";',
     'std::string rpx = config::game_dir + "/code/Kinopio.rpx";'),
    ('mem::write_cstr(arg0, "cking.rpx", 16);', 'mem::write_cstr(arg0, "Kinopio.rpx", 16);'),
    # Windows crash reports also name the guest arguments and walk the guest stack back chain.
    ('    if(Cpu* c=threads::current()){n=snprintf(buf,sizeof buf,"guest lr=%08X ctr=%08X\\n",c->lr,c->ctr); win_crash_out(fd,buf,n);}\n',
     '    if(Cpu* c=threads::current()){n=snprintf(buf,sizeof buf,"guest lr=%08X ctr=%08X\\n",c->lr,c->ctr); win_crash_out(fd,buf,n);}\n'
     '    if(Cpu* c=threads::current()){\n'
     '        n=snprintf(buf,sizeof buf,"guest r1=%08X r3=%08X r4=%08X r5=%08X r31=%08X\\n",c->r[1],c->r[3],c->r[4],c->r[5],c->r[31]); win_crash_out(fd,buf,n);\n'
     '        uint32_t sp=c->r[1];\n'
     '        for(int i=0;i<24&&sp>=0x10000&&sp<0xF0000000u;i++){uint32_t next=ld32(sp);if(next<0x10000||next>=0xF0000000u)break;\n'
     '            n=snprintf(buf,sizeof buf,"  guest frame %08X lr %08X\\n",next,ld32(next+4)); win_crash_out(fd,buf,n); sp=next;}\n'
     '    }\n'),
]
# valid, even when it falls inside Captain Toad's ranges: features that check validity switch
# themselves off, and direct uses resolve into the protected guest null page and fault.
REPLACEMENTS['include/guest_addr.h'] = [
    ('static inline int guest_code_valid(uint32_t a) {\n',
     'static inline int guest_code_valid(uint32_t a) {\n#ifdef CT_FOREIGN_GUEST\n    (void)a;\n    return 0;\n#endif\n'),
    ('static inline int guest_data_valid(uint32_t a) {\n',
     'static inline int guest_data_valid(uint32_t a) {\n#ifdef CT_FOREIGN_GUEST\n    (void)a;\n    return 0;\n#endif\n'),
    ('static inline uint32_t guest_code(uint32_t canon) {\n',
     'static inline uint32_t guest_code(uint32_t canon) {\n#ifdef CT_FOREIGN_GUEST\n    (void)canon;\n    return 0x00001000u;\n#endif\n'),
    ('static inline uint32_t guest_data(uint32_t canon) {\n',
     'static inline uint32_t guest_data(uint32_t canon) {\n#ifdef CT_FOREIGN_GUEST\n    (void)canon;\n    return 0x00001000u;\n#endif\n'),
]
REPLACEMENTS['src/hle/ax.cpp'] = [
    ('    uint32_t mgr = ld32(GD(0x1018EC64));\n',
     '    if (!guest_data_valid(0x1018EC64)) return false;\n    uint32_t mgr = ld32(GD(0x1018EC64));\n'),
]
# Counting arrivals let Captain Toad's main thread (core 1, mask 1) pass before its audio launch
# thread (core 0) had initialized the sound system. `arrived` now holds the arrived-core bits.
REPLACEMENTS['src/threads.cpp'] = [
    ('    uint32_t arrived = 0;\n', '    uint32_t arrived = 0;  // bit per core that has arrived\n'),
    ('''    // arg1 is a core mask; we treat each set bit as one participant
    HRendezvous* r = g_rdv.get(arg(c, 0));
    uint32_t need = __builtin_popcount(arg(c, 1) & 7);
    std::unique_lock<std::mutex> lk(r->m);
    r->arrived++;
    r->cv.notify_all();
    park_wait(lk, r->cv, [&] { return r->arrived >= need; }, W_RDV, arg(c, 0));''',
     '''    // arg1 is a core mask: mark this core, then wait until every core in the mask has arrived
    HRendezvous* r = g_rdv.get(arg(c, 0));
    uint32_t need = arg(c, 1) & 7;
    std::unique_lock<std::mutex> lk(r->m);
    r->arrived |= 1u << (c->core & 3);
    r->cv.notify_all();
    park_wait(lk, r->cv, [&] { return (r->arrived & need) == need; }, W_RDV, arg(c, 0));'''),
]
REPLACEMENTS['src/savestate.cpp'] = [
    ('fopen((config::game_dir + "/code/cking.rpx").c_str(), "rb")',
     'fopen((config::game_dir + "/code/Kinopio.rpx").c_str(), "rb")'),
    # The stage name is Wind Waker HD data: closing the window asked for it and read the null page.
    ('    const char* p = (const char*)mem::ptr(kStageName);\n',
     '    if (!guest_data_valid(0x1046F0B0)) return "";\n'
     '    const char* p = (const char*)mem::ptr(kStageName);\n'),
    # Portable states hold Wind Waker HD save data: Captain Toad's states are always full ones.
    ('bool full_states() {\n',
     'bool full_states() {\n#ifdef CT_FOREIGN_GUEST\n    return true;\n#endif\n'),
]
REPLACEMENTS['../CMakeLists.txt'] = [
    ('target_include_directories(wwhd PRIVATE runtime/include runtime/src runtime/src/gx2)\n',
     'target_include_directories(wwhd PRIVATE runtime/include runtime/src runtime/src/gx2)\n'
     '# Captain Toad runtime services the reference runtime lacks (CaptainToadRecomp tools/patch_runtime.py)\n'
     'set(CT_EXTRA_SOURCES "" CACHE STRING "Captain Toad runtime sources added to the game executable")\n'
     'target_sources(wwhd PRIVATE ${CT_EXTRA_SOURCES})\n'),
]
# Dynamic resolution starts on (down to 0.75 of the internal resolution), so a scene the GPU can't
# draw in time costs resolution instead of frame rate. The saved setting and WWHD_DYNRES_MIN still win.
REPLACEMENTS['src/dynres.cpp'] = [
    ('std::atomic<float> g_min{env_min() ? clamp_min((float)atof(env_min())) : 0.0f};\n',
     'std::atomic<float> g_min{env_min() ? clamp_min((float)atof(env_min())) : 0.75f};\n'),
]
REPLACEMENTS['src/aspect.cpp'] = [
    # Android: the picture takes the phone's shape (runtime/ct_frame.cpp draws Captain Toad wider)
    ('    if (!e || !*e) return kOriginal;\n',
     '#if defined(CT_FOREIGN_GUEST) && defined(__ANDROID__)\n    if (!e || !*e) return kWindow;\n#else\n'
     '    if (!e || !*e) return kOriginal;\n#endif  // Captain Toad Android aspect\n'),
    ('void set_fov_scale(float scale) {\n', 'void set_fov_scale(float scale) {\n' + _ct_keep.format('scale = 1.0f;  // Wind Waker HD only')),
]
REPLACEMENTS['src/interp.cpp'] = [
    ('void set_mode(int m) {\n    g_on = false;\n',
     'void set_mode(int m) {\n' + _ct_keep.format('m = 0;  // Wind Waker HD frame pacing (its hooks); Captain Toad runs at 60') + '    g_on = false;\n'),
]
# PlayStation button prompts: the game reads a copy of FontData.szs with shapes for U+E000..E003
# (runtime/ct_prompts.cpp), the way the reference serves its item icon pack.
REPLACEMENTS['src/hle/fs.cpp'] = [
    ('    if(mode=="r"||mode=="rb")if(auto icons=item_icons::pack_for(guest,path);!icons.empty())return icons;\n',
     '    if(mode=="r"||mode=="rb")if(auto icons=item_icons::pack_for(guest,path);!icons.empty())return icons;\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    if(mode=="r"||mode=="rb")if(auto font=ct_prompts::font_for(guest,path);!font.empty())return font;  // runtime/ct_prompts.cpp\n'
     '#endif\n'),
    ('#include "../rtl_text.h"\n',
     '#include "../rtl_text.h"\n'
     '#ifdef CT_FOREIGN_GUEST\nnamespace ct_prompts { std::string font_for(const std::string& guest, const std::string& host_path); }\n#endif\n'),
]
# Mods: Captain Toad packages (content trees, Cemu graphic packs, SDCafiine folders) installed from a file
# or folder, with their own game ID so Wind Waker HD mods are refused. The Wind Waker HD catalogue, its
# built-in mods, the GameCube game and code mods (Wind Waker HD's guest ABI) are left out; Cheats stay in
# More. The tab is Mods again.
_ct_package_id = ('#ifdef CT_FOREIGN_GUEST\n#define WWHD_PACKAGE_GAME_ID "captain-toad"  // CaptainToadRecomp\n'
                  '#else\n#define WWHD_PACKAGE_GAME_ID "wwhd"\n#endif\n')
REPLACEMENTS['src/mods/packages.h'] = [
    ('inline constexpr const char* kGameId="wwhd";\ninline constexpr const char* kLegacyGameId="wwhd-usa";\n',
     '#ifdef CT_FOREIGN_GUEST  // Captain Toad packages (CaptainToadRecomp); Wind Waker HD ones are refused\n'
     'inline constexpr const char* kGameId="captain-toad";\ninline constexpr const char* kLegacyGameId="captain-toad";\n#else\n'
     'inline constexpr const char* kGameId="wwhd";\ninline constexpr const char* kLegacyGameId="wwhd-usa";\n#endif\n'),
]
for _file in ('src/mods/content.cpp', 'src/mods/cemu_pack.cpp'):
    REPLACEMENTS[_file] = [
        ('#include "../exception_report.h"\n', '#include "../exception_report.h"\n' + _ct_package_id),
        ('m["game_id"]="wwhd"', 'm["game_id"]=WWHD_PACKAGE_GAME_ID'),
    ]
# A parked thread may resume from either of two return addresses that continue the same way
# (runtime/ct_frame.cpp ct_equivalent_return: sead's thread loop), so a state saved in one session loads
# in a new one.
REPLACEMENTS['src/threads.cpp'] += [
    ('bool same_chain(const Cpu& cur, const Cpu& saved) {\n',
     '#ifdef CT_FOREIGN_GUEST\nextern "C" uint32_t ct_equivalent_return(uint32_t lr);  // runtime/ct_frame.cpp\n#else\n'
     'static uint32_t ct_equivalent_return(uint32_t lr) { return lr; }\n#endif\n'
     'bool same_chain(const Cpu& cur, const Cpu& saved) {\n'),
    ('        if (ld32(na + 4) != ss::snap_ld32(na + 4)) return false;\n',
     '        if (ct_equivalent_return(ld32(na + 4)) != ct_equivalent_return(ss::snap_ld32(na + 4))) return false;\n'),
    # A thread the game starts later (in a course, for one) cannot be made up: say what to do.
    ('            snprintf(buf, sizeof buf, "thread %08X (running in the save) does not exist yet", s.guest);\n',
     '#ifdef CT_FOREIGN_GUEST\n'
     '            snprintf(buf, sizeof buf, "the game has not started everything the state needs yet (thread %08X): "\n'
     '                     "go where it was saved (into a course for one saved in a course), then load", s.guest);\n'
     '#else\n'
     '            snprintf(buf, sizeof buf, "thread %08X (running in the save) does not exist yet", s.guest);\n'
     '#endif\n'),
]
# Gyro controllers (macOS, Windows, Linux): the reference's Controller gyro source (SDL3 sensors; the
# AppKit host's GameController.framework) and Cemuhook (DSU) move the virtual GamePad as on Android.
# Desktop builds start with Controller gyro, which does nothing until a controller with motion sensors
# is connected; a saved choice and WWHD_GYRO still win. The mouse source waits for Wind Waker HD's
# aiming hooks, so Captain Toad leaves it out, and the dialog describes Captain Toad.
REPLACEMENTS['src/motion/motion.h'] = [
    ('    int source = kOff;\n',
     '#if defined(CT_FOREIGN_GUEST) && !defined(__ANDROID__)\n'
     '    int source = kController;  // Captain Toad on desktops: a controller\'s gyro moves the GamePad\n'
     '#else\n'
     '    int source = kOff;\n'
     '#endif\n'),
]
# Sound output: the reference decides between the TV mix and the GamePad mix from Wind Waker HD's sound
# player (audio_output_mode.h), which Captain Toad does not have, so it always played the TV mix alone
# and lost what the game sends to the GamePad only. Automatic now plays the GamePad mix while the TV mix
# has been silent for a quarter of a second and the GamePad's is not, and otherwise the TV mix with the
# voices that only reach the GamePad (Settings > Audio > GamePad sounds). WWHD_AUDIO_OUTPUT still wins.
REPLACEMENTS['src/hle/ax.cpp'] += [
    ('    const float pad_gain = g_output.play_gamepad_only && audio::gamepad_sounds() ? audio::gamepad_sounds_volume() : 0.f;\n',
     '#ifdef CT_FOREIGN_GUEST\n'
     '    if (g_output.source == audio::OutputSelect::kAuto) {  // Captain Toad (CaptainToadRecomp tools/patch_runtime.py)\n'
     '        constexpr int kQuietFrames = 83;  // 0.25 s of 3 ms frames\n'
     '        static int tv_quiet = kQuietFrames;\n'
     '        bool tv_on = false, drc_on = false;\n'
     '        for (int i = 0; i < kSamples48; ++i) {\n'
     '            for (int ch = 0; ch < channels; ++ch) tv_on |= std::abs(tv_lr[ch][i]) > 8;\n'
     '            for (int ch = 0; ch < 2; ++ch) drc_on |= std::abs(drc_lr[ch][i]) > 8;\n'
     '        }\n'
     '        tv_quiet = tv_on ? 0 : std::min(tv_quiet + 1, kQuietFrames);\n'
     '        const bool pad = drc_on && tv_quiet >= kQuietFrames;\n'
     '        if (pad != g_output.play_drc) LOG("[ax] host output: %s", pad ? "GamePad (the TV mix is silent)" : "TV");\n'
     '        g_output.play_tv = !pad;\n'
     '        g_output.play_drc = pad;\n'
     '        g_output.play_gamepad_only = !pad;\n'
     '    }\n'
     '#endif  // Captain Toad sound output\n'
     '    const float pad_gain = g_output.play_gamepad_only && audio::gamepad_sounds() ? audio::gamepad_sounds_volume() : 0.f;\n'),
]
