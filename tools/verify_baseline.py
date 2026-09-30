"""Verify provenance and completeness of local baseline outputs, without running the game."""
import json
from pathlib import Path
import subprocess
import tomllib
from dune_import import EXPECTED_SHA256, sha256

ROOT=Path(__file__).resolve().parents[1]

def main():
    asset=ROOT/'generated/assets'
    manifest=json.loads((asset/'manifest.json').read_text())
    assert manifest['source_sha256']==EXPECTED_SHA256
    assert sha256(Path(manifest['source_path']))==EXPECTED_SHA256, 'Original image changed'
    assert sha256(asset/'disc.bin')==EXPECTED_SHA256, 'Runtime disc changed'
    for row in manifest['files']+manifest['mix_entries']:
        assert sha256(asset/row['local_path'])==row['sha256'], row['local_path']
    audit=json.loads((ROOT/'generated/native/overlays/AOT_STATIC_AUDIT.json').read_text())
    assert audit['all_guards_match_known_input_bytes'] and audit['all_pairs_valid']
    # Inventory profile_sha256 hashes normalized JSON; generation_inputs stores
    # the actual on-disk profile digest used for stale-output checking.
    assert audit['generation_inputs']['profile_sha256']==sha256(ROOT/'aot/overlays.json'), 'Stale AOT profile'
    assert audit['original_disc_sha256']==EXPECTED_SHA256
    for name,digest in audit['files'].items():
        assert sha256(ROOT/'generated/native/overlays'/name)==digest, name
    assert audit['recipe_count']==2
    cfg=tomllib.loads((ROOT/'game.toml').read_text())
    assert cfg['game']['entry_pc']=='0x80010168'
    assert cfg['runtime']['idle_skip'] is False
    assert cfg['recompiler']['discovery']=='reachable'
    locks=json.loads((ROOT/'dependencies.lock.json').read_text())
    for repo in ('ps1-recomp','psxrecomp'):
        actual=subprocess.check_output(['git','-C',str(ROOT/'third_party'/repo),'rev-parse','HEAD'],text=True).strip()
        assert actual==locks[repo]['commit'], repo
    for name in ('generated/assets/disc.bin','generated/assets/iso/DUNE.EXE','generated/native/boot/SLUS_009.73_dispatch.c',
                 'generated/native/overlays/overlays_static.c','disasm/DUNE.EXE.txt','game.toml'):
        subprocess.run(['git','check-ignore','-q','--',name],cwd=ROOT,check=True)
    indirect=(ROOT/'symbols/indirect.json').read_text()
    assert '"context"' not in indirect, 'Raw instruction contexts must stay ignored'
    summary=dict(status='PASS',source_sha256=EXPECTED_SHA256,iso_files=len(manifest['files']),
                 mix_assets=len(manifest['mix_entries']),xa_records=len(manifest['xa_entries']),
                 static_variants=audit['published_variants'],all_known_guards_verified=True,
                 full_static_coverage_proven=audit['full_static_coverage_proven'],
                 duckstation_parity_validated=False)
    (ROOT/'research/validation.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
