from __future__ import annotations

from typing import Any

from .clients import MockGitHubFinOpsClient
from .tools import FinOpsToolbox


def build_analysis_brief(
    toolbox: FinOpsToolbox, *, include_investigation: bool = False
) -> dict[str, Any]:
    """Collect read-only evidence for the Lab 1 Copilot Chat investigation."""
    if not isinstance(toolbox.client, MockGitHubFinOpsClient):
        raise ValueError("The workshop analysis brief supports only the mock backend")

    costs = toolbox.get_cost_summary()
    departments = toolbox.rank_department_consumption(limit=50)
    leading_department = departments["ranking"][0]["department"]
    result = {
        "schema_version": 2,
        "purpose": "Lab 1 evidence for GitHub Copilot Chat; not model-generated advice",
        "backend": "mock",
        "organization": toolbox.client.organization,
        "cost_summary": costs,
        "daily_usage": toolbox.get_daily_usage(),
        "department_ranking": departments,
        "model_breakdown": toolbox.break_down_usage("model", limit=50),
        "user_breakdown": toolbox.break_down_usage("user", limit=50),
        "leading_department_models": toolbox.break_down_usage(
            "model", department=leading_department, limit=50
        ),
        "seat_inventory": toolbox.list_seats(),
        "budget_review": toolbox.list_budgets(),
        "optimization_hypotheses": toolbox.recommend_optimizations(),
        "run_rate_scenario": toolbox.forecast_budget(600),
        "analysis_rules": [
            "All evidence is synthetic; do not upload organization data or secrets.",
            "Label each claim with its evidence section, period, unit and freshness.",
            "Daily trends describe supplied samples; missing dates are unknown, "
            "not observed zeros.",
            "The run-rate amount 600 is a scenario, not an actual budget balance.",
            "Totals are rounded after aggregation; independently rounded subtotals "
            "may differ slightly. Do not alter the overall total to hide rounding.",
            "Missing activity or a high usage rank alone does not authorize removal.",
            "Credits are not raw tokens; savings estimates need explicit assumptions.",
            "Human review is required; this brief creates no approvals or writes.",
        ],
    }
    if include_investigation:
        departments_to_review = ("AI Lab", "Security", "Platform Engineering")
        result["investigation_evidence"] = {
            "daily_comparison": toolbox.get_daily_usage_trend(),
            "teams": [toolbox.get_team_roster(name) for name in departments_to_review],
            "workflows": [
                toolbox.get_workflow_evidence(name) for name in departments_to_review
            ],
            "options": toolbox.compare_improvement_options(),
        }
    return result
