from __future__ import annotations
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

from app.environment import EmailTriageEnv
from app.models import EmailAction
from app.tasks import TASKS

app = FastAPI(title="Email Triage Environment", version="1.0.0")

sessions: dict[str, EmailTriageEnv] = {}


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/tasks")
def list_tasks():
    return {"tasks": list(TASKS.values())}


@app.post("/reset")
def reset(task_id: str = Query("task_1"), session_id: str | None = Query(None)):
    active_session_id = session_id or str(uuid4())
    env = EmailTriageEnv(task_id)
    observation = env.reset()
    sessions[active_session_id] = env
    return {
        "session_id": active_session_id,
        "observation": observation.model_dump(mode="json"),
    }


@app.post("/step")
def step(action: EmailAction, session_id: str = Query(...)):
    env = sessions.get(session_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Session not found")

    observation, reward, done, info = env.step(action)
    return {
        "observation": observation.model_dump(mode="json"),
        "reward": reward.model_dump(mode="json"),
        "done": done,
        "info": info,
    }


@app.get("/state")
def state(session_id: str = Query(...)):
    env = sessions.get(session_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return env.state()


@app.get("/validate")
def validate():
    project_root = Path(__file__).resolve().parent.parent
    manifest_exists = (project_root / "openenv.yaml").exists()
    task_checks = {}

    for task_id in TASKS:
        try:
            env = EmailTriageEnv(task_id)
            observation = env.reset()
            task_checks[task_id] = {
                "loadable": True,
                "inbox_size": observation.inbox_size,
            }
        except Exception as exc:
            task_checks[task_id] = {
                "loadable": False,
                "error": str(exc),
            }

    passed = manifest_exists and all(result["loadable"] for result in task_checks.values())
    return {
        "status": "pass" if passed else "fail",
        "openenv_yaml_exists": manifest_exists,
        "task_checks": task_checks,
    }
