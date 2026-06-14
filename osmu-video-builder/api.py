#!/usr/bin/env python3
"""
api.py — (선택) HTTP로 파이프라인을 호출하는 얇은 래퍼.
n8n의 'HTTP Request' 노드로 부르고 싶을 때 사용. Execute Command 방식이면 불필요.

실행:  pip install fastapi uvicorn
       uvicorn api:app --host 127.0.0.1 --port 8000
호출:  POST http://127.0.0.1:8000/prep    {"config":"examples/tulip_full_config.json","era":"17c"}
       POST http://127.0.0.1:8000/build   {"config":"examples/tulip_full_config.json","era":"17c"}
"""
import os
import subprocess

from fastapi import FastAPI
from pydantic import BaseModel

HERE = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title="OSMU Video Builder API")


class Job(BaseModel):
    config: str = "examples/tulip_full_config.json"
    era: str = "17c"


def _run(cfg, era, build):
    cfg_path = cfg if os.path.isabs(cfg) else os.path.join(HERE, cfg)
    cmd = ["python3", os.path.join(HERE, "auto.py"), cfg_path,
           "--era", era, "--yes"] + (["--build"] if build else [])
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    return {"ok": p.returncode == 0, "returncode": p.returncode,
            "stdout": p.stdout[-4000:], "stderr": p.stderr[-1500:]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/prep")
def prep(job: Job):
    return _run(job.config, job.era, build=False)


@app.post("/build")
def build(job: Job):
    return _run(job.config, job.era, build=True)
