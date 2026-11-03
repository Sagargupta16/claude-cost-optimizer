"""Command line entry point."""

from __future__ import annotations

import sys

from users import fetch_user


def main(argv: list[str]) -> None:
    print(fetch_user(int(argv[1]))["name"])


if __name__ == "__main__":
    main(sys.argv)
