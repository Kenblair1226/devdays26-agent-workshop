"""Re-simulate September usage and synchronize the bundled teaching fixtures."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

SNAPSHOT = datetime(2026, 9, 22, 23, 59, 59, tzinfo=UTC)
MONTH_START = SNAPSHOT.date().replace(day=1)
MODEL_RATES = {
    "gpt-5.4": Decimal("0.01"),
    "gpt-5-mini": Decimal("0.006"),
    "claude-opus-5": Decimal("0.012"),
}
MONTHLY_SAMPLES = (
    ("alice", "gpt-5.4", 530, 0),
    ("bob", "gpt-5-mini", 270, 40),
    ("carol", "gpt-5.4", 1400, 0),
    ("dave", "claude-opus-5", 1000, 100),
    ("erin", "gpt-5-mini", 420, 0),
    ("frank", "gpt-5-mini", 280, 0),
    ("grace", "gpt-5.4", 650, 0),
    ("heidi", "gpt-5-mini", 120, 0),
)


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _allocate(quantity: int, weights: list[int]) -> list[int]:
    # Five-credit units keep every synthetic model's daily amounts in whole cents.
    if quantity < 0 or quantity % 5 or not weights or min(weights) <= 0:
        raise ValueError("Allocation needs non-negative five-credit units and weights")
    units = quantity // 5
    weight_sum = sum(weights)
    allocations = [units * weight // weight_sum for weight in weights]
    remainder_order = sorted(
        range(len(weights)),
        key=lambda index: (-(units * weights[index] % weight_sum), index),
    )
    for index in remainder_order[: units - sum(allocations)]:
        allocations[index] += 1
    return [amount * 5 for amount in allocations]


def _item(
    day: date, user: str, model: str, net: int, discount: int = 0
) -> dict[str, Any]:
    price = MODEL_RATES[model]
    return {
        "date": day.isoformat(),
        "user": user,
        "product": "copilot",
        "sku": "ai_credits",
        "model": model,
        "unit_type": "AI credits",
        "price_per_unit": float(price),
        "gross_quantity": net + discount,
        "gross_amount": float(price * (net + discount)),
        "discount_quantity": discount,
        "discount_amount": float(price * discount),
        "net_quantity": net,
        "net_amount": float(price * net),
    }


def build_usage_report() -> dict[str, Any]:
    dates = [MONTH_START + timedelta(days=offset) for offset in range(SNAPSHOT.day)]
    weekday_weights = (6, 7, 8, 6, 5, 1, 1)
    items = [_item(date(2026, 8, 31), "carol", "gpt-5.4", 300)]
    for phase, (user, model, net, discount) in enumerate(MONTHLY_SAMPLES):
        weights = [
            weekday_weights[day.weekday()] * (4 + (day.day + phase) % 4)
            for day in dates
        ]
        for day, net_part, discount_part in zip(
            dates, _allocate(net, weights), _allocate(discount, weights), strict=True
        ):
            if net_part + discount_part:
                items.append(_item(day, user, model, net_part, discount_part))
    items.extend(
        [
            _item(date(2026, 9, 2), "ivan", "gpt-5-mini", 50),
            _item(date(2026, 9, 21), "ivan", "gpt-5-mini", 40),
        ]
    )
    return {
        "time_period": {"year": SNAPSHOT.year, "month": SNAPSHOT.month},
        "organization": "octo-demo",
        "as_of": _timestamp(SNAPSHOT),
        "currency": "USD",
        "coverage": {
            "start": (SNAPSHOT.date() - timedelta(days=27)).isoformat(),
            "end": SNAPSHOT.date().isoformat(),
            "kind": "sparse_training_samples",
        },
        "usage_items": sorted(items, key=lambda item: (item["date"], item["user"])),
    }


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def _shift_activity(records: list[dict[str, Any]], offset: timedelta) -> None:
    for record in records:
        if record["last_activity_at"] is not None:
            record["last_activity_at"] = _timestamp(
                datetime.fromisoformat(record["last_activity_at"]) + offset
            )


def build_fixture_files(data_dir: Path) -> dict[str, str]:
    old_usage = json.loads((data_dir / "ai-credit-usage.json").read_text("utf-8"))
    old_snapshot = datetime.fromisoformat(old_usage["as_of"])
    files = {"ai-credit-usage.json": _json_text(build_usage_report())}
    for name in ("seats.json", "budgets.json", "department-mapping.json"):
        document = json.loads((data_dir / name).read_text("utf-8"))
        if name == "seats.json":
            _shift_activity(
                document["seats"],
                SNAPSHOT - datetime.fromisoformat(document["as_of"]),
            )
        document["as_of"] = _timestamp(SNAPSHOT)
        files[name] = _json_text(document)
    metrics = [
        json.loads(line)
        for line in (data_dir / "users-28-day.ndjson").read_text("utf-8").splitlines()
        if line.strip()
    ]
    _shift_activity(metrics, SNAPSHOT - old_snapshot)
    files["users-28-day.ndjson"] = "".join(
        json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
        for row in metrics
    )
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Check all fixture copies without writing"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    files = build_fixture_files(root / "data")
    mismatches = []
    for directory in (
        root / "data",
        root / "solution" / "data",
        root / "starter" / "data",
    ):
        for name, text in files.items():
            path = directory / name
            if args.check:
                if not path.is_file() or path.read_text("utf-8") != text:
                    mismatches.append(str(path.relative_to(root)))
            else:
                path.write_text(text, encoding="utf-8", newline="\n")
    if mismatches:
        parser.exit(1, "Synthetic fixtures differ:\n" + "\n".join(mismatches) + "\n")
    print(
        "Synthetic workshop fixtures are current."
        if args.check
        else "Fixtures updated."
    )


if __name__ == "__main__":
    main()
