"""E2E tests: auth flow (register → login → me → logout)."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_register_login_me_flow(client: AsyncClient):
    """Full auth lifecycle against a real database."""
    phone = f"139{uuid.uuid4().hex[:8]}"
    username = f"auth_{uuid.uuid4().hex[:8]}"
    password = "Secure12345"

    # --- Register ---
    resp = await client.post("/api/auth/register", json={
        "phone": phone,
        "username": username,
        "password": password,
        "confirmPassword": password,
        "captcha": "123456",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["username"] == username
    assert body["data"]["phone"] == phone

    # --- Login ---
    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    token = body["data"]["accessToken"]
    assert token
    assert body["data"]["expiresIn"] > 0

    # --- Me ---
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["username"] == username
    assert body["data"]["phone"] == phone

    # --- Logout ---
    resp = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


@pytest.mark.anyio
async def test_login_wrong_password(client: AsyncClient):
    """Login with wrong password returns 401-equivalent error."""
    phone = f"137{uuid.uuid4().hex[:8]}"
    username = f"badpw_{uuid.uuid4().hex[:8]}"

    await client.post("/api/auth/register", json={
        "phone": phone, "username": username,
        "password": "Correct123", "confirmPassword": "Correct123", "captcha": "123456",
    })

    resp = await client.post("/api/auth/login", json={
        "username": username, "password": "Wrong12345",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 40101


@pytest.mark.anyio
async def test_register_duplicate_username(client: AsyncClient):
    """Registering the same username twice returns 409."""
    phone = f"136{uuid.uuid4().hex[:8]}"
    username = f"dup_{uuid.uuid4().hex[:8]}"

    payload = {
        "phone": phone, "username": username,
        "password": "Test123456", "confirmPassword": "Test123456", "captcha": "123456",
    }
    resp1 = await client.post("/api/auth/register", json=payload)
    assert resp1.json()["code"] == 0

    resp2 = await client.post("/api/auth/register", json={**payload, "phone": f"135{uuid.uuid4().hex[:8]}"})
    assert resp2.json()["code"] == 40901


@pytest.mark.anyio
async def test_me_without_token_returns_401(client: AsyncClient):
    """GET /auth/me without token returns 401."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["code"] == 40101
