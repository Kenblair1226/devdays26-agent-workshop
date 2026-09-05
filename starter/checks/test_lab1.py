from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.tools import FinOpsToolbox


def test_lab1_department_ranking_checkpoint() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())

    result = tools.rank_department_consumption()

    assert result["ranking"], "Complete TODO(Lab 1); do not return empty rankings"
    assert result["ranking"][0]["department"] == "AI Lab"
    assert result["ranking"][0]["net_quantity"] == 2400
    assert result["unallocated_quantity"] == 90
    assert result["ranking"][0]["net_amount"] == 26
    assert result["ranking"][0]["user_count"] == 2
    assert result["period"]["start"] == "2026-09-01"
    assert result["as_of"] == "2026-09-03T23:59:59Z"
    assert sum(row["net_quantity"] for row in result["ranking"]) == 4760
    assert tools.rank_department_consumption(limit=1)["unallocated_quantity"] == 90
