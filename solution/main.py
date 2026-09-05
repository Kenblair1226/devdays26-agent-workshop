from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import sys

from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from azure.ai.agentserver.invocations import InvocationAgentServerHost
from starlette.requests import Request
from starlette.responses import JSONResponse

from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.harness import CopilotFinOpsHarness
from finops_agent.tools import FinOpsToolbox

load_dotenv(pathlib.Path(__file__).with_name(".env"), override=False)
logger = logging.getLogger(__name__)
app = InvocationAgentServerHost()


@app.invoke_handler
async def handle_invoke(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _invalid_request()
    if not isinstance(data, dict):
        return _invalid_request()
    prompt = data.get("input")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000:
        return _invalid_request()

    # Lab 3 is isolated mock analysis/planning. Real writes stay on instructor CLI.
    harness = CopilotFinOpsHarness(FinOpsToolbox(MockGitHubFinOpsClient()))
    invocation_id = request.state.invocation_id
    try:
        async with asyncio.timeout(150):
            reply = await harness.ask(prompt)
    except TimeoutError:
        logger.warning("Invocation %s timed out", invocation_id)
        return JSONResponse(
            {"error": "agent_timeout", "invocation_id": invocation_id},
            status_code=504,
        )
    except (OSError, RuntimeError, ValueError) as error:
        logger.error("Invocation %s failed: %s", invocation_id, type(error).__name__)
        return JSONResponse(
            {"error": "agent_unavailable", "invocation_id": invocation_id},
            status_code=503,
        )
    return JSONResponse(
        {
            "reply": reply,
            "invocation_id": invocation_id,
            "tool_calls": harness.tool_calls,
            "backend": "mock",
        }
    )


def _invalid_request() -> JSONResponse:
    return JSONResponse(
        {"error": "invalid_request", "message": "input must be 1-8000 characters"},
        status_code=400,
    )


if __name__ == "__main__":
    app.run()
