"""Extend the original three-day usage baseline and synchronize teaching fixtures."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

SNAPSHOT = datetime(2026, 9, 22, 23, 59, 59, tzinfo=UTC)
MONTH_START = SNAPSHOT.date().replace(day=1)
BASELINE_DAYS = 3
SCALE_FACTOR = Decimal(SNAPSHOT.day) / BASELINE_DAYS
RAW_PRECISION = Decimal("0.00000001")
DISPLAY_PRECISION = Decimal("0.01")
MODEL_RATES = {
    "gpt-5.4": Decimal("0.01"),
    "gpt-5-mini": Decimal("0.006"),
    "claude-opus-5": Decimal("0.012"),
}
BASELINE_SAMPLES = (
    (1, "alice", "gpt-5.4", 320, 0),
    (2, "alice", "gpt-5.4", 210, 0),
    (3, "bob", "gpt-5-mini", 270, 40),
    (1, "carol", "gpt-5.4", 850, 0),
    (2, "carol", "gpt-5.4", 550, 0),
    (3, "dave", "claude-opus-5", 1000, 100),
    (1, "erin", "gpt-5-mini", 420, 0),
    (2, "frank", "gpt-5-mini", 280, 0),
    (1, "grace", "gpt-5.4", 650, 0),
    (3, "heidi", "gpt-5-mini", 120, 0),
    (2, "ivan", "gpt-5-mini", 90, 0),
)
BASELINE_BUDGETS = {
    "budget-org-ai": (80, Decimal("45.20")),
    "budget-user-carol": (20, Decimal(14)),
}


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _baseline_totals() -> dict[tuple[str, str], tuple[int, int]]:
    totals: dict[tuple[str, str], tuple[int, int]] = {}
    for _day, user, model, net, discount in BASELINE_SAMPLES:
        previous_net, previous_discount = totals.get((user, model), (0, 0))
        totals[user, model] = (previous_net + net, previous_discount + discount)
    return totals


def _item(
    day: date,
    user: str,
    model: str,
    net: int | Decimal,
    discount: int | Decimal = 0,
) -> dict[str, Any]:
    price = MODEL_RATES[model]
    net_quantity = Decimal(net).quantize(RAW_PRECISION, ROUND_HALF_UP)
    discount_quantity = Decimal(discount).quantize(RAW_PRECISION, ROUND_HALF_UP)
    net_amount = (price * net_quantity).quantize(RAW_PRECISION, ROUND_HALF_UP)
    discount_amount = (price * discount_quantity).quantize(RAW_PRECISION, ROUND_HALF_UP)
    return {
        "date": day.isoformat(),
        "user": user,
        "product": "copilot",
        "sku": "ai_credits",
        "model": model,
        "unit_type": "AI credits",
        "price_per_unit": float(price),
        "gross_quantity": float(net_quantity + discount_quantity),
        "gross_amount": float(net_amount + discount_amount),
        "discount_quantity": float(discount_quantity),
        "discount_amount": float(discount_amount),
        "net_quantity": float(net_quantity),
        "net_amount": float(net_amount),
    }


def build_usage_report() -> dict[str, Any]:
    items = [_item(date(2026, 8, 31), "carol", "gpt-5.4", 300)]
    complete_cycles, remaining_days = divmod(SNAPSHOT.day, BASELINE_DAYS)
    for cycle in range(complete_cycles):
        for day, user, model, net, discount in BASELINE_SAMPLES:
            simulated_date = MONTH_START + timedelta(
                days=cycle * BASELINE_DAYS + day - 1
            )
            items.append(_item(simulated_date, user, model, net, discount))
    for offset in range(remaining_days):
        simulated_date = MONTH_START + timedelta(
            days=complete_cycles * BASELINE_DAYS + offset
        )
        for (user, model), (net, discount) in _baseline_totals().items():
            items.append(
                _item(
                    simulated_date,
                    user,
                    model,
                    Decimal(net) / BASELINE_DAYS,
                    Decimal(discount) / BASELINE_DAYS,
                )
            )
    return {
        "time_period": {"year": SNAPSHOT.year, "month": SNAPSHOT.month},
        "organization": "octo-demo",
        "as_of": _timestamp(SNAPSHOT),
        "currency": "USD",
        "simulation_basis": {
            "baseline_start": MONTH_START.isoformat(),
            "baseline_end": (
                MONTH_START + timedelta(days=BASELINE_DAYS - 1)
            ).isoformat(),
            "scale_numerator": SNAPSHOT.day,
            "scale_denominator": BASELINE_DAYS,
            "method": (
                "Repeat the original three-day pattern for complete cycles; use "
                "each user/model's three-day average for remaining days. Synthetic "
                "linear extrapolation, not measured usage or a validated forecast."
            ),
            "precision_note": (
                "Raw quantities and amounts retain eight decimal places; "
                "display totals are rounded after aggregation."
            ),
        },
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
        elif name == "budgets.json":
            for budget in document["budgets"]:
                baseline_limit, baseline_consumed = BASELINE_BUDGETS[budget["id"]]
                # Whole-dollar teaching caps round up to the next USD 50.
                budget["budget_amount"] = int(
                    (Decimal(baseline_limit) * SCALE_FACTOR / 50).to_integral_value(
                        rounding=ROUND_CEILING
                    )
                    * 50
                )
                budget["consumed_amount"] = float(
                    (baseline_consumed * SCALE_FACTOR).quantize(
                        DISPLAY_PRECISION, ROUND_HALF_UP
                    )
                )
        document["as_of"] = _timestamp(SNAPSHOT)
        files[name] = _json_text(document)
    metrics = [
        json.loads(line)
        for line in (data_dir / "users-28-day.ndjson").read_text("utf-8").splitlines()
        if line.strip()
    ]
    _shift_activity(metrics, SNAPSHOT - old_snapshot)
    baseline_credits = {"judy": 0}
    for (user, _model), (net, _discount) in _baseline_totals().items():
        baseline_credits[user] = baseline_credits.get(user, 0) + net
    for metric in metrics:
        metric["ai_credits_used"] = float(
            (Decimal(baseline_credits[metric["user"]]) * 28 / BASELINE_DAYS).quantize(
                DISPLAY_PRECISION, ROUND_HALF_UP
            )
        )
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
