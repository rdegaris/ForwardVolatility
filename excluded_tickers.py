from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ExcludedTickers:
    """JSON-backed persistent exclude list for tickers that IB cannot qualify.

    Structure on disk (v1):
      {
        "version": 1,
        "updated_at": "...",
        "tickers": {
          "ABC": {"reason": "...", "source": "...", "first_seen": "...", "last_seen": "...", "count": 3}
        }
      }
    """

    def __init__(
        self,
        path: str,
        *,
        enabled: bool = True,
        autosave: bool = True,
        min_seconds_between_saves: float = 2.0,
    ) -> None:
        self.path = path
        self.enabled = enabled
        self.autosave = autosave
        self.min_seconds_between_saves = float(min_seconds_between_saves)

        self._data: Dict[str, Any] = {
            "version": 1,
            "updated_at": _utc_now_iso(),
            "tickers": {},
        }
        self._dirty = False
        self._last_save_ts = 0.0

        if self.enabled:
            self.load()

    def load(self) -> None:
        if not self.enabled:
            return

        try:
            if not os.path.exists(self.path):
                return
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict) and isinstance(loaded.get("tickers"), dict):
                self._data = loaded
        except Exception:
            # If the file is corrupt or unreadable, do not break the scan.
            return

    def is_excluded(self, ticker: str) -> bool:
        if not self.enabled:
            return False
        if not ticker:
            return False
        return ticker.upper() in self._data.get("tickers", {})

    def get_record(self, ticker: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        return self._data.get("tickers", {}).get(ticker.upper())

    def add(self, ticker: str, *, reason: str, source: str) -> bool:
        """Add/update a ticker exclusion.

        Returns True if this call changed stored data.
        """
        if not self.enabled:
            return False
        if not ticker:
            return False

        ticker_u = ticker.upper()
        tickers = self._data.setdefault("tickers", {})
        now = _utc_now_iso()

        existing = tickers.get(ticker_u)
        if existing is None:
            tickers[ticker_u] = {
                "reason": str(reason)[:500],
                "source": str(source)[:80],
                "first_seen": now,
                "last_seen": now,
                "count": 1,
            }
            changed = True
        else:
            existing["last_seen"] = now
            existing["count"] = int(existing.get("count", 0) or 0) + 1
            # Keep the first reason/source for traceability, but update if blank.
            if not existing.get("reason") and reason:
                existing["reason"] = str(reason)[:500]
            if not existing.get("source") and source:
                existing["source"] = str(source)[:80]
            changed = True

        if changed:
            self._data["updated_at"] = now
            self._dirty = True
            if self.autosave:
                self.save_if_needed()
        return changed

    def save_if_needed(self, *, force: bool = False) -> None:
        if not self.enabled:
            return
        if not self._dirty and not force:
            return

        now_ts = time.time()
        if not force and (now_ts - self._last_save_ts) < self.min_seconds_between_saves:
            return

        self._atomic_write_json(self.path, self._data)
        self._dirty = False
        self._last_save_ts = now_ts

    @staticmethod
    def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        os.replace(tmp, path)
