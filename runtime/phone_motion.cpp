// The phone's own motion sensors as the virtual GamePad's gyro (Android). While Settings > Controls >
// Gyro is "controller" and no connected controller has motion sensors, the phone's gyroscope and
// accelerometer feed the reference's motion module (motion.h) like a controller would: the phone held
// in landscape is the GamePad. Captain Toad reads the GamePad's motion through VPADRead.
// Built into the Android game runtime only (tools/build_game_android.ps1, CT_EXTRA_SOURCES).
#ifdef __ANDROID__
#include <android/looper.h>
#include <android/sensor.h>
#include <SDL3/SDL.h>
#include <chrono>
#include <thread>

#include "motion/motion.h"
#include "runtime.h"

namespace {
constexpr uint64_t kPhoneDevice = 0x50484F4E45ull;  // "PHONE": apart from SDL joystick ids
constexpr int kLooperId = 3;
constexpr int kRateUs = 5000;  // 200 samples per second

// Android reports both sensors in the device's natural (portrait) frame: x right, y up, z out of the
// screen, like SDL's controller frame. The screen the player holds may be turned: map to its frame.
void to_screen(SDL_DisplayOrientation o, const float in[3], float out[3]) {
    switch (o) {
    case SDL_ORIENTATION_LANDSCAPE: out[0] = -in[1]; out[1] = in[0]; break;  // right side up
    case SDL_ORIENTATION_LANDSCAPE_FLIPPED: out[0] = in[1]; out[1] = -in[0]; break;
    case SDL_ORIENTATION_PORTRAIT_FLIPPED: out[0] = -in[0]; out[1] = -in[1]; break;
    default: out[0] = in[0]; out[1] = in[1]; break;
    }
    out[2] = in[2];
}

void run() {
    // the runtime (and its motion settings) is up once SDL has a video subsystem
    while (!SDL_WasInit(SDL_INIT_VIDEO)) std::this_thread::sleep_for(std::chrono::milliseconds(250));
    ASensorManager* sensors = ASensorManager_getInstanceForPackage("org.ctrecomp.captaintoad");
    const ASensor* gyro = sensors ? ASensorManager_getDefaultSensor(sensors, ASENSOR_TYPE_GYROSCOPE) : nullptr;
    const ASensor* accel = sensors ? ASensorManager_getDefaultSensor(sensors, ASENSOR_TYPE_ACCELEROMETER) : nullptr;
    if (!gyro || !accel) {
        LOG("[gyro] this phone has no gyroscope and accelerometer: no phone motion");
        return;
    }
    ALooper* looper = ALooper_prepare(ALOOPER_PREPARE_ALLOW_NON_CALLBACKS);
    ASensorEventQueue* queue = ASensorManager_createEventQueue(sensors, looper, kLooperId, nullptr, nullptr);
    if (!queue) {
        LOG("[gyro] cannot open the phone's motion sensors");
        return;
    }
    bool on = false, have_accel = false;
    float a[3] = {};
    for (;;) {
        const bool want = motion::wants_controller_sensors() && motion::gyro_controllers() == 0;
        if (want != on) {
            on = want;
            if (on) {
                ASensorEventQueue_enableSensor(queue, gyro);
                ASensorEventQueue_setEventRate(queue, gyro, kRateUs);
                ASensorEventQueue_enableSensor(queue, accel);
                ASensorEventQueue_setEventRate(queue, accel, kRateUs);
                LOG("[gyro] phone motion sensors on: the phone is the GamePad");
            } else {
                ASensorEventQueue_disableSensor(queue, gyro);
                ASensorEventQueue_disableSensor(queue, accel);
                motion::controller_gone(kPhoneDevice);
                have_accel = false;
                LOG("[gyro] phone motion sensors off");
            }
        }
        if (!on) {
            std::this_thread::sleep_for(std::chrono::milliseconds(250));
            continue;
        }
        ALooper_pollOnce(250, nullptr, nullptr, nullptr);
        const SDL_DisplayOrientation o = SDL_GetCurrentDisplayOrientation(SDL_GetPrimaryDisplay());
        ASensorEvent events[32];
        ssize_t n;
        while ((n = ASensorEventQueue_getEvents(queue, events, 32)) > 0) {
            for (ssize_t i = 0; i < n; i++) {
                const ASensorEvent& e = events[i];
                if (e.type == ASENSOR_TYPE_ACCELEROMETER) {
                    to_screen(o, e.acceleration.v, a);
                    have_accel = true;
                } else if (e.type == ASENSOR_TYPE_GYROSCOPE && have_accel) {
                    float g[3];
                    to_screen(o, e.vector.v, g);
                    motion::controller_sample(kPhoneDevice, uint64_t(e.timestamp), g, a);
                }
            }
        }
    }
}

struct Start {
    Start() { std::thread(run).detach(); }
} g_start;
}  // namespace
#endif
