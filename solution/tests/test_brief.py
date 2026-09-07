import json
import subprocess
import sys
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
    assert result["backend"] == "mock"
    assert result["cost_summary"] == tools.get_cost_summary()
    assert result["department_ranking"]["unallocated_quantity"] == 90
    assert result["leading_department_models"]["department_filter"] == "AI Lab"
    assert result["run_rate_scenario"]["scenario_only"] is True
    assert result["run_rate_scenario"]["projected_month_end_amount"] == 448.8
    assert result["seat_inventory"] == seats_before == tools.list_seats()
    assert result["budget_review"] == budgets_before == tools.list_budgets()
    assert tools.list_action_plans() == []
    assert tools.get_audit_log()["events"] == []


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
    assert brief["cost_summary"]["net_quantity"] == 4760
    assert brief["budget_review"]["budgets"][0]["remaining_amount"] == 34.8
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
