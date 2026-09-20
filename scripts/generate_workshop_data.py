"""Extend the three-day usage baseline and generate synthetic workshop evidence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

SNAPSHOT = datetime(2026, 9, 22, 23, 59, 59, tzinfo=UTC)
MONTH_START = SNAPSHOT.date().replace(day=1)
COMPARISON_START = date(2026, 8, 1)
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
WORKFLOW_OUTCOMES = {
    "alice": ("simple-maintenance", 40, 40),
    "bob": ("lightweight-checks", 20, 20),
    "carol": ("migration", 100, 40),
    "dave": ("migration", 100, 40),
    "erin": ("mobile-assistance", 20, 20),
    "frank": ("mobile-assistance", 20, 20),
    "grace": ("automated-review", 20, 20),
    "heidi": ("automated-review", 10, 10),
    "ivan": ("support-triage", 10, 10),
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


def _evidence_header(source: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "organization": "octo-demo",
        "as_of": _timestamp(SNAPSHOT),
        "source": f"Synthetic fictional workshop evidence: {source}",
    }


def _period(start: date, end: date) -> dict[str, str]:
    return {"start": start.isoformat(), "end": end.isoformat()}


def _current_usage_items(usage: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in usage["usage_items"]
        if MONTH_START.isoformat() <= item["date"] <= SNAPSHOT.date().isoformat()
    ]


def build_usage_comparison(usage: dict[str, Any]) -> dict[str, Any]:
    factors = {
        "carol": Decimal("0.4"),
        "dave": Decimal("0.4"),
        "grace": Decimal("0.5"),
        "heidi": Decimal("0.5"),
    }
    items = []
    for item in _current_usage_items(usage):
        baseline_item = dict(item)
        baseline_item["date"] = (
            date.fromisoformat(item["date"])
            .replace(year=COMPARISON_START.year, month=COMPARISON_START.month)
            .isoformat()
        )
        factor = factors.get(item["user"], Decimal(1))
        for field in (
            "gross_quantity",
            "gross_amount",
            "discount_quantity",
            "discount_amount",
            "net_quantity",
            "net_amount",
        ):
            baseline_item[field] = float(
                (Decimal(str(item[field])) * factor).quantize(
                    RAW_PRECISION, ROUND_HALF_UP
                )
            )
        items.append(baseline_item)
    baseline_snapshot = SNAPSHOT.replace(
        year=COMPARISON_START.year, month=COMPARISON_START.month
    )
    return {
        **_evidence_header(
            "matched 22-day comparison derived from the September usage rows, "
            "not a full prior-month invoice or observed historical usage."
        ),
        "current_period": _period(MONTH_START, SNAPSHOT.date()),
        "baseline": {
            "as_of": _timestamp(baseline_snapshot),
            "period": _period(COMPARISON_START, baseline_snapshot.date()),
            "usage_items": items,
            "limitations": [
                "Fictional matched comparison for 2026-08-01 through 2026-08-22 only.",
                (
                    "AI Lab quantities and amounts are 0.4 times September; Security "
                    "quantities and amounts are 0.5 times September; others are unchanged."
                ),
                (
                    "Models and unit prices are unchanged; scaled quantities and amounts "
                    "are independently rounded to eight decimal places."
                ),
            ],
        },
        "limitations": [
            (
                "The 2026-08-31 billing sample is excluded. This separate comparison "
                "does not extend the billing fixture's sparse prior-month coverage."
            ),
            (
                "Both periods are fictional teaching data, not complete historical "
                "invoices or evidence of real organizational performance."
            ),
        ],
    }


def build_team_roster() -> dict[str, Any]:
    return {
        **_evidence_header("team membership and task plans as of 2026-09-22."),
        "teams": [
            {
                "department": "AI Lab",
                "members": ["carol", "dave"],
                "initiative": "Legacy platform migration",
                "success_definition": "One migration batch passes regression checks",
                "deadline": "2026-09-30",
                "planned_remaining_tasks": [
                    {"user": "carol", "workflow": "migration", "count": 60},
                    {"user": "dave", "workflow": "migration", "count": 30},
                ],
            },
            {
                "department": "Platform Engineering",
                "members": ["alice", "bob"],
                "initiative": "Platform service maintenance",
                "success_definition": (
                    "One maintenance task or lightweight check passes regression checks"
                ),
                "deadline": None,
                "planned_remaining_tasks": [],
            },
            {
                "department": "Security",
                "members": ["grace", "heidi"],
                "initiative": "Automated pull request review",
                "success_definition": (
                    "One automated review artifact per pull request revision"
                ),
                "deadline": None,
                "planned_remaining_tasks": [],
            },
            {
                "department": "Mobile",
                "members": ["erin", "frank"],
                "initiative": "Mobile application maintenance",
                "success_definition": (
                    "One mobile-assistance task passes acceptance checks"
                ),
                "deadline": None,
                "planned_remaining_tasks": [],
            },
        ],
        "limitations": [
            "All teams, initiatives, deadlines and task counts are fictional.",
            (
                "Remaining tasks are plans as of 2026-09-22, not spend approvals or "
                "delivery commitments."
            ),
            (
                "Independent human and compliance reviews are separate from automated "
                "review artifacts and are not candidates for removal."
            ),
            "Users absent from this roster require separate accounting attribution.",
        ],
    }


def _raw_ticks(value: float) -> int:
    return int(Decimal(str(value)) / RAW_PRECISION)


def _allocate_outcomes(items: list[dict[str, Any]], count: int) -> list[int]:
    remaining = count - len(items)
    if remaining < 0:
        raise ValueError("Each positive usage row needs at least one unique outcome")
    weights = [_raw_ticks(item["net_quantity"]) for item in items]
    total_weight = sum(weights)
    shares = [divmod(remaining * weight, total_weight) for weight in weights]
    counts = [1 + quotient for quotient, _remainder in shares]
    ranked = sorted(range(len(items)), key=lambda index: (-shares[index][1], index))
    for index in ranked[: count - sum(counts)]:
        counts[index] += 1
    return counts


def _split_raw(value: float, count: int) -> list[float]:
    quotient, remainder = divmod(_raw_ticks(value), count)
    return [
        float(Decimal(quotient + (index < remainder)) * RAW_PRECISION)
        for index in range(count)
    ]


def build_workflow_runs(
    usage: dict[str, Any],
    comparison: dict[str, Any],
    roster: dict[str, Any],
) -> dict[str, Any]:
    departments = {
        member: team["department"]
        for team in roster["teams"]
        for member in team["members"]
    }
    departments["ivan"] = "Unallocated"
    runs = []
    minutes_by_date: dict[str, int] = {}
    for period, items in (
        ("current", _current_usage_items(usage)),
        ("baseline", comparison["baseline"]["usage_items"]),
    ):
        for user in sorted({item["user"] for item in items}):
            workflow, current_count, baseline_count = WORKFLOW_OUTCOMES[user]
            count = current_count if period == "current" else baseline_count
            user_items = sorted(
                (
                    item
                    for item in items
                    if item["user"] == user and item["net_quantity"] > 0
                ),
                key=lambda item: (item["date"], item["model"]),
            )
            if workflow == "automated-review":
                triggers = (
                    ("pull_request", "push")
                    if period == "current"
                    else ("pull_request",)
                )
            else:
                triggers = (
                    "scheduled" if workflow == "lightweight-checks" else "manual",
                )
            task_number = 0
            for item, outcome_count in zip(
                user_items, _allocate_outcomes(user_items, count), strict=True
            ):
                run_count = outcome_count * len(triggers)
                quantities = _split_raw(item["net_quantity"], run_count)
                amounts = _split_raw(item["net_amount"], run_count)
                for task_index in range(outcome_count):
                    task_number += 1
                    identity = f"{period}-{user}-{task_number:03d}"
                    for attempt, trigger in enumerate(triggers):
                        run_index = task_index * len(triggers) + attempt
                        minute = minutes_by_date.get(item["date"], 0)
                        started_at = datetime.fromisoformat(item["date"]).replace(
                            hour=9, tzinfo=UTC
                        ) + timedelta(minutes=minute)
                        minutes_by_date[item["date"]] = minute + 1
                        runs.append(
                            {
                                "run_id": f"synthetic-run-{identity}-{attempt + 1}",
                                "period": period,
                                "date": item["date"],
                                "started_at": _timestamp(started_at),
                                "user": user,
                                "department": departments[user],
                                "workflow": workflow,
                                "task_id": f"synthetic-task-{identity}",
                                "input_revision": f"synthetic-input-{identity}-v1",
                                "result_digest": f"synthetic-result-{identity}-passed",
                                "trigger": trigger,
                                "status": "success",
                                "model": item["model"],
                                "net_quantity": quantities[run_index],
                                "net_amount": amounts[run_index],
                            }
                        )
    return {
        **_evidence_header(
            "deterministic workflow runs allocated from each period's billing rows; "
            "not real run telemetry."
        ),
        "periods": {
            "current": dict(comparison["current_period"]),
            "baseline": dict(comparison["baseline"]["period"]),
        },
        "runs": sorted(
            runs, key=lambda run: (run["date"], run["started_at"], run["run_id"])
        ),
        "limitations": [
            (
                "All run IDs, tasks, input revisions, result digests and timestamps are "
                "fictional. No real execution or measured outcome is claimed."
            ),
            (
                "Quantities and amounts are allocated in 0.00000001 units within each "
                "period/date/user/model, not independently measured per-run costs."
            ),
            (
                "Successful outcome identity is (workflow, task_id, input_revision); "
                "repeated results also require matching result_digest."
            ),
            (
                "Security evidence covers automated review artifacts only; independent "
                "human and compliance reviews remain separate requirements."
            ),
        ],
    }


def build_model_pilots() -> dict[str, Any]:
    return {
        **_evidence_header(
            "controlled model experiment for 2026-09-01 through 2026-09-22, "
            "separate from organization billing."
        ),
        "pilots": [
            {
                "id": "platform-simple-20",
                "department": "Platform Engineering",
                "workflow": "simple-maintenance",
                "baseline_model": "gpt-5.4",
                "candidate_model": "gpt-5-mini",
                "sample_tasks": 20,
                "baseline_successful_tasks": 20,
                "candidate_successful_tasks": 20,
                "baseline_net_amount": 2.0,
                "candidate_net_amount": 1.2,
                "currency": "USD",
                "quality_gate": (
                    "Both models passed the same regression checks on the same "
                    "20 tasks; all 20 passed for each model. This small synthetic "
                    "controlled pilot is not production proof."
                ),
                "limitations": [
                    "The same 20 tasks were evaluated with each model.",
                    (
                        "The monetary ratio applies only to representative tasks with "
                        "equal quality; it is not a raw-token savings claim."
                    ),
                    (
                        "Any broader model pilot requires its own regression and quality "
                        "gates before changing production model selection."
                    ),
                ],
            }
        ],
        "limitations": [
            "Fictional controlled experiment, not evidence of production quality.",
            (
                "Pilot amounts are a separate experiment sample, not additional "
                "organization billing, and must never be added to month-to-date usage."
            ),
        ],
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
    usage = build_usage_report()
    files = {"ai-credit-usage.json": _json_text(usage)}
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
    comparison = build_usage_comparison(usage)
    roster = build_team_roster()
    files.update(
        {
            "usage-comparison.json": _json_text(comparison),
            "team-roster.json": _json_text(roster),
            "workflow-runs.json": _json_text(
                build_workflow_runs(usage, comparison, roster)
            ),
            "model-pilots.json": _json_text(build_model_pilots()),
        }
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
