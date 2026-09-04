#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
import json

from backend.services.pilot_report import generate_pilot_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the read-only morning-loop pilot report")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--date-from", required=True, type=date.fromisoformat)
    parser.add_argument("--date-to", required=True, type=date.fromisoformat)
    parser.add_argument("--timezone")
    args = parser.parse_args()
    report = generate_pilot_report(
        user_id=args.user_id,
        date_from=args.date_from,
        date_to=args.date_to,
        timezone=args.timezone,
    )
    print(json.dumps(report, default=str, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
