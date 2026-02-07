"""
FastAPI backend for the email support session system.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import init_db
from email_session import EmailSession

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(
    title="Lookfor Email Support API",
    description="Multi-agent email support with continuous memory and escalation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}

class SessionStartRequest(BaseModel):
    customer_email: str
    first_name: str
    last_name: str
    shopify_customer_id: str

class SessionStartResponse(BaseModel):
    session_id: int
    customer_email: str
    first_name: str
    last_name: str
    shopify_customer_id: str

class ReplyRequest(BaseModel):
    message: str

class ReplyResponse(BaseModel):
    session_id: int
    escalated: bool
    final_message: Optional[str]
    tool_calls: list[dict]
    actions_taken: list[str]

class SessionResponse(BaseModel):
    session_id: int
    customer_email: str
    first_name: str
    last_name: str
    shopify_customer_id: str
    escalated: bool

class TraceResponse(BaseModel):
    session_id: int
    customer_email: str
    escalated: bool
    messages: list[dict]
    tool_calls: list[dict]

@app.post("/sessions", response_model=SessionStartResponse)
def start_session(req: SessionStartRequest):
    """Start a new email support session."""
    session = EmailSession.start(
        customer_email=req.customer_email,
        first_name=req.first_name,
        last_name=req.last_name,
        shopify_customer_id=req.shopify_customer_id,
    )
    return SessionStartResponse(
        session_id=session.session_id,
        customer_email=session.customer_email,
        first_name=session.first_name,
        last_name=session.last_name,
        shopify_customer_id=session.shopify_customer_id,
    )

@app.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: int):
    """Get session info."""
    session = EmailSession.load(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    row = session.get_trace()
    return SessionResponse(
        session_id=session.session_id,
        customer_email=session.customer_email,
        first_name=session.first_name,
        last_name=session.last_name,
        shopify_customer_id=session.shopify_customer_id,
        escalated=row.get("escalated", False),
    )

@app.post("/sessions/{session_id}/reply", response_model=ReplyResponse)
def reply(session_id: int, req: ReplyRequest):
    """
    Send a customer message and get the agent's reply.
    Returns null final_message when session is escalated (no automatic reply).
    """
    session = EmailSession.load(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    trace = session.reply(req.message)

    return ReplyResponse(
        session_id=session_id,
        escalated=session.get_trace().get("escalated", False),
        final_message=trace.final_message if trace else None,
        tool_calls=trace.tool_calls if trace else [],
        actions_taken=trace.actions_taken if trace else [],
    )

@app.get("/sessions/{session_id}/trace", response_model=TraceResponse)
def get_trace(session_id: int):
    """Get full session trace: messages, tool calls, escalation status."""
    session = EmailSession.load(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    t = session.get_trace()
    return TraceResponse(
        session_id=t["session_id"],
        customer_email=t["customer_email"],
        escalated=t["escalated"],
        messages=t["messages"],
        tool_calls=t["tool_calls"],
    )
