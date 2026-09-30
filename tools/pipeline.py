"""Reproduce the native research build from pinned tools and the user's disc."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV = os.environ.copy()
ENV['PATH'] = str(ROOT/'third_party/toolchain/bin') + os.pathsep + ENV['PATH']
ENV['PS1RECOMP_DATA_DIR'] = str(ROOT/'third_party/ps1-recomp/ps1Analyzer/data')
CM = ROOT/'.venv/Scripts/cmake.exe'
PY = ROOT/'.venv/Scripts/python.exe'

def run(args, label, cwd=ROOT):
    log=ROOT/'research/logs'/f'{label}.log';log.parent.mkdir(parents=True,exist_ok=True)
    print(f'{label}: running (log: {log.relative_to(ROOT)})',flush=True)
    with log.open('wb') as f:
        result=subprocess.run([str(a) for a in args],cwd=cwd,env=ENV,stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text(errors='replace')[-6000:])
        raise SystemExit(f'{label} failed with exit {result.returncode}')

def configure(source, build, extra=()):
    run([CM,'-S',ROOT/source,'-B',ROOT/build,'-G','Ninja',
         '-DCMAKE_C_COMPILER=clang.exe','-DCMAKE_CXX_COMPILER=clang++.exe',
         '-DCMAKE_POLICY_VERSION_MINIMUM=3.5','-DBUILD_TESTING=OFF',*extra],
        'configure-'+Path(build).name)

def tools():
    configure('tools/cmake_ps1recomp','build/ps1-tools',['-DCMAKE_BUILD_TYPE=Release'])
    run([CM,'--build',ROOT/'build/ps1-tools','-j','4'],'build-ps1-tools')
    configure('third_party/psxrecomp/recompiler','build/psx-tools',
              ['-DCMAKE_BUILD_TYPE=Release','-DPSXRECOMP_ENABLE_CHD=OFF'])
    run([CM,'--build',ROOT/'build/psx-tools','--target','psxrecomp-game','psxrecomp-analyze','psxrecomp-bios','-j','4'],'build-psx-tools')

def config():
    # Immutable original entry and load span; no patch table or new gameplay.
    manifest=json.loads((ROOT/'generated/assets/manifest.json').read_text())
    from dune_import import EXPECTED_SHA256
    if manifest['source_sha256']!=EXPECTED_SHA256:raise SystemExit('Import the exact original disc first')
    template=(ROOT/'runtime/game.template.toml').read_text()
    (ROOT/'game.toml').write_text(template,encoding='utf-8')

def analyze():
    for name in ('SLUS_009.73','D2KF.EXE','DUNE.EXE'):
        exe=ROOT/'generated/assets/iso'/name
        out=ROOT/'generated/ps1'/f'{name}.toml';out.parent.mkdir(parents=True,exist_ok=True)
        (ROOT/'disasm').mkdir(exist_ok=True)
        run([ROOT/'build/ps1-tools/analyzer/ps1Analyzer.exe',exe,out],'ps1-'+name)
        run([ROOT/'build/psx-tools/psxrecomp-analyze.exe',exe,'--out',ROOT/f'generated/psx/{name}-analysis',
             '--disasm',ROOT/'disasm'/f'{name}.txt'],'psx-'+name)
    run([PY,ROOT/'tools/audit_executables.py'],'audit-executables')
    run([ROOT/'build/ps1-tools/recompiler/ps1Recomp.exe',ROOT/'generated/ps1/DUNE.EXE.toml',
         ROOT/'generated/ps1/DUNE.cpp'],'ps1-codegen-DUNE')

def generate():
    config()
    framework=ROOT/'third_party/psxrecomp'
    run([ROOT/'build/psx-tools/psxrecomp-bios.exe','--config','bios/OpenBIOS.toml'],'openbios-codegen',framework)
    run([ROOT/'build/psx-tools/psxrecomp-game.exe','--config',ROOT/'game.toml','--project-root',framework],'psx-native-boot')
    run([PY,ROOT/'tools/seed_static_transfers.py'],'static-transfer-seeds')
    run([PY,ROOT/'tools/build_aot.py'],'aot-static')

def build(release=False,strict=False,pc_input=False):
    # Release is always fail-closed. A playable hybrid is explicitly research.
    strict=strict or release
    target='build/strict' if strict else 'build/pc' if pc_input else 'build/native'
    configure('.',target,[f'-DCMAKE_BUILD_TYPE={"Release" if release else "RelWithDebInfo"}',
                          f'-DPSX_DEBUG_TOOLS={"OFF" if release else "ON"}',
                          '-DPSX_RECOMP_UI=OFF','-DPSX_NETPLAY=OFF','-DPSX_REWIND=OFF',
                          '-DPSX_STATIC_RUNTIME=ON','-DPSX_ENABLE_VULKAN=OFF',
                          f'-DDUNE_STRICT_AOT={"ON" if strict else "OFF"}',
                          f'-DDUNE_PC_INPUT={"ON" if pc_input else "OFF"}',
                          f'-DPSX_PYTHON={PY.as_posix()}',
                          f'-DSDL3_DIR={(ROOT/"third_party/toolchain/deps/lib/cmake/SDL3").as_posix()}',
                          f'-DZLIB_ROOT={(ROOT/"third_party/toolchain/deps").as_posix()}'])
    run([CM,'--build',ROOT/target,'-j','4'],'build-'+Path(target).name)
    print(ROOT/target/'Dune2000Native.exe')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('step',choices=['tools','config','analyze','generate','build','all'])
    p.add_argument('--release',action='store_true')
    p.add_argument('--strict',action='store_true')
    p.add_argument('--pc-input',action='store_true')
    a=p.parse_args()
    if a.step=='all':tools();analyze();generate();build(a.release,a.strict,a.pc_input)
    elif a.step=='build':build(a.release,a.strict,a.pc_input)
    else:globals()[a.step]()
