cmake_minimum_required(VERSION 3.20)
project(captain_toad_translation_prototype LANGUAGES C CXX)

# This target checks generated code on the selected architecture. It is not an APK or a runnable port.
if(NOT CMAKE_C_COMPILER_ID MATCHES "Clang")
  message(FATAL_ERROR "Generated PPC code requires Clang musttail support")
endif()
set(REFERENCE_DIR "${CMAKE_SOURCE_DIR}/upstream" CACHE PATH "Reference Wii U runtime headers")
set(GEN_DIR "${CMAKE_SOURCE_DIR}/build/gen" CACHE PATH "Locally generated Captain Toad C code")
file(GLOB GENERATED_CODE CONFIGURE_DEPENDS "${GEN_DIR}/code_*.c")
if(NOT GENERATED_CODE)
  message(FATAL_ERROR "Run python tools/recompile.py against your extracted game first")
endif()
add_library(captain_toad_gamecode STATIC ${GENERATED_CODE} "${GEN_DIR}/table.c" "${GEN_DIR}/imports.c")
target_include_directories(captain_toad_gamecode PRIVATE "${REFERENCE_DIR}/runtime/include" "${GEN_DIR}")
target_compile_features(captain_toad_gamecode PRIVATE c_std_11)
target_compile_options(captain_toad_gamecode PRIVATE -O2 -ffp-contract=off -fno-strict-aliasing -fsigned-char -w)

option(CT_BUILD_DIAGNOSTIC "Build a headless boot diagnostic with generic Cafe components" ON)
if(CT_BUILD_DIAGNOSTIC)
  file(READ "${REFERENCE_DIR}/runtime/src/core.cpp" REFERENCE_CORE)
  string(FIND "${REFERENCE_CORE}" "#ifdef CT_DIAGNOSTIC_STRICT_HLE" STRICT_HLE_MARKER)
  if(STRICT_HLE_MARKER EQUAL -1)
    message(FATAL_ERROR "Run python tools/patch_diagnostic.py upstream before building the strict diagnostic")
  endif()
  find_package(ZLIB REQUIRED)
  find_package(Threads REQUIRED)
  set(CT_CEMU "${REFERENCE_DIR}/runtime/third_party/cemu")
  set(CT_GX2_SOURCES runtime/gx2_bridge.cpp runtime/gx2_state_test.cpp runtime/gx2_scanout.cpp runtime/gx2_surface.cpp runtime/gx2_fetch.cpp runtime/gx2_texture.cpp runtime/gx2_copy.cpp
    "${REFERENCE_DIR}/runtime/src/gx2/gx2_state.cpp"
    "${CT_CEMU}/gx2_surface_calc.cpp" "${CT_CEMU}/gx2_texture_regs.cpp"
    "${CT_CEMU}/Cafe/HW/Latte/LatteAddrLib/LatteAddrLib.cpp"
    "${CT_CEMU}/Cafe/HW/Latte/LatteAddrLib/LatteAddrLib_Coord.cpp")
  add_executable(ct-diagnostic
    runtime/diagnostic.cpp runtime/vulkan_device.cpp ${CT_GX2_SOURCES} runtime/coreinit_boot.cpp runtime/fast_mutex.cpp runtime/mutex_test.cpp
    runtime/filesystem.cpp runtime/filesystem_test.cpp
    runtime/mcp.cpp runtime/uc.cpp runtime/act.cpp runtime/system_test.cpp
    "${REFERENCE_DIR}/runtime/src/core.cpp"
    "${REFERENCE_DIR}/runtime/src/threads.cpp"
    "${REFERENCE_DIR}/runtime/src/hle/coreinit_mem.cpp"
    "${REFERENCE_DIR}/runtime/src/write_watch.cpp"
    "${REFERENCE_DIR}/runtime/src/espresso_fp.c")
  target_include_directories(ct-diagnostic PRIVATE runtime "${REFERENCE_DIR}/runtime/include" "${REFERENCE_DIR}/runtime/src")
  target_include_directories(ct-diagnostic PRIVATE "${REFERENCE_DIR}/runtime/src/gx2" "${CT_CEMU}" "${REFERENCE_DIR}/runtime/third_party/fmt/include")
  set_source_files_properties(${CT_GX2_SOURCES}
    PROPERTIES COMPILE_OPTIONS "-include;${CT_CEMU}/cemu_shim.h")
  find_path(CT_VULKAN_INCLUDE_DIR vulkan/vulkan.h HINTS "${ZLIB_ROOT}/include" REQUIRED)
  target_include_directories(ct-diagnostic SYSTEM PRIVATE "${CT_VULKAN_INCLUDE_DIR}")
  target_compile_features(ct-diagnostic PRIVATE cxx_std_20)
  target_compile_definitions(ct-diagnostic PRIVATE CT_DIAGNOSTIC_STRICT_HLE=1)
  target_compile_options(ct-diagnostic PRIVATE -O2 -ffp-contract=off -fsigned-char -Wall -Wno-unused-function)
  target_link_libraries(ct-diagnostic PRIVATE captain_toad_gamecode ZLIB::ZLIB Threads::Threads ${CMAKE_DL_LIBS})
  if(ANDROID)
    target_link_libraries(ct-diagnostic PRIVATE log)
    target_link_options(ct-diagnostic PRIVATE -Wl,--strip-debug)
  endif()
  enable_testing()
  add_test(NAME ct_hash_known_vectors COMMAND ct-diagnostic --self-test)
  add_test(NAME ct_fast_mutex_same_core COMMAND ct-diagnostic --mutex-self-test)
  set_tests_properties(ct_fast_mutex_same_core PROPERTIES TIMEOUT 12)
  add_test(NAME ct_filesystem_roundtrip COMMAND ct-diagnostic --fs-self-test "${CMAKE_BINARY_DIR}/fs-fixture")
  add_test(NAME ct_system_record COMMAND ct-diagnostic --system-self-test)
  add_test(NAME ct_gx2_state COMMAND ct-diagnostic --gx2-self-test)
  file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/rejected-fixture/code")
  file(WRITE "${CMAKE_BINARY_DIR}/rejected-fixture/code/Kinopio.rpx" "synthetic invalid RPX fixture")
  add_test(NAME ct_reject_unknown_image COMMAND ct-diagnostic --game "${CMAKE_BINARY_DIR}/rejected-fixture" --verify-only)
  set_tests_properties(ct_reject_unknown_image PROPERTIES WILL_FAIL TRUE)
endif()
