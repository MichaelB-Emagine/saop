# # telemetry.py
# """
# Telemetry initializer for OpenTelemetry.
# Call init_tracing() once at startup to enable traces.
# """

# import os
# from typing import Dict

# # Core OpenTelemetry imports
# from opentelemetry import trace
# from opentelemetry.sdk.resources import Resource
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
# from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


# def _parse_headers(raw: str | None) -> Dict[str, str]:
#     """
#     Helper: turns a string like:
#         "authorization=Bearer mytoken,env=prod"
#     into:
#         {"authorization": "Bearer mytoken", "env": "prod"}
#     Used for OTEL_EXPORTER_OTLP_HEADERS if backend needs extra headers.
#     """
#     if not raw:
#         return {}
#     pairs = [p.strip() for p in raw.split(",") if p.strip()]
#     out: Dict[str, str] = {}
#     for p in pairs:
#         if "=" in p:
#             k, v = p.split("=", 1)
#             out[k.strip()] = v.strip()
#     return out


# def init_tracing() -> None:
#     """
#     Initialize OpenTelemetry tracing with OTLP exporter.
#     Reads config from environment variables:
#         OTEL_SERVICE_NAME          - Name of this service (e.g., "agent-factory")
#         OTEL_EXPORTER_OTLP_ENDPOINT - Where to send traces (default: http://localhost:4318)
#         OTEL_EXPORTER_OTLP_HEADERS  - Optional headers (comma-separated key=value)
#     """

#     # --- Define "who is sending telemetry" (the Resource)
#     service_name = os.getenv("OTEL_SERVICE_NAME", "saop-agent")
#     resource = Resource.create(
#         {
#             "service.name": service_name,
#         }
#     )

#     # --- Create and register the global tracer provider
#     provider = TracerProvider(resource=resource)
#     trace.set_tracer_provider(provider)

#     # --- Configure the OTLP exporter (default = local collector on port 4318)
#     # endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318").rstrip("/")
#     # headers = _parse_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS"))
#     base = os.getenv(
#         "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318"
#     ).rstrip("/")
#     exporter = OTLPSpanExporter(endpoint=f"{base}/v1/traces")

#     # exporter = OTLPSpanExporter(
#     #     endpoint=f"{endpoint}/v1/traces",
#     #     headers=headers or None,
#     #     timeout=10,
#     # )

#     # --- Add a BatchSpanProcessor (efficiently sends spans in the background)
#     processor = BatchSpanProcessor(exporter)
#     provider.add_span_processor(processor)

#     # --- Create a test span so you can confirm it's working
#     tracer = trace.get_tracer("startup")
#     with tracer.start_as_current_span("otlp_init_ok"):
#         # Span starts here and ends when we leave this block
#         pass


# saop_core/telemetry.py
from __future__ import annotations
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


def init_tracing(service_name: str, otlp_endpoint: str) -> None:
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
