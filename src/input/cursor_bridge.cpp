#include "native_input.h"
#include <algorithm>
#include <cstdint>
extern "C" uint32_t psx_read_word(uint32_t address);
extern "C" uint16_t psx_read_half(uint32_t address);
extern "C" void psx_write_half(uint32_t address,uint16_t value);
// Recovered from exact-SHA DUNE.EXE and confirmed by controlled D-pad reads.
// Only gameplay's module owns these fields. D2KF has different code/data here.
// Generated header contains words of ORIGINAL code for module identity guards.
#include "dune_module_guards.h"
static bool gameplay_module() {
    for(unsigned i=0;i<dune_module_guard_count;i++)
        if(psx_read_word(dune_module_guards[i].address)!=dune_module_guards[i].word)return false;
    return true;
}
int dune_cursor_get(int *x,int *y) {
    if(!gameplay_module())return 0;
    int cx=int16_t(psx_read_half(0x80101E1Cu));
    int cy=int16_t(psx_read_half(0x80101E1Eu));
    if(cx<0 || cx>383 || cy<0 || cy>239)return 0;
    *x=cx;*y=cy;return 1;
}
void dune_cursor_set(int x,int y) {
    if(!gameplay_module())return;
    // Original cursor update copies these current fields to the drawn/hit-test
    // pair at +4; writing both would bypass the game's update sequence.
    psx_write_half(0x80101E1Cu,uint16_t(std::clamp(x,0,383)));
    psx_write_half(0x80101E1Eu,uint16_t(std::clamp(y,0,239)));
}
