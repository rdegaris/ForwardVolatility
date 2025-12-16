from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from env_loader import load_env
from earnings_checker import EarningsChecker


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def _save_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)


def _enrich_opportunities(payload: Dict[str, Any], checker: EarningsChecker) -> int:
    opps = payload.get('opportunities')
    if not isinstance(opps, list):
        return 0

    updated = 0
    for opp in opps:
        if not isinstance(opp, dict):
            continue
        ticker = opp.get('ticker')
        if not isinstance(ticker, str) or not ticker.strip():
            continue

        existing = opp.get('next_earnings')
        if isinstance(existing, str) and existing.strip():
            continue

        dte2 = opp.get('dte2')
        try:
            dte2_int = int(dte2) if dte2 is not None else 0
        except Exception:
            dte2_int = 0

        days_ahead = max(180, dte2_int + 14)
        dt = checker.get_earnings_date(ticker.strip().upper(), days_ahead=days_ahead)
        if dt:
            opp['next_earnings'] = dt.strftime('%Y-%m-%d')
            updated += 1

    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description='Enrich scan results JSON with next earnings dates.')
    parser.add_argument('files', nargs='*', help='Result JSON files to update (in-place).')
    args = parser.parse_args()

    # Ensure secrets are available for Finnhub in scheduler/direct runs.
    load_env(__file__)

    files = [Path(p) for p in (args.files or [])]
    if not files:
        files = [
            Path('nasdaq100_results_latest.json'),
            Path('midcap400_results_latest.json'),
        ]

    checker = EarningsChecker()

    total_updates = 0
    for path in files:
        if not path.exists():
            print(f'Skipping missing: {path}')
            continue

        payload = _load_json(path)
        updated = _enrich_opportunities(payload, checker)
        if updated:
            _save_json(path, payload)
        total_updates += updated
        print(f'{path}: updated {updated}')

    print(f'Total updated: {total_updates}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
