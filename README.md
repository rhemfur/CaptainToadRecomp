# Captain Toad EUR — Android recompilation prototype

Captain Toad Wii U EUR with internal update version 16 has been translated and compiled into native code. Linked with the full reference game runtime, it plays on a Windows ARM64 Snapdragon X PC: the title screen, the opening cutscene, the episode book and the first level render through Vulkan at about 60 frames per second, the reference's SDL input drives the menus and moves Captain Toad, and progress is saved. Its audio mixer and SDL output run (not yet checked by ear). The separate headless diagnostic enters the game's startup code on Windows and a Samsung Galaxy S25 Ultra. Stream-out output, a full playthrough, Android rendering and APK packaging remain unfinished.

The project started on October 10, 2026. All public documentation, code comments, commit messages and GitHub discussions for this project should use English.

## Set up the project

Requirements: Git, Python 3.10 or later and, for ARM64 builds, an Android SDK with NDK, CMake and Ninja. The prototype was tested on Windows with Python 3.11.

```powershell
git clone https://github.com/rhemfur/CaptainToadRecomp.git
cd CaptainToadRecomp
powershell -ExecutionPolicy Bypass -File tools/setup_reference.ps1
```

On macOS or Linux, run `sh tools/setup_reference.sh` instead; it does the same.

The setup script downloads the pinned runtime/recompiler commit and applies the hook-list and strict diagnostic extensions. It preserves an existing checkout and refuses to change a different revision automatically.

Supply your own Captain Toad Wii U game (EUR or USA) and its v16 update, extracted separately into `code/content/meta` directory trees. [cdecrypt](https://github.com/VitaSmith/cdecrypt) supports NUS installation packages. This repository does not include the game, tickets, keys or the extractor.

Place the extracted trees in `work/extracted/base` and `work/extracted/update`, then run:

```powershell
python tools/prepare_game.py --base work/extracted/base --update work/extracted/update --output game --manifest local-reports/game-manifest.json
python tools/audit_rpx.py --game game --upstream upstream --output local-reports/rpx-audit.json
python tools/recompile.py
powershell -ExecutionPolicy Bypass -File tools/build_android.ps1
```

Preparation and generation require empty output directories. These commands produce a static library and a headless diagnostic executable. They do not produce a playable game or APK.

## Repository layout

- `tools/`: game preparation, RPX auditing, C generation, builds and device diagnostics.
- `profiles/captain-toad-eur-v16.json`: SHA-256 identification of the updated RPX, with no Zelda hooks.
- `runtime/`: startup services, fast mutex, filesystem, GX2 bridge, headless Vulkan device and tests; `reference_hle.cpp` adds imports to the full reference runtime.
- `upstream/`: separately downloaded ZeldaWWHDRecomp reference checkout, ignored by Git.
- `work/extracted/base` and `work/extracted/update`: separate local game/update extractions.
- `game/`: effective game tree, with update files replacing matching base paths.
- `local-reports/`: local manifests, import audits and diagnostic logs.
- `build/gen/`: C generated locally from the game executable.
- `build/android-gamecode/`: ARM64 static library and `ct-diagnostic` executable.
- `build/game-windows/`: the reference game runtime linked with Captain Toad's code (`wwhd.exe`).

Game files, tickets, keys, generated game code, builds and local reports are excluded from Git. Keep them on your machine. Executables or future APKs containing recompiled game code must not be included in public releases.

## Pinned references

- [ZeldaWWHDRecomp](https://github.com/ZeldaWWHDRecomp/ZeldaWWHDRecomp), commit `59aa6ddeadd08b557a17743834a2d89a1d2dfc11`. Its MPL-2.0 license and credits remain in the reference checkout.
- [cdecrypt](https://github.com/VitaSmith/cdecrypt), commit `0ca58c66b0f23309c69b691caf6d39bf8868d96d`, used for the initial local extraction. Its original license remains in the separate `work/cdecrypt` checkout.

The reference recompiler accepts an optional `hook_paths` argument. Omitting it preserves the original behavior; passing `[]` explicitly disables all hooks. This prototype always uses `[]`, so Zelda-specific addresses and hooks are not applied to Captain Toad. `tools/patch_reference.py` reproduces this extension and rejects an unexpected source layout.

## Executable identification and translation

- Updated executable: `Kinopio.rpx`.
- SHA-256: `3e867817ff4cfbefcd1f3323fe1e97919852cd86aee3738bd8d44e6e460a0464`.
- Entry point: `0x02511BB0`.
- Decompressed text: 5,746,620 bytes.
- Generated code: 45,773 functions in 48 C translation units, with no game or instruction hooks.
- Imports: 362 functions and 8 data objects across 12 libraries.
- The initial lexical audit of the reference runtime found direct definitions for 300 functions and none for 62. This is a source inventory, not proof of correct behavior or successful linking; macros, aliases and build conditions require further checks. Captain Toad adapters added since that audit resolve some of those gaps.
- Translation reported 36 words with primary opcode 0. They still call `ppc_unimplemented`; they have not been replaced with NOPs. Their reachability and possible use as embedded data or padding remain to be investigated.
- Two calls to undefined symbols remain explicit diagnostics.

Diagnostic startup passes `GX2Init` on Android and Windows, configures a 1280x720 TV buffer and reaches the depth-buffer auxiliary-size query. On the S25 Ultra, Vulkan instance and logical device creation passed; the Adreno 830 driver reported API 1.3.284. This does not validate the game's renderer, menus, audio, real saves or gameplay.

## Regenerate local outputs

The initial packages were extracted into separate destination directories without modifying the originals.

To rebuild the effective game tree, use a new empty output directory:

```powershell
python tools/prepare_game.py --base work/extracted/base --update work/extracted/update --output game-new --manifest local-reports/game-new-manifest.json
python tools/audit_rpx.py --game game-new --upstream upstream --output local-reports/rpx-new-audit.json
```

To regenerate C, use a new empty directory:

```powershell
python tools/patch_reference.py upstream
python tools/recompile.py --output build/gen-new
```

The generator rejects an RPX whose SHA-256 differs from the identified profile. Do not select another game's profile to bypass this check.

The default Android build uses SDK `C:\Android\Sdk`, NDK `30.0.16248370`, CMake `4.1.2`, Android API 33 and ABI `arm64-v8a`. These are prototype build parameters, not a list of verified compatible devices.

Run the existing reference recompiler tests with:

```powershell
python -m unittest discover -s upstream/tools/recomp -p test_builds.py
```

## Run the diagnostic

The native diagnostic verifies the RPX SHA-256 before loading guest memory, initializes data imports and starts Captain Toad's guest threads. It has a headless Vulkan device bootstrap and a GX2 resource/state bridge, but no game draw translation, scanout presentation, audio backend, snapshots or Zelda hooks. An unsupported API stops it with exit code 78; the default ten-second deadline stops it with 124.

On Windows, using the installed Clang/MSYS2 and CMake:

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_windows.ps1
build/windows-diagnostic/ct-diagnostic.exe --game game --seconds 10
```

On Android, authorize USB debugging and use the local identifier from `adb devices`. Do not publish device identifiers:

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_android.ps1
powershell -ExecutionPolicy Bypass -File tools/run_android_diagnostic.ps1 -Serial <local-device-id> -Mode Vulkan
powershell -ExecutionPolicy Bypass -File tools/run_android_diagnostic.ps1 -Serial <local-device-id> -Mode Boot
```

The device script uses `/data/local/tmp/captain-toad` and selects the device explicitly. Logs remain in `local-reports/`, outside Git. This diagnostic does not require installing an APK. Its executable contains recompiled game code and stays local.

Other script modes are `SelfTest`, `Mutex`, `Filesystem`, `System`, `Gx2`, `Clear` and `Verify`. `Gx2` exercises resource/state handling; `Clear` checks a synthetic Vulkan image and readback. Filesystem tests use synthetic content and save files in a separate fixture directory.

Validation on October 10, 2026:

- Six CTest cases passed on Windows: SHA-256 vectors, same-core mutex contention, filesystem reads/writes/bounds, MCP/UC records, GX2 resources/state and rejection of an unknown RPX.
- Native SHA-256, fast mutex, filesystem and MCP/UC tests passed on the S25 Ultra. The Vulkan probe created an instance and a logical device.
- The diagnostic passes `GX2Init` and configures the game's 1280x720 TV scan buffer. It prepares surfaces, fetch descriptors, samplers and render-target registers. A later Windows ARM64 run passed the HiZ queries for every depth buffer, including two that request HiZ, initialized `nn_act`, answered the shader GPR and stack-entry queries, bound vertex shader registers and stopped at `padscore.WPADEnableURCC`.

## Run the game runtime (Windows)

`tools/build_game_windows.ps1` builds the pinned reference runtime with Captain Toad's generated code: its native GX2, Vulkan renderer with the Cemu-derived shader decompiler, SDL3 window/input host and AX audio. `tools/patch_runtime.py` prepares the `upstream/` checkout first:

- The loader opens `Kinopio.rpx`.
- Wind Waker HD guest symbols that the runtime names get weak stubs, following nsmbu-recomp. A stub stops through `ppc_unimplemented` if it runs. The script refuses a symbol that matches a Captain Toad function, because the game's function would silently replace the stub.
- With `CT_FOREIGN_GUEST`, every Wind Waker HD canonical address is invalid, even inside Captain Toad's ranges. Features that check validity switch off; direct uses resolve into the protected null page and fault instead of reading unrelated game data. The audio mixer's fader lookup now checks validity.
- `OSWaitRendezvous` waits for the cores in its mask, as Cemu does. The reference counted arrivals, which let the main thread use the sound system before the audio launch thread had initialized it.
- CPU surface copies identify depth surfaces by their depth-buffer usage flag, not by the 0x800 float-format bit, so R16G16 float copies work.
- `runtime/reference_hle.cpp` and the appended blocks add imports the reference lacks, following Cemu: amiibo detection without figures, no GamePad microphone, absent saves of other titles (Super Mario 3D World), GX2 polygon offset, cull/depth-only controls, point limits, restart index, display-list status, default state and tessellation levels.
- Stream out follows Cemu's command semantics: `GX2SetStreamOutBuffer` sets each buffer's base and size, `GX2SetVertexShader` sets the vertex strides, `GX2SetStreamOutContext` and `GX2SaveStreamOutContext` reset, load or save the write offset on the render thread in command order, and each stream-out draw advances the offsets by the bytes its vertices emit. On Metal (macOS) the vertex shaders write that output on the GPU, as Cemu's Metal renderer does: each shader stores its stream-out vertices through a device pointer at the buffer's write offset, dropping writes past the buffer's end as the hardware does. The output goes to a GPU shadow of each buffer, never into guest memory (the GPU runs a frame behind the game, which reuses these small buffers from per-frame memory), and draws of that frame and the next read the shadow; and draws with rasterization disabled run alone in a pass without attachments (`[gfx] stream-out: vertex shaders write their buffers on the GPU`). The Vulkan renderer (Windows, Android) still skips those draws, so there the buffers keep their previous contents.

The build is strict: it stops at the first missing import. Tested with llvm-mingw 20260922 (aarch64), the Visual Studio Build Tools CMake/Ninja and Vulkan headers:

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_game_windows.ps1
build/game-windows/wwhd.exe --game game
```

On October 10, 2026, on a Snapdragon X PC (Adreno X1-85, Vulkan 1.3.295), the game loaded its shader, layout, font and localized message archives, initialized audio and its worker threads, faded in the title screen and played the opening cutscene on the TV and GamePad views at 46–60 frames per second. It looked up a Super Mario 3D World save, found none and continued to the episode book menu, about 4,000 frames after startup. Idle at the book, it plays its attract demo of the first level, collecting coins, gems and the Power Star.

Input was checked with the reference's scripted test input, timed from the book (`WWHD_TEST_ORIGIN=4000`): A opens the book at Plucky Pass Beginnings, a second A starts the level, and holding the left stick walks Captain Toad away from the start, collecting four coins. The same script without the stick leaves him at the start with no coins. The game writes `save/user/GameData.bin` next to the executable. Runs of up to 140 seconds, including a level, hit no missing import. The executable and any frame captures contain recompiled game code or game imagery and stay local. `tools/patch_runtime.py` renames the runtime's window titles, menus, dialogs, overlay, logs and per-user folders for Captain Toad.

## Run the game (macOS)

`tools/build_game_macos.sh` makes `build/game-macos/Captain Toad Treasure Tracker.app` for Apple Silicon Macs, a portable app. Its first start asks for your base game and v16 update, each as an extracted folder (`code`, `content`, `meta`) or a `.rar`, `.zip` or `.7z` archive of one, then prepares the game on the Mac: it extracts the archives, merges the update over the base game, translates `Kinopio.rpx` and compiles the patched reference runtime with it. Later starts launch the game directly; hold Shift while starting it to run the setup again. The runtime has the Metal renderer and the Vulkan renderer through MoltenVK in one executable, with the AppKit host (TV/GamePad windows, menus, controls window, input, audio).

```sh
xcode-select --install
brew install cmake ninja vulkan-headers vulkan-loader molten-vk glslang zstd
sh tools/build_game_macos.sh
open "build/game-macos/Captain Toad Treasure Tracker.app"
```

The app runs this repository's tools, so keep the repository where it is. Everything the setup and the game create stays in `build/game-macos/data/`: the prepared game, the generated code, the runtime (`bin/Captain Toad Treasure Tracker.app`, shown as Captain Toad: Treasure Tracker, with an icon made from the game's own title art), saves (`save/`), the setup log and, through `WWHD_USER_DIR`, settings, controls, save states, shader caches and logs (`user/`). The icon, like everything else made from the game, stays in `build/` and is never committed. Nothing is written to the per-user Library folders or user defaults. The data folder contains game files and recompiled game code: keep it local.

The same steps without the app: `sh tools/setup_game_macos.sh build/game-macos/data <base> <update>`. `tools/build_runtime_macos.sh` rebuilds only the runtime; `CT_RENDERER=METAL` or `CT_RENDERER=VULKAN` (SDL3 host, also needs `brew install sdl3 lz4`) builds a single renderer.

**Mods.** Settings (F1) > Mods installs Captain Toad mods from a file or folder (More > Install from a file or folder) and lists them under Installed, to switch on or off; changes apply after a restart. A mod is a package with `"game_id": "captain-toad"` in its `manifest.json`, or a folder the importer recognises: a content tree that mirrors the game's `content/` folder (SDCafiine style), or a Cemu graphic pack (`rules.txt` with texture rules; shader packs need the Vulkan renderer). The game then reads the mod's files instead of its own. Wind Waker HD packages are refused, and Cemu `patches.txt` code patches are not applied. `sh tools/fetch_cemu_packs_macos.sh` installs the Captain Toad pack from Cemu's community graphic packs (CC0) that works here, Shadow Resolution, switched off. Installed mods live in `data/user/ModManager`.

Both the European (`CT-EUR-v16`) and the American (`CT-USA-v16`) v16 update are identified; `tools/prepare_game.py` and `tools/recompile.py` select the matching profile. The USA executable translates to the same 45,773 functions, 362 used imports and 36 primary-opcode-0 words as the European one. `runtime/mcp.cpp` reports the game's own region from `meta/meta.xml`; with the fixed European region the USA game found no message archive and stopped during startup.

On October 24, 2026, on an Apple M3 Pro with macOS 27.0.1, the app's setup prepared the USA game and v16 update (1,567 files) and compiled it in about a minute. The game started on Metal and on Vulkan through MoltenVK, initialized CoreAudio and ran for 40–60 seconds per test (3,000 frames at about 58 frames per second at 1x internal resolution on Metal) without stopping. Menus, gameplay, input, audio output and saves on macOS have not been checked yet.

Metal is the default renderer. Choose Vulkan with *Graphics > Renderer*. Dynamic resolution starts on (down to 0.75 of the internal resolution), so scenes the GPU cannot draw in time cost resolution instead of frame rate.

The *Gameplay* menu and the settings overlay's *Cheats* edit the save (`save/user/GameData.bin`, kept as `GameData.bin.before-cheats` before the first cheat) and restart the game: unlock every episode and course, clear every course, every Super Gem, every bonus objective, every challenge time, every Pixel Toad and 100% completion. The course list comes from the game's `content/SystemData/StageList.szs`; the save layout follows the CTSe save editor's description. Clearing episode 3's final course also marks the ending as seen, as the game does after the credits: a save with that course cleared and the ending unseen makes the episode book fail.

Settings > Display > Window size gives the TV window 1280x720, 1600x900, 1920x1080, 2560x1440 or 3840x2160 pixels inside, the sizes that fit its screen (macOS and Windows, out of full screen). With the Vulkan renderer, Settings > Graphics > Internal resolution > *Screen* draws the game with as many pixels as its window shows. Neither has been tested on a Mac or a Windows PC yet.

Gyro controllers: on macOS, Windows and Linux, Settings > Controls > Gyro starts at *Controller gyro*, so a controller with motion sensors (DualSense, DualShock 4, Switch Pro Controller, Joy-Con, Steam Deck and others) moves the virtual GamePad as the phone's gyro does on Android; *Cemuhook (DSU)* takes the motion from a DSU server app instead. This is the reference runtime's own gyro support (SDL3 sensors, GameController.framework on macOS); it has not been tried with Captain Toad on a desktop yet.

On Linux, `tools/build_game_linux.sh` builds the same runtime (Vulkan, SDL3 host) from `build/gen` as `build/game-linux/wwhd`; run it with `--game <prepared game folder>`. The script lists the packages it needs. Controller gyro needs read access to `/dev/hidraw*` (Steam's udev rules give it). On Ubuntu 24.04 every source file compiles; linking and running with real generated code have not been tried.

In the TV window, the picture-in-picture GamePad (Display > GamePad screen > Picture in picture) can be moved by dragging it with the right mouse button or with Option held, resized by dragging its bottom-right corner the same way or by scrolling over it; the placement is saved. A plain click on it stays a GamePad touch.

## Build the Android test APK

`tools/build_game_android.ps1` builds the same runtime with the NDK as the reference Android app's `libmain.so` (with SDL3, libc++ and the AdrenoTools hooks), then a private APK with Gradle. `tools/patch_runtime.py` gives the app its own package, `org.ctrecomp.captaintoad`, and name, so it never replaces a Wind Waker HD install. `tools/run_game_android.ps1` installs it on the phone named by `-Serial` or `local-reports/device-target.json`, copies the prepared game tree with `-PushGame`, starts it and saves `adb logcat -s wwhd` to `local-reports/android-game.log`:

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_game_android.ps1 -Cpu oryon-1
powershell -ExecutionPolicy Bypass -File tools/run_game_android.ps1 -PushGame
```

The scripts default to the SDK in `C:\Android\Sdk`, NDK `30.0.16248370`, CMake `4.1.2` and Android Studio's JDK. They have not been run on Windows yet. The APK contains recompiled game code: keep it on your own devices.

On macOS (and Linux), `tools/build_game_android.sh` and `tools/run_game_android.sh` do the same from the code the macOS app generated (`build/game-macos/data/gen` and `game`). They need the Android SDK with platform 36, build tools 35.0.0 and NDK `30.0.16248370` (Android Studio's, or Homebrew's `android-commandlinetools` with `sdkmanager`), a JDK 17 to 21 for Gradle 8.12 (`brew install openjdk@21`), CMake, Ninja and Python 3. Pillow, if installed, makes the launcher icon from your own game's title screen (`android/app/local-res`, never committed). Wireless debugging works: `adb connect <phone address>`, then pass `--serial`:

```sh
tools/build_game_android.sh
tools/run_game_android.sh --push-game --serial <adb serial>   # --push-save copies your save too
```

Tested on a Pixel 9 Pro XL (Tensor G4, Mali-G715, Android 17): the title screen, menus and levels run at about 60 fps through Vulkan. On Android the phone's screen starts as the GamePad, so a touch anywhere on the picture is a GamePad touch, and touches on the TV picture touch the GamePad at the same place (the TV shows the GamePad's picture in this game). Android's Back gesture opens Settings. Long-press the app icon to export or import the save (`user/GameData.bin`).

The game files and the save live in the app's own folder, `Android/data/org.ctrecomp.captaintoad/files` (`game/`, `save/`, `config/`), which Android deletes with the app; nothing in the app writes elsewhere except a save you export to Downloads. Android's app backup keeps the save and `settings.ini` (`data_extraction_rules.xml`), so they can come back when the app is installed again.

Tested on a Pixel 9 Pro XL. One menu button (☰) in the top left corner replaces the view button, the touch controls' show/hide button and the tilt button. Its menu opens Settings, moves and resizes the touch controls (a long press on the button does too), turns the phone's gyro camera on or off (Settings > Controls > Gyro, "device") and applies the save cheats; on Android a cheat closes the game, and the next start plays with it. Display options live in Settings > Display only: the view (GamePad only, TV with the GamePad in a corner, TV only), the picture shape, the touch controls and their opacity, and the camera cutout (*Use the area* draws up to the screen's edge around a punch-hole or notch camera; *Keep clear* leaves a black bar along that edge; from Android 15 the game's layout is padded by the cutout's size, since apps can no longer keep their window out of it). The internal resolution starts at *Screen* on Android: the picture on screen is drawn with as many pixels as it covers on the phone's display (Settings > Graphics; dynamic resolution still lowers it when the GPU cannot keep up).

Internal resolution *Screen* (Settings > Graphics, and the macOS Graphics menu): the picture is drawn with as many pixels as it covers on screen, up to 4x. Captain Toad draws its course once, into the TV's buffers, and copies it to the GamePad, so in GamePad only the GamePad's buffers get the factor for the lines they cover (up to 4x) and the TV's the factor that fills them and no more: on a 5K screen the GamePad picture is 3416x1920 and the TV source 3360x1890, sharp and at 60 fps on an M3 Pro, where a fixed 3x draws both screens at 3x. In TV only the GamePad's buffers, shown nowhere, draw at 1x. Checked on macOS (Metal).

Picture shape (Settings > Display, every platform): 16:9 as on the Wii U, *Match screen* (Android) or *Match window* (desktop), 16:10, 21:9 or 32:9. Wider shapes show more of the course at the sides with nothing stretched, on the TV and the GamePad: the runtime widens the screen-sized buffers, and the game's camera aspect (USA v16 0x023734F8, a profile hook in runtime/ct_frame.cpp) and three 16:9 constants take the new shape, the same places Cemu's community Resolution pack patches. The camera takes a new shape when the next course starts. Touches reach the GamePad's middle 16:9. Android starts with *Match screen*. Checked at 21:9 on macOS (the attract demo's course) and at the phone's shape on a Pixel 9 Pro XL in a course; the EUR build has no camera hook yet and stays 16:9. `CT_LOG_ASPECT=1` logs each camera's viewport and aspect.

## Next step: stream-out output, a longer playthrough and Android

Play further levels with a real controller to find the next missing imports and rendering differences. Produce stream-out output on the Vulkan renderer too (done on Metal): its vertex data is uploaded from guest memory rather than mapped, so the output must be written to a GPU buffer and either copied back to guest memory or used in place by later draws. Android needs the same runtime built as the reference's SDL activity library, then a private test APK. Audio quality, saves, suspend/resume behavior and performance on the S25 Ultra remain to be validated.

The headless diagnostic's own GX2 bridge stays as a resource-level test target. The Switch decompilation may help identify equivalent functions, but no code from that project has been incorporated.

## License and credits

Project tools and modifications are licensed under MPL-2.0; see `LICENSE`. ZeldaWWHDRecomp provides the reference recompiler/runtime and retains its original license and third-party credits in the separate checkout. See `THIRD_PARTY_NOTICES.md`.

This is an independent fan project, not affiliated with Nintendo. Game and console names identify intended compatibility. The repository contains tools, runtime source, identification metadata and documentation; game files and generated game code remain local.

## Graphics bootstrap validation

On October 10, 2026:

- GX2 defaults, viewport packing, display-list record/replay, context isolation, scan-buffer sizing, surface alignment, ring sizes, fetch descriptors and samplers passed tests on Windows and the S25 Ultra.
- CPU surface copies passed linear-to-tiled round trips and overlapping source/destination tests, with guard bytes preserved. The real startup code performed a 16x8, 32-bit surface copy from tiling mode 0 to mode 2.
- The synthetic Vulkan clear/readback test matched all 256 expected RGBA pixels on Adreno 830 and the desktop NVIDIA GeForce RTX 2080 Ti. This verifies a transfer operation; it does not validate game shaders or draw calls.
- All 1,569 transferred content/meta files were verified by SHA-256 on the S25 Ultra. Game files, checksum manifests and logs remain local.

Run the GPU readback test with:

```powershell
powershell -ExecutionPolicy Bypass -File tools/run_android_diagnostic.ps1 -Serial <local-device-id> -Mode Clear
```

The native device uses basic Vulkan 1.3 functionality for this test. Optional renderer features have not yet been enabled or validated.
