"""Captain Toad's exact-text changes to the reference runtime (tools/patch_runtime.py).

Markers shared by the areas' changes.
"""
# Settings that only act on Wind Waker HD (its frame pacing hooks, camera, projection, sky, clouds,
# bloom and occlusion shaders, gameplay mods) are left out of the Captain Toad runtime: the Graphics
# and Gameplay menus and the settings overlay keep what applies to any game.
_ct_only = '#ifndef CT_FOREIGN_GUEST  // Wind Waker HD only (CaptainToadRecomp tools/patch_runtime.py)\n'
_ct_end = '#endif  // Wind Waker HD only\n'
# Saved settings from a Wind Waker HD build (or an earlier Captain Toad one) still reach the setters of
# those features: the gameplay FOV rescaled Captain Toad's 2D layouts and broke its text. They keep the
# original game's values here whatever is saved.
_ct_keep = '#ifdef CT_FOREIGN_GUEST\n    {}\n#endif\n'
