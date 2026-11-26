"""Tests for user registration and login."""

from __future__ import annotations


def test_register_creates_account_and_logs_in(client):
    response = client.post(
        "/register",
        data={
            "email": "new.user@students.fhnw.ch",
            "password": "secret12",
            "password_confirm": "secret12",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/")
    assert "lostfound_session" in response.cookies


def test_register_rejects_non_fhnw_email(client):
    response = client.post(
        "/register",
        data={
            "email": "someone@gmail.com",
            "password": "secret12",
            "password_confirm": "secret12",
        },
    )
    assert response.status_code == 422


def test_register_rejects_password_mismatch(client):
    response = client.post(
        "/register",
        data={
            "email": "another@students.fhnw.ch",
            "password": "secret12",
            "password_confirm": "different",
        },
    )
    assert response.status_code == 422
    assert b"do not match" in response.content.lower()


def test_register_rejects_duplicate_email(client):
    data = {
        "email": "dup@students.fhnw.ch",
        "password": "secret12",
        "password_confirm": "secret12",
    }
    first = client.post("/register", data=data, follow_redirects=False)
    assert first.status_code == 303

    second = client.post("/register", data=data)
    assert second.status_code == 409
    assert b"already exists" in second.content.lower()


def test_login_with_registered_user(client):
    client.post(
        "/register",
        data={
            "email": "login.me@students.fhnw.ch",
            "password": "secret12",
            "password_confirm": "secret12",
        },
        follow_redirects=False,
    )
    client.post("/logout", follow_redirects=False)

    response = client.post(
        "/login",
        data={
            "email": "login.me@students.fhnw.ch",
            "password": "secret12",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "lostfound_session" in response.cookies


def test_login_rejects_wrong_password(client):
    client.post(
        "/register",
        data={
            "email": "wrong.pass@students.fhnw.ch",
            "password": "secret12",
            "password_confirm": "secret12",
        },
        follow_redirects=False,
    )
    client.post("/logout", follow_redirects=False)

    response = client.post(
        "/login",
        data={
            "email": "wrong.pass@students.fhnw.ch",
            "password": "nope",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=" in response.headers.get("location", "")


def test_demo_user_can_login(client):
    response = client.post(
        "/login",
        data={
            "email": "john.smith@students.fhnw.ch",
            "password": "1234",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "lostfound_session" in response.cookies


def test_register_page_renders(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Create account" in response.content