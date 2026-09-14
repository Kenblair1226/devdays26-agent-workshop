import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from copilot.client import JsonRpcError, ProcessExitedError, ServerRpc

import finops_agent.copilot_usage as usage_module
import finops_agent.local_cli as cli_module
from finops_agent.copilot_usage import CopilotUsageError, read_copilot_usage


@pytest.fixture
def quota_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "test-personal-copilot-token")
    monkeypatch.setenv("GITHUB_ADMIN_TOKEN", "private-admin-token")
    monkeypatch.setenv("GITHUB_TOKEN", "unrelated-github-token")
    monkeypatch.setenv("GH_TOKEN", "unrelated-gh-token")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "private-foundry-key")
    monkeypatch.setenv("FINOPS_BACKEND", "mock")
    monkeypatch.setenv("FINOPS_ALLOW_REAL_WRITES", "false")
    monkeypatch.setattr(
        cli_module, "__file__", str(tmp_path / "src" / "finops_agent" / "local_cli.py")
    )
    snapshot = {
        "entitlementRequests": 300,
        "isUnlimitedEntitlement": False,
        "overage": 0.0,
        "overageAllowedWithExhaustedQuota": False,
        "remainingPercentage": 60.0,
        "usageAllowedWithExhaustedQuota": False,
        "usedRequests": 120,
        "resetDate": "2026-10-01T00:00:00Z",
    }
    transport = AsyncMock()
    transport.request.return_value = {
        "quotaSnapshots": {"premium_interactions": snapshot}
    }
    state = {
        "clients": [],
        "started": 0,
        "stopped": 0,
        "transport": transport,
        "snapshot": snapshot,
        "startup_error": None,
    }

    class Client:
        def __init__(self, **kwargs):
            state["clients"].append(kwargs)
            self.rpc = ServerRpc(transport)

        async def start(self):
            state["started"] += 1
            if state["startup_error"] is not None:
                raise state["startup_error"]

        async def stop(self):
            state["stopped"] += 1

    monkeypatch.setattr(usage_module, "CopilotClient", Client)
    return state


def assert_cleaned_up(state):
    assert state["started"] == state["stopped"] == 1
    assert not Path(state["clients"][0]["base_directory"]).exists()


def test_reads_explicit_account_via_pinned_sdk_rpc_without_session_or_model(
    quota_runtime,
):
    result = asyncio.run(read_copilot_usage(live=True))
    quota_runtime["transport"].request.assert_awaited_once_with(
        "account.getQuota", {"gitHubToken": "test-personal-copilot-token"}
    )
    assert result["source"] == "copilot_sdk.account.getQuota"
    assert result["mode"] == "live_read_only"
    assert result["scope"] == "copilot_account"
    assert result["credential_source"] == "COPILOT_GITHUB_TOKEN"
    assert result["as_of"] is None
    assert datetime.fromisoformat(result["retrieved_at"]).tzinfo is not None
    assert (
        result["quota_snapshots"]["premium_interactions"] == quota_runtime["snapshot"]
    )
    assert "billing_amount" not in result
    assert "test-personal-copilot-token" not in json.dumps(result)
    client = quota_runtime["clients"][0]
    assert client["mode"] == "empty"
    assert client["use_logged_in_user"] is False
    assert client["github_token"] == "test-personal-copilot-token"
    assert client["base_directory"] == client["working_directory"]
    for key in (
        "COPILOT_GITHUB_TOKEN",
        "GITHUB_ADMIN_TOKEN",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "AZURE_OPENAI_API_KEY",
    ):
        assert key not in client["env"]
    assert_cleaned_up(quota_runtime)


@pytest.mark.parametrize("live", [False, "true", 1])
def test_opt_in_is_required_before_starting_any_runtime(quota_runtime, live):
    with pytest.raises(CopilotUsageError, match="--live"):
        asyncio.run(read_copilot_usage(live=live))
    assert quota_runtime["clients"] == []


@pytest.mark.parametrize("value", [None, "", "  "])
def test_no_fallback_to_admin_ambient_or_foundry_credentials(
    quota_runtime, monkeypatch, value
):
    if value is None:
        monkeypatch.delenv("COPILOT_GITHUB_TOKEN")
    else:
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", value)
    with pytest.raises(CopilotUsageError, match="Set COPILOT_GITHUB_TOKEN"):
        asyncio.run(read_copilot_usage(live=True))
    assert quota_runtime["clients"] == []


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeout_is_rejected_before_runtime_start(quota_runtime, timeout):
    with pytest.raises(CopilotUsageError, match="finite and positive"):
        asyncio.run(read_copilot_usage(live=True, timeout_seconds=timeout))
    assert quota_runtime["clients"] == []


def test_reports_every_returned_quota_type_without_assuming_premium(quota_runtime):
    quota_runtime["transport"].request.return_value = {
        "quotaSnapshots": {
            "chat": {
                **quota_runtime["snapshot"],
                "entitlementRequests": -1,
                "isUnlimitedEntitlement": True,
                "usedRequests": 0,
                "resetDate": None,
            },
            "completions": {**quota_runtime["snapshot"], "resetDate": None},
            "future_quota": {**quota_runtime["snapshot"], "resetDate": "2026-10-01"},
        }
    }
    result = asyncio.run(read_copilot_usage(live=True))
    assert set(result["quota_snapshots"]) == {"chat", "completions", "future_quota"}
    chat = result["quota_snapshots"]["chat"]
    assert chat["entitlementRequests"] == -1
    assert chat["isUnlimitedEntitlement"] is True
    assert chat["usedRequests"] == 0
    assert "resetDate" not in chat
    assert "remaining_requests" not in chat
    assert_cleaned_up(quota_runtime)


def test_overage_is_preserved_as_requests_not_converted_to_cost(quota_runtime):
    quota_runtime["snapshot"].update(
        usedRequests=305,
        remainingPercentage=0,
        overage=5,
        overageAllowedWithExhaustedQuota=True,
        usageAllowedWithExhaustedQuota=True,
    )
    result = asyncio.run(read_copilot_usage(live=True))
    assert result["quota_snapshots"]["premium_interactions"]["overage"] == 5
    assert any("not raw tokens, AI credits or USD" in note for note in result["notes"])


def test_empty_quota_is_unavailable_not_zero_or_mock_data(quota_runtime):
    quota_runtime["transport"].request.return_value = {"quotaSnapshots": {}}
    with pytest.raises(CopilotUsageError, match="no account quota snapshots"):
        asyncio.run(read_copilot_usage(live=True))
    assert_cleaned_up(quota_runtime)


@pytest.mark.parametrize(
    "error",
    [
        JsonRpcError(-32000, "401 test-personal-copilot-token"),
        JsonRpcError(-32000, "403 test-personal-copilot-token"),
        JsonRpcError(-32000, "429 test-personal-copilot-token"),
        RuntimeError("runtime failed test-personal-copilot-token"),
        ProcessExitedError("test-personal-copilot-token"),
        OSError("network failed test-personal-copilot-token"),
    ],
)
def test_transport_errors_are_explicit_and_do_not_echo_credentials(
    quota_runtime, caplog, error
):
    quota_runtime["transport"].request.side_effect = error
    with pytest.raises(CopilotUsageError, match="Quota lookup failed") as failure:
        asyncio.run(read_copilot_usage(live=True))
    assert "test-personal-copilot-token" not in str(failure.value) + caplog.text
    assert failure.value.__suppress_context__ is True
    assert_cleaned_up(quota_runtime)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"quotaSnapshots": None},
        {"quotaSnapshots": {"premium_interactions": {}}},
    ],
)
def test_malformed_provider_payload_is_unavailable(quota_runtime, payload):
    quota_runtime["transport"].request.return_value = payload
    with pytest.raises(CopilotUsageError, match="unsupported quota response"):
        asyncio.run(read_copilot_usage(live=True))
    assert_cleaned_up(quota_runtime)


@pytest.mark.parametrize(
    "change",
    [
        {"remainingPercentage": float("nan")},
        {"overage": float("inf")},
        {"resetDate": "not-a-date"},
    ],
)
def test_invalid_values_are_not_printed_as_valid_usage(quota_runtime, change):
    quota_runtime["snapshot"].update(change)
    with pytest.raises(CopilotUsageError, match="unsupported quota response"):
        asyncio.run(read_copilot_usage(live=True))
    assert_cleaned_up(quota_runtime)


def test_startup_failure_still_stops_runtime_and_cleans_directory(quota_runtime):
    quota_runtime["startup_error"] = OSError("runtime could not start")
    with pytest.raises(CopilotUsageError, match="Quota lookup failed"):
        asyncio.run(read_copilot_usage(live=True))
    quota_runtime["transport"].request.assert_not_awaited()
    assert_cleaned_up(quota_runtime)


def test_lookup_timeout_closes_runtime_without_retrying(quota_runtime):
    async def wait_forever(*_):
        await asyncio.Event().wait()

    quota_runtime["transport"].request.side_effect = wait_forever
    with pytest.raises(CopilotUsageError, match="timed out"):
        asyncio.run(read_copilot_usage(live=True, timeout_seconds=0.01))
    assert quota_runtime["transport"].request.await_count == 1
    assert_cleaned_up(quota_runtime)


def test_cancellation_is_not_swallowed_and_cleans_runtime(quota_runtime):
    async def run():
        started = asyncio.Event()

        async def wait_forever(*_):
            started.set()
            await asyncio.Event().wait()

        quota_runtime["transport"].request.side_effect = wait_forever
        task = asyncio.create_task(read_copilot_usage(live=True))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert_cleaned_up(quota_runtime)


def test_cli_rejects_missing_live_flag_before_access(
    quota_runtime, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "argv", ["finops_agent", "copilot-usage"])
    with pytest.raises(SystemExit) as result:
        cli_module.main()
    assert result.value.code == 2
    assert "--live" in capsys.readouterr().err
    assert quota_runtime["clients"] == []


@pytest.mark.parametrize("backend", ["mock", "github"])
@pytest.mark.parametrize("provider", ["copilot", "foundry-key", "foundry-identity"])
def test_cli_lookup_is_separate_from_org_backend_and_model_provider(
    quota_runtime, monkeypatch, capsys, backend, provider
):
    monkeypatch.setenv("FINOPS_BACKEND", backend)
    monkeypatch.setenv("FINOPS_MODEL_PROVIDER", provider)
    monkeypatch.setattr(sys, "argv", ["finops_agent", "copilot-usage", "--live"])

    def forbid_org_client(*_):
        pytest.fail("account lookup must not create an organization client")

    monkeypatch.setattr(cli_module, "create_finops_client", forbid_org_client)
    cli_module.main()
    output = capsys.readouterr()
    assert json.loads(output.out)["scope"] == "copilot_account"
    assert output.err == ""
    assert_cleaned_up(quota_runtime)


@pytest.mark.parametrize("extra", [["--instructor"], ["--data-dir", "private-data"]])
def test_cli_rejects_org_options(quota_runtime, monkeypatch, extra):
    monkeypatch.setattr(
        sys, "argv", ["finops_agent", *extra, "copilot-usage", "--live"]
    )
    with pytest.raises(SystemExit) as result:
        cli_module.main()
    assert result.value.code == 2
    assert quota_runtime["clients"] == []


def test_cli_errors_are_nonzero_without_raw_transport_data(
    quota_runtime, monkeypatch, capsys
):
    quota_runtime["transport"].request.side_effect = JsonRpcError(
        -32000, "denied: test-personal-copilot-token private-admin-token"
    )
    monkeypatch.setattr(sys, "argv", ["finops_agent", "copilot-usage", "--live"])
    with pytest.raises(SystemExit) as result:
        cli_module.main()
    output = capsys.readouterr()
    assert result.value.code == 1
    assert output.out == ""
    assert "quota unavailable" in output.err
    assert "test-personal-copilot-token" not in output.err
    assert "private-admin-token" not in output.err
    assert "Traceback" not in output.err


def test_cli_loads_service_dotenv_but_keeps_environment_priority(
    quota_runtime, monkeypatch, tmp_path, capsys
):
    (tmp_path / ".env").write_text(
        "COPILOT_GITHUB_TOKEN=test-dotenv-copilot-token\n", encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["finops_agent", "copilot-usage", "--live"])
    cli_module.main()
    assert quota_runtime["clients"][0]["github_token"] == "test-personal-copilot-token"
    assert "test-dotenv-copilot-token" not in capsys.readouterr().out
    monkeypatch.delenv("COPILOT_GITHUB_TOKEN")
    cli_module.main()
    assert quota_runtime["clients"][1]["github_token"] == "test-dotenv-copilot-token"
    assert "test-dotenv-copilot-token" not in capsys.readouterr().out
