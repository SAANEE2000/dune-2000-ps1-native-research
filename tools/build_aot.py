"""Framework AOT pipeline with explicit nested-checkout profile resolution.

Upstream CLI assumes its checkout is immediately below the title root. We use
the same extraction/audit/publish primitives, passing the real framework root
to codegen. No failed audit can publish output.
"""
import json
from pathlib import Path
import sys
import tempfile
import tomllib

ROOT=Path(__file__).resolve().parents[1]
FRAMEWORK=ROOT/'third_party/psxrecomp'
sys.path.insert(0,str(FRAMEWORK/'tools'))
import aot_overlay_pipeline as p

def main():
    config=ROOT/'game.toml';profile_path=ROOT/'aot/overlays.json'
    cfg=tomllib.loads(config.read_text(encoding='utf-8-sig'))
    profile=p.load_profile(profile_path,cfg)
    cue=p.game_disc(config,cfg);disc=p.Disc(cue)
    digests=p.check_disc(profile,disc,cue)
    tool=ROOT/'build/psx-tools/psxrecomp-game.exe'
    gcc=str(ROOT/'third_party/toolchain/bin/clang.exe')
    cmake=str(ROOT/'.venv/Scripts/cmake.exe')
    p.write_codegen_hash_header(cmake)
    parent=ROOT/'generated/aot-static';parent.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='disc-aot-',dir=parent))
    out=ROOT/'generated/native/overlays'
    inputs,input_hash=p.generation_inputs(profile_path,profile,config,tool,digests,gcc,True)
    inv=p.extract(profile_path,config,tool,work,cue=cue,disc=disc,profile=profile)
    print(f'Verified {len(inv["jobs"])} recipes; evidence {work}',flush=True)
    build=p.build_static(inv,config,tool,work,out,gcc,2,project_root=FRAMEWORK,cps=True)
    receipt=p.audit(config,tool,None,work/'runtime-input-inventory.json',work/'audit.json',build/p.STATIC_OUTPUT_NAME)
    for key in ('profile_sha256','original_disc_sha256','required_images','mod_packages'):receipt[key]=inv[key]
    receipt['generation_inputs']=inputs;receipt['generation_inputs_sha256']=input_hash
    receipt['explicit_codegen_project_root']='third_party/psxrecomp'
    p.publish_static(build,out,receipt)
    print(f'Published {receipt["published_variants"]} audited static variants in {len(receipt["files"])} files',flush=True)

if __name__=='__main__':main()
