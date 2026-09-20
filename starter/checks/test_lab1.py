from finops_agent.brief import build_analysis_brief
from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.tools import FinOpsToolbox


def test_lab1_department_ranking_checkpoint() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())

    result = tools.rank_department_consumption()

    assert result["ranking"], "Lab 1 needs department evidence"
    assert result["ranking"][0]["department"] == "AI Lab"
    assert result["ranking"][0]["net_quantity"] == 17600
    assert result["unallocated_quantity"] == 660
    assert result["ranking"][0]["net_amount"] == 190.67
    assert result["ranking"][0]["user_count"] == 2
    assert result["period"]["start"] == "2026-09-01"
    assert result["as_of"] == "2026-09-22T23:59:59Z"
    assert result["period"]["end"] == "2026-09-22"
    assert round(sum(row["net_quantity"] for row in result["ranking"]), 2) == 34906.67
    assert tools.rank_department_consumption(limit=1)["unallocated_quantity"] == 660


def test_lab1_brief_supports_cost_seat_and_budget_investigation() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    brief = build_analysis_brief(tools)
    assert brief["schema_version"] == 2
    assert brief["cost_summary"]["net_amount"] == 329.12
    assert len(brief["daily_usage"]["items"]) == 22
    assert brief["daily_usage"]["items"][-1]["date"] == "2026-09-22"
    assert brief["daily_usage"]["missing_dates"] == []
    assert brief["leading_department_models"]["department_filter"] == "AI Lab"
    budgets = {budget["id"]: budget for budget in brief["budget_review"]["budgets"]}
    assert budgets["budget-user-carol"]["remaining_amount"] == 47.33
    assert budgets["budget-org-ai"]["remaining_amount"] == 268.53
    users = {row["user"]: row for row in brief["user_breakdown"]["items"]}
    assert users["ivan"]["net_quantity"] == 660
    seats = {seat["user"]: seat for seat in brief["seat_inventory"]["seats"]}
    assert seats["judy"]["last_activity_at"] is None
    assert tools.get_audit_log()["events"] == []


def test_lab1_checks_workload_before_choosing_an_improvement() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    trend = tools.get_daily_usage_trend()
    assert trend["change"]["credits_percent"] == 62.18
    migration = tools.get_workflow_evidence("AI Lab")
    assert migration["current"]["summary"]["successful_tasks"] == 200
    assert migration["baseline"]["summary"]["successful_tasks"] == 80
    assert (
        migration["current"]["summary"]["cost_per_successful_task_usd"]
        == migration["baseline"]["summary"]["cost_per_successful_task_usd"]
    )
    review = tools.get_workflow_evidence("Security")
    assert review["current"]["summary"]["successful_tasks"] == 30
    assert review["current"]["summary"]["duplicate_success_candidates"] == 30
    options = tools.compare_improvement_options()
    assert {option["id"] for option in options["options"]} == {
        "deduplicate_triggers",
        "simple_task_model",
        "temporary_budget",
    }
    assert tools.forecast_budget(600)["projected_month_end_quantity"] == 47600
    assert tools.list_action_plans() == []
    assert tools.get_audit_log()["events"] == []
