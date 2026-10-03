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
from app.identity import seed  # noqa: E402


def main() -> None:
    app = create_app()
    with app.app_context():
        seed.run()


if __name__ == "__main__":
    main()
