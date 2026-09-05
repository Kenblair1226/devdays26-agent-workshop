import pytest

import finops_agent.clients as clients
from finops_agent.clients import (
    MockGitHubFinOpsClient,
    RealGitHubFinOpsClient,
    create_finops_client,
)
from finops_agent.tools import FinOpsToolbox


def test_action_requires_approval_and_is_idempotent() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    plan = tools.plan_action(
        "remove_seats",
        "octo-demo",
        {"selected_usernames": ["judy"]},
    )

    with pytest.raises(PermissionError, match="must be approved"):
        tools.execute_approved_action(plan["plan_id"], "not-approved")

    approval = tools.approve_action(plan["plan_id"], confirmed=True)
    executed = tools.execute_approved_action(
        plan["plan_id"], approval["approval_token"]
    )
    replayed = tools.execute_approved_action(
        plan["plan_id"], approval["approval_token"]
    )

    assert executed["result"]["changed"] == 1
    assert executed["idempotent_replay"] is False
    assert replayed["idempotent_replay"] is True


def test_bad_approval_token_is_rejected() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    plan = tools.plan_action(
        "create_budget",
        "octo-demo",
        {
            "budget_scope": "organization",
            "budget_amount": 50,
            "budget_type": "BundlePricing",
            "budget_product_sku": "ai_credits",
            "prevent_further_usage": True,
        },
    )
    tools.approve_action(plan["plan_id"], confirmed=True)

    with pytest.raises(PermissionError, match="does not match"):
        tools.execute_approved_action(plan["plan_id"], "wrong-token")


def test_real_writes_are_disabled_by_default() -> None:
    client = RealGitHubFinOpsClient("octo-demo", "test-token")

    with pytest.raises(PermissionError, match="disabled"):
        client.execute_action(
            "remove_seats",
            "octo-demo",
            {"selected_usernames": ["judy"]},
        )


def test_real_client_rejects_unsupported_reporting_periods(monkeypatch) -> None:
    client = RealGitHubFinOpsClient("octo-demo", "test-token")
    monkeypatch.setattr(client, "get_usage_items", lambda: [])
    monkeypatch.setattr(client, "list_budgets", lambda: [])
    monkeypatch.setattr(client, "list_seats", lambda: [])
    tools = FinOpsToolbox(client)

    with pytest.raises(ValueError, match="supports only"):
        tools.get_cost_summary("previous_month")


def test_real_client_sends_the_configured_token(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def read(self) -> bytes:
            return b'{"budgets": []}'

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        assert timeout == 30
        return Response()

    monkeypatch.setattr(clients.urllib.request, "urlopen", fake_urlopen)
    client = RealGitHubFinOpsClient("octo-demo", "test-token")

    assert client.list_budgets() == []
    assert captured["authorization"] == "Bearer test-token"


def test_client_factory_defaults_to_mock(monkeypatch) -> None:
    monkeypatch.delenv("FINOPS_BACKEND", raising=False)

    assert isinstance(create_finops_client(), MockGitHubFinOpsClient)


def test_client_factory_can_select_real_backend(monkeypatch) -> None:
    monkeypatch.setenv("FINOPS_BACKEND", "github")
    monkeypatch.setenv("GITHUB_ORG", "octo-demo")
    monkeypatch.setenv("GITHUB_ADMIN_TOKEN", "test-token")

    assert isinstance(create_finops_client(), RealGitHubFinOpsClient)


def test_approval_requires_a_real_confirmation_decision() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    plan = tools.plan_action(
        "remove_seats", "octo-demo", {"selected_usernames": ["judy"]}
    )
    with pytest.raises(PermissionError, match="human confirmation"):
        tools.approve_action(plan["plan_id"])
    assert tools.approvals.get_plan(plan["plan_id"])["status"] == "planned"


def test_payload_and_result_cannot_mutate_an_approved_plan() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    payload = {"selected_usernames": ["judy"]}
    plan = tools.plan_action("remove_seats", "octo-demo", payload)
    approval = tools.approve_action(plan["plan_id"], confirmed=True)
    payload["selected_usernames"].append("alice")
    plan["payload"]["selected_usernames"].append("bob")
    approval["payload"]["selected_usernames"].append("carol")
    result = tools.execute_approved_action(plan["plan_id"], approval["approval_token"])
    assert result["result"]["users"] == ["judy"]
    with pytest.raises(PermissionError, match="token"):
        tools.execute_approved_action(plan["plan_id"], "invalid-replay")


def test_expired_approval_cannot_execute(monkeypatch) -> None:
    import finops_agent.approvals as approvals

    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    plan = tools.plan_action(
        "remove_seats", "octo-demo", {"selected_usernames": ["judy"]}
    )
    monkeypatch.setattr(approvals, "monotonic", lambda: 0)
    approval = tools.approve_action(plan["plan_id"], confirmed=True)
    monkeypatch.setattr(approvals, "monotonic", lambda: 301)
    with pytest.raises(PermissionError, match="expired"):
        tools.execute_approved_action(plan["plan_id"], approval["approval_token"])


@pytest.mark.parametrize(
    "kind,target,payload",
    [
        ("remove_seats", "different-org", {"selected_usernames": ["judy"]}),
        ("remove_seats", "octo-demo", {"selected_usernames": ["judy", "JUDY"]}),
        ("remove_seats", "octo-demo", {"selected_usernames": [None]}),
        ("update_budget", "missing-budget", {"budget_amount": 5}),
        ("update_budget", "budget-user-carol", {"prevent_further_usage": False}),
        ("update_budget", "budget-user-carol", {"budget_amount": float("nan")}),
        ("update_budget", "budget-user-carol", {"budget_amount": True}),
        ("update_budget", "budget-user-carol", {"budget_amount": -1}),
        ("update_budget", "budget-user-carol", {"budget_scope": "enterprise"}),
    ],
)
def test_bad_write_inputs_rejected_before_approval(kind, target, payload) -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    with pytest.raises(ValueError):
        tools.plan_action(kind, target, payload)
    assert tools.approvals.list_plans() == []


def test_human_console_decline_leaves_mock_state_unchanged(monkeypatch) -> None:
    from finops_agent.local_cli import _confirm_and_execute

    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    plan = tools.plan_action(
        "remove_seats", "octo-demo", {"selected_usernames": ["judy"]}
    )
    monkeypatch.setattr("builtins.input", lambda _: "no")
    result = _confirm_and_execute(tools, plan["plan_id"])
    assert result["writes"] == 0
    assert tools.approvals.get_plan(plan["plan_id"])["status"] == "planned"
