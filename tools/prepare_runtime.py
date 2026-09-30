"""Create auditable adapted upstream sources without editing the pinned checkout.

The strict translation unit contains no MIPS instruction evaluator. Missing AOT
entries fail before retiring an instruction. This is a gate, NOT a claim that
the current game/BIOS path already passes that gate.
"""
from pathlib import Path
import subprocess
import hashlib
import struct

ROOT=Path(__file__).resolve().parents[1]
UP=ROOT/'third_party/psxrecomp'
OUT=ROOT/'generated/adapted'

def source(path):
    return subprocess.check_output(['git','-C',str(UP),'show','HEAD:'+path]).decode('utf-8')

def once(text,old,new):
    if text.count(old)!=1:raise ValueError(f'Upstream anchor is not unique: {old[:90]}')
    return text.replace(old,new)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    text=source('runtime/src/dirty_ram_interp.c')
    begin='static int exec_one_fetched_inner(CPUState *cpu, uint32_t pc, uint32_t insn,\n                                  uint32_t *next_pc_out) {'
    start=text.index(begin)
    end=text.index('\nstatic int dirty_ram_dispatch_inner(CPUState* cpu, uint32_t addr, uint32_t stop_addr);',start)
    # Remove the opcode evaluator itself, including all opcode switch branches.
    text=text[:start]+begin+'\n    (void)insn; (void)next_pc_out;\n    dune_aot_missing(cpu, pc, "instruction evaluator");\n    return 0;\n}\n'+text[end:]
    text=once(text,'#include "dirty_ram_interp.h"','#include "dirty_ram_interp.h"\n#include "dune_aot_gate.h"')
    anchor='    /* Interp-pressure signal for variant-capture automation (step 2.8):'
    text=once(text,anchor,'    dune_aot_missing(cpu, addr, "unresolved dispatch");\n\n'+anchor)
    (OUT/'dirty_ram_nointerp.c').write_text(text,encoding='utf-8')
    stub=source('runtime/src/stub_interpreter.c')
    stub=once(stub,'#include "psx_interpreter.h"','#include "psx_interpreter.h"\n#include "dune_aot_gate.h"')
    stub=once(stub,'{ (void)cpu; (void)count; return 0; }','{ (void)count; dune_aot_missing(cpu, cpu->pc, "interp_step API"); return 0; }')
    stub=once(stub,'{ (void)cpu; (void)max; return 0; }','{ (void)max; dune_aot_missing(cpu, cpu->pc, "interp_run API"); return 0; }')
    (OUT/'nointerp_api.c').write_text(stub,encoding='utf-8')
    main=source('runtime/src/main.cpp')
    main='#include "native_input.h"\n'+main
    main=once(main,'        debug_server_init(debug_port);',
        '        if (debug_port != 0) debug_server_init(debug_port);')
    anchor=('static int capture_pad_slot(int s, PsxNetPad* out) {\n'
        '    if (!out) return 0;\n    out->buttons = 0xFFFFu;\n'
        '    out->lx = out->ly = out->rx = out->ry = 0x80u;\n'
        '    out->analog = 0;\n    out->connected = 0;')
    main=once(main,anchor,anchor+'\n'
        '    if (s == 0 && dune_input_capture(&out->buttons)) { out->connected = 1; return 1; }')
    anchor='        /* Pump SDL events to prevent window freeze. */\n        SDL_Event ev;\n        while (SDL_PollEvent(&ev)) {'
    main=once(main,anchor,anchor+'\n            if (dune_input_event(&ev)) continue;')
    anchor='    psx_apply_window_icon(sdl_window, argv[0]);'
    main=once(main,anchor,'    dune_input_initialize(sdl_window);\n'+anchor)
    anchor='    SDL_RenderCopy(sdl_renderer, sdl_texture, &src, &dst);'
    main=once(main,anchor,'    dune_input_viewport(sdl_window, sdl_renderer, float(dst.x), float(dst.y),\n'
        '        float(dst.w), float(dst.h), int(present_w), int(present_h));\n'+anchor)
    (OUT/'main_pc_input.cpp').write_text(main,encoding='utf-8')
    original=(ROOT/'generated/assets/iso/DUNE.EXE').read_bytes()
    expected='c55547212b78ac324c3c5fc6b1c5353cf6ab4c2412b69419fcba2689ff1816a8'
    if hashlib.sha256(original).hexdigest()!=expected:raise ValueError('Wrong DUNE.EXE for cursor layout')
    addresses=[0x80019000,0x80019004,0x8005A888,0x8005A88C,0x8005B8A4,0x8005B8A8]
    words=[struct.unpack_from('<I',original,a-0x80019000+0x800)[0] for a in addresses]
    guard='// Generated from locally imported, hash-verified DUNE.EXE. Do not distribute.\n'
    guard+='struct DuneModuleGuard { uint32_t address,word; };\n'
    guard+='static const DuneModuleGuard dune_module_guards[] = {\n'
    guard+=''.join(f'    {{0x{a:08X}u,0x{w:08X}u}},\n' for a,w in zip(addresses,words))+'};\n'
    guard+=f'static const unsigned dune_module_guard_count={len(words)};\n'
    (OUT/'dune_module_guards.h').write_text(guard,encoding='utf-8')
    print('Strict sources prepared: opcode evaluator removed; missing native entry is fatal.')

if __name__=='__main__':main()
