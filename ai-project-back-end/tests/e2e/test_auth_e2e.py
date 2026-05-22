from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from helpers import assert_success, unique_phone


def test_register_login_me_logout_flow(client: TestClient) -> None:
    suffix = uuid.uuid4().hex[:10]
    username = f"auth_{suffix}"
    password = "Test123456"

    register_resp = client.post(
        "/api/auth/register",
        json={
            "phone": unique_phone("138"),
            "username": username,
            "password": password,
            "confirmPassword": password,
            "captcha": "123456",
        },
    )
    assert register_resp.status_code == 200
    register_data = assert_success(register_resp.json())
    assert register_data["username"] == username

    login_resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert login_resp.status_code == 200
    login_data = assert_success(login_resp.json())
    token = login_data["accessToken"]

    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = assert_success(me_resp.json())
    assert me_data["userId"] == register_data["userId"]
    assert me_data["username"] == username
    assert me_data["tenantId"]

    logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200
    assert_success(logout_resp.json())


def test_login_rejects_wrong_password(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"username": "missing-user", "password": "wrong"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 40101
    assert body["data"] is None
