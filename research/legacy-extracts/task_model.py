# Extracted from: 2025/Build agentic platform.md
# Preserved as a research reference; not production-ready.

import uuid
from sqlalchemy import (
    Column, String, Text, DateTime, Integer
)
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def gen_uuid():
    return str(uuid.uuid4())

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, default=gen_uuid)
    prompt = Column(Text, nullable=False)
    status = Column(String, default="queued")  # queued, running, completed, failed
    result = Column(Text)
    logs = Column(Text)
    max_steps = Column(Integer, default=5)
    allowed_tools = Column(Text)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
