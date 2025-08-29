# LangChain and LangGraph imports
from langchain_core.messages import BaseMessage, HumanMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import MessagesState

# Import the custom configuration loader
# Import the new MultiServerMCPClient from the correct library
from langchain_mcp_adapters.client import MultiServerMCPClient

import asyncio
from typing import Any, Mapping

from agent_config import load_env_config


ENV = load_env_config()


async def build_tool_graph(env_config: Mapping[str, Any]):
    """
    Build and return a compiled LangGraph that:
      - uses your chat model
      - discovers MCP tools via MultiServerMCPClient
      - routes messages to tools when tool_calls are present
    This function DOES NOT run any queries. It just returns the compiled graph.
    """
    if not env_config.get("MODEL_NAME") or not env_config.get("MODEL_API_KEY"):
        raise RuntimeError("MODEL_NAME and MODEL_API_KEY must be set")

    # --- Initialize the Model and Client ---
    model = init_chat_model(
        env_config["MODEL_NAME"],
        openai_api_key=env_config["MODEL_API_KEY"],
        model_provider=env_config["MODEL_PROVIDER"],
        base_url=env_config.get("MODEL_BASE_URL") or None,
    )

    # Discover MCP tools only if configured
    tools: list = []
    mcp_url = (env_config.get("MCP_BASE_URL") or "").strip()
    if mcp_url:
        client_config = {"mcp_server": {"url": mcp_url, "transport": "streamable_http"}}
        client = MultiServerMCPClient(client_config)
        tools = await client.get_tools()

    model_with_tools = model.bind_tools(tools)

    tool_node = ToolNode(tools) if tools else None

    async def call_model(state: MessagesState) -> dict[str, list[BaseMessage]]:
        messages = state["messages"]
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)

    try:
        builder.set_entry_point("call_model")  # some versions support/expect this
    except Exception:
        pass

    builder.add_edge(START, "call_model")

    if tools:

        def should_continue(state: MessagesState) -> str:
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        builder.add_node("tools", tool_node)  # type: ignore[arg-type]
        builder.add_conditional_edges(
            "call_model", should_continue, {"tools": "tools", END: END}
        )
        builder.add_edge("tools", "call_model")
    else:
        # No tools discovered → straight to END
        builder.add_edge("call_model", END)

    graph = builder.compile()
    return graph


if __name__ == "__main__":

    async def _demo():
        g = await build_tool_graph(ENV)
        greet_query = {"messages": [HumanMessage(content="Say hi to my friend Tim.")]}
        print("\n▶️ Invoking agent to test the 'greet' tool...")
        response = await g.ainvoke(greet_query)
        print(f"✅ Final agent response: {response['messages'][-1].content}")

        simple_query = {"messages": [HumanMessage(content="What's your name?")]}
        print("\n▶️ Invoking agent for a simple query...")
        response = await g.ainvoke(simple_query)
        print(f"✅ Final agent response: {response['messages'][-1].content}")

    asyncio.run(_demo())
