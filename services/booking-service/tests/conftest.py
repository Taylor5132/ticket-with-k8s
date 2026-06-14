import pytest
import jwt

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
