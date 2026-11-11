# Extracted from: 2025/Build agentic platform.md
# Preserved as a research reference; requires the source project's package layout.

import os
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Task, Base
from .agent_executor import AgentExecutor

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentic.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

def run_task_job(task_id: str):
    db = SessionLocal()
    t = db.query(Task).get(task_id)
    if not t:
        return
    try:
        t.status = "running"
        t.started_at = datetime.utcnow()
        db.commit()

        allowed_tools = json.loads(t.allowed_tools or "[]")
        executor = AgentExecutor(
            task_id=t.id,
            prompt=t.prompt,
            max_steps=t.max_steps,
            allowed_tools=allowed_tools
        )
        result, logs = executor.run()

        t.result = result
        t.logs = logs
        t.status = "completed"
    except Exception as e:
        t.status = "failed"
        t.logs = (t.logs or "") + f"\nException: {str(e)}"
    finally:
        t.finished_at = datetime.utcnow()
        db.commit()
