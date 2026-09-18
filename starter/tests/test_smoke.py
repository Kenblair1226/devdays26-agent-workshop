from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.tools import FinOpsToolbox


def test_starter_cost_and_approval_flow_are_runnable() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())

    summary = tools.get_cost_summary()
    plan = tools.plan_action(
        "remove_seats",
        "octo-demo",
        {"selected_usernames": ["judy"]},
    )
    approval = tools.approve_action(plan["plan_id"], confirmed=True)
    execution = tools.execute_approved_action(
        plan["plan_id"], approval["approval_token"]
    )

    assert summary["net_quantity"] == 34906.67
    assert summary["net_amount"] == 329.12
    assert execution["result"]["mock"] is True
