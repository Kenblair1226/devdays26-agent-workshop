import asyncio
import json
import os
from contextlib import AsyncExitStack
from pathlib import Path
from types import SimpleNamespace

import pytest
from copilot.session import ProviderTokenArgs
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
from finops_agent.harness import CopilotFinOpsHarness, _openai_base_url
from finops_agent.tools import FinOpsToolbox


@pytest.fixture(autouse=True)
def clean_model_settings(monkeypatch):
    for name in (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "MODEL_NAME",
        "FOUNDRY_MODEL_URL",
        "FOUNDRY_API_KEY",
        "COPILOT_MODEL",
        "FOUNDRY_PROJECT_ENDPOINT",
        "AZURE_AI_MODEL_DEPLOYMENT_NAME",
        "FINOPS_OTEL_FILE",
        "FINOPS_OTEL_EXPORTER",
    ):
        monkeypatch.delenv(name, raising=False)


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
                    data=AssistantMessageData(content="AI Lab: 17600", message_id="m1")
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
            assert await harness.ask("first") == "AI Lab: 17600"
            assert await harness.ask("follow up") == "AI Lab: 17600"
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


def test_runtime_telemetry_is_opt_in(runtime, monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://collector.example.test")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "authorization=private-token")
    monkeypatch.setenv("COPILOT_OTEL_ENABLED", "true")
    monkeypatch.setenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")
    harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
    asyncio.run(harness.ask("hello"))
    client = runtime["clients"][0]
    assert client["telemetry"] is None
    assert not any("OTEL" in key for key in client["env"])


def test_runtime_file_telemetry_is_metadata_only(runtime, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FINOPS_OTEL_FILE", "workshop-output/copilot-trace.jsonl")
    monkeypatch.setenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://collector.example.test")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "must-not-reach-runtime")
    harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
    asyncio.run(harness.ask("hello"))
    client = runtime["clients"][0]
    path = tmp_path / "workshop-output/copilot-trace.jsonl"
    assert client["telemetry"] == {
        "exporter_type": "file",
        "file_path": str(path),
        "source_name": "finops-agent",
        "capture_content": False,
    }
    assert path.is_file()
    if os.name == "posix":
        assert path.stat().st_mode & 0o077 == 0
    assert "GITHUB_ADMIN_TOKEN" not in client["env"]
    assert "AZURE_OPENAI_API_KEY" not in client["env"]
    assert not any("OTEL" in key for key in client["env"])
    assert runtime["client_closed"]


def test_runtime_telemetry_preserves_existing_file(runtime, monkeypatch, tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text('{"existing":true}\n', encoding="utf-8")
    monkeypatch.setenv("FINOPS_OTEL_FILE", str(path))
    harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
    asyncio.run(harness.ask("hello"))
    assert path.read_text(encoding="utf-8") == '{"existing":true}\n'


@pytest.mark.parametrize("value", [" ", "\t"])
def test_runtime_telemetry_rejects_blank_path(runtime, monkeypatch, value):
    monkeypatch.setenv("FINOPS_OTEL_FILE", value)
    harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
    with pytest.raises(ValueError, match="FINOPS_OTEL_FILE"):
        asyncio.run(harness.ask("hello"))
    assert not runtime["clients"]


def test_runtime_telemetry_rejects_unwritable_target(runtime, monkeypatch, tmp_path):
    monkeypatch.setenv("FINOPS_OTEL_FILE", str(tmp_path))
    harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
    with pytest.raises(OSError):
        asyncio.run(harness.ask("hello"))
    assert not runtime["clients"]


def test_timeout_aborts_and_unsubscribes(runtime) -> None:
    harness = CopilotFinOpsHarness(
        FinOpsToolbox(MockGitHubFinOpsClient()), timeout_seconds=0.05
    )
    with pytest.raises(TimeoutError):
        asyncio.run(harness.ask("timeout"))
    assert runtime["aborted"] == 1
    assert runtime["unsub"] == 1


@pytest.mark.parametrize("prompt", ["hello", "error", "timeout", "cancel"])
def test_cloud_telemetry_exports_after_runtime_exit_and_removes_buffer(
    runtime, monkeypatch, prompt
) -> None:
    from finops_agent import telemetry

    monkeypatch.setenv("FINOPS_OTEL_EXPORTER", "azure-monitor")
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "synthetic-connection")
    paths = []

    async def flush(path, connection, auth_mode):
        assert runtime["client_closed"]
        assert path.is_file()
        assert connection == "synthetic-connection"
        assert auth_mode == ""
        paths.append(path)

    monkeypatch.setattr(telemetry, "_flush_cloud", flush)
    harness = CopilotFinOpsHarness(
        FinOpsToolbox(MockGitHubFinOpsClient()), timeout_seconds=0.05
    )

    async def run():
        if prompt == "cancel":
            task = asyncio.create_task(harness.ask("timeout"))
            await asyncio.sleep(0.01)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        elif prompt in ("error", "timeout"):
            with pytest.raises(RuntimeError if prompt == "error" else TimeoutError):
                await harness.ask(prompt)
        else:
            assert await harness.ask(prompt) == "AI Lab: 17600"

    asyncio.run(run())
    assert len(paths) == 1
    assert not paths[0].parent.exists()
    client = runtime["clients"][0]
    assert client["telemetry"]["capture_content"] is False
    assert client["telemetry"]["file_path"] == str(paths[0])
    assert "APPLICATIONINSIGHTS_CONNECTION_STRING" not in client["env"]
    assert "FINOPS_OTEL_EXPORTER" not in client["env"]


def test_no_token_does_not_silently_use_host_credentials(monkeypatch) -> None:
    monkeypatch.delenv("COPILOT_GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("FINOPS_MODEL_PROVIDER", "copilot")
    harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
    with pytest.raises(ValueError, match="COPILOT_GITHUB_TOKEN"):
        asyncio.run(harness.ask("hello"))


def _configure_foundry(monkeypatch, provider: str) -> None:
    monkeypatch.setenv("FINOPS_MODEL_PROVIDER", provider)
    values = {
        "AZURE_OPENAI_ENDPOINT": (
            "https://model.example.test"
            if provider == "foundry-key"
            else "https://project.example.test/api/projects/lab"
        ),
        "AZURE_OPENAI_API_KEY": "synthetic-foundry-key",
        "MODEL_NAME": (
            "workshop-key-deployment"
            if provider == "foundry-key"
            else "workshop-identity-deployment"
        ),
        "COPILOT_MODEL": "separate-github-model",
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
                assert (
                    model_provider["base_url"] == "https://model.example.test/openai/v1"
                )
                assert model_provider["api_key"] == "synthetic-foundry-key"
            else:
                assert config["model"] == "workshop-identity-deployment"
                assert model_provider["base_url"] == (
                    "https://project.example.test/api/projects/lab/openai/v1"
                )
                assert "api_key" not in model_provider
                get_token = model_provider["bearer_token_provider"]
                token_args: ProviderTokenArgs = {
                    "provider_name": "default",
                    "session_id": "fake-session",
                }
                assert await get_token(token_args) == "token-1"
                assert await get_token(token_args) == "token-2"

            result = await tools["request_budget_increase"].handler(
                ToolInvocation(arguments={"new_limit": 220, "reason": "Migration"})
            )
            pending = json.loads(result.text_result_for_llm)
            assert pending["status"] == "pending"
            assert service.profile()["budget"]["budget_amount"] == 150
            assert service.profile()["budget"]["remaining_amount"] == 47.33
            with pytest.raises(PermissionError):
                service.approve(pending["id"], confirmed=False)
            service.approve(pending["id"], confirmed=True)
            budget = service.profile()["budget"]
            assert budget["budget_amount"] == 220
            assert budget["consumed_amount"] == 102.67
            assert budget["remaining_amount"] == 117.33

    asyncio.run(run())
    client = runtime["clients"][0]
    assert client["github_token"] is None
    assert client["use_logged_in_user"] is False
    assert "GITHUB_ADMIN_TOKEN" not in client["env"]
    assert "AZURE_OPENAI_API_KEY" not in client["env"]
    assert "FOUNDRY_API_KEY" not in client["env"]
    if provider == "foundry-identity":
        assert credential_state["scopes"] == ["https://ai.azure.com/.default"] * 2
        assert credential_state["closed"] is True
    else:
        assert credential_state["created"] == 0


@pytest.mark.parametrize(
    "provider,missing",
    [
        ("foundry-key", "AZURE_OPENAI_ENDPOINT"),
        ("foundry-key", "AZURE_OPENAI_API_KEY"),
        ("foundry-key", "MODEL_NAME"),
        ("foundry-identity", "AZURE_OPENAI_ENDPOINT"),
        ("foundry-identity", "MODEL_NAME"),
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


@pytest.mark.parametrize(
    "endpoint,expected",
    [
        (
            "https://resource.openai.azure.com",
            "https://resource.openai.azure.com/openai/v1",
        ),
        (
            "https://resource.openai.azure.com/",
            "https://resource.openai.azure.com/openai/v1",
        ),
        (
            "https://resource.openai.azure.com/openai/v1",
            "https://resource.openai.azure.com/openai/v1",
        ),
        (
            "https://resource.openai.azure.com/openai/v1/",
            "https://resource.openai.azure.com/openai/v1",
        ),
        (
            "https://resource.services.ai.azure.com/api/projects/lab/",
            "https://resource.services.ai.azure.com/api/projects/lab/openai/v1",
        ),
        (
            "https://resource.services.ai.azure.com/api/projects/lab/openai/v1/",
            "https://resource.services.ai.azure.com/api/projects/lab/openai/v1",
        ),
        (
            "https://api.example.test/v1",
            "https://api.example.test/v1",
        ),
        (
            "https://api.example.test/v1/",
            "https://api.example.test/v1",
        ),
    ],
)
def test_foundry_base_url_adds_v1_once(endpoint, expected) -> None:
    assert _openai_base_url(endpoint) == expected


@pytest.mark.parametrize(
    "endpoint",
    [
        "",
        "not-a-url",
        "http://example.test",
        "https://",
        "https://user:secret@example.test",
        "https://example.test?api-key=secret",
        "https://example.test/#fragment",
        "https://example.test/openai/v1/responses",
        "https://example.test/openai/deployments/model",
        "https://example.test/api/projects/lab/agents/finops/endpoint",
        "https://example.test/v1/chat/completions",
        "https://example.test/v1/responses",
        "https://example.test/v1/models",
        "https://example.test/v1beta",
    ],
)
def test_foundry_endpoint_rejects_non_base_urls(endpoint) -> None:
    with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
        _openai_base_url(endpoint)


def test_copilot_model_configuration_is_not_renamed(monkeypatch) -> None:
    _configure_foundry(monkeypatch, "foundry-key")
    monkeypatch.setenv("FINOPS_MODEL_PROVIDER", "copilot")
    provider, model = CopilotFinOpsHarness._model_configuration(AsyncExitStack())
    assert provider is None
    assert model == "separate-github-model"


def test_legacy_key_configuration_is_compatible_and_warns(monkeypatch, caplog) -> None:
    monkeypatch.setenv("FINOPS_MODEL_PROVIDER", "foundry-key")
    monkeypatch.setenv("FOUNDRY_MODEL_URL", "https://legacy.example.test/openai/v1/")
    monkeypatch.setenv("FOUNDRY_API_KEY", "synthetic-legacy-key")
    monkeypatch.setenv("COPILOT_MODEL", "legacy-deployment")
    provider, model = CopilotFinOpsHarness._model_configuration(AsyncExitStack())
    assert provider["base_url"] == "https://legacy.example.test/openai/v1"
    assert provider["api_key"] == "synthetic-legacy-key"
    assert model == "legacy-deployment"
    assert "deprecated" in caplog.text
    assert "synthetic-legacy-key" not in caplog.text


def test_new_foundry_key_names_take_precedence(monkeypatch) -> None:
    _configure_foundry(monkeypatch, "foundry-key")
    monkeypatch.setenv("FOUNDRY_MODEL_URL", "https://legacy.example.test/openai/v1/")
    monkeypatch.setenv("FOUNDRY_API_KEY", "synthetic-legacy-key")
    provider, model = CopilotFinOpsHarness._model_configuration(AsyncExitStack())
    assert provider["base_url"] == "https://model.example.test/openai/v1"
    assert provider["api_key"] == "synthetic-foundry-key"
    assert model == "workshop-key-deployment"


def test_partial_new_configuration_does_not_mix_legacy_secrets(monkeypatch) -> None:
    _configure_foundry(monkeypatch, "foundry-key")
    monkeypatch.delenv("AZURE_OPENAI_API_KEY")
    monkeypatch.setenv("FOUNDRY_API_KEY", "synthetic-legacy-key")
    monkeypatch.setenv("FOUNDRY_MODEL_URL", "https://legacy.example.test/openai/v1/")
    with pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY"):
        CopilotFinOpsHarness._model_configuration(AsyncExitStack())


@pytest.mark.parametrize(
    "model_variable", ["MODEL_NAME", "AZURE_AI_MODEL_DEPLOYMENT_NAME"]
)
def test_identity_keeps_platform_injected_project_compatibility(
    monkeypatch, model_variable
) -> None:
    import azure.identity.aio as azure_identity

    monkeypatch.setenv("FINOPS_MODEL_PROVIDER", "foundry-identity")
    monkeypatch.setenv(
        "FOUNDRY_PROJECT_ENDPOINT", "https://project.example.test/api/projects/lab"
    )
    monkeypatch.setenv(model_variable, "hosted-deployment")
    state = {"closed": False}

    class Credential:
        async def close(self):
            state["closed"] = True

    monkeypatch.setattr(azure_identity, "DefaultAzureCredential", Credential)

    async def run():
        async with AsyncExitStack() as stack:
            provider, model = CopilotFinOpsHarness._model_configuration(stack)
            assert model == "hosted-deployment"
            assert provider["base_url"].endswith("/api/projects/lab/openai/v1")
            assert "api_key" not in provider

    asyncio.run(run())
    assert state["closed"] is True


def test_env_examples_and_hosted_binding_use_new_foundry_names() -> None:
    root = Path(__file__).parents[2]
    for project in ("starter", "solution"):
        example = (root / project / ".env.example").read_text(encoding="utf-8")
        for name in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "MODEL_NAME"):
            assert f"\n{name}=" in example
        assert "\nFOUNDRY_MODEL_URL=" not in example
        assert "\nFOUNDRY_API_KEY=" not in example
        assert "\nCOPILOT_MODEL=gpt-6-astra" in example
        config = (root / project / "azure.yaml").read_text(encoding="utf-8")
        assert "MODEL_NAME: ${AZURE_AI_MODEL_DEPLOYMENT_NAME}" in config
