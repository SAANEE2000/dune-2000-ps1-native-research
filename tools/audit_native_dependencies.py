"""Auditable inventory of observed fallback PCs and statically decoded BIOS calls.

Old telemetry normalizes addresses and does not record overlay identity. It is
therefore never used as original code, or treated as a complete game-path proof.
"""
import argparse
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--build',default='strict');args=p.parse_args()
    functions=json.loads((ROOT/'symbols/functions.json').read_text())
    entries={}
    for path in (ROOT/'generated/probes').glob('**/*dirty*stats*.json'):
        data=json.loads(path.read_text())
        for item in data.get('per_pc',[]):
            pc=int(item['pc'],16)|0x80000000
            row=entries.setdefault(pc,{'pc':f'0x{pc:08X}','observations':[]})
            row['observations'].append({'source':path.relative_to(ROOT).as_posix(),
                'hits':item.get('hits',0),'entry_hits':item.get('entries',0),
                'instructions':item.get('insns',0),'return_address':item.get('ext_ra')})
    for path in (ROOT/'generated/probes').glob('**/runtime.log'):
        for pc,ra,reason in re.findall(r'DUNE_AOT_REQUIRED pc=(0x[0-9A-F]+) ra=(0x[0-9A-F]+).*?reason=([^\r\n]+)',path.read_text(errors='replace')):
            number=int(pc,16)|0x80000000
            row=entries.setdefault(number,{'pc':f'0x{number:08X}','observations':[]})
            row['observations'].append({'source':path.relative_to(ROOT).as_posix(),'strict_gate':True,'return_address':ra,'reason':reason})
    for pc,row in entries.items():
        candidates=[f for f in functions if int(f['address'],16)<=pc<int(f['address'],16)+f['size']]
        row['static_candidates']=[{'module':f['image'],'function':f['address'],'name':f['proposed_name']} for f in candidates]
        if pc<0x80010000:kind='BIOS RAM / interrupt or kernel continuation; needs original source proof'
        elif pc<0x80018800:kind='resident boot callback / continuation'
        elif candidates:kind='overlay function / indirect jump / continuation; module identity ambiguous in old telemetry'
        else:kind='unresolved dynamic address'
        row['classification']=kind
    result={'scope':'all PCs in retained telemetry; NOT all possible game execution paths',
        'overlay_identity_limitation':True,'count':len(entries),'pcs':[entries[k] for k in sorted(entries)]}
    (ROOT/'research/fallback-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    calls=[f for f in functions if f.get('bios_call')]
    lines=['# BIOS boundary inventory','',
        'Static thunks from the exact imported executables; reachability at runtime is not proven for every row.',
        'No replacement in this table is claimed implemented. OpenBIOS is still required.','',
        '| Module | Thunk | Selector / semantics | Direct callers | Native replacement status |',
        '|---|---|---|---|---|']
    for f in calls:
        lines.append('| '+ ' | '.join([f['image'],f['address'],f['bios_call'],', '.join(f['callers']) or 'indirect/unknown','NOT REPLACED'])+' |')
    (ROOT/'docs/BIOS_CALLS.md').write_text('\n'.join(lines)+'\n')
    build=ROOT/'build'/args.build;ninja=(build/'build.ninja').read_text()
    link=next(line for line in ninja.splitlines() if line.startswith('build Dune2000Native.exe:'))
    evaluator_linked=bool(re.search(r'/(dirty_ram_interp|psx_interpreter)\.c\.obj',link))
    checks={'mips_evaluator_not_linked':not evaluator_linked,
        'strict_fail_closed_adapter_linked':'dirty_ram_nointerp.c.obj' in link and 'dune_aot_gate.c.obj' in link,
        'bios_not_linked':'OpenBIOS' not in link,
        'cpu_state_machine_removed':False,'raw_bin_dependency_removed':False,
        'hardware_register_runtime_removed':not any('/'+name+'.c.obj' in link for name in ('gpu','spu','cdrom','timers','interrupts','sio')),
        'full_path_zero_fallback_proven':False,'ai_parity_proven':False}
    gate={'build':args.build,'native_only_release_allowed':all(checks.values()),'checks':checks,
        'note':'Source/link inventory plus strict failure tests; zero full-path execution cannot be inferred from missing evaluator.'}
    (ROOT/f'research/native-release-gate-{args.build}.json').write_text(json.dumps(gate,indent=2)+'\n')
    print(json.dumps({'fallback_pcs':len(entries),'bios_thunks':len(calls),**gate},indent=2))
    return 0 if gate['native_only_release_allowed'] else 2

if __name__=='__main__':raise SystemExit(main())
