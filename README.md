# Captain Toad EUR — Android recompilation prototype

Captain Toad Wii U EUR with internal update version 16 has been translated and compiled into native code. The headless diagnostic enters the game's startup code on Windows and a Samsung Galaxy S25 Ultra, then stops at `gx2.GX2Init`. Graphics, menus, gameplay, audio and APK packaging remain unfinished.

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
- `runtime/`: startup services, fast mutex, filesystem, diagnostic executable and tests.
- `upstream/`: separately downloaded ZeldaWWHDRecomp reference checkout, ignored by Git.
- `work/extracted/base` and `work/extracted/update`: separate local game/update extractions.
- `game/`: effective game tree, with update files replacing matching base paths.
- `local-reports/`: local manifests, import audits and diagnostic logs.
- `build/gen/`: C generated locally from the game executable.
- `build/android-gamecode/`: ARM64 static library and `ct-diagnostic` executable.

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

Diagnostic startup is confirmed on Android and Windows through the call to `GX2Init`. On the S25 Ultra, Vulkan instance and logical device creation passed; the Adreno 830 driver reported API 1.3.284. This does not validate the game's renderer, menus, audio, real saves or gameplay.

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

The native diagnostic verifies the RPX SHA-256 before loading guest memory, initializes data imports and starts Captain Toad's guest threads. It has no renderer, audio backend, snapshots or Zelda hooks. An unsupported API stops it with exit code 78; the default ten-second deadline stops it with 124.

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

Other script modes are `SelfTest`, `Mutex`, `Filesystem`, `System` and `Verify`. Filesystem tests use synthetic content and save files in a separate fixture directory.

Validation on October 10, 2026:

- Five CTest cases passed on Windows: SHA-256 vectors, same-core mutex contention, filesystem reads/writes/bounds, MCP/UC records and rejection of an unknown RPX.
- Native SHA-256, fast mutex, filesystem and MCP/UC tests passed on the S25 Ultra. The Vulkan probe created an instance and a logical device.
- With startup services implemented, the diagnostic reached `gx2.GX2Init`. Graphics initialization and rendering remain unfinished.

## Next step: GX2 and Vulkan rendering

Integrate GX2 APIs and the generic rendering queue while separating Zelda's mod, camera and interpolation dependencies. Start at the first graphics call, `GX2Init`, and work toward the first rendered image. Audio, controls, real saves and APK packaging follow.

Current limitations: `_iob` has no implemented stream ABI; imported exception/atexit callbacks remain null; unsupported words and undefined calls remain explicit failures; only three UC settings are supported, with English and an EUR virtual console as the initial configuration. Unknown settings stop the diagnostic. Fast-mutex ownership queues, priority inheritance and save states are not implemented.

The Switch decompilation may help identify equivalent functions, but no code from that project has been incorporated.

## License and credits

Project tools and modifications are licensed under MPL-2.0; see `LICENSE`. ZeldaWWHDRecomp provides the reference recompiler/runtime and retains its original license and third-party credits in the separate checkout. See `THIRD_PARTY_NOTICES.md`.

This is an independent fan project, not affiliated with Nintendo. Game and console names identify intended compatibility. The repository contains tools, runtime source, identification metadata and documentation; game files and generated game code remain local.
