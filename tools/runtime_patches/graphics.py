"""Captain Toad's exact-text changes to the reference runtime (tools/patch_runtime.py).

The Metal and Vulkan renderers, GX2, display modes and the shader decompiler.
"""
from .common import _ct_keep

REPLACEMENTS = {}
# A depth surface is one created for depth-buffer use, as Cemu's GX2CalculateSurfaceInfo decides.
# Name the formats, so an unsupported copy identifies itself.
REPLACEMENTS['src/gfx/vulkan/surfaces.cpp'] = [
    ('    auto sf=format_info(uint32_t(s->format.value()),bool(uint32_t(s->format.value())&0x800));\n'
     '    auto df=format_info(uint32_t(d->format.value()),bool(uint32_t(d->format.value())&0x800));\n',
     '    auto sf=format_info(uint32_t(s->format.value()),(s->resFlag&(1u<<2))!=0);  // GX2_RESFLAG_USAGE_DEPTH_BUFFER\n'
     '    auto df=format_info(uint32_t(d->format.value()),(d->resFlag&(1u<<2))!=0);\n'),
    ('        exception_report::raise("Unsupported CPU GX2CopySurface format layout");\n',
     '        exception_report::raise("Unsupported CPU GX2CopySurface format layout: " +\n'
     '            std::to_string(uint32_t(s->format.value())) + " tile " + std::to_string(uint32_t(s->tileMode.value())) + " -> " +\n'
     '            std::to_string(uint32_t(d->format.value())) + " tile " + std::to_string(uint32_t(d->tileMode.value())));\n'),
]
# updates run on the render thread in command order; draws advance each buffer's write offset.
REPLACEMENTS['src/gx2/gx2_cmd.h'] = [
    ('    OP_SUBMITTED_UNIFORMS,\n    OP_COUNT\n',
     '    OP_SUBMITTED_UNIFORMS,\n'
     '    OP_STREAMOUT_UPDATE,  // buffer index, mode (0 reset, 2 load from context, 3 save to context), context\n'
     '    OP_COUNT\n'),
]
REPLACEMENTS['src/gx2/gx2_core.cpp'] = [
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
]
REPLACEMENTS['src/gx2/gx2_resources.cpp'] = [
    ('        set_regs(mmSQ_VTX_SEMANTIC_0, tmp.at(mmSQ_VTX_SEMANTIC_0), nsem);\n    }\n}\n',
     '        set_regs(mmSQ_VTX_SEMANTIC_0, tmp.at(mmSQ_VTX_SEMANTIC_0), nsem);\n    }\n'
     '    if (ld32(vs + 0x110))  // usesStreamOut: per-buffer vertex strides in dwords (Cemu GX2_Shader.cpp)\n'
     '        for (uint32 i = 0; i < 4; i++) set_reg(mmVGT_STRMOUT_VTX_STRIDE_0 + i * 4, ld32(vs + 0x114 + 4 * i) >> 2);\n'
     '}\n'),
]
# Captain Toad is played on the GamePad (touch, gyro camera). On Android the phone starts with the TV
# picture drawn at the phone's shape (aspect.cpp "Match window", runtime/ct_frame.cpp), and a touch
# anywhere on it is a GamePad touch (overlay_hit below); the menu's Screen item switches.
REPLACEMENTS['src/gfx/display_modes.cpp'] = [
    ('std::atomic<int> g_mode{kDrcOff};\n',
     '#if defined(CT_FOREIGN_GUEST) && defined(__ANDROID__)\nstd::atomic<int> g_mode{kDrcOff};\n'
     '#elif defined(CT_FOREIGN_GUEST)\nstd::atomic<int> g_mode{kDrcGamePad};\n#else\n'
     'std::atomic<int> g_mode{kDrcOff};\n#endif  // Captain Toad GamePad view\n'),
    # The TV shows the GamePad's picture in Captain Toad: on Android a touch on the TV picture (TV only,
    # or outside the corner GamePad) touches the GamePad at the same place.
    ('    const Layout& L = g_tv_layout;\n    if (!L.pip_on || L.pip.w <= 0) return false;\n'
     '    float x = (nx * g_tv_dw - L.pip.x) / L.pip.w, y = (ny * g_tv_dh - L.pip.y) / L.pip.h;\n'
     '    if (!clamp_outside && (x < 0 || x > 1 || y < 0 || y > 1)) return false;\n',
     '    const Layout& L = g_tv_layout;\n'
     '#if defined(CT_FOREIGN_GUEST) && defined(__ANDROID__)\n'
     '    const bool on_pip = L.pip_on && L.pip.w > 0 && nx * g_tv_dw >= L.pip.x && ny * g_tv_dh >= L.pip.y &&\n'
     '        nx * g_tv_dw <= L.pip.x + L.pip.w && ny * g_tv_dh <= L.pip.y + L.pip.h;\n'
     '    Box P = on_pip || L.drc_only || L.tv.w <= 0 ? L.pip : L.tv;\n'
     '    if (P.w <= 0) return false;\n'
     '    // a picture wider than 16:9 (Settings > Display > Picture shape) shows more at the sides of the\n'
     '    // GamePad\'s 854x480: its middle 16:9 is the GamePad screen\n'
     '    if (P.w > P.h * 16.0f / 9.0f + 1.0f) {\n'
     '        const float w = P.h * 16.0f / 9.0f;\n'
     '        P.x += (P.w - w) / 2;\n'
     '        P.w = w;\n'
     '    }\n'
     '    float x = (nx * g_tv_dw - P.x) / P.w, y = (ny * g_tv_dh - P.y) / P.h;\n'
     '#else\n'
     '    if (!L.pip_on || L.pip.w <= 0) return false;\n'
     '    float x = (nx * g_tv_dw - L.pip.x) / L.pip.w, y = (ny * g_tv_dh - L.pip.y) / L.pip.h;\n'
     '#endif  // Captain Toad TV touch\n'
     '    if (!clamp_outside && (x < 0 || x > 1 || y < 0 || y > 1)) return false;\n'),
    # Android: one menu button (TouchControls.java, runtime/ct_touch_menu.cpp) replaces the view button,
    # the touch controls' show/hide button and the tilt button; WWHD_VIEW_BUTTON=1 still shows the view button.
    ('#ifdef __ANDROID__\n        return !e || atoi(e) != 0;\n#else\n',
     '#if defined(__ANDROID__) && !defined(CT_FOREIGN_GUEST)\n        return !e || atoi(e) != 0;\n#else\n'),
    ('bool overlay_hit(float nx, float ny, float* tx, float* ty, bool clamp_outside) {\n',
     '// ---- the picture-in-picture GamePad moved and resized with the pointer (display_modes.h)\n'
     'static int g_pip_drag = 0;  // 0 none, 1 move, 2 resize\n'
     'static float g_pip_grab_x = 0, g_pip_grab_y = 0;  // moving: the pointer minus the picture\'s centre\n'
     'static bool pip_under(const Layout& L, float x, float y) {\n'
     '    const Box& P = L.pip;\n'
     '    return L.pip_on && !L.drc_only && P.w > 0 && P.h > 0 && L.tv.w > 0 && L.tv.h > 0 && x >= P.x && y >= P.y &&\n'
     '        x <= P.x + P.w && y <= P.y + P.h;\n'
     '}\n'
     '// the picture with its centre at (cx, cy) in display units, `size` of the TV picture\'s width\n'
     'static void pip_put(const Layout& L, float cx, float cy, float size) {\n'
     '    g_pip_size = pip_clamp_size(size);\n'
     '    pip_set_position(pip_place(L.tv, L.pip.w / L.pip.h, g_pip_size, (cx - L.tv.x) / L.tv.w, (cy - L.tv.y) / L.tv.h));\n'
     '}\n'
     'bool pip_drag_begin(float nx, float ny) {\n'
     '    std::lock_guard<std::mutex> lk(g_layout_mu);\n'
     '    const Layout& L = g_tv_layout;\n'
     '    const float x = nx * g_tv_dw, y = ny * g_tv_dh;\n'
     '    if (!pip_under(L, x, y)) return false;\n'
     '    const Box& P = L.pip;\n'
     '    const float corner = std::max(12.0f, std::min(P.w, P.h) * 0.2f);\n'
     '    g_pip_drag = x > P.x + P.w - corner && y > P.y + P.h - corner ? 2 : 1;\n'
     '    g_pip_grab_x = x - (P.x + P.w / 2);\n'
     '    g_pip_grab_y = y - (P.y + P.h / 2);\n'
     '    return true;\n'
     '}\n'
     'bool pip_dragging() { return g_pip_drag != 0; }\n'
     'void pip_drag_move(float nx, float ny) {\n'
     '    std::lock_guard<std::mutex> lk(g_layout_mu);\n'
     '    const Layout& L = g_tv_layout;\n'
     '    if (!g_pip_drag || L.pip.w <= 0 || L.pip.h <= 0 || L.tv.w <= 0 || L.tv.h <= 0) return;\n'
     '    const float x = nx * g_tv_dw, y = ny * g_tv_dh;\n'
     '    if (g_pip_drag == 1) {\n'
     '        pip_put(L, x - g_pip_grab_x, y - g_pip_grab_y, g_pip_size);\n'
     '        return;\n'
     '    }\n'
     '    // resizing: the top-left corner stays, the bottom-right one follows the pointer\n'
     '    const float aspect = L.pip.w / L.pip.h;\n'
     '    const float w = pip_clamp_size(std::max({x - L.pip.x, (y - L.pip.y) * aspect, 1.0f}) / L.tv.w) * L.tv.w;\n'
     '    pip_put(L, L.pip.x + w / 2, L.pip.y + w / aspect / 2, w / L.tv.w);\n'
     '}\n'
     'bool pip_drag_end() {\n'
     '    const bool was = g_pip_drag != 0;\n'
     '    g_pip_drag = 0;\n'
     '    return was;\n'
     '}\n'
     'bool pip_wheel(float nx, float ny, float steps) {\n'
     '    std::lock_guard<std::mutex> lk(g_layout_mu);\n'
     '    const Layout& L = g_tv_layout;\n'
     '    if (!pip_under(L, nx * g_tv_dw, ny * g_tv_dh) || steps == 0) return false;\n'
     '    pip_put(L, L.pip.x + L.pip.w / 2, L.pip.y + L.pip.h / 2, g_pip_size * std::pow(1.1f, steps));\n'
     '    return true;\n'
     '}\n'
     'bool overlay_hit(float nx, float ny, float* tx, float* ty, bool clamp_outside) {\n'),
]
# The picture-in-picture GamePad moved and resized with the pointer (macOS TV window): a right-button
# or Option drag on the picture moves it (Custom placement), the same drag from its bottom-right corner
# resizes it, and the scroll wheel over it resizes it. A plain click stays a GamePad touch.
REPLACEMENTS['src/gfx/display.mm'] = [
    ('''- (void)mouseDown:(NSEvent*)e {
    float x, y;
    if ([self map:e x:&x y:&y clamp:false]) {
        self.touching = true;
''', '''// the picture-in-picture GamePad: a right-button or Option drag moves it (from its bottom-right corner:
// resizes it), the scroll wheel over it resizes it (display_modes.h)
- (void)point:(NSEvent*)e x:(float*)nx y:(float*)ny {
    NSPoint p = [self convertPoint:e.locationInWindow fromView:nil];
    NSSize sz = self.bounds.size;
    *nx = sz.width > 0 ? p.x / sz.width : 0;
    *ny = sz.height > 0 ? 1.0f - p.y / sz.height : 0;
}
- (bool)pipBegin:(NSEvent*)e {
    float nx, ny;
    [self point:e x:&nx y:&ny];
    if (!gfx::pip_drag_begin(nx, ny)) return false;
    [NSCursor.closedHandCursor push];
    return true;
}
- (bool)pipMove:(NSEvent*)e {
    if (!gfx::pip_dragging()) return false;
    float nx, ny;
    [self point:e x:&nx y:&ny];
    gfx::pip_drag_move(nx, ny);
    return true;
}
- (bool)pipEnd {
    if (!gfx::pip_drag_end()) return false;
    [NSCursor pop];
    gfx::save_options();
    return true;
}
- (void)rightMouseDown:(NSEvent*)e {
    if (![self pipBegin:e]) [super rightMouseDown:e];
}
- (void)rightMouseDragged:(NSEvent*)e {
    if (![self pipMove:e]) [super rightMouseDragged:e];
}
- (void)rightMouseUp:(NSEvent*)e {
    if (![self pipEnd]) [super rightMouseUp:e];
}
- (void)scrollWheel:(NSEvent*)e {
    float nx, ny;
    [self point:e x:&nx y:&ny];
    const float steps = e.hasPreciseScrollingDeltas ? e.scrollingDeltaY / 20.0f : e.scrollingDeltaY;
    if (gfx::pip_wheel(nx, ny, steps)) gfx::save_options();
    else [super scrollWheel:e];
}
- (void)mouseDown:(NSEvent*)e {
    float x, y;
    if ((e.modifierFlags & NSEventModifierFlagOption) && [self pipBegin:e]) return;
    if ([self map:e x:&x y:&y clamp:false]) {
        self.touching = true;
'''),
    ('''- (void)mouseDragged:(NSEvent*)e {
    float x, y;
    if (self.touching''', '''- (void)mouseDragged:(NSEvent*)e {
    float x, y;
    if ([self pipMove:e]) return;
    if (self.touching'''),
    ('''- (void)mouseUp:(NSEvent*)e {
    float x, y;
    if (!self.touching) return;''', '''- (void)mouseUp:(NSEvent*)e {
    float x, y;
    if ([self pipEnd]) return;
    if (!self.touching) return;'''),
]
REPLACEMENTS['src/gfx/display_modes.h'] = [
    ('void pip_set_position(PipPosition position);\n',
     'void pip_set_position(PipPosition position);\n'
     '// Pointer gestures on the picture-in-picture GamePad in the TV window (0..1 from the top left):\n'
     '// begin is true when the point is on the picture (a drag from its bottom-right corner resizes it,\n'
     '// any other drag moves it); end is true when a drag ended (the host saves the placement); wheel\n'
     '// resizes the picture under the point by 10% per step and is true when it did.\n'
     'bool pip_drag_begin(float nx, float ny);\n'
     'bool pip_dragging();\n'
     'void pip_drag_move(float nx, float ny);\n'
     'bool pip_drag_end();\n'
     'bool pip_wheel(float nx, float ny, float steps);\n'),
]
REPLACEMENTS['src/gfx/gamepad_ui_state.cpp'] = [
    ('void display_read_gamepad_ui() {\n    if (!display_gamepad_state_needed()) return;\n',
     'void display_read_gamepad_ui() {\n#ifdef CT_FOREIGN_GUEST\n    return;\n#endif\n    if (!display_gamepad_state_needed()) return;\n'),
]
REPLACEMENTS['src/gfx/renderer.cpp'] = [
    ('void set_cloud_style(int style) { g_cloud_style.store(std::clamp(style, 0, 2), std::memory_order_relaxed); }\n',
     '#ifdef CT_FOREIGN_GUEST\nvoid set_cloud_style(int) { g_cloud_style.store(0, std::memory_order_relaxed); }  // Wind Waker HD only\n#else\n'
     'void set_cloud_style(int style) { g_cloud_style.store(std::clamp(style, 0, 2), std::memory_order_relaxed); }\n#endif\n'),
    ('void set_cloud_shadows(bool on) { g_cloud_shadows.store(on, std::memory_order_relaxed); }\n',
     '#ifdef CT_FOREIGN_GUEST\nvoid set_cloud_shadows(bool) { g_cloud_shadows.store(false, std::memory_order_relaxed); }  // Wind Waker HD only\n#else\n'
     'void set_cloud_shadows(bool on) { g_cloud_shadows.store(on, std::memory_order_relaxed); }\n#endif\n'),
    ('void set_horizon_haze(float v) {\n', 'void set_horizon_haze(float v) {\n' + _ct_keep.format('v = 1.0f;  // Wind Waker HD only')),
    ('void set_bloom_strength(float v) {\n', 'void set_bloom_strength(float v) {\n' + _ct_keep.format('v = 1.0f;  // Wind Waker HD only')),
]
REPLACEMENTS['src/gfx/metal_draw.mm'] = [
    ('void set_ao_mode(int m) { g_ao_mode = m % 3;',
     'void set_ao_mode(int m) {\n' + _ct_keep.format('m = 0;  // Wind Waker HD only') + '    g_ao_mode = m % 3;'),
    ('void set_ao_hires(bool v) { g_ao_hires = v;',
     'void set_ao_hires(bool v) {\n' + _ct_keep.format('v = false;  // Wind Waker HD only') + '    g_ao_hires = v;'),
    # Stream-out on the GPU, as Cemu's Metal renderer does it: vertex shaders that write stream-out data
    # store it through a device pointer (sb) at each buffer's write offset, which gx2_core.cpp advances
    # after the draw, into a GPU shadow of the buffer that later draws read (never into guest memory). Draws with rasterization disabled run alone, in a pass
    # without attachments. Captain Toad's effects (particles and trails) are drawn from these buffers.
    ('    opt.strictMul = strictMul;\n',
     '    opt.strictMul = strictMul;\n'
     '    opt.useTFViaSSBO = vertex;  // stream-out writes go to a device buffer (sb)\n'),
    ('        cache_record_pipeline(regs, vs, ps, fsKey, tf);\n',
     '        if (ps) cache_record_pipeline(regs, vs, ps, fsKey, tf);  // no pixel shader: a stream-out-only draw\n'),
    ('    d.fragmentFunction = ps->fn;\n',
     '    d.fragmentFunction = ps ? ps->fn : nil;\n'
     '    if (!ps) d.rasterizationEnabled = NO;  // stream-out only: the vertex shader writes the buffers\n'),
    ('static void bind_stage(id<MTLRenderCommandEncoder> enc, const uint32_t* regs, Shader* sh, bool vertex, Surface* const* colors) {\n',
     '// ---- stream-out (Captain Toad)\n'
     '// The GPU runs a frame behind the game, and the game reuses small stream-out buffers from per-frame\n'
     '// memory, so the output never goes into guest memory: each buffer gets a shadow in one GPU arena\n'
     '// (seeded with the guest bytes; one arena, so the shader\'s one device pointer reaches every buffer),\n'
     '// and draws of this frame and the next that read the buffer read its shadow.\n'
     'static uint32_t g_so_vertices = 0;  // the current draw\'s vertices per instance (supportBuffer.verticesPerInstance)\n'
     'struct SoShadow { uint32_t base, size, at; uint64_t frame; };\n'
     'static std::vector<SoShadow> g_so_shadows;\n'
     'static id<MTLBuffer> g_so_arena = nil;\n'
     'static uint32_t g_so_used = 0;\n'
     'constexpr uint32_t kSoArena = 64u << 20;\n'
     'static uint32_t g_so_at[LATTE_NUM_STREAMOUT_BUFFER];  // the current draw\'s buffers: their shadows in the arena\n'
     '// the shadow holding `addr`, written this frame or the last, and the offset of addr in the arena\n'
     'static id<MTLBuffer> so_shadow(uint32_t addr, uint32_t* offset) {\n'
     '    for (auto& s : g_so_shadows)\n'
     '        if (addr - s.base < s.size && R.frame - s.frame <= 1) {\n'
     '            *offset = s.at + (addr - s.base);\n'
     '            return g_so_arena;\n'
     '        }\n'
     '    return nil;\n'
     '}\n'
     '// Shadows for the buffers the draw writes, made or reused. The shader drops writes past a buffer\'s\n'
     '// end, as the hardware does (supportBuffer.streamoutBufferEnd).\n'
     'static bool streamout_ready(const uint32_t* regs, const LatteDecompilerShader* dec, uint64_t vertices) {\n'
     '    if (!g_so_arena) g_so_arena = [R.device newBufferWithLength:kSoArena options:MTLResourceStorageModeShared];\n'
     '    if (!g_so_arena) return false;\n'
     '    for (int i = 0; i < LATTE_NUM_STREAMOUT_BUFFER; i++) {\n'
     '        if (dec->uniform.loc_streamoutBufferBase[i] < 0) continue;\n'
     '        const uint32_t base = regs[mmVGT_STRMOUT_BUFFER_BASE_0 + i * 4], size = regs[mmVGT_STRMOUT_BUFFER_SIZE_0 + i * 4] << 2;\n'
     '        const uint32_t offset = regs[mmVGT_STRMOUT_BUFFER_OFFSET_0 + i * 4];\n'
     '        if (!base || !size || size > kSoArena / 4 || offset > size || !mem::ptr(base)) {\n'
     '            static int logged = 0;\n'
     '            if (logged++ < 8)\n'
     '                LOG("[gfx] stream-out draw skipped: buffer %d at %08X size %X offset %X (%llu vertices)", i, base, size, offset,\n'
     '                    (unsigned long long)vertices);\n'
     '            return false;\n'
     '        }\n'
     '        SoShadow* shadow = nullptr;\n'
     '        for (auto it = g_so_shadows.begin(); it != g_so_shadows.end();) {\n'
     '            if (it->base == base && it->size == size) { shadow = &*it; break; }\n'
     '            // another buffer over the same bytes (the game reused the memory): forget the old one\n'
     '            if (base < it->base + it->size && it->base < base + size) it = g_so_shadows.erase(it);\n'
     '            else ++it;\n'
     '        }\n'
     '        if (!shadow) {\n'
     '            if (g_so_used + size > kSoArena) {  // full: start over (older shadows are long read)\n'
     '                g_so_shadows.clear();\n'
     '                g_so_used = 0;\n'
     '            }\n'
     '            memcpy((uint8_t*)g_so_arena.contents + g_so_used, mem::ptr(base), size);\n'
     '            g_so_shadows.push_back({base, size, g_so_used, R.frame});\n'
     '            g_so_used += (size + 255) & ~255u;\n'
     '            shadow = &g_so_shadows.back();\n'
     '        }\n'
     '        shadow->frame = R.frame;\n'
     '        g_so_at[i] = shadow->at;\n'
     '    }\n'
     '    return true;\n'
     '}\n'
     'static void bind_stage(id<MTLRenderCommandEncoder> enc, const uint32_t* regs, Shader* sh, bool vertex, Surface* const* colors) {\n'),
    ('            sz[1] = (regs[REGADDR::SQ_TEX_RESOURCE_WORD0_N_PS + t * 7 + 1] & 0x1FFF) + 1;\n        }\n'
     '        if (buf.size() <= 4096) {\n',
     '            sz[1] = (regs[REGADDR::SQ_TEX_RESOURCE_WORD0_N_PS + t * 7 + 1] & 0x1FFF) + 1;\n        }\n'
     '        if (vertex && dec->uniform.loc_verticesPerInstance >= 0) {  // stream-out (streamout_ready checked the buffers)\n'
     '            *(sint32*)at(dec->uniform.loc_verticesPerInstance) = (sint32)g_so_vertices;\n'
     '            for (int i = 0; i < LATTE_NUM_STREAMOUT_BUFFER; i++) {\n'
     '                if (dec->uniform.loc_streamoutBufferBase[i] < 0) continue;\n'
     '                *(sint32*)at(dec->uniform.loc_streamoutBufferBase[i]) = (sint32)(g_so_at[i] + regs[mmVGT_STRMOUT_BUFFER_OFFSET_0 + i * 4]);\n'
     '                *(sint32*)at(dec->uniform.loc_streamoutBufferBase[i] + 4) = (sint32)(g_so_at[i] + (regs[mmVGT_STRMOUT_BUFFER_SIZE_0 + i * 4] << 2));\n'
     '                if (rm.tfStorageBindingPoint >= 0) [enc setVertexBuffer:g_so_arena offset:0 atIndex:rm.tfStorageBindingPoint];\n'
     '            }\n'
     '        }\n'
     '        if (buf.size() <= 4096) {\n'),
    ('// ---------------------------------------------------------------- draw\n',
     '// A stream-out draw with rasterization disabled: only its vertex shader runs, writing the stream-out\n'
     '// buffers, in a pass without attachments (kept open for the next such draw).\n'
     'static bool streamout_only(const uint32_t* regs, Shader* vs, LatteFetchShader* fs, uint64_t fsKey, uint32_t prim, uint32_t count,\n'
     '                           uint32_t indexType, uint32_t indexAddr, uint32_t baseVertex, uint32_t instances) {\n'
     '    if (!vs || !vs->dec) return false;\n'
     '    retry_failed_compile(vs, false);\n'
     '    if (vs->state == CS_FAILED) return false;\n'
     '    compile_deferred(vs);\n'
     '    if (!wait_compiled(vs->state) || !vs->dec->hasStreamoutBufferWrite) return false;\n'
     '    static std::vector<uint32_t> indices;\n'
     '    MTLPrimitiveType ptype;\n'
     '    if (!build_indices(prim, count, indexType, indexAddr, indices, ptype)) return false;\n'
     '    uint64_t span = uint64_t(baseVertex) + count;\n'
     '    for (uint32_t i : indices) span = std::max<uint64_t>(span, uint64_t(baseVertex) + i + 1);\n'
     '    if (!streamout_ready(regs, vs->dec, span + uint64_t(count) * (instances - 1))) return false;\n'
     '    TargetFormats none;\n'
     '    id<MTLRenderPipelineState> pipe = get_pipeline(regs, vs, nullptr, fs, fsKey, none);\n'
     '    if (!pipe) return false;\n'
     '    bool open = R.enc && !R.passDepth;\n'
     '    for (auto* c : R.passColor) open = open && !c;\n'
     '    if (!open) {\n'
     '        end_encoder();\n'
     '        MTLRenderPassDescriptor* rp = [MTLRenderPassDescriptor renderPassDescriptor];\n'
     '        rp.renderTargetWidth = 1;\n'
     '        rp.renderTargetHeight = 1;\n'
     '        rp.defaultRasterSampleCount = 1;\n'
     '        R.enc = [command_buffer() renderCommandEncoderWithDescriptor:rp];\n'
     '        if (!R.enc) return false;\n'
     '        for (auto& c : R.passColor) c = nullptr;\n'
     '        R.passDepth = nullptr;\n'
     '    }\n'
     '    id<MTLRenderCommandEncoder> enc = R.enc;\n'
     '    [enc setRenderPipelineState:pipe];\n'
     '    for (auto& g : fs->bufferGroups) {\n'
     '        uint32_t off = 0;\n'
     '        const uint32_t addr = regs[mmSQ_VTX_ATTRIBUTE_BLOCK_START + g.attributeBufferIndex * 7];\n'
     '        id<MTLBuffer> b = so_shadow(addr, &off);\n'
     '        if (!b) b = guest_buffer(addr, &off);\n'
     '        if (b) [enc setVertexBuffer:b offset:off atIndex:GET_MTL_VERTEX_BUFFER_INDEX(g.attributeBufferIndex)];\n'
     '    }\n'
     '    Surface* noColors[8] = {};\n'
     '    g_so_vertices = count;\n'
     '    R.binding = true;\n'
     '    bind_stage(enc, regs, vs, true, noColors);\n'
     '    R.binding = false;\n'
     '    if (indices.empty()) {\n'
     '        [enc drawPrimitives:ptype vertexStart:baseVertex vertexCount:count instanceCount:instances];\n'
     '    } else {\n'
     '        Upload u = upload(indices.data(), (uint32_t)(indices.size() * 4));\n'
     '        [enc drawIndexedPrimitives:ptype indexCount:indices.size() indexType:MTLIndexTypeUInt32 indexBuffer:u.buf\n'
     '                 indexBufferOffset:u.offset instanceCount:instances baseVertex:baseVertex baseInstance:0];\n'
     '    }\n'
     '    [enc memoryBarrierWithScope:MTLBarrierScopeBuffers afterStages:MTLRenderStageVertex beforeStages:MTLRenderStageVertex];\n'
     '    static bool logged = false;\n'
     '    if (!logged) { logged = true; LOG("[gfx] stream-out: vertex shaders write their buffers on the GPU"); }\n'
     '    return true;\n'
     '}\n'
     '// ---------------------------------------------------------------- draw\n'),
    ('    if (regs[REGADDR::PA_CL_CLIP_CNTL] & (1 << 22)) { g_skip[SK_RASTER_KILL]++; return; }  // rasterization disabled\n',
     '    const bool rasterKill = (regs[REGADDR::PA_CL_CLIP_CNTL] & (1 << 22)) != 0;  // rasterization disabled\n'
     '    if (rasterKill && !regs[mmVGT_STRMOUT_EN]) { g_skip[SK_RASTER_KILL]++; return; }\n'),
    ('    Shader* ps = get_shader(regs, false, fs, fsKey);\n',
     '    if (rasterKill) {  // stream-out only\n'
     '        if (!streamout_only(regs, vs, fs, fsKey, prim, count, indexType, indexAddr, baseVertex, instances)) g_skip[SK_RASTER_KILL]++;\n'
     '        return;\n'
     '    }\n'
     '    Shader* ps = get_shader(regs, false, fs, fsKey);\n'),
    ('        if (g_snapshot && size <= kSnapshotLimit) {\n',
     '        uint32_t soOff = 0;  // stream-out output of this frame or the last: its shadow\n'
     '        if (id<MTLBuffer> shadow = so_shadow(addr, &soOff)) {\n'
     '            [enc setVertexBuffer:shadow offset:soOff atIndex:GET_MTL_VERTEX_BUFFER_INDEX(g.attributeBufferIndex)];\n'
     '            continue;\n'
     '        }\n'
     '        if (g_snapshot && size <= kSnapshotLimit) {\n'),
    ('        R.binding = true;\n        bind_stage(enc, regs, vs, true, colors);\n',
     '        g_so_vertices = count;\n'
     '        const bool streamout = vs->dec->uniform.loc_verticesPerInstance >= 0;\n'
     '        if (streamout) {\n'
     '            uint64_t span = uint64_t(baseVertex) + count;\n'
     '            for (uint32_t i : indices) span = std::max<uint64_t>(span, uint64_t(baseVertex) + i + 1);\n'
     '            if (!streamout_ready(regs, vs->dec, span + uint64_t(count) * (instances - 1))) { g_skip[SK_NO_SHADER]++; return; }\n'
     '        }\n'
     '        R.binding = true;\n        bind_stage(enc, regs, vs, true, colors);\n'),
    ('    for (int i = 0; i < 8; i++)\n        if (colors[i] && regs[mmCB_COLOR0_BASE + i]) g_target_drawn[regs[mmCB_COLOR0_BASE + i]].drawn(R.frame);\n',
     '    if (vs->dec->uniform.loc_verticesPerInstance >= 0)  // later draws read the stream-out output\n'
     '        [enc memoryBarrierWithScope:MTLBarrierScopeBuffers afterStages:MTLRenderStageVertex beforeStages:MTLRenderStageVertex];\n'
     '    for (int i = 0; i < 8; i++)\n        if (colors[i] && regs[mmCB_COLOR0_BASE + i]) g_target_drawn[regs[mmCB_COLOR0_BASE + i]].drawn(R.frame);\n'),
]
# Stream-out on Metal: each buffer's end (bytes, after its base in the support buffer) bounds the
# vertex shader's writes, which the hardware drops past a buffer's end (draws often emit more vertices
# than their buffer holds).
REPLACEMENTS['third_party/cemu/Cafe/HW/Latte/LegacyShaderDecompiler/LatteDecompilerEmitMSLHeader.hpp'] = [
    ('\t\t\t\t\tsrc->addFmt("int streamoutBufferBase{};" _CRLF, i);\n'
     '\t\t\t\t\tuniformOffsets.offset_streamoutBufferBase[i] = uniformCurrentOffset;\n'
     '\t\t\t\t\tuniformCurrentOffset += 4;\n',
     '\t\t\t\t\tsrc->addFmt("int streamoutBufferBase{};" _CRLF, i);\n'
     '\t\t\t\t\tuniformOffsets.offset_streamoutBufferBase[i] = uniformCurrentOffset;\n'
     '\t\t\t\t\tuniformCurrentOffset += 4;\n'
     '\t\t\t\t\tsrc->addFmt("int streamoutBufferEnd{};" _CRLF, i);  // Captain Toad: bounds the writes\n'
     '\t\t\t\t\tuniformCurrentOffset += 4;\n'),
]
REPLACEMENTS['third_party/cemu/Cafe/HW/Latte/LegacyShaderDecompiler/LatteDecompilerEmitMSL.cpp'] = [
    ('\t\t\tsrc->addFmt("sb[sbBase{} + {}]", streamoutBufferIndex, u32Offset);\n',
     '\t\t\tsrc->addFmt("if (sbBase{0} + {1} < supportBuffer.streamoutBufferEnd{0} / 4) sb[sbBase{0} + {1}]", streamoutBufferIndex, u32Offset);\n'),
]
REPLACEMENTS['src/gfx/vulkan/settings.cpp'] = [
    ('void set_ao_mode(int v) { settings().ao.store(normalize(v),std::memory_order_relaxed);',
     'void set_ao_mode(int v) {\n' + _ct_keep.format('v = 0;  // Wind Waker HD only') + '    settings().ao.store(normalize(v),std::memory_order_relaxed);'),
    ('void set_ao_hires(bool v) { settings().hires.store(v,std::memory_order_relaxed);',
     'void set_ao_hires(bool v) {\n' + _ct_keep.format('v = false;  // Wind Waker HD only') + '    settings().hires.store(v,std::memory_order_relaxed);'),
]
# Internal resolution "Screen" (Vulkan): 0 asks for the factor that draws the picture on screen (the
# 1280x720 TV picture, or the 854x480 GamePad picture in GamePad-only mode) with as many pixels as it
# covers in the TV window (in steps of 1/16), so a phone draws at its panel's resolution. Captain Toad on
# Android starts with it; a saved choice and WWHD_RES_SCALE still win.
REPLACEMENTS['src/gfx/display_modes.h'] += [
    ('bool main_picture(float* x, float* y, float* w, float* h);\n',
     'bool main_picture(float* x, float* y, float* w, float* h);\n'
     'bool main_picture_is_gamepad();  // that picture is the GamePad\'s (Captain Toad screen resolution)\n'),
]
REPLACEMENTS['src/gfx/display_modes.cpp'] += [
    ('// ---------------------------------------------------------------- view button (touch screens)\n',
     'bool main_picture_is_gamepad() {\n'
     '    std::lock_guard<std::mutex> lk(g_layout_mu);\n'
     '    return g_tv_layout.drc_only;\n'
     '}\n'
     '\n'
     '// ---------------------------------------------------------------- view button (touch screens)\n'),
]
REPLACEMENTS['src/gfx/vulkan/surfaces.cpp'] += [
    ('#include "dynres.h"\n', '#include "dynres.h"\n#include "../display_modes.h"\n'),
    # before the first frame's latch: 1x, never 0
    ('static float g_res_frame = g_res_requested.load();  // render thread: the factor for this frame\n',
     'static float g_res_frame = std::max(g_res_requested.load(), 1.0f);  // render thread: the factor for this frame\n'),
    ('static float parse_scale(const char* e) {\n    float f = e ? (float)atof(e) : 1.0f;\n',
     'static float parse_scale(const char* e) {\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '#ifdef __ANDROID__\n'
     '    if (!e) return 0.0f;  // the screen\'s own resolution\n'
     '#endif\n'
     '    if (e && atof(e) == 0) return 0.0f;\n'
     '#endif  // Captain Toad screen resolution\n'
     '    float f = e ? (float)atof(e) : 1.0f;\n'),
    ('void set_res_scale(float f) {\n    g_res_requested = std::clamp(std::isfinite(f) ? f : 1.0f, 1.0f, 4.0f);\n',
     'void set_res_scale(float f) {\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    if (f == 0) {\n'
     '        g_res_requested = 0;\n'
     '        LOG("[gfx] internal resolution: the screen\'s");\n'
     '        return;\n'
     '    }\n'
     '#endif  // Captain Toad screen resolution\n'
     '    g_res_requested = std::clamp(std::isfinite(f) ? f : 1.0f, 1.0f, 4.0f);\n'),
    ('void latch_res_scale() {\n',
     '#ifdef CT_FOREIGN_GUEST\n'
     '// the factor that draws the picture on screen (TV 720 lines, GamePad 480) with the TV window\'s pixels\n'
     '// it covers, in steps of 1/16 so that resizing a window does not make new render targets every pixel\n'
     'static float screen_res_scale() {\n'
     '    float x, y, w, h;\n'
     '    const float pixels = float(R.tv.swapExtent.height);\n'
     '    if (pixels <= 0 || !gfx::main_picture(&x, &y, &w, &h)) return 1.0f;\n'
     '    // the TV\'s 720 lines: its buffers are also the GamePad picture\'s source; the GamePad\'s own 480\n'
     '    // apart (gfx::g_ct_pad_scale)\n'
     '    auto factor = [&](float lines) { return std::clamp(std::round(h * pixels / lines * 16.0f) / 16.0f, 1.0f, 4.0f); };\n'
     '    if (!gfx::main_picture_is_gamepad()) return factor(720.0f);\n'
     '    // GamePad only: the course reaches the screen through the GamePad\'s buffers, so the TV\'s need no\n'
     '    // more lines than those hold (480 at up to 4x)\n'
     '    gfx::g_ct_pad_scale = factor(480.0f);\n'
     '    return std::max(1.0f, std::floor(gfx::g_ct_pad_scale * 480.0f / 720.0f * 16.0f) / 16.0f);\n'
     '}\n'
     '#endif  // Captain Toad screen resolution\n'
     'void latch_res_scale() {\n'),
    ('    g_res_frame = g_res_requested.load(std::memory_order_relaxed);\n    latch_aspect();\n',
     '    g_res_frame = g_res_requested.load(std::memory_order_relaxed);\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    gfx::g_ct_pad_scale = 0;\n'
     '    if (g_res_frame == 0) g_res_frame = screen_res_scale();\n'
     '#endif  // Captain Toad screen resolution\n'
     '    latch_aspect();\n'),
]
# The same "Screen" resolution with Metal (macOS): the TV window's drawable sets the factor, so GamePad only
# on a 4K screen draws the GamePad's 854x480 at 4x instead of the 3x that suits the TV's 1280x720. The
# Graphics menu and Settings > Graphics offer it; it is saved as resScale 0.
REPLACEMENTS['src/gfx/metal_surfaces.mm'] = REPLACEMENTS.get('src/gfx/metal_surfaces.mm', []) + [
    ('#include "mods/cemu_pack.h"\n', '#include "mods/cemu_pack.h"\n#include "gfx/display_modes.h"\n'),
    ('static float parse_scale(const char* e) {\n    float f = e ? (float)atof(e) : 1.0f;\n',
     'static float parse_scale(const char* e) {\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    if (e && atof(e) == 0) return 0.0f;  // the screen\'s resolution\n'
     '#endif  // Captain Toad screen resolution\n'
     '    float f = e ? (float)atof(e) : 1.0f;\n'),
    ('static float g_res_frame = g_res_requested.load();\n',
     'static float g_res_frame = std::max(g_res_requested.load(), 1.0f);\n'),
    ('void set_res_scale(float f) {\n    g_res_requested = std::clamp(f, 1.0f, 4.0f);\n',
     'void set_res_scale(float f) {\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    if (f == 0) {\n'
     '        g_res_requested = 0;\n'
     '        LOG("[gfx] internal resolution: the screen\'s");\n'
     '        return;\n'
     '    }\n'
     '#endif  // Captain Toad screen resolution\n'
     '    g_res_requested = std::clamp(f, 1.0f, 4.0f);\n'),
    ('void latch_res_scale() {\n',
     '#ifdef CT_FOREIGN_GUEST\n'
     '// the factor that draws the picture on screen (TV 720 lines, GamePad 480) with the TV window\'s pixels\n'
     '// it covers, in steps of 1/16 so that resizing a window does not make new render targets every pixel\n'
     'static float screen_res_scale() {\n'
     '    float x, y, w, h;\n'
     '    const float pixels = R.tv.layer ? float(R.tv.layer.drawableSize.height) : 0.0f;\n'
     '    if (pixels <= 0 || !gfx::main_picture(&x, &y, &w, &h)) return 1.0f;\n'
     '    // the TV\'s 720 lines: its buffers are also the GamePad picture\'s source; the GamePad\'s own 480\n'
     '    // apart (gfx::g_ct_pad_scale)\n'
     '    auto factor = [&](float lines) { return std::clamp(std::round(h * pixels / lines * 16.0f) / 16.0f, 1.0f, 4.0f); };\n'
     '    if (!gfx::main_picture_is_gamepad()) return factor(720.0f);\n'
     '    // GamePad only: the course reaches the screen through the GamePad\'s buffers, so the TV\'s need no\n'
     '    // more lines than those hold (480 at up to 4x)\n'
     '    gfx::g_ct_pad_scale = factor(480.0f);\n'
     '    return std::max(1.0f, std::floor(gfx::g_ct_pad_scale * 480.0f / 720.0f * 16.0f) / 16.0f);\n'
     '}\n'
     '#endif  // Captain Toad screen resolution\n'
     'void latch_res_scale() {\n'),
    ('    g_res_frame = g_res_requested.load(std::memory_order_relaxed);\n    latch_aspect();\n',
     '    g_res_frame = g_res_requested.load(std::memory_order_relaxed);\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    gfx::g_ct_pad_scale = 0;\n'
     '    if (g_res_frame == 0) {\n'
     '        g_res_frame = screen_res_scale();\n'
     '        static float logged = 0;\n'
     '        if (g_res_frame != logged) LOG("[gfx] screen resolution: %gx", logged = g_res_frame);\n'
     '    }\n'
     '#endif  // Captain Toad screen resolution\n'
     '    latch_aspect();\n'),
]
# The GamePad's buffers draw at 1x in TV only, where its picture is shown nowhere (the game still draws it
# each frame). The TV's buffers never do: Captain Toad draws its course once, into the TV's buffers, and
# copies it to the GamePad, so they are the GamePad picture's source in GamePad only too. With the Screen
# resolution in GamePad only, the TV's buffers get the factor for the lines the GamePad picture covers
# (720 of them in it) and the GamePad's own (its 2D layers) theirs: ct_screen_pad_scale.
REPLACEMENTS['src/gfx/display_modes.h'] += [
    ('extern std::atomic<bool> g_touch_controller, g_touch_controls;\n',
     'extern std::atomic<bool> g_touch_controller, g_touch_controls;\n'
     '// Captain Toad: 2 the GamePad\'s picture is shown nowhere (TV only): the renderers draw its buffers\n'
     '// at 1x (display_plan sets it)\n'
     'extern std::atomic<int> g_ct_hidden_screen;\n'
     'bool ct_gamepad_sized(uint32_t width, uint32_t height);  // 854x480 or one of its halvings\n'
     'bool ct_hidden_target(uint32_t width, uint32_t height, uint32_t slices);  // a buffer of that screen\n'
     '// with the Screen resolution in GamePad only: the factor for the GamePad\'s own buffers (render thread,\n'
     '// set where the factor is latched; 0 otherwise)\n'
     'extern float g_ct_pad_scale;\n'),
]
REPLACEMENTS['src/gfx/display_modes.cpp'] += [
    ('std::atomic<bool> g_has_drc_window{false};\n',
     'std::atomic<bool> g_has_drc_window{false};\n'
     'std::atomic<int> g_ct_hidden_screen{0};\n'
     'float g_ct_pad_scale = 0;\n'
     'bool ct_gamepad_sized(uint32_t width, uint32_t height) {\n'
     '    for (uint32_t w = 854, h = 480; w >= 32; w >>= 1, h >>= 1)\n'
     '        if ((width == w || width == w + 1) && height == h) return true;\n'
     '    return false;\n'
     '}\n'
     'bool ct_hidden_target(uint32_t width, uint32_t height, uint32_t slices) {\n'
     '    return g_ct_hidden_screen.load(std::memory_order_relaxed) == 2 && slices == 1 && ct_gamepad_sized(width, height);\n'
     '}\n'),
    ('    if (have_tv || drc_only) L = layout(dw, dh, have_tv ? tw : 0, have_tv ? th : 0, have_drc ? pw : 0, have_drc ? ph : 0, pip, drc_only);\n',
     '    if (have_tv || drc_only) L = layout(dw, dh, have_tv ? tw : 0, have_tv ? th : 0, have_drc ? pw : 0, have_drc ? ph : 0, pip, drc_only);\n'
     '#ifdef CT_FOREIGN_GUEST\n'
     '    g_ct_hidden_screen = !L.drc_only && g_mode == kDrcOff && !g_has_drc_window && !pip ? 2 : 0;\n'
     '#endif  // Captain Toad hidden screen at 1x\n'),
]
_ct_hidden_scale = ('#ifdef CT_FOREIGN_GUEST\n'
    '    if (gfx::ct_hidden_target(s->width, s->height, s->slices)) return 1.0f;  // Captain Toad: shown nowhere\n'
    '#endif\n')
_ct_pad_scale = ('#ifdef CT_FOREIGN_GUEST\n'
    '    if (gfx::g_ct_pad_scale > 0 && s->slices == 1 && gfx::ct_gamepad_sized(s->width, s->height))\n'
    '        return gfx::g_ct_pad_scale * g_dyn_frame;  // Captain Toad: the GamePad\'s own, Screen resolution\n'
    '#endif\n')
for _file in ('src/gfx/metal_surfaces.mm', 'src/gfx/vulkan/surfaces.cpp'):
    REPLACEMENTS[_file] = REPLACEMENTS.get(_file, []) + [
        ('    if (s->slices > 1) return res_scale();\n    return res_scale() * g_dyn_frame;\n',
         _ct_hidden_scale + _ct_pad_scale + '    if (s->slices > 1) return res_scale();\n    return res_scale() * g_dyn_frame;\n'),
    ]
    REPLACEMENTS[_file] += [
        ('    if (g_dyn_frame == 1.0f || s->fmt.compressed || s->mips > 1 || s->slices > 1) return 1.0f;\n',
         '    if (g_dyn_frame == 1.0f || s->fmt.compressed || s->mips > 1 || s->slices > 1) return 1.0f;\n' + _ct_hidden_scale),
    ]
REPLACEMENTS['src/gfx/vulkan/backend.cpp'] = [
    # the window title names the factor in use
    ('          double(requested_res_scale()), fxaa_enabled() ? " · FXAA" : "");\n',
     '          double(requested_res_scale() > 0 ? requested_res_scale() : res_scale()), fxaa_enabled() ? " · FXAA" : "");\n'),
]
# Captain Toad's GamePad shows the same course as the TV, drawn with its own camera (runtime/ct_frame.cpp):
# with a wider picture shape its screen-sized buffers widen too, so GamePad only fills the screen as well.
_ct_drc_shape = ('#ifndef CT_FOREIGN_GUEST  // Captain Toad: the GamePad\'s picture takes the shape too\n', '#endif\n')
REPLACEMENTS['src/gfx/metal_surfaces.mm'] = REPLACEMENTS.get('src/gfx/metal_surfaces.mm', []) + [
    ('    for (uint32_t w = 854, h = 480; w >= 32; w >>= 1, h >>= 1)\n'
     '        if ((s->width == w || s->width == w + 1) && s->height == h) return false;\n',
     _ct_drc_shape[0] + '    for (uint32_t w = 854, h = 480; w >= 32; w >>= 1, h >>= 1)\n'
     '        if ((s->width == w || s->width == w + 1) && s->height == h) return false;\n' + _ct_drc_shape[1]),
]
REPLACEMENTS['src/gfx/vulkan/surfaces.cpp'] = REPLACEMENTS.get('src/gfx/vulkan/surfaces.cpp', []) + [
    ('    for (uint32_t w = 854, h = 480; w >= 32; w >>= 1, h >>= 1)\n'
     '        if ((width == w || width == w + 1) && height == h) return false;\n',
     _ct_drc_shape[0] + '    for (uint32_t w = 854, h = 480; w >= 32; w >>= 1, h >>= 1)\n'
     '        if ((width == w || width == w + 1) && height == h) return false;\n' + _ct_drc_shape[1]),
]
