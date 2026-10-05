"""Dev bootstrap seed.

Idempotent — safe to re-run. Seeds, in order:
  1. RBAC roles + permissions and a bootstrap `admin.high` user
     (credentials from BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD).
  2. The chart of accounts and the event→journal map.

Run against a database that already has the schema applied
(`alembic upgrade head`). Usage, from the repo root:

    python scripts/seed_dev.py
"""

from __future__ import annotations

import pathlib
import sys

# Make the backend package importable regardless of the current directory.
_BACKEND = pathlib.Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app import create_app
from app.accounting import seed as accounting_seed
from app.identity import seed as identity_seed


def main() -> None:
    app = create_app()
    with app.app_context():
        identity_seed.run()
        accounting_seed.run()
    print("Dev seed complete.")


if __name__ == "__main__":
    main()
