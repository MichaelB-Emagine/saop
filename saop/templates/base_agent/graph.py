"""
Minimal LangGraph with:
- A single "echo" node that returns what you send it.
- An in-memory checkpointer so state persists across calls in the same thread.

Run it:
    python graph.py
"""

from __future__ import annotations

import operator
from typing import Annotated, List, TypedDict

# LangGraph core pieces
from langgraph.graph import StateGraph, END

# Different LangGraph versions expose the in-memory saver under slightly different names.

try:
    # Older versions
    from langgraph.checkpoint import MemorySaver as InMemorySaver  # type: ignore
except Exception:
    try:
        # Expose InMemorySaver directly
        from langgraph.checkpoint import InMemorySaver  # type: ignore
    except Exception:
        # Newer module path
        from langgraph.checkpoint.memory import MemorySaver as InMemorySaver  # type: ignore


# 1) Define the graph "state"
# The state is just a dictionary with a "messages" list.
class EchoState(TypedDict):
    messages: Annotated[List[str], operator.add]


# 2) Define a node (a function)
# Nodes receive the current state and RETURN a partial state update.
# Take the last incoming message and append an "echo: ..." response.
def echo_node(state: EchoState) -> dict:
    last = state["messages"][-1] if state["messages"] else ""
    response = f"echo: {last}"
    return {"messages": [response]}


# 3) Build the graph
# - Create a StateGraph with state type
# - Add the node
# - Set it as the entry point
# - Add an edge to END (one-node graph)
graph = StateGraph(EchoState)
graph.add_node("echo", echo_node)
graph.set_entry_point("echo")
graph.add_edge("echo", END)

# 4) Compile with an in-memory checkpointer
# The checkpointer lets LangGraph save the state between runs of the same "thread".
checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)


# 5) Demo: Run
# Call the graph twice using the SAME thread_id to show that state persists.
if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "demo-thread"}}

    # First user message
    result1 = app.invoke({"messages": ["hello"]}, config=cfg)
    print("First call result:", result1)

    # Second user message (same thread_id -> previous state is loaded)
    result2 = app.invoke({"messages": ["world"]}, config=cfg)
    print("Second call result:", result2)

    # You can also stream events if you like:
    print("\nStreaming a single call:")
    for event in app.stream({"messages": ["stream me"]}, config=cfg):
        # event is a dict like {"echo": {"messages": [...]}} or {"__end__": {...}}
        print(event)
