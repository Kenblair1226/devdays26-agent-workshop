"""Opt-in transport check: real Copilot SDK/runtime, loopback fake model, no Azure."""

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SpanExportResult

from finops_agent import telemetry
from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.harness import CopilotFinOpsHarness
from finops_agent.tools import FinOpsToolbox


@pytest.mark.skipif(
    os.getenv("FINOPS_TEST_RUNTIME") != "1",
    reason="Set FINOPS_TEST_RUNTIME=1 after downloading the SDK-pinned runtime",
)
@pytest.mark.parametrize("destination", ["file", "azure-monitor"])
@pytest.mark.parametrize(
    "operation,arguments",
    [
        ("rank_department_consumption", {"period": "month_to_date"}),
        (
            "plan_action",
            {
                "kind": "remove_seats",
                "target": "octo-demo",
                "payload": {"selected_usernames": ["judy"]},
            },
        ),
        ("get_my_costs", {}),
        ("get_my_savings", {}),
        ("investigation_path", {}),
        ("request_budget_increase", {"new_limit": 220, "reason": "Migration project"}),
        (
            "plan_action",
            {
                "kind": "create_budget",
                "target": "octo-demo",
                "payload": {
                    "budget_scope": "user",
                    "user": "carol",
                    "budget_amount": 220,
                    "budget_type": "BundlePricing",
                    "budget_product_sku": "ai_credits",
                    "prevent_further_usage": True,
                },
            },
        ),
    ],
)
def test_real_sdk_calls_finops_tool_without_cloud_credentials(
    monkeypatch, tmp_path, operation, arguments, destination
):
    telemetry_path = tmp_path / "copilot-trace.jsonl"
    monkeypatch.setenv("FINOPS_OTEL_FILE", str(telemetry_path))
    monkeypatch.delenv("FINOPS_OTEL_EXPORTER", raising=False)
    exported = []
    cloud_paths = []

    class Exporter:
        def export(self, batch):
            exported.extend(batch)
            return SpanExportResult.SUCCESS

    monkeypatch.setattr(telemetry, "_azure_exporter", lambda *_: Exporter())
    if destination == "azure-monitor":
        monkeypatch.delenv("FINOPS_OTEL_FILE")
        monkeypatch.setenv("FINOPS_OTEL_EXPORTER", "azure-monitor")
        monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "synthetic")
        monkeypatch.delenv("APPLICATIONINSIGHTS_AUTH_MODE", raising=False)
        flush = telemetry._flush_cloud

        async def capture_buffer(path, connection, auth_mode):
            cloud_paths.append(path)
            telemetry_path.write_bytes(path.read_bytes())
            await flush(path, connection, auth_mode)

        monkeypatch.setattr(telemetry, "_flush_cloud", capture_buffer)
    trace_id = 0x0123456789ABCDEF0123456789ABCDEF
    parent_id = 0x0123456789ABCDEF
    observed = {"requests": 0, "tool_result": None, "tools": []}
    actions = (
        [
            ("get_daily_usage_trend", {}),
            ("break_down_usage", {"dimension": "model", "department": "AI Lab"}),
            ("get_team_roster", {"department": "AI Lab"}),
            ("get_workflow_evidence", {"department": "AI Lab", "limit": 2}),
            ("get_team_roster", {"department": "Security"}),
            ("get_workflow_evidence", {"department": "Security", "limit": 2}),
            ("forecast_budget", {"budget_amount": 600}),
            ("compare_improvement_options", {}),
        ]
        if operation == "investigation_path"
        else [(operation, arguments)]
    )

    class Model(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            observed["requests"] += 1
            offered = [
                tool["function"]["name"]
                for tool in data.get("tools", [])
                if "function" in tool
            ]
            observed["tools"] = offered
            results = [m for m in data["messages"] if m["role"] == "tool"]
            if results:
                observed["tool_result"] = results[-1]["content"]
                observed["tool_results"] = [row["content"] for row in results]
            if len(results) == len(actions):
                message = {
                    "role": "assistant",
                    "content": "FinOps tool result recorded.",
                }
                reason = "stop"
            else:
                next_operation, next_arguments = actions[len(results)]
                name = next(n for n in offered if n.endswith(next_operation))
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call-finops-{len(results) + 1}",
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(next_arguments),
                            },
                        }
                    ],
                }
                reason = "tool_calls"
            if data.get("stream"):
                delta = dict(message)
                if "tool_calls" in delta:
                    delta["tool_calls"][0]["index"] = 0
                chunks = [
                    {
                        "id": "chatcmpl-test",
                        "object": "chat.completion.chunk",
                        "model": "gpt-5",
                        "choices": [{"index": 0, "delta": delta}],
                    },
                    {
                        "id": "chatcmpl-test",
                        "object": "chat.completion.chunk",
                        "model": "gpt-5",
                        "choices": [{"index": 0, "delta": {}, "finish_reason": reason}],
                        "usage": {
                            "prompt_tokens": 1,
                            "completion_tokens": 1,
                            "total_tokens": 2,
                        },
                    },
                ]
                payload = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks)
                body = (payload + "data: [DONE]\n\n").encode()
                content_type = "text/event-stream"
            else:
                body = json.dumps(
                    {
                        "id": "chatcmpl-test",
                        "object": "chat.completion",
                        "model": "gpt-5",
                        "choices": [
                            {"index": 0, "message": message, "finish_reason": reason}
                        ],
                        "usage": {
                            "prompt_tokens": 1,
                            "completion_tokens": 1,
                            "total_tokens": 2,
                        },
                    }
                ).encode()
                content_type = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Model)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.delenv("COPILOT_GITHUB_TOKEN", raising=False)
    provider = {
        "type": "openai",
        "base_url": f"http://127.0.0.1:{server.server_port}/v1",
        "wire_api": "completions",
        "api_key": "synthetic-local-only",
    }
    monkeypatch.setattr(
        CopilotFinOpsHarness,
        "_model_configuration",
        staticmethod(lambda _stack: (provider, "gpt-5")),
    )
    try:
        toolbox = FinOpsToolbox(MockGitHubFinOpsClient())
        personal = operation in {
            "get_my_costs",
            "get_my_savings",
            "request_budget_increase",
        }
        if personal:
            from finops_agent.budget_demo import BudgetDemo
            from finops_agent.demo_connection import build_demo_harness

            service = BudgetDemo(toolbox)
            harness = build_demo_harness(service)
        else:
            harness = CopilotFinOpsHarness(toolbox, timeout_seconds=45)
        prompt = "Which department used the most AI credits?"
        parent = trace.NonRecordingSpan(
            trace.SpanContext(
                trace_id=trace_id,
                span_id=parent_id,
                is_remote=False,
                trace_flags=trace.TraceFlags(trace.TraceFlags.SAMPLED),
            )
        )
        with trace.use_span(parent):
            answer = asyncio.run(harness.ask(prompt))
        assert answer == "FinOps tool result recorded."
        assert observed["requests"] >= 2
        raw_trace = telemetry_path.read_text(encoding="utf-8")
        spans = [
            entry
            for line in raw_trace.splitlines()
            if (entry := json.loads(line)).get("type") == "span"
        ]
        assert spans
        assert all(
            span["instrumentationScope"]["name"] == "finops-agent" for span in spans
        )
        operations = {span["attributes"].get("gen_ai.operation.name") for span in spans}
        assert {"invoke_agent", "chat", "execute_tool"} <= operations
        assert all(span["traceId"] == f"{trace_id:032x}" for span in spans)
        invocation = next(
            span
            for span in spans
            if span["attributes"].get("gen_ai.operation.name") == "invoke_agent"
        )
        assert invocation["parentSpanId"] == f"{parent_id:016x}"
        chat_spans = [
            span
            for span in spans
            if span["attributes"].get("gen_ai.operation.name") == "chat"
        ]
        assert len(chat_spans) == len(actions) + 1
        for span in chat_spans:
            assert span["parentSpanId"] == invocation["spanId"]
            assert span["attributes"]["gen_ai.usage.input_tokens"] == 1
            assert span["attributes"]["gen_ai.usage.output_tokens"] == 1
        tool_spans = [
            span
            for span in spans
            if span["attributes"].get("gen_ai.operation.name") == "execute_tool"
        ]
        assert any(
            span["attributes"]["gen_ai.tool.name"].endswith(actions[0][0])
            for span in tool_spans
        )
        assert all(span["parentSpanId"] == invocation["spanId"] for span in tool_spans)
        for span in spans:
            assert span["endTime"] >= span["startTime"]
            assert (
                not {
                    "gen_ai.input.messages",
                    "gen_ai.output.messages",
                    "gen_ai.tool.call.arguments",
                    "gen_ai.tool.call.result",
                }
                & span["attributes"].keys()
            )
        assert prompt not in raw_trace
        assert answer not in raw_trace
        assert "synthetic-local-only" not in raw_trace
        converted = telemetry.read_runtime_spans(
            telemetry_path, Resource({"service.name": "test-host"})
        )
        assert len(converted) == len(spans)
        for original, span in zip(spans, converted, strict=True):
            assert span.context.trace_id == int(original["traceId"], 16)
            assert span.context.span_id == int(original["spanId"], 16)
            assert span.parent.span_id == int(original["parentSpanId"], 16)
            assert span.resource.attributes["service.name"] == "test-host"
            assert (
                span.attributes["gen_ai.conversation.id"]
                == (original["attributes"]["gen_ai.conversation.id"])
            )
            assert "synthetic-local-only" not in span.to_json()
            assert prompt not in span.to_json()
            assert answer not in span.to_json()

        if destination == "azure-monitor":
            assert len(cloud_paths) == 1
            assert not cloud_paths[0].parent.exists()
        else:
            asyncio.run(telemetry._flush_cloud(telemetry_path, "synthetic", ""))
        assert [span.context for span in exported] == [
            span.context for span in converted
        ]
        if personal:
            assert "alice" not in str(observed["tool_result"])
            if operation == "request_budget_increase":
                from starlette.testclient import TestClient

                from finops_agent.demo_server import create_demo_app

                app = create_demo_app(service)
                pending = service.requests()[0]
                assert pending["status"] == "pending"
                assert service.profile()["budget"]["budget_amount"] == 150
                url = f"/api/admin/requests/{pending['id']}/approve"
                with TestClient(app) as admin_client:
                    assert (
                        admin_client.post(
                            url,
                            headers={"X-Demo-Token": app.state.user_token},
                            json={"confirmed": True},
                        ).status_code
                        == 403
                    )
                    assert (
                        admin_client.post(
                            url,
                            headers={"X-Demo-Token": app.state.admin_token},
                            json={"confirmed": True},
                        ).status_code
                        == 200
                    )
                    updated = admin_client.get(
                        "/api/user", headers={"X-Demo-Token": app.state.user_token}
                    ).json()
                    assert updated["budget"]["budget_amount"] == 220
                    assert updated["budget"]["remaining_amount"] == 117.33
            elif operation == "get_my_costs":
                assert "10266.67" in str(observed["tool_result"])
                assert "remaining_amount" in str(observed["tool_result"])
            else:
                assert "recommendations" in str(observed["tool_result"])
        elif operation == "investigation_path":
            assert [name.removeprefix("custom:") for name in harness.tool_calls] == [
                name for name, _args in actions
            ]
            assert len(observed["tool_results"]) == len(actions)
            assert "0.953333" in str(observed["tool_results"][3])
            assert "duplicate_success_candidates" in str(observed["tool_results"][5])
            assert "47600" in str(observed["tool_results"][6])
            assert "temporary_budget" in str(observed["tool_results"][7])
            assert toolbox.list_action_plans() == []
            assert toolbox.get_audit_log()["events"] == []
            assert toolbox.list_budgets()["budgets"][1]["budget_amount"] == 150
        elif operation == "rank_department_consumption":
            assert "AI Lab" in str(observed["tool_result"])
            assert "17600" in str(observed["tool_result"])
        else:
            from finops_agent.local_cli import _confirm_and_execute

            plan = toolbox.list_action_plans()[0]
            assert plan["status"] == "planned"
            with pytest.raises(PermissionError):
                toolbox.execute_approved_action(plan["plan_id"], "model-cannot-approve")
            monkeypatch.setattr(
                "builtins.input", lambda _: f"APPROVE {plan['plan_id']}"
            )
            result = _confirm_and_execute(toolbox, plan["plan_id"])
            assert result["status"] == "executed"
            assert result["result"]["mock"] is True
            assert toolbox.get_audit_log()["events"][-1]["event"] == "plan_executed"
        assert "approve_action" not in observed["tools"]
        assert not {"shell", "bash", "powershell", "read_file"} & set(observed["tools"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
