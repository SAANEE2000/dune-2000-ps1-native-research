"""Bounded local diagnostic runner and one-request TCP client for the research build."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]

def request(command,port=4392,**args):
    with socket.create_connection(('127.0.0.1',port),timeout=15) as s:
        s.settimeout(15)
        s.sendall((json.dumps({'cmd':command,**args})+'\n').encode())
        data=bytearray()
        while not data.endswith(b'\n'):
            part=s.recv(1024*1024)
            if not part:raise ConnectionError('Diagnostic connection closed')
            data.extend(part)
            if len(data)>24*1024*1024:raise ValueError('Oversized diagnostic response')
        return json.loads(data)

def launch(label,seconds=600,port=4392,build='native',strict=False):
    out=ROOT/'generated/probes'/label;out.mkdir(parents=True,exist_ok=False)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',port))
    env=os.environ.copy();env['PATH']=str(ROOT/'third_party/toolchain/bin')+os.pathsep+env['PATH']
    cmd=[str(ROOT/'build'/build/'Dune2000Native.exe'),'--headless','--game',str(ROOT/'game.toml'),
         '--disc',str(ROOT/'generated/assets/disc.cue'),'--memcard-dir',str(out/'memcards'),
         '--renderer','software','--debug-port',str(port)]
    with (out/'runtime.log').open('wb') as log:
        p=subprocess.Popen(cmd,cwd=ROOT/'build'/build,env=env,stdout=log,stderr=subprocess.STDOUT,
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        print(json.dumps({'pid':p.pid,'port':port,'output':str(out)}),flush=True)
        try:p.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            p.terminate();p.wait(timeout=10)
        finally:
            if p.poll() is None:p.terminate();p.wait(timeout=10)
        print(json.dumps({'exit_code':p.returncode}),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--port',type=int,default=4392)
    a.add_argument('--launch');a.add_argument('--seconds',type=int,default=600)
    a.add_argument('--build',default='native');a.add_argument('--command')
    a.add_argument('--output',type=Path);v=a.parse_args()
    if v.launch:launch(v.launch,v.seconds,v.port,v.build)
    elif v.command:
        req=json.loads(v.command);res=request(req.pop('cmd'),v.port,**req)
        if v.output:
            v.output.parent.mkdir(parents=True,exist_ok=True)
            if 'hex' in res:v.output.write_bytes(bytes.fromhex(res['hex']));print({'saved':str(v.output),'bytes':res['len']})
            else:v.output.write_text(json.dumps(res,indent=2));print({'saved':str(v.output),'ok':res.get('ok')})
        else:print(json.dumps(res,indent=2)[:12000])
