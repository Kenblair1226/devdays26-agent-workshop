import asyncio
import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from copilot.tools import ToolInvocation
from test_cli import process_environment

from finops_agent.analytics import FinOpsAnalyzer
from finops_agent.brief import build_analysis_brief
from finops_agent.budget_demo import BudgetDemo
from finops_agent.clients import MockGitHubFinOpsClient, RealGitHubFinOpsClient
from finops_agent.investigation import WorkflowRun, _run_summary
from finops_agent.models import ReportingPeriod
from finops_agent.sdk_tools import build_sdk_tools
from finops_agent.tools import FinOpsToolbox


@pytest.fixture
def tools():
    return FinOpsToolbox(MockGitHubFinOpsClient())


@pytest.fixture
def case_data(tools, monkeypatch):
    original = tools.client.get_investigation_fixture

    def mutate(name, change):
        def load(requested):
            data = original(requested)
            if requested == name:
                change(data)
            return data

        monkeypatch.setattr(tools.client, "get_investigation_fixture", load)

    return mutate


def test_case_evidence_is_loaded_only_when_requested(tools, monkeypatch):
    read = tools.client.get_investigation_fixture
    loaded = []

    def record(name):
        loaded.append(name)
        return read(name)

    monkeypatch.setattr(tools.client, "get_investigation_fixture", record)
    build_sdk_tools(tools)
    brief = build_analysis_brief(tools)
    assert loaded == []
    assert "investigation_evidence" not in brief
    tools.get_daily_usage_trend()
    assert loaded == ["usage-comparison"]
    loaded.clear()
    tools.get_team_roster("AI Lab")
    assert loaded == ["team-roster"]
    loaded.clear()
    tools.get_workflow_evidence("Security")
    assert set(loaded) == {"workflow-runs", "usage-comparison"}


@pytest.mark.parametrize("name", ["../.env", "unknown", "ai-credit-usage"])
def test_case_fixture_names_cannot_access_arbitrary_files(tools, name):
    with pytest.raises(ValueError, match="unsupported workshop evidence"):
        tools.client.get_investigation_fixture(name)


def test_trend_compares_equal_windows_without_revealing_business_context(tools):
    result = tools.get_daily_usage_trend()
    assert result["current"]["period"]["start"] == "2026-09-01"
    assert result["current"]["period"]["end"] == "2026-09-22"
    assert result["baseline"]["period"]["start"] == "2026-08-01"
    assert result["baseline"]["period"]["end"] == "2026-08-22"
    assert result["baseline"]["as_of"] == "2026-08-22T23:59:59Z"
    assert len(result["current"]["items"]) == len(result["baseline"]["items"]) == 22
    assert result["current_summary"]["net_quantity"] == 34906.67
    assert result["baseline_summary"]["net_quantity"] == 21523.33
    assert result["change"] == {
        "net_quantity": 13383.33,
        "net_amount": 140.87,
        "credits_percent": 62.18,
        "amount_percent": 74.83,
    }
    drivers = result["department_changes"]
    assert [row["department"] for row in drivers[:2]] == ["AI Lab", "Security"]
    assert drivers[0]["credit_change"] == 10560
    assert drivers[1]["credit_change"] == 2823.33
    assert drivers[1]["amount_change"] == 26.47
    assert "migration" not in json.dumps(result).lower()
    assert "duplicate" not in json.dumps(result).lower()
    with pytest.raises(ValueError, match="unavailable"):
        tools.get_cost_summary("previous_month")


def test_migration_growth_tracks_successful_work_not_unit_cost_regression(tools):
    roster = tools.get_team_roster("ai lab")
    assert roster["team"]["members"] == ["carol", "dave"]
    assert "migration" in roster["team"]["initiative"].lower()
    result = tools.get_workflow_evidence("AI Lab", limit=2)
    current = result["current"]["summary"]
    previous = result["baseline"]["summary"]
    assert current["successful_tasks"] == 200
    assert previous["successful_tasks"] == 80
    assert current["net_quantity"] / previous["net_quantity"] == 2.5
    assert current["successful_tasks"] / previous["successful_tasks"] == 2.5
    assert (
        current["cost_per_successful_task_usd"]
        == previous["cost_per_successful_task_usd"]
        == 0.953333
    )
    assert (
        current["credits_per_successful_task"]
        == previous["credits_per_successful_task"]
        == 88
    )
    assert current["duplicate_success_candidates"] == 0
    assert result["current"]["truncated"] is True
    assert result["current"]["returned_runs"] == len(result["current"]["runs"]) == 2
    assert result["current"]["total_runs"] == 200
    assert "all validated runs" in result["current"]["summary_scope"]
    assert "alice" not in json.dumps(result)


def test_security_has_more_attempts_without_more_successful_outcomes(tools):
    result = tools.get_workflow_evidence("Security", limit=2)
    current = result["current"]["summary"]
    previous = result["baseline"]["summary"]
    assert current["run_count"] == 60
    assert previous["run_count"] == 30
    assert current["successful_tasks"] == previous["successful_tasks"] == 30
    assert current["duplicate_success_candidates"] == 30
    assert previous["duplicate_success_candidates"] == 0
    assert current["duplicate_candidate_amount"] == 26.47
    assert current["duplicate_candidate_credits"] == 2823.33
    first, duplicate = result["current"]["runs"]
    assert first["run_id"] != duplicate["run_id"]
    for field in ("workflow", "task_id", "input_revision", "result_digest", "model"):
        assert first[field] == duplicate[field]
    assert {first["trigger"], duplicate["trigger"]} == {"pull_request", "push"}


def a_run():
    return WorkflowRun(
        run_id="original",
        period="current",
        date=date(2026, 9, 1),
        started_at=datetime(2026, 9, 1, tzinfo=UTC),
        user="grace",
        department="Security",
        workflow="automated-review",
        task_id="pr-1",
        input_revision="rev-1",
        result_digest="artifact-1",
        trigger="pull_request",
        status="success",
        model="gpt-5.4",
        net_quantity=100,
        net_amount=1,
    )


@pytest.mark.parametrize(
    "change",
    [
        {"input_revision": "rev-2"},
        {"task_id": "pr-2"},
        {"workflow": "independent-compliance-review"},
        {"model": "another-model"},
        {"result_digest": "different-artifact"},
        {"status": "failure", "result_digest": None},
    ],
)
def test_retries_new_inputs_and_independent_work_are_not_duplicate_savings(change):
    first = a_run()
    second = replace(
        first,
        run_id="second",
        started_at=first.started_at + timedelta(seconds=1),
        **change,
    )
    assert _run_summary([first, second])["duplicate_success_candidates"] == 0


def test_failed_attempt_followed_by_success_is_not_a_duplicate():
    first = replace(a_run(), status="failure", result_digest=None)
    retry = replace(
        a_run(), run_id="retry", started_at=first.started_at + timedelta(seconds=1)
    )
    summary = _run_summary([first, retry])
    assert summary["successful_tasks"] == 1
    assert summary["successful_attempts"] == 1
    assert summary["net_amount"] == 2
    assert summary["duplicate_candidate_amount"] == 0
    failed = _run_summary([first])
    assert failed["cost_per_successful_task_usd"] is None


@pytest.mark.parametrize("department", ["unknown", "Unallocated", "", 42])
def test_unknown_team_context_is_unavailable_not_zero(tools, department):
    with pytest.raises(ValueError):
        tools.get_team_roster(department)
    with pytest.raises(ValueError):
        tools.get_workflow_evidence(department)


@pytest.mark.parametrize("limit", [0, 21, True, 2.5, "6"])
def test_workflow_sample_limit_is_validated(tools, limit):
    with pytest.raises(ValueError, match="1 to 20"):
        tools.get_workflow_evidence("AI Lab", limit)


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("schema_version", 2, "schema"),
        ("organization", "other-org", "organization"),
        ("as_of", "2026-09-21T23:59:59Z", "snapshot"),
    ],
)
def test_context_snapshots_cannot_be_mixed(tools, case_data, field, value, match):
    case_data("team-roster", lambda data: data.update({field: value}))
    with pytest.raises(ValueError, match=match):
        tools.get_team_roster("AI Lab")


def test_roster_members_must_match_financial_mapping(tools, case_data):
    def change(data):
        row = next(team for team in data["teams"] if team["department"] == "AI Lab")
        row["members"] = ["carol", "alice"]

    case_data("team-roster", change)
    with pytest.raises(ValueError, match="conflicts"):
        tools.get_team_roster("AI Lab")


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda data: data["runs"].append(dict(data["runs"][0])), "IDs"),
        (lambda data: data["runs"][0].update(net_amount=999), "reconcile"),
        (lambda data: data["runs"][0].update(net_quantity=-1), "non-negative"),
        (lambda data: data["runs"][0].update(department="other-team"), "mapping"),
        (lambda data: data["runs"][0].update(date="2099-01-01"), "period"),
    ],
)
def test_invalid_workflow_evidence_fails_before_any_savings_claim(
    tools, case_data, change, match
):
    case_data("workflow-runs", change)
    with pytest.raises(ValueError, match=match):
        tools.get_workflow_evidence("Security")


def test_comparison_requires_a_matched_earlier_window(tools, case_data):
    def change(data):
        data["baseline"]["period"]["start"] = "2026-08-02"

    case_data("usage-comparison", change)
    with pytest.raises(ValueError, match="equal-length"):
        tools.get_daily_usage_trend()


def test_options_separate_counterfactual_savings_future_savings_and_headroom(tools):
    budgets = tools.list_budgets()
    result = tools.compare_improvement_options()
    options = {option["id"]: option for option in result["options"]}
    duplicate = options["deduplicate_triggers"]
    assert duplicate["observed_period_opportunity_usd"] == 26.47
    assert duplicate["remaining_month_savings_usd"] == 9.63
    assert duplicate["remaining_month_credit_savings"] == 1026.67
    routing = options["simple_task_model"]
    assert routing["observed_period_opportunity_usd"] == 15.55
    assert routing["remaining_month_savings_usd"] == 5.65
    assert routing["quality_gate_passed"] is True
    assert routing["estimated_credit_savings"] is None
    budget = options["temporary_budget"]
    assert budget["current_limit_usd"] == 150
    assert budget["proposed_limit_usd"] == 220
    assert budget["additional_headroom_usd"] == 70
    assert budget["remaining_migration_tasks"] == 60
    assert budget["estimated_remaining_work_cost_usd"] == 61.6
    assert budget["projected_user_spend_usd"] == 164.27
    assert budget["proposed_limit_covers_plan"] is True
    assert budget["projected_gap_at_current_limit_usd"] == 14.27
    assert budget["review_or_expiry_date"] == "2026-09-30"
    assert budget["estimated_savings_usd"] == 0
    assert result["remaining_period"] == {
        "start": "2026-09-23",
        "end": "2026-09-30",
        "days": 8,
    }
    assert result["combination"]["remaining_month_savings_usd"] == 15.28
    assert result["combination"]["disjoint_scopes"] is True
    assert tools.list_budgets() == budgets
    assert tools.list_action_plans() == []
    assert tools.get_audit_log()["events"] == []


@pytest.mark.parametrize("sku", ["license-based-example", "premium_requests"])
def test_budget_option_requires_matching_budget_units_and_sku(tools, sku):
    tools.client._budgets[1].update(budget_type="SkuPricing", budget_product_sku=sku)
    with pytest.raises(ValueError, match="monetary AI-credit budget"):
        tools.compare_improvement_options()


@pytest.mark.parametrize(
    "change,status",
    [
        ({"candidate_successful_tasks": 19}, "quality_gate_failed"),
        ({"candidate_net_amount": 3}, "not_cheaper"),
    ],
)
def test_model_savings_are_not_claimed_when_quality_or_cost_gate_fails(
    tools, case_data, change, status
):
    case_data("model-pilots", lambda data: data["pilots"][0].update(change))
    options = tools.compare_improvement_options()
    routing = next(
        row for row in options["options"] if row["id"] == "simple_task_model"
    )
    assert routing["estimate_status"] == status
    assert routing["observed_period_opportunity_usd"] is None
    assert routing["remaining_month_savings_usd"] is None
    assert options["combination"]["remaining_month_savings_usd"] is None


def test_investigation_export_is_explicit_and_preserves_core_schema(tools):
    brief = build_analysis_brief(tools, include_investigation=True)
    evidence = brief["investigation_evidence"]
    assert brief["schema_version"] == 2
    assert len(evidence["teams"]) == len(evidence["workflows"]) == 3
    assert evidence["daily_comparison"]["change"]["credits_percent"] == 62.18
    assert len(evidence["options"]["options"]) == 3
    assert brief["run_rate_scenario"]["projected_month_end_quantity"] == 47600
    assert brief["run_rate_scenario"]["projected_month_end_amount"] == 448.8


def test_context_tool_registry_does_not_expand_personal_or_real_access(tools):
    names = {tool.name for tool in build_sdk_tools(tools)}
    context = {
        "get_daily_usage_trend",
        "get_team_roster",
        "get_workflow_evidence",
        "compare_improvement_options",
    }
    assert context <= names
    assert {tool.name for tool in BudgetDemo(tools).user_tools()} == {
        "get_my_costs",
        "get_my_savings",
        "request_budget_increase",
    }
    real = FinOpsToolbox(RealGitHubFinOpsClient("org", "synthetic-token"))
    assert not context & {tool.name for tool in build_sdk_tools(real)}
    with pytest.raises(ValueError, match="mock-only"):
        real.get_daily_usage_trend()


def test_sdk_arguments_cannot_smuggle_identity_or_approval(tools):
    registry = {tool.name: tool for tool in build_sdk_tools(tools)}

    async def run():
        result = await registry["get_workflow_evidence"].handler(
            ToolInvocation(arguments={"department": "Security", "limit": 2})
        )
        assert result.result_type == "success"
        assert (
            json.loads(result.text_result_for_llm)["current"]["summary"][
                "successful_tasks"
            ]
            == 30
        )
        rejected = await registry["compare_improvement_options"].handler(
            ToolInvocation(arguments={"confirmed": True, "user": "admin"})
        )
        assert rejected.result_type == "failure"

    asyncio.run(run())
    assert tools.list_action_plans() == []


def test_daily_usage_never_invents_dates_from_period_aggregates():
    row = MockGitHubFinOpsClient().get_usage_items()[0]
    period = ReportingPeriod(date(2026, 9, 1), date(2026, 9, 22), "month_to_date")
    record = replace(row, date=None, period=period)
    analyzer = FinOpsAnalyzer([record], [], as_of=None)
    with pytest.raises(ValueError, match="daily usage is unavailable"):
        analyzer.daily_usage(period)


@pytest.mark.parametrize(
    "arguments,key",
    [
        (["trend"], "department_changes"),
        (["roster", "AI Lab"], "team"),
        (["workflows", "Security", "--limit", "2"], "current"),
        (["options"], "options"),
        (
            ["breakdown", "--dimension", "model", "--department", "AI Lab"],
            "department_filter",
        ),
        (["brief", "--include-investigation"], "investigation_evidence"),
    ],
)
@pytest.mark.parametrize("project", ["solution", "starter"])
def test_ready_made_investigation_cli_needs_no_sdk_or_cloud(arguments, key, project):
    root = Path(__file__).parents[2] / project
    env = process_environment()
    env.update(PYTHONPATH=str(root / "src"), FINOPS_BACKEND="mock")
    result = subprocess.run(
        [sys.executable, "-S", "-m", "finops_agent", *arguments],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert key in json.loads(result.stdout)


@pytest.mark.parametrize("command", ["trend", "roster", "workflows", "options"])
def test_case_cli_rejects_real_backend_even_with_instructor_flag(command):
    root = Path(__file__).parents[1]
    env = process_environment()
    env.update(PYTHONPATH=str(root / "src"), FINOPS_BACKEND="github")
    arguments = [command, "AI Lab"] if command in {"roster", "workflows"} else [command]
    result = subprocess.run(
        [sys.executable, "-S", "-m", "finops_agent", "--instructor", *arguments],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "mock-only" in result.stderr
