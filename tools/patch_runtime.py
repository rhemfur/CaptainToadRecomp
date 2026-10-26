"""Prepare the reference game runtime (renderer, audio, input) for Captain Toad's generated code.

The reference runtime names the Wind Waker HD executable and calls Wind Waker HD guest functions
from its game-specific features. This script points the loader at Kinopio.rpx and writes weak stubs
for those guest symbols, following nsmbu-recomp tools/recomp/guest_stubs.py (MPL-2.0). A stub that
runs stops through ppc_unimplemented instead of executing unrelated Captain Toad code.
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('upstream', type=Path)
parser.add_argument('--gen', type=Path, default=Path('build/gen'), help='generated Captain Toad code')
args = parser.parse_args()
runtime = args.upstream / 'runtime'

# The reference's own extensions (tools/setup_reference.sh): a checkout reset since then would otherwise
# build without strict HLE and recompile without the profile's hooks. Both are idempotent.
for _tool in ('patch_reference.py', 'patch_diagnostic.py'):
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / _tool), str(args.upstream)], check=True)

# Exact-text changes, one module per area (tools/runtime_patches). Each reference file belongs to one
# area, so its changes apply in the order written there.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_patches import android, core, graphics, ui  # noqa: E402
REPLACEMENTS = {}
for _area in (core, graphics, ui, android):
    _shared = REPLACEMENTS.keys() & _area.REPLACEMENTS.keys()
    if _shared:
        raise SystemExit(f'{_area.__name__} changes files another area changes: {", ".join(sorted(_shared))}')
    REPLACEMENTS.update(_area.REPLACEMENTS)

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
HLE(gx2, GX2GetDisplayListWriteStatus) { ret(c, recording() != nullptr); }  // this thread records a display list
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
    'src/savestate.cpp': '''
// ---- Captain Toad additions (CaptainToadRecomp tools/patch_runtime.py)
namespace ss {
// Captain Toad's frame start (runtime/ct_frame.cpp): the full save and load requests of service(); the
// rest of it follows Wind Waker HD's scenes, events, portable states and automatic states.
void ct_service(Cpu* c) {
    (void)c;
    // test aids (TV frames), as in service(): WWHD_STATE_SAVE_AT=frame:slot,... / WWHD_STATE_LOAD_AT
    static const std::vector<Timed> save_at = parse_timed("WWHD_STATE_SAVE_AT"), load_at = parse_timed("WWHD_STATE_LOAD_AT");
    if (!save_at.empty() || !load_at.empty()) {
        static uint64_t last = 0;
        const uint64_t f = render::frame_count();
        for (auto& t : save_at)
            if (t.frame > last && t.frame <= f) request_save_full(t.slot);
        for (auto& t : load_at)
            if (t.frame > last && t.frame <= f) request_load(t.slot);
        last = f;
    }
    if (int slot = g_save_req.load()) {
        if (do_save(slot)) {
            g_save_req = 0;
            g_attempts = 0;
        }
        return;
    }
    std::shared_ptr<Snapshot> s;
    {
        std::lock_guard<std::mutex> lk(g_mu);
        s = g_load_ready;
    }
    if (s && do_load(s)) {
        if (s->load_applied) {
            g_last_load_frame = render::frame_count();
            g_last_load_step = interp::logic_steps();
        }
        {
            std::lock_guard<std::mutex> lk(g_mu);
            g_load_ready.reset();
        }
        g_loading = false;
        g_attempts = 0;
    }
}
}  // namespace ss
''',
}
# Captain Toad files that replace or join reference files
for source, relative in (('cheats.cpp', 'src/mods/cheats.cpp'), ('ct_save.h', 'src/mods/ct_save.h'),
                         ('ct_touch_menu.cpp', 'src/ct_touch_menu.cpp'), ('ct_touch_menu.h', 'src/ct_touch_menu.h')):
    text = (Path(__file__).resolve().parent.parent / 'runtime' / source).read_text(encoding='utf-8')
    (runtime / relative).write_text(text, encoding='utf-8', newline='\n')

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

# Names the player sees (window titles, menus, dialogs, overlay, logs, crash reports) and the per-user
# folders outside portable mode name Captain Toad. Only string literals change: comments keep naming
# the reference code they describe, and the vendored third-party code is left alone.
BRANDING = [
    ('The Legend of Zelda: The Wind Waker HD', 'Captain Toad: Treasure Tracker'),
    ('Wind Waker HD', 'Captain Toad'),
    ('captures/wwhd', 'captures/captain-toad'),
    ('./build/cmake/wwhd', 'captain-toad'),
    ('Application Support/wwhd', 'Application Support/Captain Toad'),
    ('Application Support/WWHD', 'Application Support/Captain Toad'),
    ('Library/Caches/wwhd', 'Library/Caches/org.ctrecomp.captaintoad'),
    ('/.config/wwhd', '/.config/captain-toad'),
]
literal = re.compile(r'"(?:[^"\\\n]|\\.)*"')
def rebrand(match):
    text = match.group(0)
    if text == '"/wwhd"':  # $XDG_CONFIG_HOME/wwhd (platform/host.h)
        return '"/captain-toad"'
    if text == '"/WWHD"':  # %APPDATA%/WWHD (platform/host.h)
        return '"/Captain Toad"'
    for old, new in BRANDING:
        text = text.replace(old, new)
    return text
for path in sorted((runtime / 'src').rglob('*')):
    if path.suffix not in {'.c', '.cpp', '.h', '.mm'} or 'third_party' in path.parts:
        continue
    source = path.read_text(encoding='utf-8')
    branded = literal.sub(rebrand, source)
    if branded != source:
        path.write_text(branded, encoding='utf-8', newline='\n')

# The Android app's own text and save checks: its texts in every language, the save export/import
# (Captain Toad's save is user/GameData.bin) and the setup notification. Java comments are left alone.
ANDROID_BRANDING = [
    ('The Wind Waker HD', 'Captain Toad: Treasure Tracker'),
    ('Wind Waker HD', 'Captain Toad'),
    ('code/cking.rpx', 'code/Kinopio.rpx'),
    ('user/cking.sav', 'user/GameData.bin'),
]
android_main = runtime.parent / 'android/app/src/main'
android_files = sorted(android_main.glob('res/values*/strings.xml')) + [
    android_main / 'java/org/wwhdrecomp/wwhd' / name for name in ('SaveFiles.java', 'SetupService.java')]
for path in android_files:
    source = path.read_text(encoding='utf-8')
    if path.suffix == '.java':
        def android_rebrand(match):
            text = match.group(0)
            for old, new in ANDROID_BRANDING:
                text = text.replace(old, new)
            return text
        branded = literal.sub(android_rebrand, source)
    else:
        branded = source
        for old, new in ANDROID_BRANDING:
            branded = branded.replace(old, new)
    if branded != source:
        path.write_text(branded, encoding='utf-8', newline='\n')

STUBS = runtime / 'src/ct_guest_stubs.c'
symbol = re.compile(r'\bf_([0-9A-F]{8})(_orig)?\b')
fence = re.compile(r'\bT60_FENCE_(?:LINK|ANY)\(([0-9A-F]{8})')  # pastes f_<address>_orig
names = set()
for path in sorted((runtime / 'src').rglob('*')):  # sources built into the game executable
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
