# Captain Toad Android: development status

Updated October 10, 2026. Local workspace: `C:\DEV\Captain Toad`.

**The native diagnostic enters Captain Toad's startup code on Windows and the Galaxy S25 Ultra, passes GX2 initialization and graphics resource preparation, then stops at `gx2.GX2CalcDepthBufferHiZInfo`. There is no rendered game, playable APK or gameplay validation yet.**

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

Resolve the HiZ auxiliary-size query and integrate shader translation, drawing and presentation to obtain the first game image, then work toward the menu and first playable level. Audio, controls, real saves, suspend/resume behavior and APK packaging remain to be validated.

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

The boot stops at GX2CalcDepthBufferHiZInfo. Its allocation behavior still needs an implementation; enabling HiZ, tessellated fetch shaders and unsupported draw operations remain explicit failures. Game shader translation and presentation are not implemented. All transferred content/meta assets passed SHA-256 verification on the phone.
