# # templates/base_agent/main.py
# # Purpose: Web entrypoint for a scaffolded agent.

# from __future__ import annotations

# import json


# from pathlib import Path

# from contextlib import asynccontextmanager

# from fastapi import FastAPI, HTTPException
# import traceback

# from fastapi.encoders import jsonable_encoder

# from pydantic import BaseModel

# from typing import Any, List, Dict

# from prometheus_fastapi_instrumentator import Instrumentator

# from agent_config import load_env_config

# from langgraph_tool_wrapper import build_tool_graph

# from langchain_core.messages import HumanMessage

# from prometheus_client import Counter, Histogram

# from telemetry import init_tracing


# ENV = None
# GRAPH = None


# class RunRequest(BaseModel):
#     prompt: str


# class RunResponse(BaseModel):
#     output: str


# class TraceResponse(BaseModel):
#     messages: List[Dict[str, Any]]


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """
#     Build Agent when the container starts up
#     """
#     init_tracing()

#     global ENV, GRAPH
#     ENV = load_env_config()

#     GRAPH = await build_tool_graph(ENV)
#     # Enable Prometheus metrics
#     yield


# app = FastAPI(title="SAOP Agent Service", version="0.1.0", lifespan=lifespan)
# # app = FastAPI(lifespan=lifespan)
# Instrumentator().instrument(app).expose(
#     app, endpoint="/metrics", include_in_schema=False
# )


# @app.get("/health")
# async def health():
#     return {"status": "ok", "graph_ready": GRAPH is not None}


# @app.get("/.well-known/agent-card.json")
# async def agent_card():
#     """
#     Serve agent card from ENV['A2A_AGENT_CARD_PATH'] if it exists.
#     """
#     if ENV is None:
#         raise HTTPException(status_code=503, detail="Agent not initialized yet.")

#     path = ENV.get("A2A_AGENT_CARD_PATH")
#     if not path:
#         raise HTTPException(status_code=404, detail="Agent card path not configured.")
#     p = Path(path)

#     if not p.is_absolute():
#         # Interpret relative to the agent directory in the container
#         # (Dockerfile will set --app-dir=/app/agent)
#         p = Path("/app/agent") / p
#     if not p.exists():
#         raise HTTPException(status_code=404, detail="Agent card not found.")

#     try:
#         data = json.loads(p.read_text(encoding="utf-8"))
#         return data
#     except json.JSONDecodeError:
#         raise HTTPException(status_code=500, detail="Invalid agent card JSON.")


# # @app.post("/run",response_model=RunResponse)
# # async def run_agent(req: RunRequest):
# #     """
# #     Turn a simple 'prompt' into the input structure your graph expects
# #     and return the agent's final text output.
# #     """
# #     if GRAPH is None:
# #         raise HTTPException(status_code=503, detail="Agent not initialized yet.")


# #     try:
# #         result = await GRAPH.ainvoke({"messages": [HumanMessage(content=req.prompt)]})
# #         last = result["messages"][-1]
# #         text = getattr(last, "content", str(last))
# #         return RunResponse(output=text)
# #     except Exception as e:
# #         print("[/run] ERROR:", repr(e))
# #         traceback.print_exc()
# #         raise HTTPException(status_code=500, detail="Agent failed to run.")
# # Track request latency
# AGENT_LATENCY = Histogram(
#     "agent_request_latency_seconds", "Latency of agent /run requests"
# )

# # Track cost tokens
# AGENT_COST = Counter(
#     "agent_tokens_total", "Total tokens processed by agent", ["model", "type"]
# )

# # Track errors
# AGENT_ERRORS = Counter(
#     "agent_errors_total", "Number of failed agent requests", ["reason"]
# )


# @app.post("/run", response_model=TraceResponse)
# async def run_agent(req: RunRequest):
#     if GRAPH is None or ENV is None:
#         raise HTTPException(status_code=503, detail="Agent not initialized yet.")

#     model_name = ENV.get("MODEL_NAME") or "unknown"

#     with AGENT_LATENCY.time():
#         try:
#             result = await GRAPH.ainvoke(
#                 {"messages": [HumanMessage(content=req.prompt)]}
#             )

#             messages: list[dict] = []
#             total_input_tokens = 0
#             total_output_tokens = 0

#             for m in result["messages"]:
#                 entry = {
#                     "type": type(m).__name__,
#                     "content": getattr(m, "content", None),
#                 }
#                 if hasattr(m, "tool_calls") and m.tool_calls:
#                     entry["tool_calls"] = jsonable_encoder(m.tool_calls)
#                 if hasattr(m, "tool_call_id"):
#                     entry["tool_call_id"] = getattr(m, "tool_call_id", None)

#                 usage = getattr(m, "usage_metadata", None)
#                 if isinstance(usage, dict) and usage:
#                     inp = int(usage.get("input_tokens") or 0)
#                     out = int(usage.get("output_tokens") or 0)
#                     if inp:
#                         entry["input_tokens"] = inp
#                         total_input_tokens += inp
#                     if out:
#                         entry["output_tokens"] = out
#                         total_output_tokens += out
#                     # (optional) include total if present
#                     if "total_tokens" in usage:
#                         entry["total_tokens"] = int(usage["total_tokens"])

#                 messages.append(entry)

#             # increment metrics once per request
#             if total_input_tokens:
#                 AGENT_COST.labels(model=model_name, type="input").inc(
#                     total_input_tokens
#                 )
#             if total_output_tokens:
#                 AGENT_COST.labels(model=model_name, type="output").inc(
#                     total_output_tokens
#                 )
#             # if total_input_tokens or total_output_tokens:
#             #     AGENT_TOTAL_TOKENS.labels(model=model_name).inc(total_input_tokens + total_output_tokens)

#             return TraceResponse(messages=messages)

#         except Exception as e:
#             AGENT_ERRORS.labels(reason=type(e).__name__).inc()
#             print("[/run] ERROR:", repr(e))
#             traceback.print_exc()
#             raise HTTPException(status_code=500, detail="Agent failed to run.")

# templates/legal_agent/main.py
from __future__ import annotations
import json
import time
import pathlib
from typing import Any, Dict, Optional, List

import uvicorn
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from pydantic import BaseModel

# Shared imports
from saop_core.agent_config import load_config
from saop_core.telemetry import init_tracing
from saop_core.llm.client import LLMClient
from saop_core.mcp.client import MCPClient

BASE_DIR = pathlib.Path(__file__).resolve().parent
CFG = load_config(BASE_DIR)  # .env + agent.yaml (env wins where specified)

init_tracing(service_name=CFG.service.service_name, otlp_endpoint=CFG.obs.otlp_endpoint)

llm = LLMClient(base_url=CFG.model.base_url, api_key=CFG.model.api_key)
mcp = MCPClient(base_url=CFG.mcp.base_url, bearer_token=CFG.mcp.bearer_token)

SYSTEM_PROMPT = (CFG.raw_yaml.get("agent") or {}).get("prompt_template", "")
DECLARED_TOOLS = {
    t.get("name") for t in ((CFG.raw_yaml.get("agent") or {}).get("tools") or [])
}

app = FastAPI(title=f"saop {CFG.service.agent_name} agent")
router = APIRouter(prefix=f"/agents/{CFG.service.agent_name}")


def _extract_json_block(md: str) -> Optional[Dict[str, Any]]:
    fence = "```"
    i = md.rfind(fence)
    while i != -1:
        block = md[i + len(fence) :].strip()
        if block.startswith("json"):
            block = block[len("json") :].lstrip()
        try:
            return json.loads(block)
        except Exception:
            md = md[:i]
            i = md.rfind(fence)
    return None


@router.get("/healthz")
async def healthz():
    return {
        "ok": True,
        "agent": CFG.service.agent_name,
        "model": CFG.model.name,
        "provider": CFG.model.provider,
    }


@router.get("/agent-card")
async def agent_card():
    p = BASE_DIR / ".well-known" / "agent-card.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="agent-card.json not found")
    return FileResponse(p)


class RunBody(BaseModel):
    contract_id: Optional[str] = None
    source: str = "db"
    path_or_url: Optional[str] = None
    prior_context_query: Optional[str] = None
    store: bool = True


@router.post("/run")
async def run(body: RunBody):
    t0 = time.perf_counter()

    # 1) fetch via MCP
    doc = await mcp.call_tool(
        "fetch_contract_text",
        {
            "source": body.source,
            "contract_id": body.contract_id,
            "path_or_url": body.path_or_url,
        },
    )
    if "error" in doc:
        raise HTTPException(
            status_code=404, detail=f"fetch_contract_text failed: {doc['error']}"
        )

    # 2) optional prior context
    context: List[str] = []
    if body.prior_context_query:
        prior = await mcp.call_tool(
            "search_prior_summaries", {"query": body.prior_context_query, "limit": 5}
        )
        for r in prior.get("results", []):
            title = r.get("title") or r.get("contract_id") or ""
            preview = (r.get("preview") or "").replace("\n", " ")
            context.append(f"- {title}: {preview}")

    user_prompt = (
        "You will analyze the following contract.\n\n"
        + ("Prior context:\n" + "\n".join(context) + "\n\n" if context else "")
        + f"Contract text (may be truncated):\n\n{(doc.get('text') or '')[:200_000]}\n\n"
    )

    # 3) call model
    res = await llm.responses(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        model=CFG.model.name,
        temperature=CFG.model.temperature,
    )
    content = res.get("content", "")
    gdpr = _extract_json_block(content)

    # 4) optional store
    summary_id = None
    if body.store and "store_summary" in DECLARED_TOOLS:
        try:
            sresp = await mcp.call_tool(
                "store_summary",
                {
                    "contract_id": body.contract_id
                    or doc.get("contract_id")
                    or body.path_or_url
                    or "unknown",
                    "summary_md": content,
                    "gdpr_json": gdpr,
                    "hash": doc.get("sha256"),
                },
            )
            summary_id = sresp.get("id")
        except Exception:
            summary_id = None  # non-fatal

    return JSONResponse(
        {
            "ok": True,
            "agent": CFG.service.agent_name,
            "model": CFG.model.name,
            "latency_seconds": time.perf_counter() - t0,
            "summary_id": summary_id,
            "content": content,
            "gdpr_json": gdpr,
        }
    )


app.include_router(router)

if __name__ == "__main__":
    import os

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", CFG.service.host),
        port=int(os.getenv("PORT", CFG.service.port)),
        reload=os.getenv("RELOAD", "false").lower() == "true",
    )
