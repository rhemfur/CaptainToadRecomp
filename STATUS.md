# Captain Toad Android: development status

Updated October 10, 2026.

**Linked with the full reference game runtime, Captain Toad plays its first level on a Windows ARM64 Snapdragon X PC: menus, cutscenes and the level render through Vulkan at about 60 frames per second, SDL input moves Captain Toad and progress is saved. Its audio mixer runs (not yet checked by ear). Stream-out output, a full playthrough, Android rendering and an APK are not done yet. The headless diagnostic also enters the startup code on the Galaxy S25 Ultra.**

## Completed

- Downloaded the pinned ZeldaWWHDRecomp reference without modifying the existing Zelda project.
- Extracted the EUR base game and v16 update separately, preserving the original packages.
- Prepared an effective game tree with 1,572 files, replacing 124 base paths with update files. Every copied file was hash-checked against its extracted source.
- Identified `Kinopio.rpx`, SHA-256 `3e867817ff4cfbefcd1f3323fe1e97919852cd86aee3738bd8d44e6e460a0464`.
- Created profile `CT-EUR-v16` with an identity address map and no Zelda hooks.
- Generated 45,773 functions in 48 C translation units and compiled them for Android ARM64.
- Built and ran a headless diagnostic using generic memory, loader and thread components.
- Added debugger/clock queries, fast mutex, filesystem and MCP/UC startup services.
- Verified Vulkan instance and logical device creation on the S25 Ultra; Adreno 830 reported API 1.3.284.
- Passed six runtime CTest cases on Windows, native hash/mutex/filesystem/system tests on Android, and 17 existing reference recompiler tests.
- Published source, tools, profiles and documentation. Game files, generated code, logs, binaries and device identifiers remain local and excluded from Git.

The initial ARM64 static library was built with NDK `30.0.16248370`, Clang 21, API 33 and ABI `arm64-v8a`. Its initial size was 447,912,254 bytes and SHA-256 was `457f4f386460d4250950b5a8d496fd22d0c14935c43d601a910274e81c52b30a`. Later runtime builds are separate artifacts.

## Initial import audit

The original lexical audit of the reference runtime found 370 imports: 362 functions and 8 data objects. It found direct source definitions for 300 functions. The following table records the 62 functions without a direct definition at that initial stage; some now have Captain Toad adapters.

| Library | Functions without a direct definition in the initial audit |
|---|---:|
| gx2 | 16 |
| coreinit | 11 |
| nn_nfp (amiibo) | 10 |
| mic | 8 |
| snd_user | 7 |
| padscore | 4 |
| snd_core | 3 |
| nn_save | 3 |

A source definition does not prove correct behavior or availability in an Android build. This lexical scan can miss macro-generated definitions. Data imports also require loader-specific validation.

The translator reported 36 words with primary opcode 0 and two calls to undefined symbols. They remain explicit diagnostics. Further analysis must establish whether those words are reachable instructions or embedded data/padding.

## Next milestone

Play further levels with a real controller, produce stream-out output on the GPU, then work toward the first playable level and an Android build of the same runtime. Audio, controls, real saves, suspend/resume behavior and APK packaging remain to be validated.

Reaching startup and compiling native code do not establish full game correctness. The diagnostic intentionally stops at unsupported APIs rather than returning fabricated success.

## Main project files

- `README.md`: setup, commands, validation and current limitations.
- `TESTING.md`: verified Android test environment.
- `CMakeLists.txt`: static game-code library and headless diagnostic targets.
- `profiles/captain-toad-eur-v16.json`: identified executable profile.
- `runtime/`: diagnostic runtime services and tests.
- `tools/prepare_game.py`: effective tree preparation and copy verification.
- `tools/audit_rpx.py`: sections, relocations and import inventory.
- `tools/recompile.py`: generation with SHA-256 validation and no Zelda hooks.
- `tools/build_android.ps1` and `tools/build_windows.ps1`: reproducible builds.
- `tools/run_android_diagnostic.ps1`: explicit-device ADB deployment and tests.
- `patches/`: reference hook-list and strict-HLE extensions.
- `local-reports/`: detailed manifests, audits and logs, kept outside Git.

Pinned references: ZeldaWWHDRecomp `defb89f21607345e2e97b2c145a071a3f362640c`; cdecrypt `0ca58c66b0f23309c69b691caf6d39bf8868d96d`.

## GX2 resource bootstrap

Implemented generic register state, display-list recording/replay, context switching, scan-buffer metadata, surface size/alignment, fetch descriptors, texture/sampler bindings, render-target registers and CPU surface copies. GX2Init creates a headless Vulkan device; the game's TV scan buffer is configured as 1280x720.

Six Windows CTest cases passed. GX2 resource tests also passed on the S25 Ultra, including tiled-copy round trips and overlapping ranges. A synthetic Vulkan clear/readback matched 256/256 expected RGBA pixels on both Adreno 830 and the desktop RTX 2080 Ti. The game performed a 16x8 CPU-backed surface copy during startup.

HiZ follows Cemu: the size query reports 0x1000 bytes with 0x100 alignment and enable requests change no host state. On Windows ARM64 the boot passed those queries for every depth buffer, initialized `nn_act` with one local account in slot 1, started the file-loading, decompression and save-data threads, answered the shader GPR and stack-entry queries (including a vertex shader header at a 2-byte-aligned address), bound vertex shader registers and stopped at `padscore.WPADEnableURCC`. Tessellated fetch shaders and unsupported draw operations remain explicit failures. Game shader translation and presentation are not implemented. All transferred content/meta assets passed SHA-256 verification on the phone.

## Full reference runtime

`tools/build_game_windows.ps1` links the generated code with the pinned reference runtime: native GX2, the Vulkan renderer and Cemu-derived shader decompiler, SDL3 host and AX audio. `tools/patch_runtime.py` points the loader at `Kinopio.rpx`, stubs Wind Waker HD guest symbols, invalidates every Wind Waker HD canonical address (`CT_FOREIGN_GUEST`) and fixes two reference behaviors that Captain Toad exposed: `OSWaitRendezvous` now waits for the cores in its mask, and CPU surface copies identify depth surfaces by their usage flag rather than the float-format bit. `runtime/reference_hle.cpp` and appended blocks add the missing imports, following Cemu.

On the Snapdragon X (Adreno X1-85) the game loaded its archives, initialized audio and worker threads, faded in the title screen and played the opening cutscene on the TV and GamePad views at 46–60 frames per second. Its Super Mario 3D World save lookup reports no save. Stream-out buffers, strides, offsets and contexts follow Cemu's command semantics, but the renderer skips the rasterizer-killed stream-out draws, so their output is not produced. The game reaches the episode book menu; scripted input opens the book, starts Plucky Pass Beginnings and walks Captain Toad with the left stick, compared against the same run without the stick. Idle at the book, the attract demo plays through the first level. The save is written to `save/user/GameData.bin`; runs of up to 140 seconds hit no missing import.

