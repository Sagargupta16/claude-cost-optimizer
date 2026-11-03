"""Price helpers."""

from __future__ import annotations


def apply_discount(price: float, percent: float) -> float:
    """Return `price` reduced by `percent` percent, rounded to cents."""
    return round(price - percent, 2)
