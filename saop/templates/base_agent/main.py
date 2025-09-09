# templates/base_agent/main.py
# Purpose: Web entrypoint for a scaffolded agent.

from __future__ import annotations

import json


from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
import traceback

from fastapi.encoders import jsonable_encoder

from pydantic import BaseModel

from typing import Any, List, Dict

from prometheus_fastapi_instrumentator import Instrumentator

from agent_config import load_env_config

from langgraph_tool_wrapper import build_tool_graph

from langchain_core.messages import HumanMessage

from prometheus_client import Counter, Histogram

app = FastAPI(title="SAOP Agent Service", version="0.1.0")

ENV = None
GRAPH = None


class RunRequest(BaseModel):
    prompt: str


class RunResponse(BaseModel):
    output: str


class TraceResponse(BaseModel):
    messages: List[Dict[str, Any]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Build Agent when the container starts up
    """
    global ENV, GRAPH
    ENV = load_env_config()

    GRAPH = await build_tool_graph(ENV)
    # Enable Prometheus metrics
    yield


app = FastAPI(lifespan=lifespan)
Instrumentator().instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/.well-known/agent-card.json")
async def agent_card():
    """
    Serve agent card from ENV['A2A_AGENT_CARD_PATH'] if it exists.
    """
    if ENV is None:
        raise HTTPException(status_code=503, detail="Agent not initialized yet.")

    path = ENV.get("A2A_AGENT_CARD_PATH")
    if not path:
        raise HTTPException(status_code=404, detail="Agent card path not configured.")
    p = Path(path)

    if not p.is_absolute():
        # Interpret relative to the agent directory in the container
        # (Dockerfile will set --app-dir=/app/agent)
        p = Path("/app/agent") / p
    if not p.exists():
        raise HTTPException(status_code=404, detail="Agent card not found.")

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid agent card JSON.")


# @app.post("/run",response_model=RunResponse)
# async def run_agent(req: RunRequest):
#     """
#     Turn a simple 'prompt' into the input structure your graph expects
#     and return the agent's final text output.
#     """
#     if GRAPH is None:
#         raise HTTPException(status_code=503, detail="Agent not initialized yet.")


#     try:
#         result = await GRAPH.ainvoke({"messages": [HumanMessage(content=req.prompt)]})
#         last = result["messages"][-1]
#         text = getattr(last, "content", str(last))
#         return RunResponse(output=text)
#     except Exception as e:
#         print("[/run] ERROR:", repr(e))
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail="Agent failed to run.")
# Track request latency
AGENT_LATENCY = Histogram(
    "agent_request_latency_seconds", "Latency of agent /run requests"
)

# Track cost tokens
AGENT_COST = Counter(
    "agent_tokens_total", "Total tokens processed by agent", ["model", "type"]
)

# Track errors
AGENT_ERRORS = Counter(
    "agent_errors_total", "Number of failed agent requests", ["reason"]
)


@app.post("/run", response_model=TraceResponse)
async def run_agent(req: RunRequest):
    if GRAPH is None or ENV is None:
        raise HTTPException(status_code=503, detail="Agent not initialized yet.")

    model_name = ENV.get("MODEL_NAME") or "unknown"

    with AGENT_LATENCY.time():
        try:
            result = await GRAPH.ainvoke(
                {"messages": [HumanMessage(content=req.prompt)]}
            )

            messages: list[dict] = []
            total_input_tokens = 0
            total_output_tokens = 0

            for m in result["messages"]:
                entry = {
                    "type": type(m).__name__,
                    "content": getattr(m, "content", None),
                }
                if hasattr(m, "tool_calls") and m.tool_calls:
                    entry["tool_calls"] = jsonable_encoder(m.tool_calls)
                if hasattr(m, "tool_call_id"):
                    entry["tool_call_id"] = getattr(m, "tool_call_id", None)

                usage = getattr(m, "usage_metadata", None)
                if isinstance(usage, dict) and usage:
                    inp = int(usage.get("input_tokens") or 0)
                    out = int(usage.get("output_tokens") or 0)
                    if inp:
                        entry["input_tokens"] = inp
                        total_input_tokens += inp
                    if out:
                        entry["output_tokens"] = out
                        total_output_tokens += out
                    # (optional) include total if present
                    if "total_tokens" in usage:
                        entry["total_tokens"] = int(usage["total_tokens"])

                messages.append(entry)

            # increment metrics once per request
            if total_input_tokens:
                AGENT_COST.labels(model=model_name, type="input").inc(
                    total_input_tokens
                )
            if total_output_tokens:
                AGENT_COST.labels(model=model_name, type="output").inc(
                    total_output_tokens
                )
            # if total_input_tokens or total_output_tokens:
            #     AGENT_TOTAL_TOKENS.labels(model=model_name).inc(total_input_tokens + total_output_tokens)

            return TraceResponse(messages=messages)

        except Exception as e:
            AGENT_ERRORS.labels(reason=type(e).__name__).inc()
            print("[/run] ERROR:", repr(e))
            traceback.print_exc()
            raise HTTPException(status_code=500, detail="Agent failed to run.")
