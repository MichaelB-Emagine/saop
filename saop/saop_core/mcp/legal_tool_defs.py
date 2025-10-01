# mcp_server/legal_tool_defs.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import os
import time
import hashlib
import json

import aiohttp


# import asyncpg
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


# ---------- Utilities ----------
def _now_id(prefix: str = "sum") -> str:
    # Deterministic-ish synthetic id (no DB required)
    return f"{prefix}_{int(time.time()*1000)}"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


# ---------- Tool: fetch_contract_text ----------
async def fetch_contract_text(
    source: str,
    contract_id: Optional[str] = None,
    path_or_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch contract plaintext by source. Today:
      - url: fetch via HTTP GET
      - db/s3/gcs/fs: return a structured "unsupported" error to keep the API stable
    """
    source = (source or "").lower()
    if source == "url":
        if not path_or_url:
            return {"error": "missing_path_or_url"}
        async with aiohttp.ClientSession() as session:
            async with session.get(path_or_url) as resp:
                resp.raise_for_status()
                text = await resp.text()
                return {
                    "contract_id": contract_id or path_or_url,
                    "text": text,
                    "source_uri": path_or_url,
                    "sha256": _sha256_text(text),
                }

    # Stubs you can implement later
    if source in {"db", "s3", "gcs", "fs"}:
        return {"error": f"unsupported_source_{source}"}

    return {"error": "unsupported_source"}


# ---------- Tool: search_prior_summaries ----------
async def search_prior_summaries(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Returns sample results now so the agent can learn how to use this tool.
    Replace with a real search when you have storage (DB, vector store, etc.).
    """
    query = (query or "").strip()
    sample = [
        {
            "id": "demo_001",
            "contract_id": "acme-2023-msa",
            "title": "ACME Master Services Agreement 2023",
            "hash": "deadbeef",
            "preview": "Summary: ACME provides services; customer data processed under DPA…",
        },
        {
            "id": "demo_002",
            "contract_id": "acme-2024-dpa",
            "title": "ACME Data Processing Addendum 2024",
            "hash": "cafebabe",
            "preview": "GDPR lawful bases include contract and legitimate interest; SCCs present…",
        },
    ]
    # Simple filter for the mock
    out = [
        r for r in sample if query.lower() in (r["title"] + r["contract_id"]).lower()
    ]
    return {"results": out[: max(1, int(limit))]}


# ---------- Tool: store_summary ----------
async def store_summary(
    contract_id: str,
    summary_md: str,
    gdpr_json: Optional[Dict[str, Any]] = None,
    hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    No DB yet: return a synthetic id and echo what would be stored.
    """
    if not contract_id or not summary_md:
        return {"error": "missing_required_fields"}

    content_hash = hash or _sha256_text(summary_md)
    result_id = _now_id("legal")
    # Optionally: persist to a file for debugging
    if os.getenv("LEGAL_STORE_TO_FILES", "false").lower() == "true":
        folder = os.getenv("LEGAL_STORE_FOLDER", "/tmp/legal_summaries")
        os.makedirs(folder, exist_ok=True)
        with open(
            os.path.join(folder, f"{result_id}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(
                {
                    "id": result_id,
                    "contract_id": contract_id,
                    "hash": content_hash,
                    "summary_md": summary_md,
                    "gdpr_json": gdpr_json,
                    "model": os.getenv("MODEL_NAME", "unknown"),
                    "created_at": int(time.time()),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    return {
        "id": result_id,
        "hash": content_hash,
        "stored": bool(os.getenv("LEGAL_STORE_TO_FILES", "false").lower() == "true"),
    }


# ---------- Tool: db_query (read-only gate) ----------
async def db_query(sql: str, params: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Read-only query placeholder. Without a schema or DATABASE_URL, return a polite error.
    """
    if not DATABASE_URL:
        return {
            "error": "database_unavailable",
            "detail": "No DATABASE_URL set; read-only DB not configured.",
        }

    return {
        "error": "not_implemented",
        "detail": "DB driver not wired yet; add asyncpg section when ready.",
    }
