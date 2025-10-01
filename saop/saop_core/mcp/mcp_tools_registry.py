# mcp_server/mcp_tools_registry.py
from fastmcp import FastMCP
from .legal_tool_defs import (
    fetch_contract_text,
    search_prior_summaries,
    store_summary,
    db_query,
)


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool(name="fetch_contract_text", title="Fetch Contract Text")
    async def _fetch_contract_text(**kwargs):
        return await fetch_contract_text(**kwargs)

    @mcp.tool(name="search_prior_summaries", title="Search Prior Summaries")
    async def _search_prior_summaries(**kwargs):
        return await search_prior_summaries(**kwargs)

    @mcp.tool(name="store_summary", title="Store Summary")
    async def _store_summary(**kwargs):
        return await store_summary(**kwargs)

    @mcp.tool(name="db_query", title="DB Query (read-only)")
    async def _db_query(**kwargs):
        return await db_query(**kwargs)
