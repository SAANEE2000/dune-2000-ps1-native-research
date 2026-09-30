cmake_minimum_required(VERSION 3.20)
project(Dune2000PSXNative LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 20)
set(PSXRECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/third_party/psxrecomp" CACHE PATH "Pinned PSXRecomp")
set(PSX_RECOMP_UI OFF CACHE BOOL "No launcher enhancements")
set(PSX_NETPLAY OFF CACHE BOOL "Baseline is offline")
set(PSXRECOMP_BIOS_STEMS "OpenBIOS" CACHE STRING "Locally recompiled BIOS")
option(DUNE_STRICT_AOT "Remove MIPS evaluator; fail on unresolved native coverage" OFF)
option(DUNE_PC_INPUT "Direct gameplay mouse cursor and SDL3 action bindings" OFF)
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")
psxrecomp_add_game_runtime(psx-runtime
    WINDOW_TITLE "Dune 2000 PS1 Native - research build"
    EXE_NAME "Dune2000Native"
    DEFAULT_GAME_CONFIG_PATH "${CMAKE_CURRENT_SOURCE_DIR}/game.toml"
    MAX_PLAYERS 1
    GAME_OVERLAY_STATIC_C "${CMAKE_CURRENT_SOURCE_DIR}/generated/native/overlays/overlays_static.c"
    GEN_MARKER "generated/native/boot/SLUS_009.73_dispatch.c"
    GEN_FULL_GLOB "generated/native/boot/SLUS_009.73_full_*.c"
    PRELOADED_MODS_DIR "NONE"
)
if(NOT MSVC)
  target_compile_definitions(psx-runtime PRIVATE FMT_CONSTEVAL=)
endif()
if(DUNE_STRICT_AOT OR DUNE_PC_INPUT)
  execute_process(COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/.venv/Scripts/python.exe"
    "${CMAKE_CURRENT_SOURCE_DIR}/tools/prepare_runtime.py"
    COMMAND_ERROR_IS_FATAL ANY)
endif()
if(DUNE_STRICT_AOT)
  get_target_property(_dune_sources psx-runtime SOURCES)
  list(FILTER _dune_sources EXCLUDE REGEX "/(dirty_ram_interp|stub_interpreter|psx_interpreter)\\.c$")
  set_property(TARGET psx-runtime PROPERTY SOURCES "${_dune_sources}")
  target_sources(psx-runtime PRIVATE generated/adapted/dirty_ram_nointerp.c
    generated/adapted/nointerp_api.c runtime/dune_aot_gate.c)
  target_include_directories(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/runtime")
  target_compile_definitions(psx-runtime PRIVATE DUNE_STRICT_AOT=1)
endif()
if(DUNE_PC_INPUT)
  get_target_property(_dune_sources psx-runtime SOURCES)
  list(FILTER _dune_sources EXCLUDE REGEX "/main\\.cpp$")
  set_property(TARGET psx-runtime PROPERTY SOURCES "${_dune_sources}")
  target_sources(psx-runtime PRIVATE generated/adapted/main_pc_input.cpp
    src/input/native_input.cpp src/input/cursor_bridge.cpp)
  target_include_directories(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/input"
    "${CMAKE_CURRENT_SOURCE_DIR}/generated/adapted" "${PSXRECOMP_ROOT}/runtime/src")
  target_compile_definitions(psx-runtime PRIVATE DUNE_INPUT_CONFIG_PATH="${CMAKE_CURRENT_SOURCE_DIR}/config/input.ini")
  add_executable(dune-input-tests tests/test_sdl_input.cpp src/input/native_input.cpp)
  target_include_directories(dune-input-tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/input")
  target_compile_definitions(dune-input-tests PRIVATE DUNE_INPUT_CONFIG_PATH="${CMAKE_CURRENT_SOURCE_DIR}/tests/input-test.ini")
  target_link_libraries(dune-input-tests PRIVATE SDL3::SDL3)
  if(MSVC)
    target_compile_options(dune-input-tests PRIVATE /UNDEBUG)
  else()
    target_compile_options(dune-input-tests PRIVATE -UNDEBUG)
  endif()
endif()
