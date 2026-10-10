# Third-party references and licenses

## ZeldaWWHDRecomp

- Source: https://github.com/ZeldaWWHDRecomp/ZeldaWWHDRecomp
- Pinned reference commit: `defb89f21607345e2e97b2c145a071a3f362640c`.
- License: Mozilla Public License 2.0.
- `patches/recompiler-hook-paths.patch` modifies `tools/recomp/recomp.py` to accept an explicit hook list. Omitting the argument preserves the original behavior.
- `patches/strict-diagnostic-hle.patch` modifies `runtime/src/core.cpp` only when `CT_DIAGNOSTIC_STRICT_HLE` is enabled.
- The `upstream/` checkout is downloaded separately. Its files, licenses and third-party credits remain in that checkout and are not incorporated into this repository's history.
- ZeldaWWHDRecomp's Android integration includes contributions by rhemfur, who also owns this project.

## Adapted diagnostic runtime components

- `runtime/filesystem.cpp` adapts ZeldaWWHDRecomp's `runtime/src/hle/fs.cpp` under MPL-2.0, removing Zelda's mod/language redirections and restricting paths and writes.
- `runtime/coreinit_boot.cpp` adapts debugger and clock queries from the same project's `coreinit_misc.cpp`.
- Fast-mutex, MCP and UC layouts/behavior were researched in Cemu's MPL-2.0 source:
  - [coreinit_Thread.h](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/coreinit/coreinit_Thread.h)
  - [coreinit_Synchronization.cpp](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/coreinit/coreinit_Synchronization.cpp)
  - [coreinit_MCP.h](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/coreinit/coreinit_MCP.h)
  - [coreinit_MCP.cpp](https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/coreinit/coreinit_MCP.cpp)

## cdecrypt

- Source: https://github.com/VitaSmith/cdecrypt
- Commit used for the initial local extraction: `0ca58c66b0f23309c69b691caf6d39bf8868d96d`.
- The extractor was obtained and compiled separately. No cdecrypt source or binary is included in this repository.
- Consult the original project's license and credits before redistributing that tool.

## cttt-decomp

- Source: https://github.com/shibbo/cttt-decomp
- Research reference for the Switch version. No source from this project has been incorporated into the prototype.

No Nintendo game assets or generated game code are included in this repository.
