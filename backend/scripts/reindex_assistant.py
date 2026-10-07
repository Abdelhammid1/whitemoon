"""Rebuild the Admin Assistant knowledge base (ticket §7).

    python scripts/reindex_assistant.py [git_sha]

Run after a successful deployment (wired into CI/CD — see docs/22-assistant.md).
Indexing + secret-scanning happen locally; nothing is sent externally here.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from app import create_app  # noqa: E402
from app.assistant.services import indexer  # noqa: E402


def main() -> None:
    git_sha = sys.argv[1] if len(sys.argv) > 1 else os.getenv("GIT_SHA")
    app = create_app()
    with app.app_context():
        stats = indexer.reindex(git_sha=git_sha)
    print(
        f"Assistant index v{stats.version} ready: "
        f"{stats.doc_count} docs, {stats.chunk_count} chunks, "
        f"{stats.skipped_secret} skipped (secrets), "
        f"{'DEGRADED (fallback embeddings)' if stats.degraded else 'embeddings OK'}."
    )


if __name__ == "__main__":
    main()
