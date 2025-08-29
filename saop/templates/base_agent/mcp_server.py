# server.py
from fastmcp import FastMCP
from mcp_tools_registry import register_tools
from agent_config import load_env_config

# Load and validate environment configuration
env_config = load_env_config()

# Create a basic server instance
mcp = FastMCP(name="MyRandomServer")

# Import and register all the tools
register_tools(mcp)

if __name__ == "__main__":
    mcp.run(
        transport="http", host=env_config["MCP_HOST"], port=int(env_config["MCP_PORT"])
    )
