import asyncio
import json
from types import SimpleNamespace

import pytest
from copilot.session_events import (
    AssistantMessageData,
    PermissionRequestCustomTool,
    SessionErrorData,
    SessionIdleData,
)
from copilot.tools import ToolInvocation

import finops_agent.harness as harness_module
from finops_agent.budget_demo import BudgetDemo
from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.demo_connection import build_demo_harness
from finops_agent.harness import CopilotFinOpsHarness
from finops_agent.tools import FinOpsToolbox


@pytest.fixture
def runtime(monkeypatch):
    state = {"clients": [], "sessions": [], "deleted": [], "aborted": 0, "unsub": 0}
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("FINOPS_MODEL_PROVIDER", "copilot")
    monkeypatch.setenv("GITHUB_ADMIN_TOKEN", "must-not-reach-runtime")

    class Session:
        session_id = "fake-session"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            state["session_closed"] = True

        def on(self, callback):
            self.callback = callback

            def unsubscribe():
                state["unsub"] += 1

            return unsubscribe

        async def send(self, prompt):
            if prompt == "timeout":
                return
            if prompt == "error":
                self.callback(
                    SimpleNamespace(
                        data=SessionErrorData(
                            error_type="test", message="model unavailable"
                        )
                    )
                )
                return
            self.callback(
                SimpleNamespace(
                    data=AssistantMessageData(content="AI Lab: 2400", message_id="m1")
                )
            )
            self.callback(SimpleNamespace(data=SessionIdleData()))

        async def abort(self):
            state["aborted"] += 1

    class Client:
        def __init__(self, **kwargs):
            state["clients"].append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            state["client_closed"] = True

        async def create_session(self, **kwargs):
            state["sessions"].append(kwargs)
            return Session()

        async def delete_session(self, session_id):
            state["deleted"].append(session_id)

    monkeypatch.setattr(harness_module, "CopilotClient", Client)
    return state


def test_local_conversation_uses_only_explicit_tools_and_cleans_up(runtime) -> None:
    async def run():
        harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
        async with harness.conversation():
            assert await harness.ask("first") == "AI Lab: 2400"
            assert await harness.ask("follow up") == "AI Lab: 2400"
        return harness

    asyncio.run(run())
    assert len(runtime["clients"]) == len(runtime["sessions"]) == 1
    client = runtime["clients"][0]
    assert client["mode"] == "empty"
    assert client["use_logged_in_user"] is False
    assert "GITHUB_ADMIN_TOKEN" not in client["env"]
    config = runtime["sessions"][0]
    assert config["available_tools"] == [
        f"custom:{tool.name}" for tool in config["tools"]
    ]
    assert runtime["deleted"] == ["fake-session"]
    assert runtime["session_closed"] and runtime["client_closed"]
    assert runtime["unsub"] == 2
    handler = config["on_permission_request"]
    rejected = handler(
        PermissionRequestCustomTool(tool_name="shell", tool_description="not ours"), {}
    )
    assert type(rejected).__name__ == "PermissionDecisionReject"
    approved = handler(
        PermissionRequestCustomTool(
            tool_name="get_cost_summary", tool_description="registered"
        ),
        {},
    )
    assert type(approved).__name__ == "PermissionDecisionApproveOnce"


def test_model_failure_is_not_reported_as_success(runtime) -> None:
    harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
    with pytest.raises(RuntimeError, match="model unavailable"):
        asyncio.run(harness.ask("error"))
    assert runtime["deleted"] == ["fake-session"]


def test_timeout_aborts_and_unsubscribes(runtime) -> None:
    harness = CopilotFinOpsHarness(
        FinOpsToolbox(MockGitHubFinOpsClient()), timeout_seconds=0.05
    )
    with pytest.raises(TimeoutError):
        asyncio.run(harness.ask("timeout"))
    assert runtime["aborted"] == 1
    assert runtime["unsub"] == 1


def test_no_token_does_not_silently_use_host_credentials(monkeypatch) -> None:
    monkeypatch.delenv("COPILOT_GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("FINOPS_MODEL_PROVIDER", "copilot")
    harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
    with pytest.raises(ValueError, match="COPILOT_GITHUB_TOKEN"):
        asyncio.run(harness.ask("hello"))


def _configure_foundry(monkeypatch, provider: str) -> None:
    monkeypatch.setenv("FINOPS_MODEL_PROVIDER", provider)
    values = {
        "FOUNDRY_MODEL_URL": "https://model.example.test/openai/v1/",
        "FOUNDRY_API_KEY": "synthetic-foundry-key",
        "COPILOT_MODEL": "workshop-key-deployment",
        "FOUNDRY_PROJECT_ENDPOINT": "https://project.example.test/api/projects/lab",
        "AZURE_AI_MODEL_DEPLOYMENT_NAME": "workshop-identity-deployment",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


@pytest.mark.parametrize("provider", ["foundry-key", "foundry-identity"])
def test_foundry_model_preserves_scoped_tools_and_human_approval(
    runtime, monkeypatch, provider
) -> None:
    import azure.identity.aio as azure_identity

    _configure_foundry(monkeypatch, provider)
    credential_state = {"scopes": [], "closed": False, "created": 0}

    class Credential:
        def __init__(self):
            credential_state["created"] += 1

        async def get_token(self, scope):
            credential_state["scopes"].append(scope)
            return SimpleNamespace(token=f"token-{len(credential_state['scopes'])}")

        async def close(self):
            credential_state["closed"] = True

    monkeypatch.setattr(azure_identity, "DefaultAzureCredential", Credential)
    service = BudgetDemo(FinOpsToolbox(MockGitHubFinOpsClient()))

    async def run():
        harness = build_demo_harness(service)
        async with harness.conversation():
            await harness.ask("Show my budget")
            config = runtime["sessions"][0]
            tools = {tool.name: tool for tool in config["tools"]}
            assert set(tools) == {
                "get_my_costs",
                "get_my_savings",
                "request_budget_increase",
            }
            assert config["available_tools"] == [f"custom:{name}" for name in tools]
            assert "mcp_servers" not in config
            model_provider = config["provider"]
            assert model_provider["type"] == "openai"
            assert model_provider["wire_api"] == "responses"
            if provider == "foundry-key":
                assert config["model"] == "workshop-key-deployment"
                assert model_provider["base_url"].endswith("/openai/v1/")
                assert model_provider["api_key"] == "synthetic-foundry-key"
            else:
                assert config["model"] == "workshop-identity-deployment"
                assert model_provider["base_url"] == (
                    "https://project.example.test/api/projects/lab/openai/v1"
                )
                assert "api_key" not in model_provider
                get_token = model_provider["bearer_token_provider"]
                assert await get_token() == "token-1"
                assert await get_token() == "token-2"

            result = await tools["request_budget_increase"].handler(
                ToolInvocation(arguments={"new_limit": 30, "reason": "Migration"})
            )
            pending = json.loads(result.text_result_for_llm)
            assert pending["status"] == "pending"
            assert service.profile()["budget"]["budget_amount"] == 20
            assert service.profile()["budget"]["remaining_amount"] == 6
            with pytest.raises(PermissionError):
                service.approve(pending["id"], confirmed=False)
            service.approve(pending["id"], confirmed=True)
            budget = service.profile()["budget"]
            assert budget["budget_amount"] == 30
            assert budget["consumed_amount"] == 14
            assert budget["remaining_amount"] == 16

    asyncio.run(run())
    client = runtime["clients"][0]
    assert client["github_token"] is None
    assert client["use_logged_in_user"] is False
    assert "GITHUB_ADMIN_TOKEN" not in client["env"]
    assert "FOUNDRY_API_KEY" not in client["env"]
    if provider == "foundry-identity":
        assert credential_state["scopes"] == ["https://ai.azure.com/.default"] * 2
        assert credential_state["closed"] is True
    else:
        assert credential_state["created"] == 0


@pytest.mark.parametrize(
    "provider,missing",
    [
        ("foundry-key", "FOUNDRY_MODEL_URL"),
        ("foundry-key", "FOUNDRY_API_KEY"),
        ("foundry-key", "COPILOT_MODEL"),
        ("foundry-identity", "FOUNDRY_PROJECT_ENDPOINT"),
        ("foundry-identity", "AZURE_AI_MODEL_DEPLOYMENT_NAME"),
    ],
)
def test_incomplete_foundry_config_never_falls_back_to_copilot(
    runtime, monkeypatch, provider, missing
) -> None:
    _configure_foundry(monkeypatch, provider)
    monkeypatch.delenv(missing)
    harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
    with pytest.raises(ValueError, match=f"{provider} requires"):
        asyncio.run(harness.ask("Show my budget"))
    assert runtime["clients"] == []
