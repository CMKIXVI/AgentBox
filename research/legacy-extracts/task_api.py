# Extracted from: 2025/Build agentic platform.md
# Preserved as a research reference; requires the source project's package layout.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import os
from redis import Redis
from rq import Queue
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Task

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentic.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

redis = Redis(host=os.getenv("REDIS_HOST", "redis"))
q = Queue("agent", connection=redis)

from .worker import run_task_job

class CreateTask(BaseModel):
    prompt: str
    max_steps: int = 5
    allowed_tools: list[str] | None = None

app = FastAPI()

@app.post("/tasks")
def create_task(body: CreateTask):
    db = SessionLocal()
    t = Task(
        prompt=body.prompt,
        max_steps=body.max_steps,
        allowed_tools=json.dumps(body.allowed_tools or [])
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    q.enqueue("app.worker.run_task_job", t.id)
    return {"id": t.id, "status": t.status}

@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    db = SessionLocal()
    t = db.query(Task).get(task_id)
    if not t:
        raise HTTPException(404, "task not found")
    return {
        "id": t.id,
        "prompt": t.prompt,
        "status": t.status,
        "result": t.result,
        "logs": t.logs
    }
