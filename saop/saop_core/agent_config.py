# import os
# from typing import TypedDict, Optional, List, Dict, Any
# import datetime
# from dotenv import load_dotenv


# class ToolConfig(TypedDict):
#     name: str
#     description: str
#     input_schema: Dict[str, Any]
#     output_schema: Dict[str, Any]


# class AgentYAMLConfig(TypedDict):
#     id: str
#     name: str
#     description: str
#     version: str
#     role: str
#     prompt_template: str
#     resources: List[str]
#     knowledge_base: Optional[str]
#     graph: Dict
#     created: datetime.datetime
#     updated: datetime.datetime
#     agents: List[str]
#     tools: List[ToolConfig]


# class EnvironmentConfig(TypedDict):
#     MODEL_API_KEY: str
#     MODEL_BASE_URL: str
#     MODEL_NAME: str
#     MODEL_TEMPERATURE: float
#     MODEL_PROVIDER: str
#     A2A_AGENT_CARD_PATH: str
#     A2A_HOST: str
#     A2A_PORT: int
#     MCP_BASE_URL: str
#     MCP_HOST: str
#     MCP_PORT: int
#     SAMPLE01_MCP_TOOL_API_KEY: Optional[str]
#     SAMPLE02_MCP_TOOL_API_KEY: Optional[str]
#     OTEL_EXPORTER_OTLP_ENDPOINT: str
#     REDIS_URL: Optional[str]
#     DATABASE_URL: Optional[str]
#     AUTH_CLIENT_ID: Optional[str]
#     AUTH_CLIENT_SECRET: Optional[str]
#     HASHICORP_VAULT_ADDR: Optional[str]
#     AWS_SECRETS_MANAGER_ARN: Optional[str]


# class SAOPAgentConfig(TypedDict):
#     agent: AgentYAMLConfig
#     environment: EnvironmentConfig


# def load_env_config() -> EnvironmentConfig:
#     # Ensure .env file is loaded before accessing variables
#     load_dotenv()

#     return EnvironmentConfig(
#         # AI Model Vars
#         MODEL_API_KEY=os.environ.get("MODEL_API_KEY", ""),
#         MODEL_BASE_URL=os.environ.get("MODEL_BASE_URL", ""),
#         MODEL_NAME=os.environ.get("MODEL_NAME", ""),
#         MODEL_TEMPERATURE=float(os.environ.get("MODEL_TEMPERATURE", 0.7)),
#         MODEL_PROVIDER=os.environ.get("MODEL_PROVIDER", "openai"),
#         # A2A Vars# agent.yaml
#         A2A_AGENT_CARD_PATH=os.environ.get("A2A_AGENT_CARD_PATH", ""),
#         A2A_HOST=os.environ.get("A2A_HOST", ""),
#         A2A_PORT=int(os.environ.get("A2A_PORT", 8000)),
#         # MCP Vars
#         MCP_BASE_URL=os.environ.get("MCP_BASE_URL", ""),
#         MCP_HOST=os.environ.get("MCP_HOST", "127.0.0.1"),  # THIS WAS MISSING
#         MCP_PORT=int(os.environ.get("MCP_PORT", "9000")),  # THIS WAS MISSING
#         SAMPLE01_MCP_TOOL_API_KEY=os.getenv("MCP_TOOL_API_KEY"),
#         SAMPLE02_MCP_TOOL_API_KEY=os.getenv("MCP_TOOL_API_KEY"),
#         # OpenTel Endpoint Var
#         OTEL_EXPORTER_OTLP_ENDPOINT=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
#         # DB & Cache Vars
#         REDIS_URL=os.getenv("REDIS_URL"),
#         DATABASE_URL=os.getenv("DATABASE_URL"),
#         # Auth Vars
#         AUTH_CLIENT_ID=os.getenv("AUTH_CLIENT_ID"),
#         AUTH_CLIENT_SECRET=os.getenv("AUTH_CLIENT_SECRET"),
#         HASHICORP_VAULT_ADDR=os.getenv("HASHICORP_VAULT_ADDR"),
#         AWS_SECRETS_MANAGER_ARN=os.getenv("AWS_SECRETS_MANAGER_ARN"),
#     )


# if __name__ == "__main__":
#     env_config = load_env_config()
#     # You can now use the structured object
#     print("Loaded Environment Configuration:")
#     print(f"Model Name: {env_config['MODEL_NAME']}")
#     print(f"MCP Base URL: {env_config['MCP_BASE_URL']}")
#     print(f"A2A Port: {env_config['A2A_PORT']}")
#     print(f"Database URL (Optional): {env_config.get('DATABASE_URL')}")

# saop_core/agent_config.py
from __future__ import annotations
import os
import pathlib
import yaml  # type: ignore[import-untyped]
from dataclasses import dataclass
from typing import Any, Dict
from dotenv import load_dotenv


@dataclass
class ModelConfig:
    provider: str
    name: str
    temperature: float
    max_tokens: int
    base_url: str
    api_key: str


@dataclass
class ServiceConfig:
    agent_name: str
    service_name: str
    host: str
    port: int
    agent_card_path: str


@dataclass
class ObservabilityConfig:
    otlp_endpoint: str  # http://otel-collector:4318


@dataclass
class MCPConfig:
    base_url: str  # e.g., http://mcp:9000/mcp
    bearer_token: str  # optional


@dataclass
class AppConfig:
    model: ModelConfig
    service: ServiceConfig
    mcp: MCPConfig
    obs: ObservabilityConfig
    raw_yaml: Dict[
        str, Any
    ]  # the loaded agent.yaml (useful for prompt_template & tools)


def _load_yaml(yaml_path: pathlib.Path) -> Dict[str, Any]:
    if not yaml_path.exists():
        raise FileNotFoundError(f"agent.yaml not found at {yaml_path}")
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(template_dir: pathlib.Path) -> AppConfig:
    """
    Load .env (in template_dir), then agent.yaml (in template_dir), then build a merged config.
    Precedence: .env overrides YAML defaults.
    """
    load_dotenv(template_dir / ".env")

    # YAML
    raw = _load_yaml(template_dir / "agent.yaml")
    yaml_model = (raw.get("agent") or {}).get("model") or {}
    yaml_agent = raw.get("agent") or {}
    # prompt_template lives in yaml_agent.get("prompt_template")

    # ENV with compatibility (MODEL_* first, fallback to OPENAI_*)
    base_url = (
        os.getenv("MODEL_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    )
    api_key = os.getenv("MODEL_API_KEY") or os.getenv("OPENAI_API_KEY") or ""

    model = ModelConfig(
        provider=os.getenv("MODEL_PROVIDER", yaml_model.get("provider", "openai")),
        name=os.getenv("MODEL_NAME", yaml_model.get("name", "gpt-4.1-mini")),
        temperature=float(
            os.getenv("MODEL_TEMPERATURE", yaml_model.get("temperature", 0.1))
        ),
        max_tokens=int(
            os.getenv("MODEL_MAX_TOKENS", yaml_model.get("max_tokens", 2000))
        ),
        base_url=base_url,
        api_key=api_key,
    )

    service = ServiceConfig(
        agent_name=os.getenv("AGENT_NAME", yaml_agent.get("role", "agent")),
        service_name=os.getenv(
            "OTEL_SERVICE_NAME", f"saop-{yaml_agent.get('role', 'agent')}-agent"
        ),
        host=os.getenv("A2A_HOST", "0.0.0.0"),
        port=int(os.getenv("A2A_PORT", "8080")),
        agent_card_path=os.getenv(
            "A2A_AGENT_CARD_PATH", "/.well-known/agent-card.json"
        ),
    )

    mcp = MCPConfig(
        base_url=os.getenv("MCP_BASE_URL", "http://mcp:9000/mcp"),
        bearer_token=os.getenv("MCP_TOOL_API_KEY", ""),
    )

    obs = ObservabilityConfig(
        otlp_endpoint=os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318"
        )
    )

    return AppConfig(model=model, service=service, mcp=mcp, obs=obs, raw_yaml=raw)
