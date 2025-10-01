# LangChain and LangGraph imports
from langchain_core.messages import BaseMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import MessagesState

# Import the custom configuration loader
# Import the new MultiServerMCPClient from the correct library
from langchain_mcp_adapters.client import MultiServerMCPClient

# from agent_config import load_env_config

# ENV = load_env_config()
from saop_core.agent_config import load_config

import pathlib

# 2) Load config for THIS template folder (where agent.yaml lives)
TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent
CFG = load_config(TEMPLATE_DIR)

# 3) Pull system prompt from YAML (legal agent.yaml)
SYSTEM_PROMPT = (CFG.raw_yaml.get("agent") or {}).get("prompt_template", "")

# 4) Tool allow-list from YAML
DECLARED_TOOLS = {
    t.get("name") for t in ((CFG.raw_yaml.get("agent") or {}).get("tools") or [])
}


async def build_tool_graph(_: dict | None = None):
    """
    Build and return a compiled LangGraph for the *legal* agent.
    - Uses centralized CFG for model + MCP settings
    - Filters discovered tools to the allow-list declared in agent.yaml
    - Injects the system prompt as the first message once per run
    """
    # Guardrails: ensure model creds exist
    if not CFG.model.name or not CFG.model.api_key:
        raise RuntimeError("MODEL_NAME and MODEL_API_KEY must be set")

    # --- Initialize the Model ---
    model = init_chat_model(
        CFG.model.name,
        openai_api_key=CFG.model.api_key,
        model_provider=CFG.model.provider,
        base_url=CFG.model.base_url or None,
    )

    # --- Discover MCP tools (if configured) ---
    tools = []
    mcp_url = (CFG.mcp.base_url or "").strip()
    if mcp_url:
        client_config = {"mcp_server": {"url": mcp_url, "transport": "streamable_http"}}
        client = MultiServerMCPClient(client_config)
        discovered = await client.get_tools()
        # 5) Filter to YAML-declared tools only (safety rail)
        tools = [t for t in discovered if t.name in DECLARED_TOOLS]

    model_with_tools = model.bind_tools(tools)
    tool_node = ToolNode(tools) if tools else None

    # Inject the system prompt ONCE at the start of the conversation
    async def call_model(state: MessagesState) -> dict[str, list[BaseMessage]]:
        messages = state["messages"]
        if not messages or (getattr(messages[0], "role", None) != "system"):
            from langchain_core.messages import SystemMessage

            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # --- Graph wiring (same as before) ---
    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)
    builder.add_edge(START, "call_model")

    if tools:

        def should_continue(state: MessagesState) -> str:
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        builder.add_node("tools", tool_node)  # Tool execution node
        builder.add_conditional_edges(
            "call_model", should_continue, {"tools": "tools", END: END}
        )
        builder.add_edge("tools", "call_model")
    else:
        builder.add_edge("call_model", END)

    return builder.compile()
