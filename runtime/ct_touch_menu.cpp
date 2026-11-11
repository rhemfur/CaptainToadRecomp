// Captain Toad's Android menu button (android TouchControls.java, as patched by tools/patch_runtime.py):
// one button in the top left corner in place of the reference's view button, the touch controls'
// show/hide button and the tilt button. It opens the settings window, where everything it offered is
// now: the view, the touch controls and their opacity, the phone's gyro and the layout editor (Settings >
// Display > Touch controls) and the save cheats (Settings > Cheats, runtime/cheats.cpp). A long press
// still starts the layout editor. It also keeps the camera cutout setting (Settings > Display > Window).
// tools/patch_runtime.py copies this file and ct_touch_menu.h into the reference runtime (src/), so
// every build has the opacity setting the settings overlay shows.
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

#include "motion/motion.h"
#include "overlay/overlay.h"
#include "runtime.h"

namespace ct_touch {
namespace {
std::atomic<bool> g_edit_layout{false};
}
bool tilt() { return motion::settings().source == motion::kDevice; }
void set_tilt(bool on) {
    motion::Settings g = motion::settings();
    g.source = on ? motion::kDevice : motion::kOff;
    if (on && g.tuning.sensitivity_x == motion::Tuning::kDefaultSensitivity &&
        g.tuning.sensitivity_y == motion::Tuning::kDefaultSensitivity)
        g.tuning.sensitivity_x = g.tuning.sensitivity_y = motion::default_sensitivity(motion::kDevice);
    LOG("[gyro] touch controls: phone gyro %s", on ? "on" : "off");
    motion::set_settings(g);
    for (const char* k : motion::kKeys) hostui::set(k, motion::value_of(g, k));
}
void request_edit_layout() { g_edit_layout = true; }
}  // namespace ct_touch

extern "C" JNIEXPORT void JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeOpenSettings(JNIEnv*, jclass) {
    overlay::set_open(true);
}
// Settings > Display > Touch controls > Move and resize (polled ten times a second)
extern "C" JNIEXPORT jboolean JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeTakeEditLayout(JNIEnv*, jclass) {
    return ct_touch::g_edit_layout.exchange(false);
}
extern "C" JNIEXPORT jfloat JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeOpacity(JNIEnv*, jclass) {
    return ct_touch::opacity();
}
// WwhdActivity lays the window out around a camera cutout or into it (TouchControls polls this)
extern "C" JNIEXPORT jboolean JNICALL Java_org_wwhdrecomp_wwhd_TouchControls_nativeCutoutClear(JNIEnv*, jclass) {
    return ct_touch::cutout_clear();
}
#endif
