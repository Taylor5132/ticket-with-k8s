import sys
from unittest.mock import MagicMock
import pytest
import jwt

# common.py는 모듈 로드 시점에 create_engine()을 호출 → psycopg/libpq 필요
# app 모듈 import 전에 sqlalchemy.create_engine을 mock으로 교체
import sqlalchemy
sqlalchemy.create_engine = MagicMock(return_value=MagicMock())

# opentelemetry / prometheus: C 라이브러리(grpcio 등) 필요하므로 mock 처리
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
