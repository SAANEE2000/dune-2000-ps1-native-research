"""Import the specifically authorized SLUS-00973 Vector disc; never modifies it.

Standard library only. Form-2 XA sectors are preserved whole, not truncated to
2048-byte ISO payloads. Copyrighted outputs belong in ignored generated/.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import struct
from pathlib import Path

EXPECTED_SHA256 = '94e0800ef92cfe9de3bd44cdbd8e0a85d878bded0fcfbde0cf373b8e34eac711'
RAW = 2352
USER = 2048

def sha256(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def resolve_image(path):
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() == '.cue':
        cue = path.read_text(encoding='utf-8-sig')
        files = re.findall(r'^\s*FILE\s+"([^"]+)"\s+BINARY\s*$', cue, re.M | re.I)
        tracks = re.findall(r'^\s*TRACK\s+(\d+)\s+(\S+)\s*$', cue, re.M | re.I)
        if len(files) != 1 or tracks != [('01', 'MODE2/2352')]:
            raise ValueError('Only this baseline single-track MODE2/2352 CUE is supported')
        if not re.search(r'INDEX\s+01\s+00:00:00', cue, re.I):
            raise ValueError('Unsupported INDEX offset')
        return (path.parent / files[0]).resolve(strict=True), path
    if path.suffix.lower() != '.bin':
        raise ValueError('Expected BIN or CUE')
    return path, None

def extent(f, lba, size):
    out = bytearray()
    for i in range((size + USER - 1) // USER):
        f.seek((lba + i) * RAW)
        sec = f.read(RAW)
        if len(sec) != RAW or sec[:12] != b'\0' + b'\xff'*10 + b'\0' or sec[15] != 2:
            raise ValueError(f'Bad Mode2 sector at LBA {lba+i}')
        if sec[18] & 0x20:
            raise ValueError(f'Form2 sector at LBA {lba+i}: use raw extraction')
        out.extend(sec[24:2072])
    return bytes(out[:size])

def record(b, off):
    n = b[off]
    if n < 34 or off+n > len(b):
        raise ValueError('Malformed ISO directory record')
    r = b[off:off+n]
    if struct.unpack_from('<I', r, 2)[0] != struct.unpack_from('>I', r, 6)[0]:
        raise ValueError('ISO LBA endian mismatch')
    name = r[33:33+r[32]].decode('ascii')
    return dict(name=name, lba=struct.unpack_from('<I',r,2)[0],
                size=struct.unpack_from('<I',r,10)[0], directory=bool(r[25]&2), length=n)

def inventory(f):
    pvd=extent(f,16,2048)
    if pvd[:7] != b'\x01CD001\x01':
        raise ValueError('Missing ISO9660 PVD')
    rows=[]
    def walk(rec,prefix='',seen=None):
        seen=set() if seen is None else seen
        if rec['lba'] in seen: return
        seen.add(rec['lba'])
        data=extent(f,rec['lba'],rec['size'])
        off=0
        while off<len(data):
            if not data[off]:
                off=(off//2048+1)*2048
                continue
            r=record(data,off); off+=r.pop('length')
            if r['name'] in ('\0','\1'): continue
            name=r['name'].split(';')[0]
            if name in ('.','..') or '/' in name or '\\' in name or ':' in name:
                raise ValueError('Unsafe ISO filename')
            r['path']=prefix+name
            rows.append(r)
            if r['directory']: walk(r,r['path']+'/',seen)
    walk(record(pvd,156))
    return pvd[40:72].decode('ascii').strip(),rows

def import_disc(source, output):
    image,cue=resolve_image(source)
    digest=sha256(image)
    if digest != EXPECTED_SHA256:
        raise ValueError(f'Baseline image SHA256 mismatch: {digest}')
    output=Path(output).resolve()
    # Validate identity before writing any assets.
    with image.open('rb') as f:
        volume,rows=inventory(f)
        byname={r['path']:r for r in rows}
        cnf=extent(f,byname['SYSTEM.CNF']['lba'],byname['SYSTEM.CNF']['size'])
        if volume!='SLUS_00973' or b'SLUS_009.73' not in cnf:
            raise ValueError('Expected SLUS-00973 identity')
        output.mkdir(parents=True,exist_ok=True)
        manifest=dict(source_sha256=digest, source_path=str(image), cue_path=str(cue) if cue else None,
                      serial='SLUS-00973',volume=volume,files=[],mix_entries=[],xa_entries=[])
        for row in rows:
            if row['directory']: continue
            dest=output/'iso'/row['path']
            dest.parent.mkdir(parents=True,exist_ok=True)
            f.seek(row['lba']*RAW)
            first=f.read(RAW)
            is_xa=row['path']=='DATA.XA' or bool(first[18]&0x20)
            if is_xa:
                # ISO length describes 2048-byte logical sectors; XA content needs
                # subheaders and full 2324-byte Form2 payload. Preserve raw bytes.
                dest=dest.with_suffix(dest.suffix+'.raw')
                n=(row['size']+2047)//2048
                f.seek(row['lba']*RAW)
                remaining=n*RAW
                with dest.open('wb') as out:
                    while remaining:
                        b=f.read(min(remaining,4*1024*1024))
                        if not b: raise ValueError('Truncated XA extent')
                        out.write(b); remaining-=len(b)
                representation='raw2352'
            else:
                dest.write_bytes(extent(f,row['lba'],row['size']))
                representation='form1_user2048'
            manifest['files'].append({**row,'local_path':dest.relative_to(output).as_posix(),
                                      'representation':representation,'sha256':sha256(dest)})
        fat=(output/'iso/DATA.FAT').read_bytes()
        mix_count,xa_count=struct.unpack_from('<II',fat)
        if len(fat)!=8+28*(mix_count+xa_count): raise ValueError('Unexpected DATA.FAT length')
        for i in range(mix_count+xa_count):
            row=fat[8+28*i:8+28*(i+1)]
            name=row[:16].split(b'\0')[0].decode('ascii')
            if Path(name).name!=name or any(c in name for c in '/\\:') or name in ('.','..'):
                raise ValueError('Unsafe FAT filename')
            sector,size,flags=struct.unpack_from('<III',row,16)
            entry=dict(name=name,sector=sector,size=size,flags=flags)
            if i<mix_count:
                dest=output/'mix'/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(extent(f,byname['DATA.MIX']['lba']+sector,size))
                entry.update(local_path=dest.relative_to(output).as_posix(),sha256=sha256(dest))
                manifest['mix_entries'].append(entry)
            else: manifest['xa_entries'].append(entry)
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        # An ASCII local alias avoids legacy runtime fopen limitations with
        # non-ASCII source directories. A hardlink costs no second disc copy.
        # It MUST only be used read-only; writing it would change the source.
        alias=output/'disc.bin'
        if not alias.exists():
            os.link(image,alias)
        if not os.path.samefile(alias,image):
            raise ValueError('Existing disc alias does not refer to validated source')
        (output/'disc.cue').write_text('FILE "disc.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n',encoding='ascii')
        print(json.dumps({'serial':manifest['serial'],'sha256':digest,'iso_files':len(rows),
                          'mix_files':mix_count,'xa_entries':xa_count,'output':str(output)},indent=2))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'generated/assets')
    a=p.parse_args()
    try: import_disc(a.source,a.output)
    except (ValueError,OSError) as e: p.exit(1,f'Import rejected: {e}\n')
