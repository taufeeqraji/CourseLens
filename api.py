"""
FastAPI backend for the Course Insight Agent.

Run locally:
    uvicorn api:app --reload
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent_factory import create_root_agent
from root_agent import RootAgent


logger = logging.getLogger("course_insight_api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

DEFAULT_FRONTEND_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
SESSION_TTL_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "120"))
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "50"))


def get_allowed_origins() -> List[str]:
    raw_origins = os.getenv("FRONTEND_ORIGINS", DEFAULT_FRONTEND_ORIGINS)
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app = FastAPI(
    title="Course Insight Agent API",
    version="0.2.0",
    description="HTTP API for the Course Insight multi-agent system.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class AgentSession:
    root: RootAgent
    lock: Lock
    created_at: datetime
    last_seen: datetime


_sessions: Dict[str, AgentSession] = {}
_sessions_lock = Lock()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = Field(default=None, max_length=80)


class ChatResponse(BaseModel):
    session_id: str
    response: str
    agent: Optional[str] = None
    reasoning: Optional[str] = None
    stats: Dict


class AgentInfo(BaseModel):
    name: str
    description: str
    calls: int


class AgentsResponse(BaseModel):
    session_id: str
    agents: List[AgentInfo]


class StatsResponse(BaseModel):
    session_id: str
    stats: Dict


class ClearRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, max_length=80)


class ClearResponse(BaseModel):
    session_id: str
    message: str
    stats: Dict


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def evict_expired_sessions(now: datetime) -> None:
    expiry = now - timedelta(minutes=SESSION_TTL_MINUTES)
    expired_ids = [
        session_id
        for session_id, session in _sessions.items()
        if session.last_seen < expiry
    ]

    for session_id in expired_ids:
        logger.info("Evicting expired session %s", session_id)
        del _sessions[session_id]

    if len(_sessions) <= MAX_SESSIONS:
        return

    oldest_ids = sorted(_sessions, key=lambda item: _sessions[item].last_seen)
    for session_id in oldest_ids[: len(_sessions) - MAX_SESSIONS]:
        logger.info("Evicting oldest session %s", session_id)
        del _sessions[session_id]


def create_session(now: datetime) -> tuple[str, AgentSession]:
    try:
        root = create_root_agent()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to initialize agent system")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize agent system: {exc}",
        ) from exc

    session_id = uuid4().hex
    session = AgentSession(root=root, lock=Lock(), created_at=now, last_seen=now)
    _sessions[session_id] = session
    logger.info("Created session %s", session_id)
    return session_id, session


def get_agent_session(session_id: Optional[str] = None) -> tuple[str, AgentSession]:
    now = utc_now()

    with _sessions_lock:
        evict_expired_sessions(now)

        if session_id and session_id in _sessions:
            session = _sessions[session_id]
            session.last_seen = now
            return session_id, session

        return create_session(now)


def build_agents_response(session_id: str, root: RootAgent) -> AgentsResponse:
    return AgentsResponse(
        session_id=session_id,
        agents=[
            AgentInfo(
                name=name,
                description=info["description"],
                calls=info["calls"],
            )
            for name, info in root.sub_agents.items()
        ],
    )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "name": "Course Insight Agent API",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")

    session_id, session = get_agent_session(payload.session_id)

    with session.lock:
        logger.info("Handling chat request session=%s chars=%d", session_id, len(message))
        result = session.root.execute_detailed(message)
        stats = session.root.get_stats()

    return ChatResponse(
        session_id=session_id,
        response=result["response"],
        agent=result.get("agent"),
        reasoning=result.get("reasoning"),
        stats=stats,
    )


@app.get("/agents", response_model=AgentsResponse)
def agents(session_id: Optional[str] = Query(default=None, max_length=80)) -> AgentsResponse:
    session_id, session = get_agent_session(session_id)
    return build_agents_response(session_id, session.root)


@app.get("/stats", response_model=StatsResponse)
def stats(session_id: Optional[str] = Query(default=None, max_length=80)) -> StatsResponse:
    session_id, session = get_agent_session(session_id)
    return StatsResponse(session_id=session_id, stats=session.root.get_stats())


@app.post("/clear", response_model=ClearResponse)
def clear(payload: ClearRequest) -> ClearResponse:
    session_id, session = get_agent_session(payload.session_id)

    with session.lock:
        session.root.clear_history()
        session.root.clear_cache()
        stats = session.root.get_stats()

    return ClearResponse(
        session_id=session_id,
        message="Conversation history and course cache cleared.",
        stats=stats,
    )
