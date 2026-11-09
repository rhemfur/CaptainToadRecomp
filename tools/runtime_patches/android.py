"""Captain Toad's exact-text changes to the reference runtime (tools/patch_runtime.py).

The Android app: its identity, texts, touch controls and activity.
"""

REPLACEMENTS = {}
# The Android app gets its own package and name, so installing it never replaces a Wind Waker HD
# install. The Java namespace stays; only the installed identity changes.
REPLACEMENTS['../android/app/build.gradle'] = [
    ('        applicationId "org.wwhdrecomp.wwhd"\n', '        applicationId "org.ctrecomp.captaintoad"\n'),
]
REPLACEMENTS['../android/app/src/main/res/values/strings.xml'] = [
    ('    <string name="app_name">Wind Waker HD</string>\n',
     '    <string name="app_name">Captain Toad: Treasure Tracker</string>\n'),
]
# The PC route's game folder (copied over USB) holds Captain Toad's executable, not Wind Waker HD's.
REPLACEMENTS['../android/app/src/main/java/org/wwhdrecomp/wwhd/SetupActivity.java'] = [
    ('                return external != null && new File(external, "game/code/cking.rpx").isFile();\n',
     '                return external != null && new File(external, "game/code/Kinopio.rpx").isFile();\n'),
    ('                    (external != null && new File(external, "game/code/cking.rpx").isFile()));\n',
     '                    (external != null && new File(external, "game/code/Kinopio.rpx").isFile()));\n'),
]
# Android: one menu button in the top left corner (where the reference has its view button) in place of
# the view button, the touch controls' show/hide button and the tilt button. Its menu (an Android dialog)
# opens the settings window, edits the touch controls' layout, turns the phone's gyro on or off and
# applies the save cheats (runtime/ct_touch_menu.cpp); display options live in Settings > Display only. A long press still edits the layout. The controls are drawn with the
# opacity of Settings > Display > Touch controls; the menu button keeps the reference's look.
_touch = '../android/app/src/main/java/org/wwhdrecomp/wwhd/TouchControls.java'
REPLACEMENTS[_touch] = [
    ('// On-screen controls over the game: two sticks, A B X Y, L R ZL ZR, + -, a D-pad, and a small button\n'
     '// under the view button (top left) that shows or hides them (remembered).',
     '// On-screen controls over the game: two sticks, A B X Y, L R ZL ZR, + -, a D-pad, and Captain Toad\'s\n'
     '// menu button (top left; CaptainToadRecomp tools/patch_runtime.py) that shows or hides them (remembered).'),
    ('    private static native void nativeShowControls(boolean shown);\n',
     '    private static native void nativeShowControls(boolean shown);\n'
     '    // Captain Toad\'s menu button (runtime/ct_touch_menu.cpp)\n'
     '    private static native int nativeMenuState();\n'
     '    private static native void nativeToggleTilt();\n'
     '    private static native void nativeOpenSettings();\n'
     '    private static native void nativeCheat(int which);\n'
     '    private static native float nativeOpacity();\n'
     '    private static native void nativeSetOpacity(float opacity);\n'
     '    private static native boolean nativeCutoutClear();\n'
     '    private static volatile boolean cutoutClear;  // Settings > Display > Camera cutout: Keep clear\n'
     '    // for WwhdActivity\'s window layout: false (use the area) until libmain.so is loaded\n'
     '    static boolean cutoutClear() {\n'
     '        try { cutoutClear = nativeCutoutClear(); } catch (UnsatisfiedLinkError ignored) {}\n'
     '        return cutoutClear;\n'
     '    }\n'),
    ('    private float lastLx, lastLy, lastRx, lastRy, lastLt, lastRt;\n',
     '    private float lastLx, lastLy, lastRx, lastRy, lastLt, lastRt;\n'
     '    private float opacity = 1f;  // the controls\' (Settings > Display > Touch controls), not the menu button\'s\n'
     '    private android.app.AlertDialog menu;\n'),
    ('        toggle = new Control(KIND_TOGGLE, 0, "🎮", 0f, 0f, 0.04f);  // placed in onSizeChanged\n',
     '        toggle = new Control(KIND_TOGGLE, 0, "☰", 0f, 0f, 0.045f);  // the menu button, placed in onSizeChanged\n'),
    ('        // under the game\'s view button (screen_layout.cpp: a square of 9% of the short side, 1.5% from\n'
     '        // the top left corner)\n'
     '        toggle.r = toggle.fr * s;\n'
     '        toggle.cx = s * (0.015f + 0.045f);\n'
     '        toggle.cy = s * (0.015f + 0.09f + 0.02f) + toggle.r;\n',
     '        // where the reference has its view button (display_modes.cpp: a square of 9% of the short side,\n'
     '        // 1.5% from the top left corner)\n'
     '        toggle.r = toggle.fr * s;\n'
     '        toggle.cx = toggle.cy = s * (0.015f + 0.045f);\n'),
    ('        fill.setColor(on ? 0x90FFFFFF : 0x38FFFFFF);\n        edge.setColor(0x80FFFFFF);\n',
     '        // CaptainToadRecomp: a dark body (translucent white vanished on the white title screen)\n'
     '        fill.setColor(faded(on ? 0x90FFFFFF : c == toggle ? 0x38FFFFFF : 0x60000000, c));\n        edge.setColor(faded(0x80FFFFFF, c));\n'),
    ('            fill.setColor(c.pressed ? 0xB0FFFFFF : 0x70FFFFFF);\n',
     '            fill.setColor(faded(c.pressed ? 0xB0FFFFFF : 0x70FFFFFF, c));\n'),
    ('        text.setColor(0xE0FFFFFF);\n', '        text.setColor(faded(0xE0FFFFFF, c));\n'
     '        text.setShadowLayer(c.r * 0.08f, 0, 0, faded(0xC0000000, c));  // CaptainToadRecomp: readable on white\n'),
    ('    private Control hit(float x, float y) {\n',
     '    // a colour with the controls\' opacity (the menu button keeps its own)\n'
     '    private int faded(int argb, Control c) {\n'
     '        if (c == toggle || opacity >= 1f) return argb;\n'
     '        return Math.round((argb >>> 24) * opacity) << 24 | (argb & 0xFFFFFF);\n'
     '    }\n'
     '\n'
     '    private Control hit(float x, float y) {\n'),
    ('                        if (!all && !longPressConsumed) setShown(toggleTo);\n',
     '                        if (!all && !longPressConsumed) post(this::showMenu);\n'),
    ('            nativeControllerConnected(controller);\n',
     '            nativeControllerConnected(controller);\n'
     '            final float o = nativeOpacity();\n'
     '            if (o != opacity) { opacity = o; invalidate(); }\n'
     '            if (getContext() instanceof WwhdActivity)  // applyFullScreen reads the setting again\n'
     '                ((WwhdActivity) getContext()).checkCutout(nativeCutoutClear() != cutoutClear);\n'),
    ('    @Override public void onWindowFocusChanged(boolean hasFocus) {\n',
     """    // ---- Captain Toad's menu (CaptainToadRecomp tools/patch_runtime.py, runtime/ct_touch_menu.cpp)
    private static final int[] CHEATS = {1, 2, 4, 8, 16, 32, 64};  // runtime/ct_save.h, as R.array.ct_cheats lists them

    private void showMenu() {
        if (menu != null && menu.isShowing()) return;
        final int state;
        try { state = nativeMenuState(); }
        catch (UnsatisfiedLinkError e) { return; }  // libmain.so not loaded yet
        final Context c = getContext();
        final boolean tilt = (state & 16) != 0;
        // display options (view, picture shape, touch controls, opacity) live in Settings > Display only
        final String[] items = {
            c.getString(R.string.ct_menu_settings),
            c.getString(R.string.ct_menu_edit_layout),
            c.getString(tilt ? R.string.ct_menu_tilt_off : R.string.ct_menu_tilt_on),
            c.getString(R.string.ct_menu_cheats)};
        show(new android.app.AlertDialog.Builder(c).setTitle(R.string.app_name).setItems(items, (d, which) -> {
            switch (which) {
                case 0: nativeOpenSettings(); break;
                case 1: post(this::beginEditing); break;
                case 2: nativeToggleTilt(); break;
                case 3: post(this::showCheats); break;
            }
        }).setNegativeButton(android.R.string.cancel, null));
    }

    // each cheat asks first: it changes the save and closes the game (runtime/cheats.cpp)
    private void showCheats() {
        final String[] names = getContext().getResources().getStringArray(R.array.ct_cheats);
        show(new android.app.AlertDialog.Builder(getContext()).setTitle(R.string.ct_menu_cheats_title)
            .setItems(names, (d, which) -> post(() -> show(new android.app.AlertDialog.Builder(getContext())
                .setTitle(names[which]).setMessage(R.string.ct_cheat_confirm)
                .setPositiveButton(R.string.ct_cheat_apply, (d2, w2) -> nativeCheat(CHEATS[which]))
                .setNegativeButton(android.R.string.cancel, null))))
            .setNegativeButton(android.R.string.cancel, null));
    }

    private void show(android.app.AlertDialog.Builder builder) {
        menu = builder.create();
        menu.show();
        WwhdActivity.syncSystemBars(menu.getWindow());  // full screen: the system bars stay hidden
    }

    @Override public void onWindowFocusChanged(boolean hasFocus) {
"""),
]
REPLACEMENTS['../android/app/src/main/res/values/strings.xml'] += [
    ('</resources>\n', """    <!-- Captain Toad's menu button (CaptainToadRecomp tools/patch_runtime.py) -->
    <string name="ct_menu_settings">Settings</string>
    <string name="ct_menu_edit_layout">Move and resize touch controls</string>
    <string name="ct_menu_tilt_on">Tilt camera (phone gyro): off, tap to turn on</string>
    <string name="ct_menu_tilt_off">Tilt camera (phone gyro): on, tap to turn off</string>
    <string name="ct_menu_cheats">Cheats</string>
    <string name="ct_menu_cheats_title">Cheats (change your save)</string>
    <string name="ct_cheat_confirm">Your save is changed and Captain Toad closes: open it again to play with the cheat. Play since the game last saved is lost. The save from before the first cheat is kept as GameData.bin.before-cheats.</string>
    <string name="ct_cheat_apply">Apply and close</string>
    <!-- runtime/ct_save.h bit order (TouchControls.CHEATS) -->
    <string-array name="ct_cheats">
        <item>Unlock every episode and course</item>
        <item>Clear every course</item>
        <item>Every Super Gem</item>
        <item>Every bonus objective</item>
        <item>Every challenge time</item>
        <item>Every Pixel Toad</item>
        <item>100% completion</item>
    </string-array>
</resources>
"""),
]
# Android: Settings > Display > Camera cutout. Keep clear lays the game out beside a punch-hole or notch
# camera (a black bar along that edge); Use the area keeps the reference's layout into it. From Android 15
# an app targeting SDK 35 or later always draws into the cutout (LAYOUT_IN_DISPLAY_CUTOUT_MODE_NEVER is
# ignored), so the window stays edge to edge and SDL's layout is padded by the cutout's safe insets.
REPLACEMENTS['../android/app/src/main/java/org/wwhdrecomp/wwhd/WwhdActivity.java'] = [
    ('        syncSystemBars(w);\n        if (gamePadDisplay != null) gamePadDisplay.syncSystemBars();\n',
     '        padForCutout(w);\n'
     '        syncSystemBars(w);\n        if (gamePadDisplay != null) gamePadDisplay.syncSystemBars();\n'),
    ('    private final Runnable reapplyFullScreen = this::applyFullScreen;\n',
     '    // Captain Toad: Settings > Display > Camera cutout > Keep clear (CaptainToadRecomp tools/patch_runtime.py)\n'
     '    private void padForCutout(Window w) {\n'
     '        if (mLayout == null) return;\n'
     '        int l = 0, t = 0, r = 0, b = 0;\n'
     '        if (mFullscreenModeActive && TouchControls.cutoutClear()) {\n'
     '            WindowInsets insets = w.getDecorView().getRootWindowInsets();\n'
     '            android.view.DisplayCutout cut = insets != null ? insets.getDisplayCutout() : null;\n'
     '            if (cut != null) {  // none, or not laid out yet (TouchControls asks again)\n'
     '                l = cut.getSafeInsetLeft(); t = cut.getSafeInsetTop(); r = cut.getSafeInsetRight(); b = cut.getSafeInsetBottom();\n'
     '            }\n'
     '        }\n'
     '        if (mLayout.getPaddingLeft() == l && mLayout.getPaddingTop() == t && mLayout.getPaddingRight() == r &&\n'
     '            mLayout.getPaddingBottom() == b) return;\n'
     '        mLayout.setBackgroundColor(android.graphics.Color.BLACK);\n'
     '        mLayout.setPadding(l, t, r, b);\n'
     '    }\n'
     '\n'
     '    private final Runnable reapplyFullScreen = this::applyFullScreen;\n'
     '    // Captain Toad: TouchControls asks ten times a second: the setting changed, or the screen turned\n'
     '    // round (the camera on the other side)\n'
     '    void checkCutout(boolean settingChanged) {\n'
     '        if (settingChanged) applyFullScreen();\n'
     '        else if (getWindow() != null) padForCutout(getWindow());\n'
     '    }\n'),
]

# Captain Toad's default layout (CaptainToadRecomp; judged on a Galaxy S25 Ultra): the controls drawn at
# 70% with a dark translucent body (translucent white ones vanished on the white title screen), grouped
# in the corners in units of the screen's short side (negative: from the right or bottom edge), so wide
# phones keep each group compact. The layout editor starts from these places and saves its own.
REPLACEMENTS[_touch] += [
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
''', '''        // CaptainToadRecomp: corners, in short-side units (negative: from the right / bottom edge); no
        // right stick: a finger dragged outside the controls turns the camera
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
    ('            c.cx=c.fx*w; c.cy=c.fy*h; c.r=c.fr*s; // unchanged default path\n',
     '            c.cx=defaultX(c,w,s); c.cy=defaultY(c,h,s); c.r=c.fr*s*SIZE; // CaptainToadRecomp default\n'),
    ('            if (p==null) p=new TouchLayout.Placement(c.fx,c.fy,c.fr);\n',
     '            if (p==null) p=new TouchLayout.Placement(defaultX(c,w,s)/w,defaultY(c,h,s)/h,c.fr*SIZE);\n'),
    ('    private static String key(Control c) { return c.kind+":"+c.code; }\n',
     '    private static String key(Control c) { return c.kind+":"+c.code; }\n'
     '    // CaptainToadRecomp: default places from a corner in short-side units, at SIZE of the reference\n'
     '    private static final float SIZE = 0.7f;\n'
     '    private static float defaultX(Control c, int w, float s) { return c.fx >= 0 ? c.fx * s : w + c.fx * s; }\n'
     '    private static float defaultY(Control c, int h, float s) { return c.fy >= 0 ? c.fy * s : h + c.fy * s; }\n'),
]

# Camera drag (CaptainToadRecomp): a finger on no control first touches the GamePad (the TV picture's
# touch above); once it moves past a small slop it turns the camera instead: the GamePad touch is
# cancelled and the finger's speed becomes the right stick (the view follows it and stops when it
# stops). Taps and holds still reach the game. The top left corner (menu button) does not drag.
REPLACEMENTS[_touch] += [
    ('    private int lastButtons = -1, lastTouchDevice;\n',
     '    private int lastButtons = -1, lastTouchDevice;\n'
     '    private static final float DRAG_FULL = 0.9f, DRAG_SLOP = 0.03f;  // short sides per second / to start\n'
     '    private int dragId = -1;\n'
     '    private boolean dragging;\n'
     '    private float dragX, dragY, dragStartX, dragStartY, camX, camY;\n'
     '    private long dragT;\n'
     '    private final Runnable dragRest = () -> { camX = 0; camY = 0; update(); };\n'
     '    private void dragStart(int id, float x, float y, long t) {\n'
     '        final float s = Math.min(getWidth(), getHeight());\n'
     '        if (dragId >= 0 || !active() || (x < s * 0.25f && y < s * 0.30f)) return;\n'
     '        dragId = id; dragging = false; dragX = dragStartX = x; dragY = dragStartY = y; dragT = t;\n'
     '    }\n'
     '    // true once the finger turns the camera (its GamePad touch is over)\n'
     '    private boolean dragMove(MotionEvent event, int i) {\n'
     '        final float s = Math.min(getWidth(), getHeight()), x = event.getX(i), y = event.getY(i);\n'
     '        final long t = event.getEventTime();\n'
     '        if (!dragging) {\n'
     '            if (Math.hypot(x - dragStartX, y - dragStartY) < s * DRAG_SLOP) return false;\n'
     '            dragging = true;\n'
     '            forward(event, i, MotionEvent.ACTION_CANCEL);  // the game no longer sees this finger\n'
     '            dragX = x; dragY = y; dragT = t;\n'
     '            return true;\n'
     '        }\n'
     '        final long dt = Math.max(1, t - dragT);\n'
     '        final float full = s * DRAG_FULL / 1000f;  // pixels per millisecond for a full stick\n'
     '        final float tx = Math.max(-1f, Math.min(1f, (x - dragX) / dt / full));\n'
     '        final float ty = Math.max(-1f, Math.min(1f, (y - dragY) / dt / full));\n'
     '        camX = camX * 0.4f + tx * 0.6f; camY = camY * 0.4f + ty * 0.6f;\n'
     '        dragX = x; dragY = y; dragT = t;\n'
     '        removeCallbacks(dragRest);\n'
     '        postDelayed(dragRest, 80);  // the finger rests: the camera stops\n'
     '        return true;\n'
     '    }\n'
     '    private boolean dragEnd() {\n'
     '        final boolean was = dragging;\n'
     '        dragId = -1; dragging = false; removeCallbacks(dragRest); camX = 0; camY = 0;\n'
     '        return was;\n'
     '    }\n'),
    ('                if (c == null && action == MotionEvent.ACTION_DOWN) {\n'
     '                    // The first finger on no control: decline the gesture',
     '                if (c == null && action == MotionEvent.ACTION_DOWN && active()) {\n'
     '                    // CaptainToadRecomp: keep the gesture: it touches the GamePad, or drags the camera\n'
     '                    forward(event, index, action);\n'
     '                    dragStart(id, x, y, event.getEventTime());\n'
     '                } else if (c == null && action == MotionEvent.ACTION_DOWN) {\n'
     '                    // The first finger on no control: decline the gesture'),
    ('                } else if (c == null) {\n                    forward(event, index, action);\n',
     '                } else if (c == null) {\n                    forward(event, index, action);\n'
     '                    dragStart(id, x, y, event.getEventTime());\n'),
    ('                    if (c == null) forward(event, i, MotionEvent.ACTION_MOVE);\n',
     '                    if (c == null) {\n'
     '                        if (id != dragId || !dragMove(event, i)) forward(event, i, MotionEvent.ACTION_MOVE);\n'
     '                    }\n'),
    ('                    if (c == null) { forward(event, i, all ? MotionEvent.ACTION_CANCEL : action); continue; }\n',
     '                    if (c == null) {\n'
     '                        if (id != dragId || !dragEnd()) forward(event, i, all ? MotionEvent.ACTION_CANCEL : action);\n'
     '                        continue;\n'
     '                    }\n'),
    ('        buttons |= face << 16;  // (only for the change check below)\n',
     '        if (dragging || camX != 0 || camY != 0) { rx = camX; ry = camY; }  // CaptainToadRecomp: camera drag\n'
     '        buttons |= face << 16;  // (only for the change check below)\n'),
]
