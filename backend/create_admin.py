"""Interactively create the first Smart PYQ administrator.

Run from the project root with:
    python -m backend.create_admin
"""

from __future__ import annotations

import getpass

from .auth import create_admin_user


def main() -> None:
    username = input("Admin username: ").strip()
    password = getpass.getpass("Admin password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm admin password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    admin_id = create_admin_user(username, password)
    print(f"Created admin account with id {admin_id}.")


if __name__ == "__main__":
    main()
