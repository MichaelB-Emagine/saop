import asyncio
from fastmcp import Client
from agent_config import load_env_config

env_config = load_env_config()


def get_mcp_session(server_url: str):
    return Client(server_url)


async def main():
    server_url = env_config["MCP_BASE_URL"]

    if not server_url:
        print("🔴 Error: MCP_BASE_URL environment variable is not set.")
        return

    async with get_mcp_session(server_url) as client:
        try:

            await client.ping()
            print("🟢 Successfully connected to the MCP server.")

            tools = await client.list_tools()
            print("ALL TOOLS:", tools)

            random_number = await client.call_tool("random_number_generator")
            print(f"✨ Result from random_number_generator: {random_number}")

            greeting = await client.call_tool("greet", {"name": "Tim"})
            print(f"👋 Result from greet tool: {greeting}")

        except Exception as e:
            print(f"🔴 An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
