from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.effectiveness import refresh_tracking_detection_prices


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh tracking returns and target closes in tracking.db")
    parser.add_argument(
        "--config",
        default="config/default.yaml",
        help="Path to merged config yaml (default: config/default.yaml)",
    )
    parser.add_argument(
        "--trade-date",
        default=None,
        help="Optional trade date (YYYY-MM-DD). Defaults to today.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = refresh_tracking_detection_prices(
        args.config,
        trade_date=args.trade_date,
    )
    print(json.dumps(asdict(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
