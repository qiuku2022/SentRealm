"""Load local development environment variables (ADR-005)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    """Load repo-root `.env` when present; existing process env takes precedence."""
    load_dotenv(Path.cwd() / ".env")
