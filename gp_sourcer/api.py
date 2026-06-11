"""
FastAPI server — GP Sourcing Dashboard.

Run:  uvicorn gp_sourcer.api:app --reload --port 8000
"""

from __future__ import annotations

import json
import asyncio
import concurrent.futures
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .deal_feed import build_deal_feed
from .fundraise_cycle import forecast_market
from .lp_watch import WATCHED_LPS, get_lp_signals
from .talent_signals import get_talent_signals
from .placement_agents import WATCHED_AGENTS, get_offerings
from .pipeline import STAGES, get_pipeline, add_to_pipeline, move_stage
from .agent import GPSourcingAgent

app = FastAPI(title="GP Sourcing Dashboard", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_agent = GPSourcingAgent()
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

_UI = Path(__file__).parent / "ui" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(_UI.read_text())


# ── Deal Feed ──────────────────────────────────────────────────────────────

@app.get("/api/feed")
async def feed(
    strategy: Optional[str] = None,
    fit: Optional[str] = None,
    emerging_only: bool = False,
    include_outside: bool = False,
):
    return build_deal_feed(
        strategy=strategy or None,
        fit=fit or None,
        emerging_only=emerging_only,
        include_outside_mandate=include_outside,
        limit=100,
    )


# ── Re-Up Radar ────────────────────────────────────────────────────────────

@app.get("/api/reup")
async def reup(status: Optional[str] = None, strategy: Optional[str] = None):
    return forecast_market(status=status or None, strategy=strategy or None)


# ── LP Watch ───────────────────────────────────────────────────────────────

@app.get("/api/lp")
async def lp_watch():
    return {
        lp_id: {**meta, "signals": get_lp_signals(lp_id, limit=5)}
        for lp_id, meta in WATCHED_LPS.items()
    }


# ── Talent Signals ─────────────────────────────────────────────────────────

@app.get("/api/talent")
async def talent():
    return {"signals": get_talent_signals(limit=50)}


# ── Placement Agents ───────────────────────────────────────────────────────

@app.get("/api/agents")
async def agents():
    return {"watched": WATCHED_AGENTS, "offerings": get_offerings(limit=50)}


# ── Pipeline ───────────────────────────────────────────────────────────────

@app.get("/api/pipeline")
async def pipeline(stage: Optional[str] = None):
    return {"stages": STAGES, "board": get_pipeline(stage or None)}


class PipelineAdd(BaseModel):
    fund_name: str
    gp_name: str = ""
    strategy: str = ""
    size_usd: Optional[int] = None
    fund_number: Optional[int] = None
    source: str = "manual"
    stage: str = "radar"
    conviction: str = ""
    note: str = ""


class PipelineMove(BaseModel):
    fund_name: str
    stage: str
    note: str = ""


@app.post("/api/pipeline/add")
async def pipeline_add(body: PipelineAdd):
    return add_to_pipeline(**body.model_dump())


@app.post("/api/pipeline/move")
async def pipeline_move(body: PipelineMove):
    return move_stage(body.fund_name, body.stage, body.note)


# ── Agent Chat (SSE streaming) ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    reset: bool = False


@app.post("/api/chat")
async def chat(body: ChatRequest):
    if body.reset:
        _agent.reset()

    loop = asyncio.get_event_loop()

    def _run_generator():
        """Run the synchronous agent generator, collect chunks into a queue."""
        return list(_agent.chat(body.message))

    async def event_stream():
        chunks = await loop.run_in_executor(_executor, _run_generator)
        for chunk in chunks:
            payload = json.dumps({"chunk": chunk})
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
