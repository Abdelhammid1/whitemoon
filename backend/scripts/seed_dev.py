"""Dev seed entrypoint — run from backend/ with the venv active.

    python scripts/seed_dev.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `app` importable when invoked as a script.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from app import create_app  # noqa: E402
from app.accounting import seed as accounting_seed  # noqa: E402
from app.identity import seed as identity_seed  # noqa: E402


def main() -> None:
    app = create_app()
    with app.app_context():
        identity_seed.run()
        accounting_seed.run()
        from app.sales.services import credit as credit_svc
        from app.sales.services import deferred_pricing as deferred_svc

        credit_svc.seed_tier_settings()
        deferred_svc.seed_defaults()
        from app.extensions import db

        db.session.commit()


if __name__ == "__main__":
    main()
