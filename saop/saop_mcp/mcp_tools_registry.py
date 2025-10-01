from .mcp_tool_defs import (
    multiply_numbers,
    get_presidents,
    generate_random_number,
    get_daily_message,
    greet_user,
)


def register_tools(mcp):

    # Tool 1: multiply
    @mcp.tool(
        name="multiply",
        title="Multiply Two Numbers",
        description="Multiplies two numbers together and returns the product.",
        annotations={
            "example_usage": "multiply(a=5, b=10)",
            "docs_link": "http://docs.example.com/math/multiply",
        },
        meta={"category": "Math", "version": "1.0.0"},
    )
    def multiply(a: float, b: float) -> float:
        return multiply_numbers(a, b)

    # Tool 2: list_past_20_presidents
    @mcp.tool(
        name="list_past_20_presidents",
        title="Get Recent US Presidents",
        description="Fetches a list of the last 20 US presidents, ordered from most recent to least recent.",
        annotations={"api_source": "internal", "data_updated": "2025-08-19"},
        meta={"category": "Historical Data"},
    )
    def list_presidents() -> list[str]:
        return get_presidents()

    # Tool 3: random_number_generator
    @mcp.tool(
        name="random_number_generator",
        title="Generate Random Number",
        description="Generates and returns a random integer between 0 and 100 (inclusive).",
        annotations={"range": "0-100"},
        meta={"category": "Utilities"},
    )
    def random_number_generator() -> int:
        return generate_random_number()

    # Tool 4: daily_warm_message
    @mcp.tool(
        name="daily_warm_message",
        title="Get Daily Encouragement",
        description="Provides a nice, warm, and encouraging message for the day.",
        annotations={"usage_note": "Message changes daily."},
        meta={"category": "Motivational"},
    )
    def daily_warm_message() -> str:
        return get_daily_message()

    # Tool 5: greet
    @mcp.tool(
        name="greet",
        title="Greet User",
        description="Greets a user by name and returns a personalized welcome message.",
        annotations={"required_params": "name"},
        meta={"category": "Communication"},
    )
    def greet(name: str) -> str:
        return greet_user(name)
