"""User lookups."""

from __future__ import annotations


def fetch_user(user_id: int) -> dict:
    """Return the user record for `user_id`."""
    return {"id": user_id, "name": f"user{user_id}"}
