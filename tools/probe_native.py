"""Bounded headless native diagnostic run. No emulator, no gameplay patches."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]

def request(sock, command, **args):
    sock.sendall((json.dumps({'cmd':command,**args})+'\n').encode())
    data=bytearray()
    while not data.endswith(b'\n'):
        part=sock.recv(65536)
        if not part: raise ConnectionError('Debugger closed connection')
        data.extend(part)
        if len(data)>16*1024*1024: raise ValueError('Unbounded debug response')
    return json.loads(data)

def probe(seconds, label):
    out=ROOT/'generated/probes'/label
    out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy()
    env['PATH']=str(ROOT/'third_party/toolchain/bin')+';'+env['PATH']
    args=[str(ROOT/'build/native/Dune2000Native.exe'),'--headless','--game',str(ROOT/'game.toml'),
          '--disc',str(ROOT/'generated/assets/disc.cue'),'--memcard-dir',str(out/'memcards'),
          '--debug-port','4378','--renderer','software']
    responses=[]
    with (out/'runtime.log').open('wb') as log:
        p=subprocess.Popen(args,cwd=ROOT/'build/native',env=env,stdout=log,stderr=subprocess.STDOUT,
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        print(f'Headless probe PID={p.pid}; {seconds}s; {out}',flush=True)
        start=time.monotonic()
        while p.poll() is None and time.monotonic()-start<seconds:
            time.sleep(min(0.25,seconds))
        if p.poll() is None:
            try:
                for cmd in ['ping','get_registers','frame','dispatch_stats','dirty_ram_stats','overlay_loader_status','video_info','fmv_state','cd_read_log']:
                    with socket.create_connection(('127.0.0.1',4378),timeout=4) as s:
                        s.settimeout(4)
                        responses.append({'command':cmd,'result':request(s,cmd)})
                with socket.create_connection(('127.0.0.1',4378),timeout=4) as s:
                    s.settimeout(4)
                    responses.append({'command':'screenshot_file','result':request(s,'screenshot_file',path=str(out/'frame.ppm'))})
                with socket.create_connection(('127.0.0.1',4378),timeout=4) as s:
                    s.settimeout(4)
                    responses.append({'command':'quit','result':request(s,'quit')})
            except Exception as e:
                responses.append({'diagnostic_error':str(e)})
            try:p.wait(timeout=4)
            except subprocess.TimeoutExpired:
                p.terminate();p.wait(timeout=4)
                responses.append({'forced_stop':True})
        result={'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start,'responses':responses}
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2)[:12000])
    print((out/'runtime.log').read_text(errors='replace')[-4500:])

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seconds',type=float,default=15)
    ap.add_argument('--label',default=time.strftime('%Y%m%d-%H%M%S'))
    a=ap.parse_args();probe(a.seconds,a.label)
