import sys
from unittest.mock import MagicMock

import sqlalchemy
sqlalchemy.create_engine = MagicMock(return_value=MagicMock())

_mock_modules = [
    "opentelemetry",
    "opentelemetry.trace",
    "opentelemetry.sdk",
    "opentelemetry.sdk.trace",
    "opentelemetry.sdk.trace.export",
    "opentelemetry.sdk.resources",
    "opentelemetry.exporter",
    "opentelemetry.exporter.otlp",
    "opentelemetry.exporter.otlp.proto",
    "opentelemetry.exporter.otlp.proto.grpc",
    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter",
    "opentelemetry.instrumentation",
    "opentelemetry.instrumentation.fastapi",
    "opentelemetry.instrumentation.sqlalchemy",
    "opentelemetry.instrumentation.redis",
    "opentelemetry.instrumentation.httpx",
    "prometheus_fastapi_instrumentator",
    "app.telemetry",
]
for _mod in _mock_modules:
    sys.modules.setdefault(_mod, MagicMock())
