from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from hypercorn.asyncio import serve
from hypercorn.config import Config
from starlette.applications import Starlette
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from .budget_demo import BudgetDemo
from .clients import MockGitHubFinOpsClient
from .harness import CopilotFinOpsHarness
from .tools import FinOpsToolbox

logger = logging.getLogger(__name__)


class DemoChat:
    def __init__(self, service: BudgetDemo) -> None:
        self.service = service
        self._stack = AsyncExitStack()
        self._harness: CopilotFinOpsHarness | None = None
        self._lock = asyncio.Lock()

    async def ask(self, message: str) -> tuple[str, list[str]]:
        from .demo_connection import build_demo_harness

        async with self._lock:
            if self._harness is None:
                harness = build_demo_harness(self.service)
                await self._stack.enter_async_context(harness.conversation())
                self._harness = harness
            try:
                reply = await self._harness.ask(message)
                return reply, list(self._harness.tool_calls)
            except (RuntimeError, TimeoutError, asyncio.CancelledError):
                await self.close()
                raise

    async def close(self) -> None:
        self._harness = None
        await self._stack.aclose()
        self._stack = AsyncExitStack()


def create_demo_app(service: BudgetDemo | None = None) -> Starlette:
    _check_demo_environment()
    service = service or BudgetDemo(FinOpsToolbox(MockGitHubFinOpsClient()))
    user_token = secrets.token_urlsafe(32)
    admin_token = secrets.token_urlsafe(32)
    chat = DemoChat(service)

    @asynccontextmanager
    async def lifespan(_app):
        try:
            yield
        finally:
            await chat.close()

    def permitted(request: Request, expected: str) -> bool:
        return secrets.compare_digest(
            request.headers.get("X-Demo-Token", "").encode("utf-8"),
            expected.encode("ascii"),
        )

    def denied() -> JSONResponse:
        return JSONResponse(
            {
                "error": "forbidden",
                "message": "This demo link cannot access that role.",
            },
            status_code=403,
        )

    async def body(request: Request, required: set[str]) -> dict:
        raw = await request.body()
        if len(raw) > 65536:
            raise ValueError("Request is too large")
        data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != required:
            raise ValueError("Invalid request fields")
        return data

    async def page(_request: Request) -> HTMLResponse:
        return HTMLResponse(
            Path(__file__).with_name("demo.html").read_text(encoding="utf-8"),
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'unsafe-inline'; "
                    "style-src 'unsafe-inline'; connect-src 'self'; "
                    "img-src 'self' data:; frame-ancestors 'none'"
                ),
            },
        )

    async def profile(request: Request) -> JSONResponse:
        if not permitted(request, user_token):
            return denied()
        return JSONResponse(service.profile(), headers={"Cache-Control": "no-store"})

    async def ask(request: Request) -> JSONResponse:
        if not permitted(request, user_token):
            return denied()
        try:
            data = await body(request, {"message"})
            message = data["message"]
            if not isinstance(message, str) or not 1 <= len(message.strip()) <= 4000:
                raise ValueError("Message must be 1-4000 characters")
        except (ValueError, UnicodeDecodeError) as error:
            return invalid(error)
        try:
            reply, tool_calls = await chat.ask(message)
        except NotImplementedError:
            return JSONResponse(
                {
                    "error": "sdk_not_connected",
                    "message": "Connect demo_connection.py to the SDK, then restart.",
                },
                status_code=503,
            )
        except (OSError, RuntimeError, ValueError) as error:
            logger.warning("Demo chat failed: %s", type(error).__name__)
            return JSONResponse(
                {
                    "error": "model_unavailable",
                    "message": (
                        "Check SDK credentials/network, or use the labelled "
                        "direct request form."
                    ),
                },
                status_code=504 if isinstance(error, TimeoutError) else 503,
            )
        return JSONResponse(
            {
                "reply": reply,
                "tool_calls": tool_calls,
                "profile": service.profile(),
            }
        )

    async def submit(request: Request) -> JSONResponse:
        if not permitted(request, user_token):
            return denied()
        try:
            data = await body(request, {"new_limit", "reason"})
            item = service.request_increase(**data)
        except (ValueError, UnicodeDecodeError) as error:
            return invalid(error)
        return JSONResponse({"request": item, "profile": service.profile()})

    async def admin(request: Request) -> JSONResponse:
        if not permitted(request, admin_token):
            return denied()
        return JSONResponse(
            {
                "requests": service.requests(),
                "audit": service.toolbox.get_audit_log()["events"],
            },
            headers={"Cache-Control": "no-store"},
        )

    async def approve(request: Request) -> JSONResponse:
        if not permitted(request, admin_token):
            return denied()
        try:
            data = await body(request, {"confirmed"})
            item = service.approve(request.path_params["request_id"], **data)
        except (ValueError, PermissionError, UnicodeDecodeError) as error:
            return invalid(error)
        except (OSError, RuntimeError) as error:
            logger.warning("Demo approval failed: %s", type(error).__name__)
            return JSONResponse(
                {
                    "error": "approval_failed",
                    "message": "The request was not completed; review before retrying.",
                },
                status_code=503,
            )
        return JSONResponse({"request": item})

    def invalid(error: Exception) -> JSONResponse:
        return JSONResponse(
            {"error": "invalid_request", "message": str(error)}, status_code=400
        )

    app = Starlette(
        routes=[
            Route("/", page),
            Route("/api/user", profile),
            Route("/api/chat", ask, methods=["POST"]),
            Route("/api/requests", submit, methods=["POST"]),
            Route("/api/admin", admin),
            Route(
                "/api/admin/requests/{request_id}/approve", approve, methods=["POST"]
            ),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )
    app.state.user_token = user_token
    app.state.admin_token = admin_token
    app.state.service = service
    app.state.chat = chat
    return app


def run_demo(*, port: int = 8098, user: str = "carol") -> None:
    _check_demo_environment()
    if not 1024 <= port <= 65535:
        raise ValueError("Choose a port between 1024 and 65535")
    app = create_demo_app(BudgetDemo(FinOpsToolbox(MockGitHubFinOpsClient()), user))
    root = f"http://127.0.0.1:{port}/"
    print(
        "Local mock role-play only; not production login. Keep the admin link private."
    )
    print(f"User:  {root}#view=user&token={app.state.user_token}", flush=True)
    print(f"Admin: {root}#view=admin&token={app.state.admin_token}", flush=True)
    config = Config()
    config.bind = [f"127.0.0.1:{port}"]
    config.accesslog = None
    asyncio.run(serve(app, config))


def _check_demo_environment() -> None:
    if os.getenv("FINOPS_BACKEND", "mock").lower() != "mock":
        raise ValueError("The browser demo is mock-only; set FINOPS_BACKEND=mock")
    if os.getenv("FINOPS_DATA_DIR"):
        raise ValueError(
            "Clear FINOPS_DATA_DIR before starting the bundled-data browser demo"
        )
