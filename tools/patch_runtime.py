"""Prepare the reference game runtime (renderer, audio, input) for Captain Toad's generated code.

The reference runtime names the Wind Waker HD executable and calls Wind Waker HD guest functions
from its game-specific features. This script points the loader at Kinopio.rpx and writes weak stubs
for those guest symbols, following nsmbu-recomp tools/recomp/guest_stubs.py (MPL-2.0). A stub that
runs stops through ppc_unimplemented instead of executing unrelated Captain Toad code.
"""
from pathlib import Path
import argparse
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('upstream', type=Path)
parser.add_argument('--gen', type=Path, default=Path('build/gen'), help='generated Captain Toad code')
args = parser.parse_args()
runtime = args.upstream / 'runtime'

REPLACEMENTS = {
    'src/main.cpp': [
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
    ],
    # Canonical addresses name Wind Waker HD code and data. With CT_FOREIGN_GUEST none of them is
    # valid, even when it falls inside Captain Toad's ranges: features that check validity switch
    # themselves off, and direct uses resolve into the protected guest null page and fault.
    'include/guest_addr.h': [
        ('static inline int guest_code_valid(uint32_t a) {\n',
         'static inline int guest_code_valid(uint32_t a) {\n#ifdef CT_FOREIGN_GUEST\n    (void)a;\n    return 0;\n#endif\n'),
        ('static inline int guest_data_valid(uint32_t a) {\n',
         'static inline int guest_data_valid(uint32_t a) {\n#ifdef CT_FOREIGN_GUEST\n    (void)a;\n    return 0;\n#endif\n'),
        ('static inline uint32_t guest_code(uint32_t canon) {\n',
         'static inline uint32_t guest_code(uint32_t canon) {\n#ifdef CT_FOREIGN_GUEST\n    (void)canon;\n    return 0x00001000u;\n#endif\n'),
        ('static inline uint32_t guest_data(uint32_t canon) {\n',
         'static inline uint32_t guest_data(uint32_t canon) {\n#ifdef CT_FOREIGN_GUEST\n    (void)canon;\n    return 0x00001000u;\n#endif\n'),
    ],
    # Wind Waker HD's sound manager supplies the TV/GamePad faders; other titles keep the TV default.
    'src/hle/ax.cpp': [
        ('    uint32_t mgr = ld32(GD(0x1018EC64));\n',
         '    if (!guest_data_valid(0x1018EC64)) return false;\n    uint32_t mgr = ld32(GD(0x1018EC64));\n'),
    ],
    # OSWaitRendezvous waits for the cores in its mask, as Cemu coreinit_Synchronization.cpp does.
    # Counting arrivals let Captain Toad's main thread (core 1, mask 1) pass before its audio launch
    # thread (core 0) had initialized the sound system. `arrived` now holds the arrived-core bits.
    'src/threads.cpp': [
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
    ],
    # GX2's 0x800 format bit marks float formats (R16_FLOAT 0x806, R16G16_FLOAT 0x810), not depth.
    # A depth surface is one created for depth-buffer use, as Cemu's GX2CalculateSurfaceInfo decides.
    # Name the formats, so an unsupported copy identifies itself.
    'src/gfx/vulkan/surfaces.cpp': [
        ('    auto sf=format_info(uint32_t(s->format.value()),bool(uint32_t(s->format.value())&0x800));\n'
         '    auto df=format_info(uint32_t(d->format.value()),bool(uint32_t(d->format.value())&0x800));\n',
         '    auto sf=format_info(uint32_t(s->format.value()),(s->resFlag&(1u<<2))!=0);  // GX2_RESFLAG_USAGE_DEPTH_BUFFER\n'
         '    auto df=format_info(uint32_t(d->format.value()),(d->resFlag&(1u<<2))!=0);\n'),
        ('        exception_report::raise("Unsupported CPU GX2CopySurface format layout");\n',
         '        exception_report::raise("Unsupported CPU GX2CopySurface format layout: " +\n'
         '            std::to_string(uint32_t(s->format.value())) + " tile " + std::to_string(uint32_t(s->tileMode.value())) + " -> " +\n'
         '            std::to_string(uint32_t(d->format.value())) + " tile " + std::to_string(uint32_t(d->tileMode.value())));\n'),
    ],
    # Stream out (Cemu GX2_Streamout.cpp, LatteCommandProcessor.cpp, LatteStreamoutGPU.cpp): context
    # updates run on the render thread in command order; draws advance each buffer's write offset.
    'src/gx2/gx2_cmd.h': [
        ('    OP_LAYOUT_CONTENT,  // DrawSelf scope: clip TV menu content to the native layout region\n    OP_COUNT\n',
         '    OP_LAYOUT_CONTENT,  // DrawSelf scope: clip TV menu content to the native layout region\n'
         '    OP_STREAMOUT_UPDATE,  // buffer index, mode (0 reset, 2 load from context, 3 save to context), context\n'
         '    OP_COUNT\n'),
    ],
    'src/gx2/gx2_core.cpp': [
        ('static void execute_op(Op op, const uint32* p, uint32 n) {\n',
         '''// Stream-out draws advance each buffer's write offset by the bytes their vertices emit, bounded by
// the buffer (Cemu LatteStreamoutGPU.cpp). The renderer does not produce that output yet: the buffers
// keep their previous contents.
static void streamout_advance(uint32 count, uint32 instances) {
    if (!g_regs[mmVGT_STRMOUT_EN]) return;
    static bool logged = false;
    if (!logged) { logged = true; LOG("[gx2] stream-out draws advance their buffer offsets; their vertex output is not produced yet"); }
    for (uint32 i = 0; i < 4; i++) {
        const uint32 stride = g_regs[mmVGT_STRMOUT_VTX_STRIDE_0 + i * 4] << 2, size = g_regs[mmVGT_STRMOUT_BUFFER_SIZE_0 + i * 4] << 2;
        uint32& offset = g_regs[mmVGT_STRMOUT_BUFFER_OFFSET_0 + i * 4];
        if (!stride || !size) continue;
        offset += (uint32)std::min<uint64>(uint64(count) * instances * stride, offset < size ? size - offset : 0);
    }
}
static void execute_op(Op op, const uint32* p, uint32 n) {
'''),
        ('    case OP_DRAW: render::draw(g_regs, p[0], p[1], 0, 0, p[2], p[3]); break;\n'
         '    case OP_DRAW_INDEXED: render::draw(g_regs, p[0], p[1], p[2], p[3], p[4], p[5]); break;\n',
         '    case OP_DRAW: render::draw(g_regs, p[0], p[1], 0, 0, p[2], p[3]); streamout_advance(p[1], p[3]); break;\n'
         '    case OP_DRAW_INDEXED: render::draw(g_regs, p[0], p[1], p[2], p[3], p[4], p[5]); streamout_advance(p[1], p[5]); break;\n'
         '    case OP_STREAMOUT_UPDATE: {  // IT_STRMOUT_BUFFER_UPDATE\n'
         '        uint32& offset = g_regs[mmVGT_STRMOUT_BUFFER_OFFSET_0 + 4 * (p[0] & 3)];\n'
         '        if (p[1] == 0) offset = 0;\n'
         '        else if (p[1] == 2) offset = p[2] ? ld32(p[2]) : 0;\n'
         '        else if (p[1] == 3 && p[2]) st32(p[2], offset);\n'
         '        break;\n'
         '    }\n'),
    ],
    'src/gx2/gx2_resources.cpp': [
        ('        set_regs(mmSQ_VTX_SEMANTIC_0, &tmp[mmSQ_VTX_SEMANTIC_0], nsem);\n    }\n}\n',
         '        set_regs(mmSQ_VTX_SEMANTIC_0, &tmp[mmSQ_VTX_SEMANTIC_0], nsem);\n    }\n'
         '    if (ld32(vs + 0x110))  // usesStreamOut: per-buffer vertex strides in dwords (Cemu GX2_Shader.cpp)\n'
         '        for (uint32 i = 0; i < 4; i++) set_reg(mmVGT_STRMOUT_VTX_STRIDE_0 + i * 4, ld32(vs + 0x114 + 4 * i) >> 2);\n'
         '}\n'),
    ],
    'src/savestate.cpp': [
        ('fopen((config::game_dir + "/code/cking.rpx").c_str(), "rb")',
         'fopen((config::game_dir + "/code/Kinopio.rpx").c_str(), "rb")'),
    ],
    # A dynamic export without HLE returned 0 when called, as Cemu's unsupported-import stub does.
    # The strict build stops there instead, like a missing static import.
    'src/hle/coreinit_misc.cpp': [
        ('            static void (*stub)(Cpu*) = [](Cpu* c) { log_msg("[dynload] call to unimplemented dynamic export (lr=%08X)", c->lr); c->r[3] = 0; };\n',
         '#ifdef CT_DIAGNOSTIC_STRICT_HLE\n'
         '            static void (*stub)(Cpu*) = [](Cpu* c) { log_msg("[ct-stop] missing HLE dynamic export (lr=%08X; see FindExport above)", c->lr); std::_Exit(78); };\n'
         '#else\n'
         '            static void (*stub)(Cpu*) = [](Cpu* c) { log_msg("[dynload] call to unimplemented dynamic export (lr=%08X)", c->lr); c->r[3] = 0; };\n'
         '#endif\n'),
    ],
}
# The Android app gets its own package and name, so installing it never replaces a Wind Waker HD
# install. The Java namespace stays; only the installed identity changes.
REPLACEMENTS['../android/app/build.gradle'] = [
    ('        applicationId "org.wwhdrecomp.wwhd"\n', '        applicationId "org.ctrecomp.captaintoad"\n'),
]
REPLACEMENTS['../android/app/src/main/res/values/strings.xml'] = [
    ('    <string name="app_name">Wind Waker HD</string>\n', '    <string name="app_name">Captain Toad</string>\n'),
]
REPLACEMENTS['../CMakeLists.txt'] = [
    ('target_include_directories(wwhd PRIVATE runtime/include runtime/src runtime/src/gx2)\n',
     'target_include_directories(wwhd PRIVATE runtime/include runtime/src runtime/src/gx2)\n'
     '# Captain Toad runtime services the reference runtime lacks (CaptainToadRecomp tools/patch_runtime.py)\n'
     'set(CT_EXTRA_SOURCES "" CACHE STRING "Captain Toad runtime sources added to the game executable")\n'
     'target_sources(wwhd PRIVATE ${CT_EXTRA_SOURCES})\n'),
    # SHELL: splits on spaces, so a checkout path with a space broke the forced include.
    ('target_compile_options(cemu_latte PRIVATE "SHELL:-include ${CEMU_DIR}/cemu_shim.h")\n',
     'target_compile_options(cemu_latte PRIVATE "SHELL:-include \\"${CEMU_DIR}/cemu_shim.h\\"")\n'),
    ('target_compile_options(shadertest PRIVATE "SHELL:-include ${CEMU_DIR}/cemu_shim.h")\n',
     'target_compile_options(shadertest PRIVATE "SHELL:-include \\"${CEMU_DIR}/cemu_shim.h\\"")\n'),
]
# The reference's on-screen controls are drawn smaller and kept in the corners, close together:
# Captain Toad is a casual game and the picture matters more than reach. Positions count in the
# screen's short side from a corner (negative: from the right or bottom edge), so wide phones keep
# each group compact.
REPLACEMENTS['../android/app/src/main/java/org/wwhdrecomp/wwhd/TouchControls.java'] = [
    ('''        controls.add(new Control(KIND_STICK, 0, "", 0.14f, 0.70f, 0.13f));
        controls.add(new Control(KIND_STICK, 1, "", 0.68f, 0.80f, 0.11f));
        // A B X Y where a Wii U GamePad has them
        final float ax = 0.86f, ay = 0.60f, d = 0.10f;
        controls.add(new Control(KIND_FACE, FACE_A, "A", ax + d * 0.75f, ay, 0.055f));
        controls.add(new Control(KIND_FACE, FACE_B, "B", ax, ay + d, 0.055f));
        controls.add(new Control(KIND_FACE, FACE_X, "X", ax, ay - d, 0.055f));
        controls.add(new Control(KIND_FACE, FACE_Y, "Y", ax - d * 0.75f, ay, 0.055f));
        final float px = 0.14f, py = 0.36f, e = 0.075f;
        controls.add(new Control(KIND_BUTTON, DPAD_UP, "▲", px, py - e, 0.04f));
        controls.add(new Control(KIND_BUTTON, DPAD_DOWN, "▼", px, py + e, 0.04f));
        controls.add(new Control(KIND_BUTTON, DPAD_LEFT, "◀", px - e * 0.75f, py, 0.04f));
        controls.add(new Control(KIND_BUTTON, DPAD_RIGHT, "▶", px + e * 0.75f, py, 0.04f));
        controls.add(new Control(KIND_TRIGGER, 0, "ZL", 0.19f, 0.15f, 0.05f));
        controls.add(new Control(KIND_BUTTON, LEFT_SHOULDER, "L", 0.30f, 0.15f, 0.05f));
        controls.add(new Control(KIND_BUTTON, RIGHT_SHOULDER, "R", 0.70f, 0.15f, 0.05f));
        controls.add(new Control(KIND_TRIGGER, 1, "ZR", 0.81f, 0.15f, 0.05f));
        controls.add(new Control(KIND_BUTTON, BACK, "−", 0.42f, 0.92f, 0.04f));
        controls.add(new Control(KIND_BUTTON, START, "+", 0.58f, 0.92f, 0.04f));
''', '''        // CaptainToadRecomp: corners, in short-side units (negative: from the right / bottom edge)
        controls.add(new Control(KIND_STICK, 0, "", 0.27f, -0.23f, 0.17f));
        final float ax = -0.17f, ay = -0.25f, d = 0.08f;  // A B X Y as on a Wii U GamePad
        controls.add(new Control(KIND_FACE, FACE_A, "A", ax + d, ay, 0.055f));
        controls.add(new Control(KIND_FACE, FACE_B, "B", ax, ay + d, 0.055f));
        controls.add(new Control(KIND_FACE, FACE_X, "X", ax, ay - d, 0.055f));
        controls.add(new Control(KIND_FACE, FACE_Y, "Y", ax - d, ay, 0.055f));
        final float px = 0.20f, py = -0.53f, e = 0.065f;  // the D-pad above the left stick
        controls.add(new Control(KIND_BUTTON, DPAD_UP, "▲", px, py - e, 0.04f));
        controls.add(new Control(KIND_BUTTON, DPAD_DOWN, "▼", px, py + e, 0.04f));
        controls.add(new Control(KIND_BUTTON, DPAD_LEFT, "◀", px - e, py, 0.04f));
        controls.add(new Control(KIND_BUTTON, DPAD_RIGHT, "▶", px + e, py, 0.04f));
        controls.add(new Control(KIND_TRIGGER, 0, "ZL", 0.20f, 0.07f, 0.05f));
        controls.add(new Control(KIND_BUTTON, LEFT_SHOULDER, "L", 0.31f, 0.07f, 0.05f));
        controls.add(new Control(KIND_BUTTON, RIGHT_SHOULDER, "R", -0.31f, 0.07f, 0.05f));
        controls.add(new Control(KIND_TRIGGER, 1, "ZR", -0.20f, 0.07f, 0.05f));
        controls.add(new Control(KIND_BUTTON, BACK, "−", -0.31f, 0.18f, 0.04f));
        controls.add(new Control(KIND_BUTTON, START, "+", -0.20f, 0.18f, 0.04f));
'''),
    # Captain Toad's menus and many levels are bright: translucent white controls vanished on its
    # white title screen. A dark translucent body keeps them visible on light and dark pictures.
    ('        fill.setColor(on ? 0x90FFFFFF : 0x38FFFFFF);\n',
     '        fill.setColor(on ? 0x90FFFFFF : 0x60000000);  // CaptainToadRecomp: dark body (reference: 0x38FFFFFF)\n'),
    ('        text.setColor(0xE0FFFFFF);\n',
     '        text.setColor(0xE0FFFFFF);\n'
     '        text.setShadowLayer(c.r * 0.08f, 0, 0, 0xC0000000);  // CaptainToadRecomp: readable on white\n'),
    # The camera follows a finger dragged anywhere outside the controls ("moving the map"): its speed
    # becomes the right stick, so the view turns with the finger and stops when it stops. The touch
    # still reaches the game as before (GamePad picture, view button). The top left corner (view and
    # show/hide buttons) does not drag. Only while the controls are shown.
    ('    private int lastButtons = -1;\n',
     '    private int lastButtons = -1;\n'
     '    // CaptainToadRecomp: camera drag (the finger on no control) as the right stick\n'
     '    private static final float DRAG_FULL = 0.9f;  // short sides per second for a full stick\n'
     '    private int dragId = -1;\n'
     '    private float dragX, dragY, camX, camY;\n'
     '    private long dragT;\n'
     '    private final Runnable dragRest = () -> { camX = 0; camY = 0; update(); };\n'
     '    private boolean dragZone(float x, float y) {\n'
     '        final float s = Math.min(getWidth(), getHeight());\n'
     '        return !(x < s * 0.25f && y < s * 0.30f);\n'
     '    }\n'
     '    private void dragStart(int id, float x, float y, long t) {\n'
     '        if (dragId >= 0 || !active() || !dragZone(x, y)) return;\n'
     '        dragId = id; dragX = x; dragY = y; dragT = t;\n'
     '    }\n'
     '    private void dragMove(float x, float y, long t) {\n'
     '        final float s = Math.min(getWidth(), getHeight());\n'
     '        final long dt = Math.max(1, t - dragT);\n'
     '        final float full = s * DRAG_FULL / 1000f;  // pixels per millisecond for a full stick\n'
     '        final float tx = Math.max(-1f, Math.min(1f, (x - dragX) / dt / full));\n'
     '        final float ty = Math.max(-1f, Math.min(1f, (y - dragY) / dt / full));\n'
     '        camX = camX * 0.4f + tx * 0.6f; camY = camY * 0.4f + ty * 0.6f;\n'
     '        dragX = x; dragY = y; dragT = t;\n'
     '        removeCallbacks(dragRest);\n'
     '        postDelayed(dragRest, 80);  // the finger rests: the camera stops\n'
     '    }\n'
     '    private void dragEnd() { dragId = -1; removeCallbacks(dragRest); camX = 0; camY = 0; }\n'),
    ('                if (c == null && action == MotionEvent.ACTION_DOWN) {\n',
     '                if (c == null && action == MotionEvent.ACTION_DOWN && active()) {\n'
     '                    // CaptainToadRecomp: keep the gesture, pass the touch on and drag the camera with it\n'
     '                    forward(event, index, action);\n'
     '                    dragStart(id, x, y, event.getEventTime());\n'
     '                } else if (c == null && action == MotionEvent.ACTION_DOWN) {\n'),
    ('                } else if (c == null) {\n                    forward(event, index, action);\n',
     '                } else if (c == null) {\n                    forward(event, index, action);\n'
     '                    dragStart(id, x, y, event.getEventTime());\n'),
    ('                    if (c == null) forward(event, i, MotionEvent.ACTION_MOVE);\n',
     '                    if (c == null) {\n'
     '                        forward(event, i, MotionEvent.ACTION_MOVE);\n'
     '                        if (id == dragId) dragMove(event.getX(i), event.getY(i), event.getEventTime());\n'
     '                    }\n'),
    ('                    if (c == null) { forward(event, i, all ? MotionEvent.ACTION_CANCEL : action); continue; }\n',
     '                    if (c == null) {\n'
     '                        forward(event, i, all ? MotionEvent.ACTION_CANCEL : action);\n'
     '                        if (id == dragId) dragEnd();\n'
     '                        continue;\n'
     '                    }\n'),
    ('        buttons |= face << 16;  // (only for the change check below)\n',
     '        if (dragId >= 0 || camX != 0 || camY != 0) { rx = camX; ry = camY; }  // CaptainToadRecomp: camera drag\n'
     '        buttons |= face << 16;  // (only for the change check below)\n'),
    ('    private static void place(Control c, int w, int h, float s) {\n        c.cx = c.fx * w; c.cy = c.fy * h; c.r = c.fr * s;\n',
     '    private static final float SIZE = 0.7f;  // CaptainToadRecomp: smaller controls\n\n'
     '    private static void place(Control c, int w, int h, float s) {\n'
     '        c.cx = c.fx >= 0 ? c.fx * s : w + c.fx * s; c.cy = c.fy >= 0 ? c.fy * s : h + c.fy * s; c.r = c.fr * s * SIZE;\n'),
]
# Settings menu: Captain Toad's build hides what only works with Wind Waker HD. The Saves tab (save
# states and crash recovery restore Wind Waker HD memory), the Mods tab (its mods, catalogue and Cemu
# packs), the frame-rate choice (interpolation from Wind Waker HD's 30 logic steps; Captain Toad
# draws 60 itself) and the bloom and ambient-occlusion fixes made for Wind Waker HD's shaders.
REPLACEMENTS['src/overlay/overlay.cpp'] = [
    ('    if (ImGui::Begin("Wind Waker HD  -  Settings", &open, fl)) {\n',
     '#ifdef CT_FOREIGN_GUEST\n'
     '    if (ImGui::Begin("Captain Toad  -  Settings", &open, fl)) {\n'
     '#else\n'
     '    if (ImGui::Begin("Wind Waker HD  -  Settings", &open, fl)) {\n'
     '#endif\n'),
    ('            if (navigation_pressed(input_map::kPadLB)) U.select_tab = (U.tab + kTabs - 1) % kTabs;\n'
     '            if (navigation_pressed(input_map::kPadRB)) U.select_tab = (U.tab + 1) % kTabs;\n',
     '            if (navigation_pressed(input_map::kPadLB)) U.select_tab = (U.tab + kTabs - 1) % kTabs;\n'
     '            if (navigation_pressed(input_map::kPadRB)) U.select_tab = (U.tab + 1) % kTabs;\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '            // L / R step over the hidden tabs in the direction pressed\n'
     '            while (U.select_tab == kSaves || U.select_tab == kMods)\n'
     '                U.select_tab = (U.select_tab + (navigation_pressed(input_map::kPadLB) ? kTabs - 1 : 1)) % kTabs;\n'
     '#endif\n'),
    ('                ImGuiTabItemFlags f = U.select_tab == i ? ImGuiTabItemFlags_SetSelected : 0;\n',
     '#ifdef CT_FOREIGN_GUEST\n'
     '                if (i == kSaves || i == kMods) continue;\n'
     '#endif\n'
     '                ImGuiTabItemFlags f = U.select_tab == i ? ImGuiTabItemFlags_SetSelected : 0;\n'),
    ('    heading("Frame rate");\n', '#ifndef CT_FOREIGN_GUEST\n    heading("Frame rate");\n'),
    ('    heading("Internal resolution");\n', '#endif\n    heading("Internal resolution");\n'),
    ('    float bloom = render::bloom_strength() * 100.0f;\n',
     '#ifndef CT_FOREIGN_GUEST\n    float bloom = render::bloom_strength() * 100.0f;\n'),
    ('        post_changed([v] { render::set_ao_hires(v); });\n    ImGui::SameLine(0, 30);\n',
     '        post_changed([v] { render::set_ao_hires(v); });\n    ImGui::SameLine(0, 30);\n#endif\n'),
]
# Gyro: the reference's 0.5 suits Wind Waker HD's first-person aiming; held at arm's length, a phone
# turned too far for a little camera movement in Captain Toad. Saved settings keep their own value.
REPLACEMENTS['src/motion/fusion.h'] = [
    ('    static constexpr float kDefaultSensitivity = 0.5f,',
     '    static constexpr float kDefaultSensitivity = 1.5f,  // CaptainToadRecomp (reference: 0.5)\n                           '),
]
# The PC route (this APK: the game copied over USB) is ready to play when the game folder has
# Captain Toad's executable; the app icon then starts the game instead of the setup screen.
REPLACEMENTS['../android/app/src/main/java/org/wwhdrecomp/wwhd/SetupActivity.java'] = [
    ('                return external != null && new File(external, "game/code/cking.rpx").isFile();\n',
     '                return external != null && new File(external, "game/code/Kinopio.rpx").isFile();\n'),
    ('                    (external != null && new File(external, "game/code/cking.rpx").isFile()));\n',
     '                    (external != null && new File(external, "game/code/Kinopio.rpx").isFile()));\n'),
]
# Exports that read state private to a reference source file are appended to that file.
APPENDS = {
    'src/hle/ax.cpp': '''
// ---- Captain Toad additions (CaptainToadRecomp tools/patch_runtime.py), following Cemu ax_aux.cpp
HLE(snd_core, AXGetAuxCallback) {
    // (device, deviceIndex, auxBus, funcOut, userOut): TV index 0 and GamePad indices 0-1 are valid
    uint32_t dev = arg(c, 0), idx = arg(c, 1), bus = arg(c, 2), func = 0, user = 0;
    if ((dev == 0 && idx != 0) || (dev == 1 && idx > 1) || dev > 1) { ret(c, (uint32_t)-1); return; }
    if (bus >= kAuxBuses) { ret(c, (uint32_t)-5); return; }
    if (dev == 0) { func = g_aux_cb[bus]; user = g_aux_user[bus]; }
    else if (idx == 0) { std::lock_guard<std::mutex> lk(g_ax_mutex); func = g_drc.aux_cb[bus]; user = g_drc.aux_user[bus]; }
    if (arg(c, 3)) st32(arg(c, 3), func);
    if (arg(c, 4)) st32(arg(c, 4), user);
    ret(c, 0);
}
''',
    'src/gx2/gx2_core.cpp': '''
// ---- Captain Toad additions (CaptainToadRecomp tools/patch_runtime.py)
HLE(gx2, GX2GetDisplayListWriteStatus) { ret(c, t_rec.start != 0); }  // this thread records a display list
HLE(gx2, GX2SetDefaultState) { set_default_state(); }                 // the state GX2Init establishes
''',
    'src/gx2/gx2_state.cpp': '''
// ---- Captain Toad additions (CaptainToadRecomp tools/patch_runtime.py), following Cemu GX2_State.cpp
HLE(gx2, GX2SetPolygonOffset) {
    // (frontOffset, frontScale, backOffset, backScale, clampOffset): the scales count 1/16 units
    set_reg(REGADDR::PA_SU_POLY_OFFSET_FRONT_SCALE, gx2::fbits(fa(c, 1) * 16.0f));
    set_reg(REGADDR::PA_SU_POLY_OFFSET_FRONT_SCALE + 1, gx2::fbits(fa(c, 0)));
    set_reg(REGADDR::PA_SU_POLY_OFFSET_FRONT_SCALE + 2, gx2::fbits(fa(c, 3) * 16.0f));
    set_reg(REGADDR::PA_SU_POLY_OFFSET_FRONT_SCALE + 3, gx2::fbits(fa(c, 2)));
    set_reg(REGADDR::PA_SU_POLY_OFFSET_CLAMP, gx2::fbits(fa(c, 4)));
}
HLE(gx2, GX2SetCullOnlyControl) {
    // (frontFace, cullFront, cullBack): polygon modes and offsets off
    LATTE_PA_SU_SC_MODE_CNTL v;
    v.set_FRONT_FACE((LATTE_PA_SU_SC_MODE_CNTL::E_FRONTFACE)arg(c, 0));
    v.set_CULL_FRONT((arg(c, 1) & 1) != 0);
    v.set_CULL_BACK((arg(c, 2) & 1) != 0);
    set_reg(REGADDR::PA_SU_SC_MODE_CNTL, v.getRawValue());
}
HLE(gx2, GX2SetDepthOnlyControl) {
    // (depthTest, depthWrite, depthFunc): also disables the stencil test
    LATTE_DB_DEPTH_CONTROL r;
    r.set_Z_ENABLE(arg(c, 0) != 0).set_Z_WRITE_ENABLE(arg(c, 1) != 0).set_Z_FUNC((LATTE_DB_DEPTH_CONTROL::E_ZFUNC)arg(c, 2));
    set_reg(REGADDR::DB_DEPTH_CONTROL, r.getRawValue());
}
HLE(gx2, GX2SetPointLimits) {
    uint32 lo = std::min<uint32>((uint32)(std::max(fa(c, 0), 0.0f) * 8.0f), 0xFFFF);
    uint32 hi = std::min<uint32>((uint32)(std::max(fa(c, 1), 0.0f) * 8.0f), 0xFFFF);
    set_reg(REGADDR::PA_SU_POINT_MINMAX, LATTE_PA_SU_POINT_MINMAX().set_MIN_SIZE(lo).set_MAX_SIZE(hi).getRawValue());
}
HLE(gx2, GX2SetPrimitiveRestartIndex) { set_reg(REGADDR::VGT_MULTI_PRIM_IB_RESET_INDX, arg(c, 0)); }
HLE(gx2, GX2SetStreamOutEnable) { set_reg(mmVGT_STRMOUT_EN, arg(c, 0) & 1); }
HLE(gx2, GX2SetStreamOutBuffer) {
    // (index, GX2StreamOutBuffer*): +0 size, +4 data, +0xC GX2RBuffer (elementSize +0x10, elementCount
    // +0x14, data +0x18) used when data is null. BASE holds the full address (this renderer's convention).
    uint32 i = arg(c, 0) & 3, b = arg(c, 1);
    uint32 data = ld32(b + 4), size = ld32(b);
    if (!data) { data = ld32(b + 0x18); size = ld32(b + 0x10) * ld32(b + 0x14); }
    set_reg(mmVGT_STRMOUT_BUFFER_SIZE_0 + i * 4, size >> 2);
    set_reg(mmVGT_STRMOUT_BUFFER_BASE_0 + i * 4, data);
}
// (index, GX2StreamOutBuffer*, reset): reset starts at offset 0, otherwise the offset its context saved
HLE(gx2, GX2SetStreamOutContext) {
    gx2::emit(gx2::OP_STREAMOUT_UPDATE, {arg(c, 0) & 3, arg(c, 2) ? 0u : 2u, ld32(arg(c, 1) + 0x1C)});
}
HLE(gx2, GX2SaveStreamOutContext) { gx2::emit(gx2::OP_STREAMOUT_UPDATE, {arg(c, 0) & 3, 3u, ld32(arg(c, 1) + 0x1C)}); }
// Cemu exports no tessellation calls; draws never select tessellated primitives here, so the mode
// changes nothing and the level registers only record the values.
HLE(gx2, GX2SetTessellation) {}
HLE(gx2, GX2SetMaxTessellationLevel) { set_reg(mmVGT_HOS_MAX_TESS_LEVEL, gx2::fbits(fa(c, 0))); }
HLE(gx2, GX2SetMinTessellationLevel) { set_reg(mmVGT_HOS_MIN_TESS_LEVEL, gx2::fbits(fa(c, 0))); }
''',
}
MARKER = '\n// ---- Captain Toad additions'
for relative, text in APPENDS.items():
    path = runtime / relative
    source = path.read_text(encoding='utf-8')
    if text not in source:
        # The additions block always ends the file: replace an older version of it.
        if source.count(MARKER) > 1:
            raise SystemExit(f'{relative} has several Captain Toad addition blocks; review it')
        source = source.split(MARKER)[0]
        path.write_text(source.rstrip('\n') + '\n' + text, encoding='utf-8', newline='\n')

for relative, pairs in REPLACEMENTS.items():
    path = runtime / relative
    source = path.read_text(encoding='utf-8')
    for old, new in pairs:
        if new in source:
            continue
        if source.count(old) != 1:
            raise SystemExit(f'reference changed: {relative} needs review')
        source = source.replace(old, new)
    path.write_text(source, encoding='utf-8', newline='\n')

STUBS = runtime / 'src/ct_guest_stubs.c'
symbol = re.compile(r'\bf_([0-9A-F]{8})(_orig)?\b')
fence = re.compile(r'\bT60_FENCE_(?:LINK|ANY)\(([0-9A-F]{8})')  # pastes f_<address>_orig
names = set()
for path in sorted(runtime.rglob('*')):
    if path.suffix in {'.c', '.cpp', '.h', '.mm'} and path != STUBS:
        text = path.read_text(encoding='utf-8', errors='replace')
        names.update(f'f_{address}{suffix}' for address, suffix in symbol.findall(text))
        names.update(f'f_{address}_orig' for address in fence.findall(text))

table = args.gen / 'table.c'
if not table.is_file():
    raise SystemExit(f'{table} is missing; run tools/recomp.py first')
generated = set(re.findall(r'\bf_[0-9A-F]{8}\b', table.read_text(encoding='utf-8')))
collisions = sorted(name for name in names if name in generated)
if collisions:
    # The strong game function would silently replace the stub and run with Wind Waker HD semantics.
    # Generation without hooks emits no *_orig symbols, so only plain names can collide.
    raise SystemExit('Wind Waker HD guest symbols match Captain Toad functions: ' + ', '.join(collisions))

lines = ['// Generated by tools/patch_runtime.py: Wind Waker HD guest symbols named by the reference runtime.',
         '#include "ppc.h"', '']
for name in sorted(names):
    lines.append(f'__attribute__((weak)) void {name}(Cpu* __restrict c) {{ ppc_unimplemented(c, 0x{name[2:10]}u, 0); }}')
STUBS.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
print(f'runtime targets Kinopio.rpx; {len(names)} weak Wind Waker HD guest stubs, no collisions')
