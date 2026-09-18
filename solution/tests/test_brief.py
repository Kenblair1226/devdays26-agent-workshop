import json
import subprocess
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from test_cli import process_environment

from finops_agent.brief import build_analysis_brief
from finops_agent.clients import MockGitHubFinOpsClient, RealGitHubFinOpsClient
from finops_agent.tools import FinOpsToolbox


def test_brief_reuses_tool_evidence_without_mutations() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    seats_before = tools.list_seats()
    budgets_before = tools.list_budgets()
    result = build_analysis_brief(tools)
    assert result["schema_version"] == 2
    assert result["backend"] == "mock"
    assert result["cost_summary"] == tools.get_cost_summary()
    assert result["department_ranking"]["unallocated_quantity"] == 660
    assert result["leading_department_models"]["department_filter"] == "AI Lab"
    assert result["run_rate_scenario"]["scenario_only"] is True
    assert result["run_rate_scenario"]["budget_amount"] == 600
    assert result["run_rate_scenario"]["projected_month_end_amount"] == 448.8
    assert result["seat_inventory"] == seats_before == tools.list_seats()
    assert result["budget_review"] == budgets_before == tools.list_budgets()
    assert tools.list_action_plans() == []
    assert tools.get_audit_log()["events"] == []


def test_brief_daily_samples_reconcile_with_dashboard_totals() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    result = build_analysis_brief(tools)
    trend = result["daily_usage"]
    summary = result["cost_summary"]
    assert trend["period"] == {
        "start": "2026-09-01",
        "end": "2026-09-22",
        "label": "month_to_date",
    }
    assert trend["as_of"] == summary["as_of"] == "2026-09-22T23:59:59Z"
    assert trend["currency"] == "USD"
    assert trend["unit"] == "AI credits"
    assert trend["source"] == summary["source"]
    assert trend["coverage"] == summary["coverage"]
    assert trend["granularity"] == "daily_samples"
    assert trend["missing_dates"] == []
    assert [row["date"] for row in trend["items"]] == [
        (date(2026, 9, 1) + timedelta(days=offset)).isoformat() for offset in range(22)
    ]
    assert len({row["net_amount"] for row in trend["items"]}) == 4
    assert trend["rounding_note"] == summary["rounding_note"]
    for field in ("net_quantity", "net_amount"):
        expected = Decimal(str(summary[field]))
        assert sum(Decimal(str(row[field])) for row in trend["items"]) == expected
    assert result["budget_review"]["budgets"][0]["consumed_amount"] == 331.47
    assert result["run_rate_scenario"]["consumed_amount"] == 329.12


def test_independently_rounded_breakdowns_do_not_replace_overall_totals() -> None:
    result = build_analysis_brief(FinOpsToolbox(MockGitHubFinOpsClient()))
    summary = result["cost_summary"]
    assert summary["net_quantity"] == 34906.67
    assert summary["net_amount"] == 329.12
    assert "Independently rounded rows" in summary["rounding_note"]
    expected_row_sums = (
        (result["department_ranking"]["ranking"], "34906.67", "329.13"),
        (result["model_breakdown"]["items"], "34906.66", "329.12"),
        (result["user_breakdown"]["items"], "34906.67", "329.13"),
    )
    for rows, quantity, amount in expected_row_sums:
        assert sum(Decimal(str(row["net_quantity"])) for row in rows) == Decimal(
            quantity
        )
        assert sum(Decimal(str(row["net_amount"])) for row in rows) == Decimal(amount)
    for key in ("model_breakdown", "user_breakdown"):
        assert result[key]["total_net_quantity"] == summary["net_quantity"]
        assert result[key]["total_net_amount"] == summary["net_amount"]


def test_brief_trend_omits_and_labels_missing_days_instead_of_zero(monkeypatch) -> None:
    client = MockGitHubFinOpsClient()
    records = [
        item for item in client.get_usage_items() if item.date != date(2026, 9, 10)
    ]
    monkeypatch.setattr(client, "get_usage_items", lambda: records)
    result = build_analysis_brief(FinOpsToolbox(client))
    trend = result["daily_usage"]
    assert trend["missing_dates"] == ["2026-09-10"]
    assert len(trend["items"]) == 21
    assert "2026-09-10" not in {item["date"] for item in trend["items"]}
    assert any(
        "missing days are not observed zeros" in note for note in trend["limitations"]
    )
    assert sum(Decimal(str(row["net_amount"])) for row in trend["items"]) == (
        Decimal(str(result["cost_summary"]["net_amount"]))
    )


def test_brief_rejects_real_backend_without_loading_any_data(monkeypatch) -> None:
    client = RealGitHubFinOpsClient("octo-demo", "test-token")

    def unexpected_read():
        pytest.fail("brief attempted a real backend read")

    monkeypatch.setattr(client, "get_usage_items", unexpected_read)
    with pytest.raises(ValueError, match="mock"):
        build_analysis_brief(FinOpsToolbox(client))


@pytest.mark.parametrize("project", ["starter", "solution"])
def test_brief_cli_exports_usable_utf8_without_sdk_or_credentials(
    project, tmp_path
) -> None:
    root = Path(__file__).parents[2]
    env = process_environment()
    env["PYTHONPATH"] = str(root / project / "src")
    env["FINOPS_BACKEND"] = "mock"
    output = tmp_path / "workshop-output" / "lab1-evidence.json"
    command = [
        sys.executable,
        "-S",
        "-m",
        "finops_agent",
        "brief",
        "--output",
        str(output),
    ]
    result = subprocess.run(
        command, cwd=root, env=env, capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stdout + result.stderr
    content = output.read_bytes()
    assert not content.startswith(b"\xef\xbb\xbf")
    brief = json.loads(content.decode("utf-8"))
    assert brief["schema_version"] == 2
    assert brief["cost_summary"]["net_quantity"] == 34906.67
    assert brief["daily_usage"]["items"][-1]["date"] == "2026-09-22"
    assert len(brief["daily_usage"]["items"]) == 22
    assert brief["budget_review"]["budgets"][0]["remaining_amount"] == 268.53
    second = subprocess.run(
        command, cwd=root, env=env, capture_output=True, text=True, timeout=20
    )
    assert second.returncode != 0
    assert "FileExistsError" in second.stderr
    assert output.read_bytes() == content


def test_brief_cli_cannot_export_a_real_org_even_with_instructor_flag() -> None:
    root = Path(__file__).parents[2]
    env = process_environment()
    env["PYTHONPATH"] = str(root / "solution" / "src")
    env["FINOPS_BACKEND"] = "github"
    result = subprocess.run(
        [sys.executable, "-S", "-m", "finops_agent", "--instructor", "brief"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode != 0
    assert "brief is mock-only" in result.stderr
