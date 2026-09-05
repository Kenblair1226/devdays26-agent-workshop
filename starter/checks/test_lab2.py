import asyncio
import json

from copilot.tools import ToolInvocation

from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.instructions import FINOPS_AGENT_INSTRUCTIONS
from finops_agent.sdk_tools import build_sdk_tools
from finops_agent.tools import FinOpsToolbox


def test_lab2_harness_checkpoint() -> None:
    sdk_tools = build_sdk_tools(FinOpsToolbox(MockGitHubFinOpsClient()))
    names = {tool.name for tool in sdk_tools}

    assert {
        "get_cost_summary",
        "rank_department_consumption",
        "break_down_usage",
        "recommend_optimizations",
        "plan_action",
        "execute_approved_action",
        "get_audit_log",
    } <= names
    assert "TODO(Lab 2)" not in FINOPS_AGENT_INSTRUCTIONS
    assert "approve_action" not in names

    async def exercise():
        definitions = {tool.name: tool for tool in sdk_tools}
        cost = await definitions["get_cost_summary"].handler(
            ToolInvocation(arguments={})
        )
        assert json.loads(cost.text_result_for_llm)["net_quantity"] == 4760
        rank = await definitions["rank_department_consumption"].handler(
            ToolInvocation(arguments={})
        )
        assert (
            json.loads(rank.text_result_for_llm)["ranking"][0]["department"] == "AI Lab"
        )
        plan = await definitions["plan_action"].handler(
            ToolInvocation(
                arguments={
                    "kind": "remove_seats",
                    "target": "octo-demo",
                    "payload": {"selected_usernames": ["judy"]},
                }
            )
        )
        plan_id = json.loads(plan.text_result_for_llm)["plan_id"]
        denied = await definitions["execute_approved_action"].handler(
            ToolInvocation(
                arguments={"plan_id": plan_id, "approval_token": "no-approval"}
            )
        )
        assert denied.result_type == "failure"

    asyncio.run(exercise())
