import importlib.util
import json
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from test_cli import process_environment

from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.tools import FinOpsToolbox

ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def generator():
    spec = importlib.util.spec_from_file_location(
        "workshop_data_generator", ROOT / "scripts" / "generate_workshop_data.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_daily_samples_cover_every_day_through_september_22() -> None:
    client = MockGitHubFinOpsClient()
    items = client.get_usage_items()
    september = [item for item in items if item.date >= date(2026, 9, 1)]
    assert len(september) == 86
    assert {item.date for item in september} == {
        date(2026, 9, 1) + timedelta(days=offset) for offset in range(22)
    }
    assert max(item.date for item in items) == date(2026, 9, 22)
    assert len({(item.date, item.user, item.model) for item in items}) == len(items)
    for item in items:
        price = Decimal(str(item.price_per_unit))
        for quantity, amount in (
            ("gross_quantity", "gross_amount"),
            ("discount_quantity", "discount_amount"),
            ("net_quantity", "net_amount"),
        ):
            difference = Decimal(str(getattr(item, quantity))) * price - Decimal(
                str(getattr(item, amount))
            )
            assert abs(difference) <= Decimal("0.00000001")
    by_day = defaultdict(Decimal)
    for item in september:
        by_day[item.date] += Decimal(str(item.net_amount))
    assert sum(by_day.values()).quantize(Decimal(".01")) == Decimal("329.12")
    for day in range(1, 22):
        assert by_day[date(2026, 9, day)] == by_day[date(2026, 9, (day - 1) % 3 + 1)]
    assert by_day[date(2026, 9, 22)].quantize(Decimal(".01")) == Decimal("14.96")


def test_original_three_day_totals_are_scaled_by_twenty_two_over_three() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    baseline = tools.get_cost_summary("custom", "2026-09-01", "2026-09-03")
    current = tools.get_cost_summary()
    original = {
        "gross_quantity": 4900,
        "discount_quantity": 140,
        "net_quantity": 4760,
        "gross_amount": 46.32,
        "discount_amount": 1.44,
        "net_amount": 44.88,
    }
    for field, expected in original.items():
        assert baseline[field] == expected
        scaled = (Decimal(str(expected)) * 22 / 3).quantize(
            Decimal(".01"), ROUND_HALF_UP
        )
        assert Decimal(str(current[field])) == scaled
    assert current["net_quantity"] == 34906.67
    assert current["net_amount"] == 329.12
    assert current["record_count"] == 86


@pytest.mark.parametrize("dimension", ["user", "model"])
def test_every_user_and_model_is_scaled_without_rounding_early(dimension) -> None:
    records = MockGitHubFinOpsClient().get_usage_items()
    baseline = defaultdict(lambda: defaultdict(Decimal))
    extended = defaultdict(lambda: defaultdict(Decimal))
    for item in records:
        if item.date < date(2026, 9, 1):
            continue
        key = getattr(item, dimension)
        for field in (
            "gross_quantity",
            "discount_quantity",
            "net_quantity",
            "gross_amount",
            "discount_amount",
            "net_amount",
        ):
            value = Decimal(str(getattr(item, field)))
            extended[key][field] += value
            if item.date <= date(2026, 9, 3):
                baseline[key][field] += value
    assert baseline.keys() == extended.keys()
    for key, fields in baseline.items():
        for field, value in fields.items():
            assert abs(extended[key][field] - value * 22 / 3) <= Decimal("0.0000001"), (
                dimension,
                key,
                field,
            )


def test_all_snapshot_dates_and_relative_activity_are_consistent() -> None:
    client = MockGitHubFinOpsClient()
    snapshot = "2026-09-22T23:59:59Z"
    for path in (ROOT / "data").glob("*.json"):
        assert json.loads(path.read_text("utf-8"))["as_of"] == snapshot, path.name
    assert client.user_metrics_metadata["period"] == {
        "label": "last_28_days",
        "start": "2026-08-26",
        "end": "2026-09-22",
    }
    seats = {seat["user"]: seat for seat in client.list_seats()}
    assert seats["ivan"]["last_activity_at"] == "2026-08-31T07:45:00Z"
    assert seats["heidi"]["last_activity_at"] == "2026-09-13T08:11:00Z"
    assert seats["judy"]["last_activity_at"] is None
    assert (
        sum(
            item.net_quantity
            for item in client.get_usage_items()
            if item.user == "ivan" and item.date.month == 9
        )
        == 660
    )
    for metric in client.get_user_metrics():
        assert 0 <= metric.total_active_days <= 28
        if metric.last_activity_at is not None:
            assert datetime.fromisoformat(
                metric.last_activity_at
            ) <= datetime.fromisoformat(snapshot)
    profile = FinOpsToolbox(client).break_down_usage("user")
    carol = next(item for item in profile["items"] if item["user"] == "carol")
    assert carol["net_quantity"] == 10266.67
    assert carol["net_amount"] == 102.67
    carol_metric = next(
        metric for metric in client.get_user_metrics() if metric.user == "carol"
    )
    assert carol_metric.ai_credits_used == 13066.67
    assert carol_metric.total_active_days == 22


def test_fixture_generator_is_current_and_read_only_in_check_mode() -> None:
    paths = [
        path
        for directory in (
            ROOT / "data",
            ROOT / "solution" / "data",
            ROOT / "starter" / "data",
        )
        for path in directory.iterdir()
        if path.suffix in {".json", ".ndjson"}
    ]
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            str(ROOT / "scripts" / "generate_workshop_data.py"),
            "--check",
        ],
        cwd=ROOT,
        env=process_environment(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths
    } == before


def test_regeneration_preserves_staleness_and_is_idempotent(
    generator, tmp_path
) -> None:
    expected = generator.build_fixture_files(ROOT / "data")
    offset = timedelta(days=19)
    old_snapshot = "2026-09-03T23:59:59Z"
    for name, content in expected.items():
        if name.endswith(".ndjson"):
            records = [json.loads(line) for line in content.splitlines()]
            generator._shift_activity(records, -offset)
            content = "".join(json.dumps(row) + "\n" for row in records)
        else:
            value = json.loads(content)
            value["as_of"] = old_snapshot
            if name == "seats.json":
                generator._shift_activity(value["seats"], -offset)
            content = json.dumps(value)
        (tmp_path / name).write_text(content, encoding="utf-8")
    assert generator.build_fixture_files(tmp_path) == expected
    for name, content in expected.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    assert generator.build_fixture_files(tmp_path) == expected
    assert generator.SNAPSHOT == datetime(2026, 9, 22, 23, 59, 59, tzinfo=UTC)


def test_partial_cycle_keeps_fractional_credits_and_balanced_rows(generator) -> None:
    report = generator.build_usage_report()
    last_day = [row for row in report["usage_items"] if row["date"] == "2026-09-22"]
    assert len(last_day) == 9
    assert any(not row["net_quantity"].is_integer() for row in last_day)
    for row in last_day:
        for unit in ("quantity", "amount"):
            assert Decimal(str(row[f"gross_{unit}"])) - Decimal(
                str(row[f"discount_{unit}"])
            ) == Decimal(str(row[f"net_{unit}"]))
