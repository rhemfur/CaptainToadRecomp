// Captain Toad's Android screen options (runtime/ct_touch_menu.cpp): the on-screen controls' opacity
// (Settings > Display > Touch controls and the menu button's menu; android TouchControls.java draws with
// it) and the camera cutout (Settings > Display > Window; android WwhdActivity.java lays the window out).
#pragma once

namespace ct_touch {
constexpr float kOpacityMin = 0.1f;
float opacity();            // 0.1..1 (1: as the reference draws the controls), saved in settings.ini
void set_opacity(float o);  // main thread
// true: the picture keeps clear of a punch-hole or notch camera (a black bar along that edge); false: it
// uses the screen up to the edge around the camera, as the reference does. Saved in settings.ini.
bool cutout_clear();
void set_cutout_clear(bool clear);  // main thread
}  // namespace ct_touch
