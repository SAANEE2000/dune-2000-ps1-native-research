"""Reproducible evidence database, not an assertion that heuristic code is correct.

Consumes independently generated PS1Recomp TOML and PSXRecomp JSON. Keeps
disassembly/instruction bodies in ignored generated/disasm, metadata in symbols.
"""
import bisect
from collections import Counter,defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import struct
import tomllib

ROOT=Path(__file__).resolve().parents[1]
NAMES=('SLUS_009.73','D2KF.EXE','DUNE.EXE')
HX=lambda n:f'0x{n:08X}'

def mask(word):
    op=word>>26
    if op in (2,3):return word&0xFC000000
    if op in (1,4,5,6,7,8,9,10,11,12,13,14,15,20,21,22,23) or op>=32:return word&0xFFFF0000
    return word

def write_db(name, rows):
    target=ROOT/'symbols'/name
    target.with_suffix('.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    if not rows:return
    with target.with_suffix('.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader()
        writer.writerows({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)

def main():
    db=tomllib.loads((ROOT/'third_party/ps1-recomp/ps1Analyzer/data/psyq_signatures.toml').read_text())['signature']
    signatures=defaultdict(list)
    for sig in db:signatures[(sig['library'],sig['name'].split('@')[0])].append(sig)
    functions=[];globals_=[];psyq=[];summaries={};indirect=[]
    for name in NAMES:
        b=(ROOT/'generated/assets/iso'/name).read_bytes()
        assert b[:8]==b'PS-X EXE'
        h=dict(zip(('pc','gp','load','payload_size','data_addr','data_size','bss_addr','bss_size','stack_addr','stack_size'),struct.unpack_from('<10I',b,16)))
        assert len(b)==2048+h['payload_size']
        body=b[2048:]
        u32=lambda address:struct.unpack_from('<I',body,address-h['load'])[0]
        signed=lambda n:n-65536 if n&0x8000 else n
        # Recognize the exact shared CRT structure before interpreting constants.
        pc=h['pc'];ops=[u32(pc+i*4) for i in range(60)]
        assert ops[0]>>16==0x3C08 and ops[1]>>16==0x2508
        assert ops[2]>>16==0x3C09 and ops[3]>>16==0x2529
        assert ops[4]==0xAD000000 and ops[5]==0x25080004
        assert ops[6]==0x0109082B and ops[7]==0x1420FFFC
        bss_lo=((ops[0]&65535)<<16)+signed(ops[1]&65535)
        bss_hi=((ops[2]&65535)<<16)+signed(ops[3]&65535)
        stack_word=((ops[9]&65535)<<16)+signed(ops[10]&65535)
        reserve_word=((ops[19]&65535)<<16)+signed(ops[20]&65535)
        crt_gp=((ops[31]&65535)<<16)+signed(ops[32]&65535)
        analysis=json.loads((ROOT/f'generated/psx/{name}-analysis/analysis.json').read_text())
        edges=json.loads((ROOT/f'generated/psx/{name}-analysis/edges.json').read_text())['edges']
        refs=json.loads((ROOT/f'generated/psx/{name}-analysis/refs.json').read_text())['refs']
        ind=json.loads((ROOT/f'generated/psx/{name}-analysis/indirect.json').read_text())
        ps1=tomllib.loads((ROOT/f'generated/ps1/{name}.toml').read_text())
        proposed={int(x['address'],16):x for x in ps1['hle_functions']}
        callers=defaultdict(set);callees=defaultdict(set)
        for e in edges:
            if e['from'] and e['kind'] not in ('address_taken',):
                callers[e['to']].add(e['from']);callees[e['from']].add(e['to'])
        for addr,p in proposed.items():
            lib=p['library'];sn=p['name'].removeprefix(lib+'_')
            matches=[]
            for sig in signatures[(lib,sn)]:
                code=body[addr-h['load']:addr-h['load']+sig['size']]
                if len(code)!=sig['size'] or len(code)%4:continue
                full=hashlib.sha256(code).hexdigest()[:16]
                masked=hashlib.sha256(b''.join(struct.pack('<I',mask(w[0])) for w in struct.iter_unpack('<I',code))).hexdigest()[:16]
                mode=sig.get('match_mode','masked')
                if (mode=='full' and full==sig['hash_full']) or (mode=='masked' and masked==sig['hash_masked']):
                    matches.append(dict(size=sig['size'],mode=mode,exact=full==sig['hash_full'],
                                        masked_hash=masked,full_hash=full,sources=sig.get('sources',[])))
            exact=any(m['exact'] for m in matches)
            psyq.append(dict(image=name,address=HX(addr),proposed_name=p['name'],library=lib,
                             confidence='CONFIRMED' if exact else 'LIKELY' if matches else 'HYPOTHESIS',
                             evidence=matches,callers=[HX(x) for x in sorted(callers[addr])],
                             notes='Exact signature bytes' if exact else 'Broad immediate masking; semantic identity/version NOT proven. No HLE replacement enabled.'))
        maprows=analysis['functions'];starts=[f['addr'] for f in maprows]
        for f in maprows:
            addr=f['addr'];p=proposed.get(addr)
            confidence='LIKELY' if f['confidence'] in ('verified','high') else 'HYPOTHESIS'
            if addr==h['pc']:confidence='CONFIRMED'
            functions.append(dict(image=name,address=HX(addr),size=f['size'],
                                  callers=[HX(x) for x in sorted(callers[addr])],callees=[HX(x) for x in sorted(callees[addr])],
                                  confidence=confidence,proposed_name=p['name'] if p else f'FUN_{addr:08X}',
                                  notes=f"PSXRecomp {f['confidence']}: {f['confidence_reason']}; reachable={f['reachable']}; boundaries are static estimates",
                                  bios_call=f['bios_call'],gte=f['sig']['gte'],
                                  ps1_agrees_entry=any(int(x['address'],16)==addr for x in ps1['functions'])))
        known=set(starts)
        for f in ps1['functions']:
            addr=int(f['address'],16)
            if addr not in known:
                functions.append(dict(image=name,address=HX(addr),size=f['size'],callers=[],callees=[],confidence='HYPOTHESIS',
                                      proposed_name=f'FUN_{addr:08X}',notes='PS1Recomp-only candidate; linear sweep can mistake data for code',
                                      bios_call='',gte=False,ps1_agrees_entry=False))
        grouped=defaultdict(list)
        for ref in refs:
            target=ref['target']
            if (0x80000000<=target<0x80200000) or (0x1f800000<=target&0x1fffffff<0x1f802000):grouped[target].append(ref)
        code_writes=[];mmio=Counter()
        def kind(t):
            if 0x1f800000<=t&0x1fffffff<0x1f802000:t &= 0x1fffffff
            if 0x1f800000<=t<0x1f800400:return 'scratchpad'
            if 0x1f801000<=t<0x1f802000:return 'MMIO'
            i=bisect.bisect_right(starts,t)-1
            if i>=0 and starts[i]<=t<maprows[i]['end']:return 'code_or_pointer'
            if bss_lo<=t<bss_hi:return 'CRT_BSS'
            return 'data_candidate'
        for target,rr in sorted(grouped.items()):
            k=kind(target)
            if k=='code_or_pointer':
                code_writes.extend(dict(target=HX(target),pc=HX(r['pc']),function=HX(r['func'])) for r in rr if r['write'])
            if k=='MMIO':mmio[HX(target)]+=len(rr)
            globals_.append(dict(image=name,address=HX(target),proposed_name=f'DAT_{target:08X}',confidence='LIKELY',kind=k,
                                 read_sites=[HX(r['pc']) for r in rr if not r['write']],write_sites=[HX(r['pc']) for r in rr if r['write']],
                                 notes='Static LUI/low-pair reference; pointer arithmetic/control flow can invalidate inferred value'))
        hardware_literals=[]
        for offset,(word,) in enumerate(struct.iter_unpack('<I',body)):
            physical=word&0x1fffffff
            if 0x1f801000<=physical<0x1f802000:
                hardware_literals.append({'address':HX(h['load']+offset*4),'value':HX(word),
                                          'physical':HX(physical),'confidence':'HYPOTHESIS',
                                          'notes':'Aligned literal only; data pointer or coincidental instruction, not a proven access.'})
        summaries[name]={'sha256':hashlib.sha256(b).hexdigest(),'file_size':len(b),'header':{k:HX(v) for k,v in h.items()},
                         'header_caveat':'PS-X EXE load span is not a recovered .text section; data/bss fields are zero.',
                         'crt':{'bss_start':HX(bss_lo),'bss_end_exclusive':HX(bss_hi),'gp':HX(crt_gp),
                                'stack_top_word':HX(stack_word),'stack_top_value':HX(u32(stack_word)),
                                'initial_crt_sp':HX(0x80000000|(u32(stack_word)-8)),
                                'stack_reserve_word':HX(reserve_word),'stack_reserve_value':HX(u32(reserve_word)),
                                'heap_base_arg':HX(bss_hi+4),'heap_size_arg':HX(u32(stack_word)-8-u32(reserve_word)-(bss_hi&0x1fffffff)),
                                'evidence_pc':HX(pc),'confidence':'CONFIRMED'},
                         'psx_stats':analysis['stats'],'ps1_stats':ps1['stats'],
                         'psyq_exact':sum(p['image']==name and p['confidence']=='CONFIRMED' for p in psyq),
                         'psyq_masked':sum(p['image']==name and p['confidence']=='LIKELY' for p in psyq),
                         'bios_thunks':[{'address':HX(f['addr']),'name':f['bios_call']} for f in maprows if f['bios_call']],
                         'gte_function_candidates':sum(f['sig']['gte'] for f in maprows),
                         'mmio_refs':dict(mmio),'hardware_pointer_literals':hardware_literals,'possible_code_writes':code_writes,
                         'self_modifying_status':'UNKNOWN: direct static write candidates need traces; DMA/indirect stores are not excluded.'}
        # Keep instruction bodies only in ignored disasm/generated outputs.
        def metadata_only(value):
            if isinstance(value,dict):return {k:metadata_only(v) for k,v in value.items() if k!='context'}
            if isinstance(value,list):return [metadata_only(v) for v in value]
            return value
        indirect.append({'image':name,'analysis':metadata_only(ind)})
    write_db('functions',functions);write_db('globals',globals_);write_db('psyq',psyq)
    (ROOT/'symbols/indirect.json').write_text(json.dumps(indirect,indent=2),encoding='utf-8')
    manifest=json.loads((ROOT/'generated/assets/manifest.json').read_text())
    ext=Counter(Path(e['name']).suffix.lower() for e in manifest['mix_entries'])
    embedded=[]
    for entry in manifest['mix_entries']:
        b=(ROOT/'generated/assets'/entry['local_path']).read_bytes()
        if b'PS-X EXE' in b:embedded.append({'file':entry['name'],'offset':b.find(b'PS-X EXE')})
    report={'source_sha256':manifest['source_sha256'],'images':summaries,
            'mix_extensions':dict(ext),'mix_psx_exe_headers':embedded,
            'overlay_conclusion':'CONFIRMED: boot selects D2KF.EXE/DUNE.EXE, same load 0x80019000. Absence of headerless executable code in MIX is NOT proven.',
            'loader_evidence':{'selector':'0x80016270','filename_table':'0x80016274','cd_read_exec_call':'0x800100FC','bios_exec_call':'0x80010118'},
            'limitations':['Static function counts are candidates, not a decompilation proof.','SDK version UNKNOWN; multiple SDK releases share signatures.',
                           'No DuckStation reference trace has been captured in this pass.','Timing/audio/gameplay parity requires runtime checkpoints.']}
    (ROOT/'research/executable_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'functions':len(functions),'globals':len(globals_),'psyq':len(psyq),'images':{
        n:{'psx':s['psx_stats']['total_functions'],'psyq_exact':s['psyq_exact'],'psyq_masked':s['psyq_masked'],'crt':s['crt']} for n,s in summaries.items()}},indent=2))

if __name__=='__main__':main()
