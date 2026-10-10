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

- The native diagnostic entered Captain Toad's startup code and reached `gx2.GX2Init`.
- Vulkan instance and logical device creation passed on the system driver.
- Native tests passed for SHA-256 vectors, fast-mutex recursion/ownership/same-core contention, filesystem reads and synthetic save round trips, and MCP/UC records.
- Five runtime CTest cases passed on Windows; 17 existing reference recompiler tests passed.

These results do not validate the game's renderer, graphics, audio, real saves, performance or gameplay. APK integration remains unfinished.

## Device selection and local files

When multiple Android devices are connected, select the phone explicitly in every command: `adb -s <local-device-id> ...`.

The local device identifier is stored in `local-reports/device-target.json`, which is excluded from Git. Do not publish it. Diagnostic logs and binaries also remain local.

The device script uses `/data/local/tmp/captain-toad`. Filesystem tests use a synthetic fixture, separate from the game files. A headless diagnostic does not require installing an APK.

## Next validation

Integrate GX2 and the Vulkan renderer to obtain the first image. Then verify the menu, first level, audio, touch/controller input, real save/load behavior and suspend/resume. Report measured performance rather than inferring frame rates from another game.

See `README.md` for reproducible commands and current runtime limitations.
