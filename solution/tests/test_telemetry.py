from __future__ import annotations

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from unittest.mock import Mock

import pytest
from azure.core.exceptions import ServiceRequestError
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExportResult

from finops_agent import telemetry

RESOURCE = Resource({"service.name": "hosted-finops", "service.version": "5"})


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch):
    for name in (
        "FINOPS_OTEL_FILE",
        "FINOPS_OTEL_EXPORTER",
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "APPLICATIONINSIGHTS_AUTH_MODE",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def record():
    return {
        "type": "span",
        "traceId": "0123456789abcdef0123456789abcdef",
        "spanId": "1111111111111111",
        "parentSpanId": "2222222222222222",
        "name": "chat gpt-5",
        "kind": 2,
        "startTime": [1700000000, 123456789],
        "endTime": [1700000001, 987654321],
        "attributes": {
            "gen_ai.operation.name": "chat",
            "gen_ai.request.model": "gpt-5",
            "gen_ai.usage.input_tokens": 12,
            "gen_ai.usage.output_tokens": 3,
            "gen_ai.conversation.id": "runtime-session",
            "gen_ai.response.finish_reasons": ["stop"],
            "gen_ai.input.messages": "private prompt",
            "gen_ai.output.messages": "private answer",
            "gen_ai.tool.call.arguments": "private arguments",
            "gen_ai.tool.call.result": "private result",
            "gen_ai.tool.definitions": "private definitions",
            "unknown.future.attribute": "private metadata",
            "server.address": "private endpoint",
        },
        "status": {"code": 2, "message": "private error"},
        "events": [{"name": "exception", "attributes": {"message": "private event"}}],
        "resource": {"attributes": {"service.name": "github-copilot"}},
        "instrumentationScope": {"name": "finops-agent", "version": "1.0.79"},
    }


def write_buffer(tmp_path, *records):
    path = tmp_path / "trace.jsonl"
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    return path


def test_conversion_preserves_context_timing_usage_and_host_identity(tmp_path, record):
    path = write_buffer(tmp_path, {"type": "metric"}, record)
    [span] = telemetry.read_runtime_spans(
        path,
        RESOURCE,
        {
            "gen_ai.agent.name": "hosted-finops",
            "gen_ai.conversation.id": "foundry-conv",
        },
    )
    assert span.context.trace_id == int(record["traceId"], 16)
    assert span.context.span_id == int(record["spanId"], 16)
    assert span.parent.trace_id == span.context.trace_id
    assert span.parent.span_id == int(record["parentSpanId"], 16)
    assert span.context.trace_flags.sampled
    assert span.start_time == 1700000000123456789
    assert span.end_time == 1700000001987654321
    assert span.kind is trace.SpanKind.CLIENT
    assert span.status.status_code is trace.StatusCode.ERROR
    assert span.status.description is None
    assert span.resource is RESOURCE
    assert span.instrumentation_scope.name == "finops-agent"
    assert span.instrumentation_scope.version == "1.0.79"
    assert span.attributes["gen_ai.usage.input_tokens"] == 12
    assert span.attributes["gen_ai.usage.output_tokens"] == 3
    assert span.attributes["gen_ai.response.finish_reasons"] == ("stop",)
    assert span.attributes["gen_ai.agent.name"] == "hosted-finops"
    assert span.attributes["gen_ai.conversation.id"] == "foundry-conv"
    assert span.attributes["github.copilot.conversation.id"] == "runtime-session"
    assert not span.events
    assert not span.links
    assert "private" not in span.to_json()


def test_root_span_and_all_native_kinds_are_supported(tmp_path, record):
    record.pop("parentSpanId")
    for kind in trace.SpanKind:
        record["kind"] = kind.value
        [span] = telemetry.read_runtime_spans(write_buffer(tmp_path, record), RESOURCE)
        assert span.kind is kind
        assert span.parent is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("traceId", "0" * 32),
        ("traceId", "not-a-trace"),
        ("spanId", "1" * 32),
        ("parentSpanId", "bad-parent"),
        ("parentSpanId", ""),
        ("startTime", [1, 1_000_000_000]),
        ("startTime", [True, 0]),
        ("endTime", [1, 0]),
        ("kind", 100),
        ("status", {"code": 100}),
        ("attributes", []),
        ("attributes", {"gen_ai.usage.input_tokens": {"bad": "shape"}}),
        ("name", None),
        ("instrumentationScope", {"name": "unexpected", "version": "1"}),
    ],
)
def test_invalid_span_fails_explicitly(tmp_path, record, field, value):
    record[field] = value
    with pytest.raises(ValueError):
        telemetry.read_runtime_spans(write_buffer(tmp_path, record), RESOURCE)


def test_buffer_limits_and_invalid_records(tmp_path, record, monkeypatch):
    path = write_buffer(tmp_path, record, record)
    monkeypatch.setattr(telemetry, "_MAX_SPANS", 1)
    with pytest.raises(ValueError, match="span limit"):
        telemetry.read_runtime_spans(path, RESOURCE)
    monkeypatch.setattr(telemetry, "_MAX_FILE_BYTES", 10)
    with pytest.raises(ValueError, match="size limit"):
        telemetry.read_runtime_spans(path, RESOURCE)
    path.write_text("null\n", encoding="utf-8")
    with pytest.raises(ValueError, match="record"):
        telemetry.read_runtime_spans(path, RESOURCE)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        telemetry.read_runtime_spans(path, RESOURCE)


@pytest.mark.parametrize(
    "settings,message",
    [
        ({"FINOPS_OTEL_EXPORTER": "otlp"}, "FINOPS_OTEL_EXPORTER"),
        (
            {"FINOPS_OTEL_EXPORTER": "azure-monitor", "FINOPS_OTEL_FILE": "old.jsonl"},
            "only one",
        ),
        ({"FINOPS_OTEL_EXPORTER": "azure-monitor"}, "CONNECTION_STRING"),
        (
            {
                "FINOPS_OTEL_EXPORTER": "azure-monitor",
                "APPLICATIONINSIGHTS_CONNECTION_STRING": "synthetic",
                "APPLICATIONINSIGHTS_AUTH_MODE": "unsupported",
            },
            "AUTH_MODE",
        ),
    ],
)
def test_configuration_errors(settings, message, monkeypatch, tmp_path):
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match=message):
        telemetry.runtime_telemetry(AsyncExitStack(), str(tmp_path))


def test_flush_uses_host_resource_and_attributes_off_event_loop(
    monkeypatch, tmp_path, record, caplog
):
    provider = TracerProvider(resource=RESOURCE)
    monkeypatch.setattr(trace, "get_tracer_provider", lambda: provider)
    exporter = Mock()
    exporter.export.return_value = SpanExportResult.SUCCESS
    monkeypatch.setattr(telemetry, "_azure_exporter", lambda *_: exporter)
    path = write_buffer(tmp_path, record)

    def export(spans):
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.get_running_loop()
        return SpanExportResult.SUCCESS

    exporter.export.side_effect = export
    with caplog.at_level(logging.INFO):
        with provider.get_tracer("test").start_as_current_span(
            "host", attributes={"gen_ai.agent.name": "hosted-finops"}
        ):
            asyncio.run(telemetry._flush_cloud(path, "synthetic", ""))
    [span] = exporter.export.call_args.args[0]
    assert span.resource is RESOURCE
    assert span.attributes["gen_ai.agent.name"] == "hosted-finops"
    assert "export succeeded; spans=1" in caplog.text
    assert "synthetic" not in caplog.text
    provider.shutdown()


@pytest.mark.parametrize("failure", ["result", "exception", "empty", "corrupt"])
def test_export_failures_are_logged_without_content(
    monkeypatch, tmp_path, record, caplog, failure
):
    exporter = Mock()
    exporter.export.return_value = SpanExportResult.FAILURE
    if failure == "exception":
        exporter.export.side_effect = ServiceRequestError("private credential")
    monkeypatch.setattr(telemetry, "_azure_exporter", lambda *_: exporter)
    path = write_buffer(tmp_path, record)
    if failure in ("empty", "corrupt"):
        path.write_text(
            "" if failure == "empty" else "private prompt", encoding="utf-8"
        )
    asyncio.run(telemetry._flush_cloud(path, "private connection", ""))
    assert caplog.records
    assert "succeeded" not in caplog.text
    assert "private" not in caplog.text
    if failure in ("empty", "corrupt"):
        exporter.export.assert_not_called()


@pytest.mark.parametrize("auth_mode", ["", "entra"])
def test_exporter_reuses_instance_without_reconfiguring_host(monkeypatch, auth_mode):
    import azure.identity
    import azure.monitor.opentelemetry.exporter as azure_exporter

    exporter = Mock()
    factory = Mock(return_value=exporter)
    credential = Mock()
    credential.__enter__ = Mock(return_value=credential)
    credential.__exit__ = Mock()
    identity_factory = Mock(return_value=credential)
    monkeypatch.setattr(azure_exporter, "AzureMonitorTraceExporter", factory)
    monkeypatch.setattr(azure.identity, "ManagedIdentityCredential", identity_factory)
    callbacks = []
    monkeypatch.setattr(telemetry.atexit, "register", callbacks.append)
    provider = trace.get_tracer_provider()
    telemetry._azure_exporter.cache_clear()
    try:
        assert telemetry._azure_exporter("synthetic", auth_mode) is exporter
        assert telemetry._azure_exporter("synthetic", auth_mode) is exporter
        factory.assert_called_once()
        kwargs = factory.call_args.kwargs
        assert kwargs["connection_string"] == "synthetic"
        assert kwargs["disable_offline_storage"] is True
        assert kwargs["timeout"] == kwargs["read_timeout"] == 5
        assert kwargs["retry_total"] == 0
        if auth_mode:
            assert kwargs["credential"] is credential
        else:
            assert "credential" not in kwargs
        assert trace.get_tracer_provider() is provider
    finally:
        for close in callbacks:
            close()
        telemetry._azure_exporter.cache_clear()
    exporter.shutdown.assert_called_once()
    if auth_mode:
        credential.__exit__.assert_called_once()
    else:
        identity_factory.assert_not_called()
