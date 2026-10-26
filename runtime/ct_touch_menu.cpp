// Captain Toad's Android menu button (android TouchControls.java, as patched by tools/patch_runtime.py):
// one button in the top left corner in place of the reference's view button, the touch controls'
// show/hide button and the tilt button. Its menu switches the view, shows or hides the touch controls,
// edits their layout, sets their opacity, turns the phone's gyro on or off, applies the save cheats
// (runtime/cheats.cpp) and opens the settings window. It also keeps the camera cutout setting
// (Settings > Display > Window). tools/patch_runtime.py copies this file and
// ct_touch_menu.h into the reference runtime (src/), so every build has the opacity setting the
// settings overlay shows.
#include <algorithm>
#include <atomic>
#include <cstdlib>
#include <mutex>
#include <string>

#include "ct_touch_menu.h"
#include "overlay/hostui.h"

namespace ct_touch {
namespace {
std::atomic<float> g_opacity{1.0f};
std::atomic<bool> g_cutout_clear{false};
std::once_flag g_loaded;
void load() {
    std::call_once(g_loaded, [] {
        std::string v;
        if (hostui::get("touchOpacity", v)) g_opacity = std::clamp((float)atof(v.c_str()), kOpacityMin, 1.0f);
        if (hostui::get("cutoutClear", v)) g_cutout_clear = atoi(v.c_str()) != 0;
    });
}
}  // namespace

float opacity() {
    load();
    return g_opacity;
}
void set_opacity(float o) {
    load();
    g_opacity = std::clamp(o, kOpacityMin, 1.0f);
    hostui::set("touchOpacity", std::to_string(g_opacity.load()));
}
bool cutout_clear() {
    load();
    return g_cutout_clear;
}
void set_cutout_clear(bool clear) {
    load();
    g_cutout_clear = clear;
    hostui::set("cutoutClear", clear ? "1" : "0");
}
}  // namespace ct_touch

#ifdef __ANDROID__
#include <jni.h>

#include "gfx/display_modes.h"
#include "mods/mods.h"
#include "motion/motion.h"
#include "overlay/overlay.h"
#include "runtime.h"

// The menu's state: bits 0-3 the view (gfx::DrcMode), bit 4 the phone's gyro moves the GamePad
extern "C" JNIEXPORT jint JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeMenuState(JNIEnv*, jclass) {
    return (hostui::drc_mode() & 15) | (motion::settings().source == motion::kDevice ? 16 : 0);
}
// the phone's gyro on or off, saved as Settings > Controls > Gyro's "device" source
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeToggleTilt(JNIEnv*, jclass) {
    hostui::post([] {
        motion::Settings g = motion::settings();
        g.source = g.source == motion::kDevice ? motion::kOff : motion::kDevice;
        if (g.source == motion::kDevice && g.tuning.sensitivity_x == motion::Tuning::kDefaultSensitivity &&
            g.tuning.sensitivity_y == motion::Tuning::kDefaultSensitivity)
            g.tuning.sensitivity_x = g.tuning.sensitivity_y = motion::default_sensitivity(motion::kDevice);
        LOG("[gyro] menu: phone gyro %s", g.source == motion::kDevice ? "on" : "off");
        motion::set_settings(g);
        for (const char* k : motion::kKeys) hostui::set(k, motion::value_of(g, k));
    });
}
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeOpenSettings(JNIEnv*, jclass) {
    overlay::set_open(true);
}
// which: ct_save cheat bits (runtime/ct_save.h). The save is edited and the game closes (cheats.cpp).
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeCheat(JNIEnv*, jclass, jint which) {
    mods::request_cheat(which);
}
extern "C" JNIEXPORT jfloat JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeOpacity(JNIEnv*, jclass) {
    return ct_touch::opacity();
}
// WwhdActivity lays the window out around a camera cutout or into it (TouchControls polls this)
extern "C" JNIEXPORT jboolean JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeCutoutClear(JNIEnv*, jclass) {
    return ct_touch::cutout_clear();
}
extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeSetOpacity(JNIEnv*, jclass, jfloat o) {
    hostui::post([o] { ct_touch::set_opacity(o); });
}
#endif
