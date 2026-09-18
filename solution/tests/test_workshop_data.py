import importlib.util
import json
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
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
    assert len(september) == 164
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
            assert Decimal(str(getattr(item, quantity))) * price == Decimal(
                str(getattr(item, amount))
            )
    by_day = defaultdict(Decimal)
    for item in september:
        by_day[item.date] += Decimal(str(item.net_amount))
    assert sum(by_day.values()) == Decimal("44.88")
    assert len(set(by_day.values())) >= 10
    weekends = [value for day, value in by_day.items() if day.weekday() >= 5]
    weekdays = [value for day, value in by_day.items() if day.weekday() < 5]
    assert sum(weekends) / len(weekends) < sum(weekdays) / len(weekdays)


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
        == 90
    )
    for metric in client.get_user_metrics():
        assert 0 <= metric.total_active_days <= 28
        if metric.last_activity_at is not None:
            assert datetime.fromisoformat(
                metric.last_activity_at
            ) <= datetime.fromisoformat(snapshot)
    profile = FinOpsToolbox(client).break_down_usage("user")
    carol = next(item for item in profile["items"] if item["user"] == "carol")
    assert carol["net_quantity"] == 1400
    assert carol["net_amount"] == 14


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


@pytest.mark.parametrize("quantity", [0, 5, 40, 100, 1400])
def test_allocation_preserves_exact_synthetic_totals(generator, quantity) -> None:
    values = generator._allocate(quantity, [5, 1, 4, 2])
    assert sum(values) == quantity
    assert all(value >= 0 and value % 5 == 0 for value in values)
