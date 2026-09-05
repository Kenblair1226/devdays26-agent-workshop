import asyncio
from types import SimpleNamespace

import pytest
from copilot.session_events import (
    AssistantMessageData,
    PermissionRequestCustomTool,
    SessionErrorData,
    SessionIdleData,
)

import finops_agent.harness as harness_module
from finops_agent.clients import MockGitHubFinOpsClient
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
