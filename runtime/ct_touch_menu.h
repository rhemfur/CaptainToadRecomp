// Captain Toad's Android screen options (runtime/ct_touch_menu.cpp), all in the settings window that the
// menu button opens: the on-screen controls' opacity, the phone's gyro and the layout editor (Settings >
// Display > Touch controls; android TouchControls.java draws with the opacity and runs the editor) and the
// camera cutout (Settings > Display > Window; android WwhdActivity.java lays the window out).
#pragma once

namespace ct_touch {
constexpr float kOpacityMin = 0.1f;
float opacity();            // 0.1..1 (1: as the reference draws the controls), saved in settings.ini
void set_opacity(float o);  // main thread
// true: the picture keeps clear of a punch-hole or notch camera (a black bar along that edge); false: it
// uses the screen up to the edge around the camera, as the reference does. Saved in settings.ini.
bool cutout_clear();
void set_cutout_clear(bool clear);  // main thread
#ifdef __ANDROID__
bool tilt();                // the phone's gyro moves the GamePad (Settings > Controls > Gyro: device)
void set_tilt(bool on);     // main thread; saved as that gyro source
void request_edit_layout(); // TouchControls.java starts its layout editor at its next poll
#endif
}  // namespace ct_touch
