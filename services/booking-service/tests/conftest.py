import sys
from unittest.mock import MagicMock
import pytest
import jwt

# app 모듈 import 전에 외부 의존성을 미리 mock 처리
# (CI 환경에서 libpq/opentelemetry/grpcio 미설치 시에도 동작)
_mock_modules = [
    # psycopg: SQLAlchemy create_engine()이 모듈 로드 시점에 import 시도
    "psycopg",
    "psycopg.pq",
    "psycopg.adapt",
    "psycopg.types",
    "psycopg.errors",
    # opentelemetry: grpcio C 라이브러리 필요
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
    # prometheus
    "prometheus_fastapi_instrumentator",
]
for _mod in _mock_modules:
    sys.modules.setdefault(_mod, MagicMock())


JWT_SECRET = "dev-secret"
JWT_ALGORITHM = "HS256"


def make_token(user_id="user-1", display_name="Test User", provider="test"):
    return jwt.encode(
        {"sub": user_id, "display_name": display_name, "provider": provider},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token()}"}
