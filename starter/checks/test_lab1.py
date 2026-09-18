from finops_agent.brief import build_analysis_brief
from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.tools import FinOpsToolbox


def test_lab1_department_ranking_checkpoint() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())

    result = tools.rank_department_consumption()

    assert result["ranking"], "Lab 1 needs department evidence"
    assert result["ranking"][0]["department"] == "AI Lab"
    assert result["ranking"][0]["net_quantity"] == 2400
    assert result["unallocated_quantity"] == 90
    assert result["ranking"][0]["net_amount"] == 26
    assert result["ranking"][0]["user_count"] == 2
    assert result["period"]["start"] == "2026-09-01"
    assert result["as_of"] == "2026-09-22T23:59:59Z"
    assert result["period"]["end"] == "2026-09-22"
    assert sum(row["net_quantity"] for row in result["ranking"]) == 4760
    assert tools.rank_department_consumption(limit=1)["unallocated_quantity"] == 90


def test_lab1_brief_supports_cost_seat_and_budget_investigation() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    brief = build_analysis_brief(tools)
    assert brief["schema_version"] == 2
    assert brief["cost_summary"]["net_amount"] == 44.88
    assert len(brief["daily_usage"]["items"]) == 22
    assert brief["daily_usage"]["items"][-1]["date"] == "2026-09-22"
    assert brief["daily_usage"]["missing_dates"] == []
    assert brief["leading_department_models"]["department_filter"] == "AI Lab"
    budgets = {budget["id"]: budget for budget in brief["budget_review"]["budgets"]}
    assert budgets["budget-user-carol"]["remaining_amount"] == 6
    assert budgets["budget-org-ai"]["remaining_amount"] == 34.8
    users = {row["user"]: row for row in brief["user_breakdown"]["items"]}
    assert users["ivan"]["net_quantity"] == 90
    seats = {seat["user"]: seat for seat in brief["seat_inventory"]["seats"]}
    assert seats["judy"]["last_activity_at"] is None
    assert tools.get_audit_log()["events"] == []
