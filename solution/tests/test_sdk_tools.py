from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.sdk_tools import build_sdk_tools
from finops_agent.tools import FinOpsToolbox


def test_sdk_tool_surface_excludes_human_approval() -> None:
    tools = build_sdk_tools(FinOpsToolbox(MockGitHubFinOpsClient()))
    names = {tool.name for tool in tools}

    assert "get_cost_summary" in names
    assert "rank_department_consumption" in names
    assert "plan_action" in names
    assert "execute_approved_action" in names
    assert "approve_action" not in names
