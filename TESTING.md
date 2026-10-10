# Android test environment

Initial target: Samsung Galaxy S25 Ultra (SM-S938B), queried through ADB on October 10, 2026.

| Item | Observed value |
|---|---|
| Android | 16, API 36 |
| ABI | arm64-v8a |
| SoC | Qualcomm/QTI SM8750 |
| GPU | Adreno 830 |
| Vulkan version advertised by Android | 1.3.0 |
| Vulkan version reported by the native probe | 1.3.284 |
| ADB | Connected and authorized |

The ARM64 prototype uses Android API 33 as its build minimum. A device running API 36 does not by itself require changing that minimum.

## Verified behavior

- The native diagnostic entered Captain Toad's startup code and passed `gx2.GX2Init`, configured the TV buffer and reached `gx2.GX2CalcDepthBufferHiZInfo`.
- Vulkan instance and logical device creation passed on the system driver.
- Native tests passed for SHA-256 vectors, fast-mutex recursion/ownership/same-core contention, filesystem reads and synthetic save round trips, and MCP/UC records.
- Six runtime CTest cases passed on Windows; 17 existing reference recompiler tests passed.

These results do not validate the game's renderer, graphics, audio, real saves, performance or gameplay. APK integration remains unfinished.

## Device selection and local files

When multiple Android devices are connected, select the phone explicitly in every command: `adb -s <local-device-id> ...`.

The local device identifier is stored in `local-reports/device-target.json`, which is excluded from Git. Do not publish it. Diagnostic logs and binaries also remain local.

The device script uses `/data/local/tmp/captain-toad`. Filesystem tests use a synthetic fixture, separate from the game files. A headless diagnostic does not require installing an APK.

## Next validation

Resolve auxiliary-buffer sizing and integrate shader draws and Vulkan presentation to obtain the first game image. Then verify the menu, first level, audio, touch/controller input, real save/load behavior and suspend/resume. Report measured performance rather than inferring frame rates from another game.

See `README.md` for reproducible commands and current runtime limitations.

## Graphics tests

The synthetic Vulkan clear/readback passed with 256/256 matching RGBA pixels on Adreno 830. The same operation passed on the desktop RTX 2080 Ti. No game frame was rendered.

GX2 resource/state tests passed for viewport packing, display lists, isolated contexts, scan-buffer sizing, surface alignment, fetch descriptors and sampler bindings. Surface-copy tests passed for linear/tiled round trips and overlapping ranges. Guard bytes were preserved.

All 1,569 transferred content/meta files passed SHA-256 verification in the isolated phone directory. This checks file transfer integrity, not gameplay compatibility.
