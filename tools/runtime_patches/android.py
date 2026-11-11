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
# the view button, the touch controls' show/hide button and the tilt button. It opens the settings window,
# which has everything in one place (runtime/ct_touch_menu.cpp): the touch controls, their opacity, the
# phone's gyro and the layout editor in Settings > Display, the cheats in Settings > Cheats. A long press
# still edits the layout. The controls are drawn with the
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
     '    private static native void nativeOpenSettings();\n'
     '    private static native boolean nativeTakeEditLayout();  // Settings > Display > Move and resize\n'
     '    private static native float nativeOpacity();\n'
     '    private static native boolean nativeCutoutClear();\n'
     '    private static volatile boolean cutoutClear;  // Settings > Display > Camera cutout: Keep clear\n'
     '    // for WwhdActivity\'s window layout: false (use the area) until libmain.so is loaded\n'
     '    static boolean cutoutClear() {\n'
     '        try { cutoutClear = nativeCutoutClear(); } catch (UnsatisfiedLinkError ignored) {}\n'
     '        return cutoutClear;\n'
     '    }\n'),
    ('    private float lastLx, lastLy, lastRx, lastRy, lastLt, lastRt;\n',
     '    private float lastLx, lastLy, lastRx, lastRy, lastLt, lastRt;\n'
     '    private float opacity = 1f;  // the controls\' (Settings > Display > Touch controls), not the menu button\'s\n'),
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
     '                        if (!all && !longPressConsumed) post(this::openSettings);\n'),
    ('            nativeControllerConnected(controller);\n',
     '            nativeControllerConnected(controller);\n'
     '            final float o = nativeOpacity();\n'
     '            if (o != opacity) { opacity = o; invalidate(); }\n'
     '            if (nativeTakeEditLayout()) post(this::beginEditing);\n'
     '            if (getContext() instanceof WwhdActivity)  // applyFullScreen reads the setting again\n'
     '                ((WwhdActivity) getContext()).checkCutout(nativeCutoutClear() != cutoutClear);\n'),
    ('    @Override public void onWindowFocusChanged(boolean hasFocus) {\n',
     """    // ---- Captain Toad's menu button (CaptainToadRecomp tools/patch_runtime.py, runtime/ct_touch_menu.cpp):
    // the settings window, where the touch controls' options and the cheats are
    private void openSettings() {
        try { nativeOpenSettings(); }
        catch (UnsatisfiedLinkError ignored) {}  // libmain.so not loaded yet
    }

    @Override public void onWindowFocusChanged(boolean hasFocus) {
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

# The layout editor's bar in the settings window's style (dark blue panel, rounded buttons with light
# text) instead of Android's white buttons, floating in the middle of the screen: the default layout
# keeps the middle free, so the bar no longer covers the top row or pushes those controls under it.
_bar_bg, _bar_edge, _btn_bg = '0xF0102F42', '0xFF2A7A9A', '0xFF1E5A78'
REPLACEMENTS[_touch] += [
    ('            p=TouchLayout.fit(p,w,h,editor.editing() && editorBar!=null ? editorBar.getBottom():0);\n',
     '            p=TouchLayout.fit(p,w,h,0);  // CaptainToadRecomp: the editor\'s bar floats in the middle\n'),
    ('                w,h,editorBar!=null ? editorBar.getBottom():0);\n',
     '                w,h,0);  // CaptainToadRecomp: the editor\'s bar floats in the middle\n'),
    ('        editorBar.setBackgroundColor(0xEE123340);\n',
     '        // CaptainToadRecomp: the settings window\'s style\n'
     '        final float dp=getResources().getDisplayMetrics().density;\n'
     '        android.graphics.drawable.GradientDrawable panel=new android.graphics.drawable.GradientDrawable();\n'
     f'        panel.setColor({_bar_bg});panel.setCornerRadius(10*dp);panel.setStroke((int)(2*dp),{_bar_edge});\n'
     '        editorBar.setBackground(panel);\n'
     '        editorBar.setPadding((int)(10*dp),(int)(8*dp),(int)(10*dp),(int)(8*dp));\n'),
    ('        hint.setTextColor(0xFFFFFFFF);hint.setGravity(android.view.Gravity.CENTER);\n',
     '        hint.setTextColor(0xFFFFFFFF);hint.setGravity(android.view.Gravity.CENTER);\n'
     '        hint.setTypeface(android.graphics.Typeface.MONOSPACE);hint.setPadding(0,0,0,(int)(6*dp));\n'),
    ('        RelativeLayout.LayoutParams lp=new RelativeLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT);\n'
     '        lp.addRule(RelativeLayout.ALIGN_PARENT_TOP);\n',
     '        RelativeLayout.LayoutParams lp=new RelativeLayout.LayoutParams(Math.round(Math.max(getWidth(),getHeight())*0.48f),ViewGroup.LayoutParams.WRAP_CONTENT);\n'
     '        lp.addRule(RelativeLayout.CENTER_IN_PARENT);  // CaptainToadRecomp: clear of the corners\' controls\n'),
    ('        Button b=new Button(getContext());b.setText(label);b.setOnClickListener(v->action.run());\n'
     '        b.setMinHeight((int)(48*getResources().getDisplayMetrics().density));\n'
     '        bar.addView(b,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));\n',
     '        Button b=new Button(getContext());b.setText(label);b.setOnClickListener(v->action.run());\n'
     '        final float dp=getResources().getDisplayMetrics().density;\n'
     '        b.setMinHeight((int)(48*dp));\n'
     '        // CaptainToadRecomp: the settings window\'s buttons\n'
     '        android.graphics.drawable.GradientDrawable face=new android.graphics.drawable.GradientDrawable();\n'
     f'        face.setColor({_btn_bg});face.setCornerRadius(6*dp);face.setStroke((int)dp,{_bar_edge});\n'
     '        b.setBackground(face);b.setTextColor(0xFFFFFFFF);b.setAllCaps(false);\n'
     '        b.setTypeface(android.graphics.Typeface.MONOSPACE);b.setStateListAnimator(null);\n'
     '        LinearLayout.LayoutParams blp=new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1);\n'
     '        blp.setMargins((int)(4*dp),0,(int)(4*dp),0);\n'
     '        bar.addView(b,blp);\n'),
]
