from __future__ import annotations

import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


def setup_otel(app, service_name: str) -> None:
    """
    Demo-safe OpenTelemetry:
    - Always creates a tracer provider
    - Exports to console by default
    - If OTEL_EXPORTER_OTLP_ENDPOINT is set, also exports OTLP
    """
    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
