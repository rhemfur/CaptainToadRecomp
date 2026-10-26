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
     '        fill.setColor(faded(on ? 0x90FFFFFF : 0x38FFFFFF, c));\n        edge.setColor(faded(0x80FFFFFF, c));\n'),
    ('            fill.setColor(c.pressed ? 0xB0FFFFFF : 0x70FFFFFF);\n',
     '            fill.setColor(faded(c.pressed ? 0xB0FFFFFF : 0x70FFFFFF, c));\n'),
    ('        text.setColor(0xE0FFFFFF);\n', '        text.setColor(faded(0xE0FFFFFF, c));\n'),
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
