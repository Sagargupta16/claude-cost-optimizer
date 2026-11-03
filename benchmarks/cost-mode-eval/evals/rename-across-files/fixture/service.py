"""Greeting service."""

from __future__ import annotations

from users import fetch_user


def greeting(user_id: int) -> str:
    user = fetch_user(user_id)
    return f"Hello, {user['name']}"
