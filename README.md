# Captain Toad EUR — Android recompilation prototype

Captain Toad Wii U EUR with internal update version 16 has been translated and compiled into native code. Linked with the full reference game runtime, it renders the title screen, the opening cutscene and the episode book menu through Vulkan at about 60 frames per second on a Windows ARM64 Snapdragon X PC, with its audio mixer and SDL output running (not yet checked by ear). It then waits at the menu for controller input. The separate headless diagnostic enters the game's startup code on Windows and a Samsung Galaxy S25 Ultra. Gameplay, controls, saves, Android rendering and APK packaging remain unfinished.

The project started on October 10, 2026. All public documentation, code comments, commit messages and GitHub discussions for this project should use English.

## Set up the project

Requirements: Git, Python 3.10 or later and, for ARM64 builds, an Android SDK with NDK, CMake and Ninja. The prototype was tested on Windows with Python 3.11.

```powershell
git clone https://github.com/rhemfur/CaptainToadRecomp.git
cd CaptainToadRecomp
powershell -ExecutionPolicy Bypass -File tools/setup_reference.ps1
```

The setup script downloads the pinned runtime/recompiler commit and applies the hook-list and strict diagnostic extensions. It preserves an existing checkout and refuses to change a different revision automatically.

Supply your own Captain Toad Wii U EUR game and v16 update, extracted separately into `code/content/meta` directory trees. [cdecrypt](https://github.com/VitaSmith/cdecrypt) supports NUS installation packages. This repository does not include the game, tickets, keys or the extractor.

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

- [ZeldaWWHDRecomp](https://github.com/ZeldaWWHDRecomp/ZeldaWWHDRecomp), commit `defb89f21607345e2e97b2c145a071a3f362640c`. Its MPL-2.0 license and credits remain in the reference checkout.
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

The generator rejects an RPX whose SHA-256 differs from the identified profile. Do not select Zelda's USA profile to bypass this check.

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
- Stream out follows Cemu's command semantics: `GX2SetStreamOutBuffer` sets each buffer's base and size, `GX2SetVertexShader` sets the vertex strides, `GX2SetStreamOutContext` and `GX2SaveStreamOutContext` reset, load or save the write offset on the render thread in command order, and each stream-out draw advances the offsets by the bytes its vertices emit. The renderer still skips those rasterizer-killed draws, so their vertex output is not produced and the buffers keep their previous contents. The first such draw logs this.

The build is strict: it stops at the first missing import. Tested with llvm-mingw 20260922 (aarch64), the Visual Studio Build Tools CMake/Ninja and Vulkan headers:

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_game_windows.ps1
build/game-windows/wwhd.exe --game game
```

On October 10, 2026, on a Snapdragon X PC (Adreno X1-85, Vulkan 1.3.295), the game loaded its shader, layout, font and localized message archives, initialized audio and its worker threads, faded in the title screen and played the opening cutscene on the TV and GamePad views at 46–60 frames per second. It looked up a Super Mario 3D World save, found none and continued to the episode book menu, about 4,000 frames after startup, where it waits for input. A 90-second run hit no missing import. The executable and any frame captures contain recompiled game code or game imagery and stay local. Window titles and logs still use the reference's Wind Waker HD naming.

## Next step: input, stream-out output and Android

Drive the menu with controller input and reach the first level. Produce stream-out output on the GPU: a vertex-only pipeline without rasterization that writes Cemu's storage-buffer stream-out path, read back into guest memory. Android needs the same runtime built as the reference's SDL activity library, then a private test APK. Audio quality, saves, suspend/resume behavior and performance on the S25 Ultra remain to be validated.

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
