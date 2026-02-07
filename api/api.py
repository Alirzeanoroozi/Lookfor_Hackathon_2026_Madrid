from __future__ import annotations
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from db import init_db, list_sessions
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
    session_id: str
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


class ConversationSummary(BaseModel):
    session_id: int
    customer_email: str
    first_name: str
    last_name: str
    shopify_customer_id: str
    escalated: bool
    created_at: str
    
class UpdateProfileRequest(BaseModel):
    model: str
    prompt: str

class UpdateProfileResponse(BaseModel):
    success: bool

@app.get("/conversations", response_model=list[ConversationSummary])
def get_all_conversations(limit: int = 100):
    """Get all conversations (sessions), newest first."""
    init_db()
    rows = list_sessions(limit=limit)
    return [
        ConversationSummary(
            session_id=r["id"],
            customer_email=r["customer_email"],
            first_name=r["first_name"],
            last_name=r["last_name"],
            shopify_customer_id=r["shopify_customer_id"],
            escalated=bool(r.get("escalated")),
            created_at=r.get("created_at", "") or "",
        )
        for r in rows
    ]

@app.post("/conversations/{session_id}", response_model=ReplyResponse)
def reply(session_id: str, req: ReplyRequest):
    """
    Send a customer message and get the agent's reply.
    Returns null final_message when session is escalated (no automatic reply).
    """
    session = EmailSession.load(session_id)
    if not session:
        session = EmailSession.start(
            customer_email="",
            first_name="",
            last_name="",
            shopify_customer_id=session_id,
            model="",
            prompt="",
        )

    trace = session.reply(req.message)

    return ReplyResponse(
        session_id=session_id,
        escalated=session.get_trace().get("escalated", False),
        final_message=trace.final_message if trace else None,
        tool_calls=trace.tool_calls if trace else [],
        actions_taken=trace.actions_taken if trace else [],
    )

@app.get("/conversations/{session_id}", response_model=TraceResponse)
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

def update_profile(session_id: int, req: UpdateProfileRequest):
    session = EmailSession.load(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.update_profile(req.model, req.prompt)
    return UpdateProfileResponse(
        success=True,
    )