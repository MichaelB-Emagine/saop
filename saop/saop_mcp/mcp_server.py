# # server.py
# from fastmcp import FastMCP
# from mcp_tools_registry import register_tools
# from agent_config import load_env_config

# # Load and validate environment configuration
# env_config = load_env_config()

# # Create a basic server instance
# mcp = FastMCP(name="MyRandomServer")

# # Import and register all the tools
# register_tools(mcp)

# if __name__ == "__main__":
#     mcp.run(
#         transport="http", host=env_config["MCP_HOST"], port=int(env_config["MCP_PORT"])
#     )

# mcp/mcp_server.py
"""
MCP server bootstrap.
"""

from __future__ import annotations
import os
from dotenv import load_dotenv

# 1) Import FastMCP and tool registry
from fastmcp import FastMCP
from .mcp_tools_registry import register_tools

# 2) Load environment that Compose provides (.env not required, but load if present)
load_dotenv(override=False)

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "9000"))

# 3) Create the MCP server instance
mcp = FastMCP(name="saop-mcp")

# 4) Register all tools from your registry (names must match agent YAML)
register_tools(mcp)


# 5) trivial 'ping' tool for a clean healthcheck
@mcp.tool(name="ping", title="Ping", description="Health check for the MCP server")
async def _ping() -> dict[str, str]:
    return {"status": "ok"}


# 6) Run the MCP HTTP server
if __name__ == "__main__":
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)
