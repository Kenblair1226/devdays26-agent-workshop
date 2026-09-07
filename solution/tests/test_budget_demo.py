import asyncio
import json

import pytest
from copilot.tools import ToolInvocation
from starlette.testclient import TestClient

from finops_agent.budget_demo import BudgetDemo
from finops_agent.clients import MockGitHubFinOpsClient, RealGitHubFinOpsClient
from finops_agent.demo_connection import build_demo_harness
from finops_agent.demo_server import create_demo_app
from finops_agent.tools import FinOpsToolbox


def service() -> BudgetDemo:
    return BudgetDemo(FinOpsToolbox(MockGitHubFinOpsClient()))


def test_demo_is_bound_to_user_and_reuses_sdk_harness() -> None:
    demo = service()
    profile = demo.profile()
    assert profile["user"] == "carol"
    assert profile["billing"]["net_amount"] == 14
    assert profile["billing"]["net_quantity"] == 1400
    assert profile["budget"]["budget_amount"] == 20
    assert profile["budget"]["remaining_amount"] == 6
    assert "alice" not in json.dumps(demo.savings())
    harness = build_demo_harness(demo)
    assert harness.toolbox is demo.toolbox
    assert {tool.name for tool in harness._custom_tools} == {
        "get_my_costs",
        "get_my_savings",
        "request_budget_increase",
    }
    assert "administrator" in harness.instructions


def test_demo_rejects_real_client() -> None:
    with pytest.raises(ValueError, match="mock"):
        BudgetDemo(FinOpsToolbox(RealGitHubFinOpsClient("org", "test-token")))


def test_pending_then_explicit_admin_approval_changes_limit_once() -> None:
    demo = service()
    request = demo.request_increase(30, "Migration project")
    duplicate = demo.request_increase(30, "Migration project")
    assert request == duplicate
    assert request["status"] == "pending"
    assert demo.profile()["budget"]["budget_amount"] == 20
    assert demo.profile()["budget"]["remaining_amount"] == 6
    with pytest.raises(PermissionError):
        demo.approve(request["id"], confirmed=False)
    approved = demo.approve(request["id"], confirmed=True)
    assert approved["status"] == "approved"
    assert demo.profile()["budget"]["budget_amount"] == 30
    assert demo.profile()["budget"]["consumed_amount"] == 14
    assert demo.profile()["budget"]["remaining_amount"] == 16
    before = demo.toolbox.get_audit_log()
    assert demo.approve(request["id"], confirmed=True) == approved
    assert demo.toolbox.get_audit_log() == before
    assert "approval_token" not in json.dumps(demo.requests())


@pytest.mark.parametrize(
    "amount,reason",
    [
        (20, "No increase"),
        (19, "Decrease"),
        (True, "Wrong type"),
        (30.5, "Non-integer"),
        (30, ""),
        (30, " " * 5),
        (30, "x" * 501),
    ],
)
def test_demo_rejects_invalid_limit_requests(amount, reason) -> None:
    demo = service()
    with pytest.raises(ValueError):
        demo.request_increase(amount, reason)
    assert demo.requests() == []


def test_pending_request_cannot_be_replaced_or_externally_mutated() -> None:
    demo = service()
    request = demo.request_increase(30, "Migration")
    request["requested_limit"] = 999
    assert demo.requests()[0]["requested_limit"] == 30
    with pytest.raises(ValueError, match="already pending"):
        demo.request_increase(40, "Changed my mind")


def test_stale_request_is_not_approved() -> None:
    demo = service()
    request = demo.request_increase(30, "Migration")
    demo.toolbox.client.execute_action(
        "update_budget", "budget-user-carol", {"budget_amount": 25}
    )
    with pytest.raises(ValueError, match="changed since"):
        demo.approve(request["id"], confirmed=True)
    assert demo.requests()[0]["status"] == "pending"
    assert demo.profile()["budget"]["budget_amount"] == 25


def test_model_has_no_admin_tools_or_identity_override() -> None:
    demo = service()
    tools = {tool.name: tool for tool in demo.user_tools()}
    assert (
        not {"approve_action", "execute_approved_action", "plan_action"} & tools.keys()
    )
    result = asyncio.run(
        tools["request_budget_increase"].handler(
            ToolInvocation(
                arguments={"new_limit": 30, "reason": "Migration", "user": "alice"}
            )
        )
    )
    assert result.result_type == "failure"
    assert demo.requests() == []


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("FINOPS_BACKEND", "mock")
    monkeypatch.delenv("FINOPS_DATA_DIR", raising=False)
    return create_demo_app()


def test_http_roles_enforced_and_balance_refreshes(app) -> None:
    user_headers = {"X-Demo-Token": app.state.user_token}
    admin_headers = {"X-Demo-Token": app.state.admin_token}
    with TestClient(app) as client:
        assert client.get("/api/user").status_code == 403
        assert client.get("/api/admin", headers=user_headers).status_code == 403
        assert client.get("/api/user", headers=admin_headers).status_code == 403
        created = client.post(
            "/api/requests",
            headers=user_headers,
            json={
                "new_limit": 30,
                "reason": "Migration",
            },
        )
        assert created.status_code == 200
        assert created.json()["profile"]["budget"]["budget_amount"] == 20
        request_id = created.json()["request"]["id"]
        url = f"/api/admin/requests/{request_id}/approve"
        assert (
            client.post(url, headers=user_headers, json={"confirmed": True}).status_code
            == 403
        )
        assert (
            client.post(
                url, headers=admin_headers, json={"confirmed": False}
            ).status_code
            == 400
        )
        response = client.post(url, headers=admin_headers, json={"confirmed": True})
        assert response.status_code == 200
        profile = client.get("/api/user", headers=user_headers).json()
        assert profile["budget"]["budget_amount"] == 30
        assert profile["budget"]["remaining_amount"] == 16
        assert profile["requests"][0]["status"] == "approved"
        assert app.state.admin_token not in json.dumps(profile)


def test_http_request_cannot_choose_another_identity(app) -> None:
    with TestClient(app) as client:
        result = client.post(
            "/api/requests",
            headers={
                "X-Demo-Token": app.state.user_token,
            },
            json={"user": "alice", "new_limit": 30, "reason": "Migration"},
        )
    assert result.status_code == 400
    assert app.state.service.requests() == []


def test_http_chat_uses_scoped_harness_and_never_approves(app, monkeypatch) -> None:
    async def ask(message):
        assert message == "raise my limit"
        app.state.service.request_increase(30, "Migration")
        return "Request pending admin approval.", ["request_budget_increase"]

    monkeypatch.setattr(app.state.chat, "ask", ask)
    with TestClient(app) as client:
        result = client.post(
            "/api/chat",
            headers={
                "X-Demo-Token": app.state.user_token,
            },
            json={"message": "raise my limit"},
        )
    assert result.status_code == 200
    assert result.json()["profile"]["budget"]["budget_amount"] == 20
    assert result.json()["profile"]["requests"][0]["status"] == "pending"


def test_demo_cannot_start_with_real_backend(monkeypatch) -> None:
    monkeypatch.setenv("FINOPS_BACKEND", "github")
    with pytest.raises(ValueError, match="mock-only"):
        create_demo_app()


def test_demo_cannot_import_an_ambient_data_directory(monkeypatch) -> None:
    monkeypatch.setenv("FINOPS_BACKEND", "mock")
    monkeypatch.setenv("FINOPS_DATA_DIR", "real-data")
    with pytest.raises(ValueError, match="Clear FINOPS_DATA_DIR"):
        create_demo_app()


def test_demo_page_does_not_embed_any_role_capability(app) -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "FinOps Copilot" in response.text
    assert app.state.user_token not in response.text
    assert app.state.admin_token not in response.text
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("sensitive provider details"),
        TimeoutError("provider timeout"),
        NotImplementedError("learner connection not complete"),
    ],
)
def test_chat_failures_do_not_fake_success_or_approval(app, monkeypatch, error):
    async def fail(_message):
        raise error

    monkeypatch.setattr(app.state.chat, "ask", fail)
    with TestClient(app) as client:
        result = client.post(
            "/api/chat",
            headers={
                "X-Demo-Token": app.state.user_token,
            },
            json={"message": "raise my limit"},
        )
    assert result.status_code in {503, 504}
    assert "reply" not in result.json()
    assert "sensitive provider details" not in result.text
    assert app.state.service.requests() == []
    assert app.state.service.profile()["budget"]["budget_amount"] == 20


def test_failed_application_never_marks_the_request_approved(app, monkeypatch):
    request = app.state.service.request_increase(30, "Migration")
    backend = app.state.service.toolbox.client
    original = backend.execute_action

    def fail(*_args, **_kwargs):
        raise RuntimeError("simulated write failure")

    monkeypatch.setattr(backend, "execute_action", fail)
    with TestClient(app) as client:
        url = f"/api/admin/requests/{request['id']}/approve"
        headers = {"X-Demo-Token": app.state.admin_token}
        response = client.post(url, headers=headers, json={"confirmed": True})
        assert response.status_code == 503
        assert app.state.service.requests()[0]["status"] == "pending"
        assert app.state.service.profile()["budget"]["budget_amount"] == 20
        monkeypatch.setattr(backend, "execute_action", original)
        assert (
            client.post(url, headers=headers, json={"confirmed": True}).status_code
            == 200
        )
