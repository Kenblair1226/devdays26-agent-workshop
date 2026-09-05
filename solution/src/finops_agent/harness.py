from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from tempfile import TemporaryDirectory
from typing import Self

from copilot import CopilotClient
from copilot.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject
from copilot.session import CopilotSession, PermissionRequest, ProviderConfig
from copilot.session_events import (
    AssistantMessageData,
    PermissionRequestCustomTool,
    SessionErrorData,
    SessionEvent,
    SessionIdleData,
    ToolExecutionStartData,
)

from .instructions import FINOPS_AGENT_INSTRUCTIONS
from .sdk_tools import build_sdk_tools
from .tools import FinOpsToolbox


class CopilotFinOpsHarness:
    """One explicitly scoped conversation; the SDK owns its stdio runtime."""

    def __init__(
        self,
        toolbox: FinOpsToolbox,
        *,
        model: str | None = None,
        timeout_seconds: float = 120,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout must be positive")
        self.toolbox = toolbox
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.tool_calls: list[str] = []
        self._session: CopilotSession | None = None
        self._turn_lock = asyncio.Lock()

    @asynccontextmanager
    async def conversation(self) -> AsyncIterator[Self]:
        if self._session is not None:
            raise RuntimeError("conversation is already open")
        async with AsyncExitStack() as stack:
            provider, model = self._model_configuration(stack)
            token = os.getenv("COPILOT_GITHUB_TOKEN")
            if provider is None and not token:
                raise ValueError(
                    "Set COPILOT_GITHUB_TOKEN for Lab 2, or configure "
                    "FINOPS_MODEL_PROVIDER and its model credentials."
                )
            home = stack.enter_context(TemporaryDirectory(prefix="finops-sdk-"))
            tools = build_sdk_tools(self.toolbox)
            tool_names = {tool.name for tool in tools}

            def permit(
                request: PermissionRequest, _invocation: dict[str, str]
            ) -> PermissionDecisionApproveOnce | PermissionDecisionReject:
                if (
                    isinstance(request, PermissionRequestCustomTool)
                    and not request.managed_approval_required
                    and request.tool_name.removeprefix("custom:") in tool_names
                ):
                    return PermissionDecisionApproveOnce()
                return PermissionDecisionReject(
                    feedback="Only registered FinOps custom tools are allowed."
                )

            client = CopilotClient(
                mode="empty",
                base_directory=home,
                working_directory=home,
                github_token=token if provider is None else None,
                use_logged_in_user=False,
                env=_runtime_environment(),
            )
            async with asyncio.timeout(self.timeout_seconds):
                await stack.enter_async_context(client)
                session = await client.create_session(
                    model=self.model or model,
                    provider=provider,
                    tools=tools,
                    available_tools=[f"custom:{tool.name}" for tool in tools],
                    system_message={
                        "mode": "append",
                        "content": FINOPS_AGENT_INSTRUCTIONS,
                    },
                    on_permission_request=permit,
                    enable_session_store=False,
                    enable_config_discovery=False,
                    enable_file_hooks=False,
                    enable_host_git_operations=False,
                    enable_skills=False,
                    streaming=False,
                )
            try:
                async with session:
                    self._session = session
                    yield self
            finally:
                self._session = None
                await client.delete_session(session.session_id)

    async def ask(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must not be blank")
        if self._session is None:
            async with self.conversation():
                return await self._ask_in_session(prompt)
        return await self._ask_in_session(prompt)

    async def _ask_in_session(self, prompt: str) -> str:
        session = self._session
        if session is None:
            raise RuntimeError("conversation is not open")
        async with self._turn_lock:
            done = asyncio.Event()
            messages: list[str] = []
            errors: list[str] = []
            self.tool_calls = []

            def on_event(event: SessionEvent) -> None:
                if isinstance(event.data, AssistantMessageData):
                    messages.append(event.data.content)
                elif isinstance(event.data, SessionErrorData):
                    errors.append(event.data.message)
                    done.set()
                elif isinstance(event.data, ToolExecutionStartData):
                    self.tool_calls.append(event.data.tool_name)
                elif isinstance(event.data, SessionIdleData):
                    done.set()

            unsubscribe = session.on(on_event)
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    await session.send(prompt)
                    await done.wait()
                if errors:
                    raise RuntimeError(f"Copilot session failed: {errors[0]}")
                if not messages:
                    raise RuntimeError("Copilot session completed without an answer")
                return messages[-1]
            except (TimeoutError, asyncio.CancelledError):
                await session.abort()
                raise
            finally:
                unsubscribe()

    @staticmethod
    def _model_configuration(
        stack: AsyncExitStack,
    ) -> tuple[ProviderConfig | None, str]:
        provider = os.getenv("FINOPS_MODEL_PROVIDER", "copilot")
        if provider == "copilot":
            return None, os.getenv("COPILOT_MODEL", "gpt-5")
        if provider == "foundry-key":
            url = os.getenv("FOUNDRY_MODEL_URL")
            key = os.getenv("FOUNDRY_API_KEY")
            model = os.getenv("COPILOT_MODEL")
            if not url or not key or not model:
                raise ValueError(
                    "foundry-key requires FOUNDRY_MODEL_URL, FOUNDRY_API_KEY, "
                    "and COPILOT_MODEL (deployment name)"
                )
            return {
                "type": "openai",
                "base_url": url,
                "api_key": key,
                "wire_api": "responses",
            }, model
        if provider == "foundry-identity":
            endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
            model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
            if not endpoint or not model:
                raise ValueError(
                    "foundry-identity requires FOUNDRY_PROJECT_ENDPOINT and "
                    "AZURE_AI_MODEL_DEPLOYMENT_NAME"
                )
            from azure.identity.aio import DefaultAzureCredential

            credential = DefaultAzureCredential()
            stack.push_async_callback(credential.close)

            async def token_provider() -> str:
                token = await credential.get_token("https://ai.azure.com/.default")
                return token.token

            return {
                "type": "openai",
                "base_url": endpoint.rstrip("/") + "/openai/v1",
                "wire_api": "responses",
                "bearer_token_provider": token_provider,
            }, model
        raise ValueError(
            "FINOPS_MODEL_PROVIDER must be copilot, foundry-key, or foundry-identity"
        )


def _runtime_environment() -> dict[str, str]:
    # Do not pass the instructor's billing credential to the model runtime.
    required = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "SYSTEMDRIVE",
        "COMSPEC",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "TEMP",
        "TMP",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "SSL_CERT_FILE",
        "NODE_EXTRA_CA_CERTS",
        "LANG",
        "LC_ALL",
    }
    return {
        key: value
        for key, value in os.environ.items()
        if key.upper() in required or key.startswith("COPILOT_CLI_")
    }
