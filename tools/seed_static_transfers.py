"""Recover module-scoped callback / jump-table exports from ORIGINAL files.

A candidate must be a statically decoded block label or non-data function, and
be referenced by an aligned word in that same exact-hash original image. No
runtime RAM, executed-PC snapshot or arbitrary MIPS scanning is an AOT source.
The native module's existing live-byte guards remain mandatory.
"""
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT=Path(__file__).resolve().parents[1]
HASHES={
 'D2KF.EXE':'82fa578104c4122c997aa0db530dfe9ee407494b07f097600033074a66b9ab5b',
 'DUNE.EXE':'c55547212b78ac324c3c5fc6b1c5353cf6ab4c2412b69419fcba2689ff1816a8'}

def main():
    profile_path=ROOT/'aot/overlays.json'
    profile=json.loads(profile_path.read_text())
    receipt={'schema':'dune static transfer exports v1','source':'original-image only','modules':[]}
    for spec in profile['images']:
        name=spec['files'][0]
        data=(ROOT/'generated/assets/iso'/name).read_bytes()
        digest=hashlib.sha256(data).hexdigest()
        if digest!=HASHES[name]:raise ValueError('Original hash mismatch: '+name)
        info=json.loads((ROOT/f'generated/psx/{name}-analysis/analysis.json').read_text())
        text=(ROOT/'disasm'/f'{name}.txt').read_text()
        instructions={int(a,16) for a in re.findall(r'^\s+([0-9A-F]{8})\s+[0-9A-F]{8}\s+',text,re.M)}
        labels={int(a,16) for a in re.findall(r'^\.L_([0-9A-F]{8}):',text,re.M)}
        labels|={f['addr'] for f in info['functions'] if not f['is_data']}
        labels&=instructions
        refs={}
        for offset in range(0x800,len(data)-3,4):
            word=struct.unpack_from('<I',data,offset)[0]
            if word in labels:refs.setdefault(word,[]).append(offset)
        # A table export can split a formerly contiguous generated function.
        # Export *all* proven CFG block starts as resumable entries as well;
        # otherwise its outbound direct edges become the next missing entry.
        ranges=[(f['addr'],f['end']) for f in info['functions'] if not f['is_data']
                and any(f['addr']<pc<f['end'] for pc in refs)]
        entries=set(refs)|{pc for pc in labels if any(lo<=pc<hi for lo,hi in ranges)}|{info['entry_point']}
        spec['entries']=[f'0x{pc:08X}' for pc in sorted(entries)]
        receipt['modules'].append({'name':name,'sha256':digest,'load':hex(info['load_address']),
            'entry_count':len(entries),'exports':[{'pc':hex(pc),'file_offsets':[hex(x) for x in refs.get(pc,[])],
            'kind':'entry' if pc==info['entry_point'] else 'static address-taken block/function' if pc in refs else 'static CFG block/function'} for pc in sorted(entries)]})
    profile_path.write_text(json.dumps(profile,indent=2)+'\n',encoding='utf-8')
    (ROOT/'research/static-transfer-exports.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print([(m['name'],m['entry_count']) for m in receipt['modules']])

if __name__=='__main__':main()
