from __future__ import annotations

import asyncio
import atexit
import json
import logging
import os
import re
from collections.abc import Mapping, Sequence
from contextlib import AsyncExitStack, ExitStack
from functools import lru_cache
from pathlib import Path
from threading import Lock

from azure.core.exceptions import AzureError
from copilot import TelemetryConfig
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import AttributeValue

logger = logging.getLogger(__name__)
_EXPORT_LOCK = Lock()
_MAX_FILE_BYTES = 8 * 1024 * 1024
_MAX_SPANS = 2048
_ATTRIBUTES = frozenset(
    {
        "gen_ai.operation.name",
        "gen_ai.provider.name",
        "gen_ai.request.model",
        "gen_ai.response.model",
        "gen_ai.response.id",
        "gen_ai.response.finish_reasons",
        "gen_ai.conversation.id",
        "gen_ai.agent.id",
        "gen_ai.agent.name",
        "gen_ai.agent.version",
        "gen_ai.tool.name",
        "gen_ai.tool.type",
        "gen_ai.tool.call.id",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "gen_ai.usage.cache_read.input_tokens",
        "gen_ai.usage.cache_creation.input_tokens",
        "gen_ai.usage.reasoning.output_tokens",
        "github.copilot.cost",
        "github.copilot.server_duration",
        "github.copilot.turn_id",
        "github.copilot.turn_count",
        "github.copilot.interaction_id",
        "github.copilot.permission.kind",
        "github.copilot.permission.tool_name",
        "github.copilot.permission.result",
        "github.copilot.external_tool.name",
        "github.copilot.external_tool.call_id",
    }
)
_HOST_ATTRIBUTES = frozenset(
    {
        "gen_ai.agent.id",
        "gen_ai.agent.name",
        "gen_ai.agent.version",
        "gen_ai.conversation.id",
        "microsoft.foundry.project.id",
        "microsoft.session.id",
        "azure.ai.agentserver.invocations.invocation_id",
    }
)


def runtime_telemetry(stack: AsyncExitStack, home: str) -> TelemetryConfig | None:
    destination = os.getenv("FINOPS_OTEL_EXPORTER", "")
    local_file = os.getenv("FINOPS_OTEL_FILE", "")
    if destination not in ("", "azure-monitor"):
        raise ValueError("FINOPS_OTEL_EXPORTER must be empty or azure-monitor")
    if destination:
        if local_file:
            raise ValueError(
                "Set only one of FINOPS_OTEL_FILE and FINOPS_OTEL_EXPORTER"
            )
        connection = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
        if not connection.strip():
            raise ValueError(
                "FINOPS_OTEL_EXPORTER requires APPLICATIONINSIGHTS_CONNECTION_STRING"
            )
        auth_mode = os.getenv("APPLICATIONINSIGHTS_AUTH_MODE", "").strip().lower()
        if auth_mode not in ("", "entra"):
            raise ValueError("APPLICATIONINSIGHTS_AUTH_MODE must be empty or entra")
        path = Path(home) / "copilot-trace.jsonl"
        # Registered before the client: flush the runtime, export, then delete home.
        stack.push_async_callback(_flush_cloud, path, connection, auth_mode)
    elif local_file:
        if not local_file.strip():
            raise ValueError("FINOPS_OTEL_FILE must be a file path or empty to disable")
        path = Path(local_file).expanduser().resolve()
    else:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    os.close(descriptor)
    logger.info(
        "Copilot runtime tracing enabled (%s); content capture disabled",
        destination or "file",
    )
    return {
        "exporter_type": "file",
        "file_path": str(path),
        "source_name": "finops-agent",
        "capture_content": False,
    }


async def _flush_cloud(path: Path, connection: str, auth_mode: str) -> None:
    provider = trace.get_tracer_provider()
    resource = (
        provider.resource
        if isinstance(provider, TracerProvider)
        else Resource.create({"service.name": "copilot-finops-agent"})
    )
    current = trace.get_current_span()
    host_attributes = (
        {
            key: value
            for key, value in (current.attributes or {}).items()
            if key in _HOST_ATTRIBUTES
        }
        if isinstance(current, ReadableSpan)
        else {}
    )
    try:
        # Read before yielding: cancellation can delete home while export continues.
        spans = read_runtime_spans(path, resource, host_attributes)
    except (OSError, ValueError, KeyError, TypeError) as error:
        logger.error("Copilot trace buffer rejected (%s)", type(error).__name__)
        return
    if not spans:
        logger.warning("Copilot trace buffer contains no completed spans")
        return
    await asyncio.to_thread(_export_spans, spans, connection, auth_mode)


def read_runtime_spans(
    path: Path,
    resource: Resource,
    host_attributes: Mapping[str, AttributeValue] | None = None,
) -> list[ReadableSpan]:
    with path.open("rb") as stream:
        data = stream.read(_MAX_FILE_BYTES + 1)
    if len(data) > _MAX_FILE_BYTES:
        raise ValueError("Copilot trace buffer exceeds size limit")
    spans = []
    for line in data.splitlines():
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError("Invalid Copilot telemetry record")
        if record.get("type") != "span":
            continue
        if len(spans) >= _MAX_SPANS:
            raise ValueError("Copilot trace buffer exceeds span limit")
        trace_id = _identifier(record["traceId"], 32)
        span_id = _identifier(record["spanId"], 16)
        parent_id = record.get("parentSpanId")
        attributes = _safe_attributes(record["attributes"])
        if host_attributes:
            if "gen_ai.conversation.id" in host_attributes:
                conversation = attributes.get("gen_ai.conversation.id")
                if conversation is not None:
                    attributes["github.copilot.conversation.id"] = conversation
            attributes.update(host_attributes)
        start = _timestamp(record["startTime"])
        end = _timestamp(record["endTime"])
        if end < start:
            raise ValueError("Copilot span ends before it starts")
        name = record["name"]
        scope = record["instrumentationScope"]
        if not isinstance(name, str) or not name or not isinstance(scope, dict):
            raise ValueError("Invalid Copilot span name or scope")
        if scope.get("name") != "finops-agent" or not isinstance(
            scope.get("version"), str
        ):
            raise ValueError("Unexpected Copilot instrumentation scope")
        spans.append(
            ReadableSpan(
                name=name,
                context=_context(trace_id, span_id),
                parent=_context(trace_id, _identifier(parent_id, 16))
                if parent_id is not None
                else None,
                resource=resource,
                attributes=attributes,
                kind=trace.SpanKind(record["kind"]),
                status=trace.Status(trace.StatusCode(record["status"]["code"])),
                start_time=start,
                end_time=end,
                instrumentation_scope=InstrumentationScope(
                    name=scope["name"], version=scope["version"]
                ),
            )
        )
    return spans


def _safe_attributes(raw: object) -> dict[str, AttributeValue]:
    if not isinstance(raw, dict):
        raise ValueError("Invalid Copilot span attributes")
    attributes: dict[str, AttributeValue] = {}
    for key, value in raw.items():
        if key not in _ATTRIBUTES:
            continue
        if isinstance(value, str | bool | int | float):
            attributes[key] = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            attributes[key] = tuple(value)
        else:
            raise ValueError("Invalid Copilot metadata attribute")
    return attributes


def _identifier(value: object, length: int) -> int:
    if not isinstance(value, str) or not re.fullmatch(
        rf"[0-9a-fA-F]{{{length}}}", value
    ):
        raise ValueError("Invalid Copilot trace/span ID")
    identifier = int(value, 16)
    if not identifier:
        raise ValueError("Invalid zero Copilot trace/span ID")
    return identifier


def _context(trace_id: int, span_id: int) -> trace.SpanContext:
    return trace.SpanContext(
        trace_id,
        span_id,
        is_remote=False,
        trace_flags=trace.TraceFlags(trace.TraceFlags.SAMPLED),
    )


def _timestamp(value: object) -> int:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(part) is not int for part in value)
        or value[0] < 0
        or not 0 <= value[1] < 1_000_000_000
    ):
        raise ValueError("Invalid Copilot span timestamp")
    return value[0] * 1_000_000_000 + value[1]


@lru_cache(maxsize=1)
def _azure_exporter(connection: str, auth_mode: str) -> SpanExporter:
    from azure.identity import ManagedIdentityCredential
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

    with ExitStack() as stack:
        credential = None
        if auth_mode == "entra":
            credential = stack.enter_context(
                ManagedIdentityCredential(
                    connection_timeout=5, read_timeout=5, retry_total=0
                )
            )
        exporter = AzureMonitorTraceExporter(
            connection_string=connection,
            disable_offline_storage=True,
            timeout=5,
            read_timeout=5,
            retry_total=0,
            **({"credential": credential} if credential is not None else {}),
        )
        stack.callback(exporter.shutdown)
        atexit.register(stack.pop_all().close)
        return exporter


def _export_spans(
    spans: Sequence[ReadableSpan], connection: str, auth_mode: str
) -> None:
    try:
        # Reuse one exporter and serialize its mutable retry/redirect state.
        with _EXPORT_LOCK:
            result = _azure_exporter(connection, auth_mode).export(spans)
        if result is not SpanExportResult.SUCCESS:
            logger.error("Copilot runtime trace export failed; spans=%d", len(spans))
            return
        logger.info("Copilot runtime trace export succeeded; spans=%d", len(spans))
    except (AzureError, OSError, ValueError) as error:
        logger.error("Copilot runtime trace export failed (%s)", type(error).__name__)
