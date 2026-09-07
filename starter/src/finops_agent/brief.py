from __future__ import annotations

from typing import Any

from .clients import MockGitHubFinOpsClient
from .tools import FinOpsToolbox


def build_analysis_brief(toolbox: FinOpsToolbox) -> dict[str, Any]:
    """Collect read-only evidence for the Lab 1 Copilot Chat investigation."""
    if not isinstance(toolbox.client, MockGitHubFinOpsClient):
        raise ValueError("The workshop analysis brief supports only the mock backend")

    costs = toolbox.get_cost_summary()
    departments = toolbox.rank_department_consumption(limit=50)
    leading_department = departments["ranking"][0]["department"]
    return {
        "schema_version": 1,
        "purpose": "Lab 1 evidence for GitHub Copilot Chat; not model-generated advice",
        "backend": "mock",
        "organization": toolbox.client.organization,
        "cost_summary": costs,
        "department_ranking": departments,
        "model_breakdown": toolbox.break_down_usage("model", limit=50),
        "user_breakdown": toolbox.break_down_usage("user", limit=50),
        "leading_department_models": toolbox.break_down_usage(
            "model", department=leading_department, limit=50
        ),
        "seat_inventory": toolbox.list_seats(),
        "budget_review": toolbox.list_budgets(),
        "optimization_hypotheses": toolbox.recommend_optimizations(),
        "run_rate_scenario": toolbox.forecast_budget(80),
        "analysis_rules": [
            "All evidence is synthetic; do not upload organization data or secrets.",
            "Label each claim with its evidence section, period, unit and freshness.",
            "The run-rate amount 80 is a scenario, not an actual budget balance.",
            "Missing activity or a high usage rank alone does not authorize removal.",
            "Credits are not raw tokens; savings estimates need explicit assumptions.",
            "Human review is required; this brief creates no approvals or writes.",
        ],
    }
