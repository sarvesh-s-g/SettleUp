from sqlalchemy import text

from app.database import engine


def test_register_success_hides_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Sarvesh", "email": "Sarvesh@Example.com", "password": "Password@123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "sarvesh@example.com"  # normalised to lowercase
    assert "password" not in body and "password_hash" not in body


def test_password_is_stored_hashed(client):
    client.post("/api/v1/auth/register", json={"name": "A", "email": "a@example.com", "password": "Password@123"})
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT password_hash FROM users WHERE email = 'a@example.com'")).scalar_one()
    assert stored != "Password@123"
    assert stored.startswith("$2b$")  # bcrypt format


def test_duplicate_email_is_rejected(client):
    body = {"name": "Rahul", "email": "rahul@example.com", "password": "Password@123"}
    assert client.post("/api/v1/auth/register", json=body).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json={**body, "email": "RAHUL@example.com"})
    assert duplicate.status_code == 409


def test_register_validation_errors(client):
    bad_email = client.post("/api/v1/auth/register", json={"name": "X", "email": "not-an-email", "password": "Password@123"})
    short_password = client.post("/api/v1/auth/register", json={"name": "X", "email": "x@example.com", "password": "Tiny7z"})
    blank_name = client.post("/api/v1/auth/register", json={"name": "   ", "email": "y@example.com", "password": "Password@123"})
    assert bad_email.status_code == 422
    assert short_password.status_code == 422
    assert blank_name.status_code == 422
    # The error must not echo the submitted password back to the client.
    assert "Tiny7z" not in short_password.text
    assert short_password.json()["detail"][0]["loc"] == ["body", "password"]


def test_login_success_and_me(client, make_user):
    user = make_user("Kiran")
    me = client.get("/api/v1/auth/me", headers=user["headers"])
    assert me.status_code == 200
    assert me.json()["email"] == "kiran@example.com"


def test_login_wrong_password(client, make_user):
    make_user("Aman")
    response = client.post("/api/v1/auth/login", json={"email": "aman@example.com", "password": "WrongPass123"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_unknown_email_gives_same_error(client):
    response = client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "Password@123"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/groups").status_code == 401
    assert client.get("/api/v1/dashboard").status_code == 401


def test_invalid_or_tampered_token_is_rejected(client, make_user):
    user = make_user("Sarvesh")
    token = user["headers"]["Authorization"].split()[1]
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_expired_token_is_rejected(client, make_user):
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.config import settings

    user = make_user("Sarvesh")
    expired = jwt.encode(
        {"sub": str(user["id"]), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
