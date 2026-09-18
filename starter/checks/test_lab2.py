import asyncio
import json

from copilot.tools import ToolInvocation

from finops_agent.budget_demo import BudgetDemo
from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.demo_connection import build_demo_harness
from finops_agent.harness import CopilotFinOpsHarness
from finops_agent.tools import FinOpsToolbox


def test_lab2_harness_checkpoint() -> None:
    service = BudgetDemo(FinOpsToolbox(MockGitHubFinOpsClient()))
    harness = build_demo_harness(service)
    assert isinstance(harness, CopilotFinOpsHarness)
    assert harness.toolbox is service.toolbox
    tools = {tool.name: tool for tool in harness._custom_tools}
    assert set(tools) == {
        "get_my_costs",
        "get_my_savings",
        "request_budget_increase",
    }
    assert "administrator" in harness.instructions

    async def exercise():
        costs = await tools["get_my_costs"].handler(ToolInvocation(arguments={}))
        profile = json.loads(costs.text_result_for_llm)
        assert profile["user"] == "carol"
        assert profile["billing"]["net_amount"] == 102.67
        assert profile["budget"]["budget_amount"] == 150
        pending = await tools["request_budget_increase"].handler(
            ToolInvocation(arguments={"new_limit": 220, "reason": "Migration project"})
        )
        request = json.loads(pending.text_result_for_llm)
        assert request["status"] == "pending"
        assert service.profile()["budget"]["remaining_amount"] == 47.33
        service.approve(request["id"], confirmed=True)
        assert service.profile()["budget"]["budget_amount"] == 220
        assert service.profile()["budget"]["consumed_amount"] == 102.67
        assert service.profile()["budget"]["remaining_amount"] == 117.33

    asyncio.run(exercise())
