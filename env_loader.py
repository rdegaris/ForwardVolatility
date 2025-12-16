from __future__ import annotations

import os
from pathlib import Path


def _load_env_file(path: Path) -> bool:
    """Load KEY=VALUE lines into os.environ (no overrides).

    Lightweight .env reader to support Task Scheduler / .bat / direct script runs.
    """
    if not path.exists() or not path.is_file():
        return False

    loaded_any = False
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key:
                continue
            if key in os.environ and (os.environ.get(key) or "").strip():
                continue
            os.environ[key] = value
            loaded_any = True
    except Exception:
        return False

    return loaded_any


def load_env(script_file: str | Path) -> None:
    """Attempt to load `.secrets.env` / `.env` near the given script."""
    script_path = Path(script_file).resolve()
    script_dir = script_path.parent

    # Try current dir, then parent (useful when launched from a different cwd).
    candidates = [
        script_dir / ".secrets.env",
        script_dir / ".env",
        script_dir.parent / ".secrets.env",
        script_dir.parent / ".env",
    ]

    for candidate in candidates:
        _load_env_file(candidate)
