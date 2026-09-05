from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from copilot.tools import Tool, ToolInvocation, ToolResult

from .tools import FinOpsToolbox

logger = logging.getLogger(__name__)


def build_sdk_tools(toolbox: FinOpsToolbox) -> list[Tool]:
    period_schema = _period_schema(toolbox.client.supported_periods)
    return [
        _tool(
            "get_cost_summary",
            "Get gross and net AI-credit cost for a reporting period.",
            period_schema,
            lambda args: toolbox.get_cost_summary(**args),
        ),
        _tool(
            "rank_department_consumption",
            "Rank departments by net AI-credit consumption.",
            {
                **period_schema,
                "properties": {
                    **period_schema["properties"],
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
            },
            lambda args: toolbox.rank_department_consumption(**args),
        ),
        _tool(
            "break_down_usage",
            "Break AI-credit usage down by model, user, department, or product.",
            {
                **period_schema,
                "properties": {
                    **period_schema["properties"],
                    "dimension": {
                        "type": "string",
                        "enum": ["model", "user", "department", "product"],
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                    "department": {
                        "type": ["string", "null"],
                        "description": "Optional department filter for drilldown.",
                    },
                },
            },
            lambda args: toolbox.break_down_usage(**args),
        ),
        _tool(
            "forecast_budget",
            "Project month-end spend using the current daily run rate.",
            {
                **period_schema,
                "properties": {
                    **period_schema["properties"],
                    "budget_amount": {"type": "number", "minimum": 0},
                },
                "required": ["budget_amount"],
            },
            lambda args: toolbox.forecast_budget(**args),
        ),
        _tool(
            "recommend_optimizations",
            "Return evidence-backed AI-credit, prompt, seat, and budget "
            "recommendations.",
            period_schema,
            lambda args: toolbox.recommend_optimizations(**args),
        ),
        _tool(
            "list_seats",
            "List Copilot seats and last activity. This tool is read-only.",
            {"type": "object", "properties": {}, "additionalProperties": False},
            lambda _args: toolbox.list_seats(),
        ),
        _tool(
            "list_budgets",
            "List current Copilot budgets and consumed amounts. "
            "This tool is read-only.",
            {"type": "object", "properties": {}, "additionalProperties": False},
            lambda _args: toolbox.list_budgets(),
        ),
        _tool(
            "plan_action",
            "Create a dry-run plan for a seat or budget change. Does not write.",
            {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "assign_seats",
                            "remove_seats",
                            "create_budget",
                            "update_budget",
                        ],
                    },
                    "target": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["kind", "target", "payload"],
                "additionalProperties": False,
            },
            lambda args: toolbox.plan_action(**args),
        ),
        _tool(
            "execute_approved_action",
            "Execute a plan only with its one-time human approval token.",
            {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string"},
                    "approval_token": {"type": "string"},
                },
                "required": ["plan_id", "approval_token"],
                "additionalProperties": False,
            },
            lambda args: toolbox.execute_approved_action(**args),
        ),
        _tool(
            "get_audit_log",
            "Read the in-memory audit trail for planned, approved, "
            "and executed actions.",
            {"type": "object", "properties": {}, "additionalProperties": False},
            lambda _args: toolbox.get_audit_log(),
        ),
    ]


def _tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    function: Callable[[dict[str, Any]], dict[str, Any]],
) -> Tool:
    async def handler(invocation: ToolInvocation) -> ToolResult:
        try:
            if invocation.arguments is not None and not isinstance(
                invocation.arguments, dict
            ):
                raise ValueError("tool arguments must be an object")
            args = invocation.arguments or {}
            if set(args) - set(parameters["properties"]):
                raise ValueError("unknown tool argument")
            if not set(parameters.get("required", [])) <= set(args):
                raise ValueError("missing required tool argument")
            result = function(args)
        except (KeyError, PermissionError, TypeError, ValueError) as error:
            logger.warning(
                "finops.tool rejected name=%s error=%s", name, type(error).__name__
            )
            return ToolResult(
                text_result_for_llm=json.dumps(
                    {"error": str(error)}, ensure_ascii=False
                ),
                result_type="failure",
                session_log=f"{name} rejected the request",
            )
        logger.info("finops.tool completed name=%s", name)
        return ToolResult(
            text_result_for_llm=json.dumps(result, ensure_ascii=False, allow_nan=False),
            result_type="success",
            session_log=f"{name} completed",
        )

    return Tool(
        name=name,
        description=description,
        parameters=parameters,
        handler=handler,
    )


def _period_schema(periods: set[str] | None = None) -> dict[str, Any]:
    available = (
        periods
        if periods is not None
        else {"today", "month_to_date", "last_28_days", "previous_month", "custom"}
    )
    return {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "enum": sorted(available),
                "default": "month_to_date",
            },
            "start": {
                "type": ["string", "null"],
                "format": "date",
                "description": "Required only when period is custom.",
            },
            "end": {
                "type": ["string", "null"],
                "format": "date",
                "description": "Required only when period is custom.",
            },
        },
        "additionalProperties": False,
    }
