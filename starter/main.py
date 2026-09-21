from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import sys
from collections.abc import AsyncIterator

from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from azure.ai.agentserver.invocations import InvocationAgentServerHost
from azure.ai.agentserver.responses import (
    CreateResponse,
    ResponseContext,
    ResponseEventStream,
    ResponsesAgentServerHost,
)
from azure.ai.agentserver.responses.models import ResponseStreamEvent
from starlette.requests import Request
from starlette.responses import JSONResponse

from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.harness import CopilotFinOpsHarness
from finops_agent.tools import FinOpsToolbox

load_dotenv(pathlib.Path(__file__).with_name(".env"), override=False)
logger = logging.getLogger(__name__)


class FinOpsAgentServerHost(InvocationAgentServerHost, ResponsesAgentServerHost):
    pass


app = FinOpsAgentServerHost()


class _AgentError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _validate_prompt(prompt: object) -> str:
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000:
        raise _AgentError(
            "invalid_request",
            "input must be a non-empty string of 1-8000 characters",
            400,
        )
    return prompt


@app.invoke_handler
async def handle_invoke(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _invalid_request("Request body must be valid UTF-8 JSON")
    if not isinstance(data, dict):
        return _invalid_request(
            "Request body must be a JSON object with an input string"
        )
    try:
        prompt = _validate_prompt(data.get("input"))
    except _AgentError as error:
        return _invalid_request(str(error))

    invocation_id = request.state.invocation_id
    try:
        reply, tool_calls = await _ask_agent(prompt, invocation_id)
    except _AgentError as error:
        return JSONResponse(
            {"error": error.code, "invocation_id": invocation_id},
            status_code=error.status_code,
        )
    return JSONResponse(
        {
            "reply": reply,
            "invocation_id": invocation_id,
            "tool_calls": tool_calls,
            "backend": "mock",
        }
    )


@app.response_handler
async def handle_response(
    request: CreateResponse,
    context: ResponseContext,
    cancellation_signal: asyncio.Event,
) -> AsyncIterator[ResponseStreamEvent]:
    stream = ResponseEventStream(response_id=context.response_id, request=request)
    yield stream.emit_created()
    yield stream.emit_in_progress()
    try:
        items = await context.get_input_items()
        if any(
            item.get("type") != "message"
            or any(part.get("type") != "input_text" for part in item.get("content", []))
            for item in items
        ):
            raise _AgentError(
                "invalid_request", "Only text message input is supported", 400
            )
        prompt = _validate_prompt(await context.get_input_text())
        reply, _ = await _ask_response(prompt, context.response_id, cancellation_signal)
    except _AgentError as error:
        logger.warning("Response %s rejected: %s", context.response_id, error.code)
        yield stream.emit_failed(code=error.code, message=str(error))
        return
    for event in stream.output_item_message(reply):
        yield event
    yield stream.emit_completed()


async def _ask_agent(prompt: str, request_id: str) -> tuple[str, list[str]]:
    # Lab 3 is isolated mock analysis/planning. Real writes stay on instructor CLI.
    try:
        async with asyncio.timeout(150):
            harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
            reply = await harness.ask(prompt)
            return reply, harness.tool_calls
    except TimeoutError as error:
        logger.warning("Request %s timed out", request_id)
        raise _AgentError("agent_timeout", "Agent request timed out", 504) from error
    except (OSError, RuntimeError, ValueError) as error:
        logger.error("Request %s failed: %s", request_id, type(error).__name__)
        raise _AgentError("agent_unavailable", "Agent is unavailable", 503) from error


async def _ask_response(
    prompt: str, response_id: str, cancellation_signal: asyncio.Event
) -> tuple[str, list[str]]:
    if cancellation_signal.is_set():
        raise asyncio.CancelledError
    answer = asyncio.create_task(_ask_agent(prompt, response_id))
    cancelled = asyncio.create_task(cancellation_signal.wait())
    try:
        await asyncio.wait((answer, cancelled), return_when=asyncio.FIRST_COMPLETED)
        if cancellation_signal.is_set():
            raise asyncio.CancelledError
        return await answer
    finally:
        answer.cancel()
        cancelled.cancel()
        await asyncio.gather(answer, cancelled, return_exceptions=True)


def _invalid_request(message: str) -> JSONResponse:
    logger.warning("Invocation rejected: invalid_request")
    return JSONResponse(
        {"error": "invalid_request", "message": message},
        status_code=400,
    )


if __name__ == "__main__":
    app.run()
