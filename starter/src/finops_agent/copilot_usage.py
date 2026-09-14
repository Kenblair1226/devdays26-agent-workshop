from __future__ import annotations

import asyncio
import logging
import math
import os
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from tempfile import TemporaryDirectory
from typing import Any

from copilot import CopilotClient, StopError
from copilot.client import JsonRpcError, ProcessExitedError
from copilot.rpc import AccountGetQuotaRequest, AccountGetQuotaResult

from .harness import _runtime_environment

logger = logging.getLogger(__name__)


class CopilotUsageError(RuntimeError):
    """A safe-to-display failure of the optional account quota lookup."""


async def read_copilot_usage(
    *, live: bool = False, timeout_seconds: float = 20
) -> dict[str, Any]:
    """Read only the explicitly configured token's account; never create a session."""
    if live is not True:
        raise CopilotUsageError("Live account access requires explicit --live opt-in.")
    token = os.getenv("COPILOT_GITHUB_TOKEN", "").strip()
    if not token:
        raise CopilotUsageError(
            "Set COPILOT_GITHUB_TOKEN to your own Copilot credential. "
            "Saved CLI logins, admin tokens and Foundry keys are not used."
        )
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise CopilotUsageError("Quota lookup timeout must be finite and positive.")

    try:
        async with AsyncExitStack() as stack:
            home = stack.enter_context(TemporaryDirectory(prefix="finops-quota-"))
            client = CopilotClient(
                mode="empty",
                base_directory=home,
                working_directory=home,
                github_token=token,
                use_logged_in_user=False,
                env=_runtime_environment(),
                log_level="error",
            )
            stack.push_async_callback(client.stop)
            async with asyncio.timeout(timeout_seconds):
                await client.start()
                result = await client.rpc.account.get_quota(
                    AccountGetQuotaRequest(git_hub_token=token)
                )
            retrieved_at = datetime.now(UTC).isoformat()
            snapshots = _quota_snapshots(result)
    except TimeoutError:
        logger.warning("Copilot account quota lookup timed out")
        raise CopilotUsageError(
            "Quota lookup timed out. Check the SDK runtime and network, or skip "
            "this optional step; no model request or budget change was made."
        ) from None
    except (
        JsonRpcError,
        ProcessExitedError,
        StopError,
        OSError,
        RuntimeError,
    ) as error:
        logger.warning("Copilot account quota lookup failed (%s)", type(error).__name__)
        raise CopilotUsageError(
            "Quota lookup failed. Check token expiry, Copilot Requests permission, "
            "account policy, SDK runtime and network. Do not add org-admin access "
            "for this exercise; no usage value is available."
        ) from None
    except (AssertionError, TypeError, ValueError) as error:
        logger.warning("Unsupported Copilot quota response (%s)", type(error).__name__)
        raise CopilotUsageError(
            "GitHub returned an unsupported quota response. Keep the pinned SDK "
            "and runtime versions; unavailable data does not mean zero usage."
        ) from None

    if not snapshots:
        raise CopilotUsageError(
            "GitHub returned no account quota snapshots. This account or policy "
            "may not expose them; unavailable data does not mean zero usage."
        )
    return {
        "source": "copilot_sdk.account.getQuota",
        "mode": "live_read_only",
        "scope": "copilot_account",
        "credential_source": "COPILOT_GITHUB_TOKEN",
        "retrieved_at": retrieved_at,
        "as_of": None,
        "quota_snapshots": snapshots,
        "notes": [
            "Account-wide entitlement counters, not usage attributed to this key "
            "or to this demo session.",
            "SDK request counters and overage are not raw tokens, AI credits or "
            "USD. No billing amount is calculated.",
            "Quota types depend on the account. An unlimited flag or entitlement "
            "of -1 means no finite entitlement cap; do not infer remaining requests.",
            "GitHub may update quota data with a delay. retrieved_at is the time "
            "of this lookup, not the provider's last update.",
            "This is separate from carol's mock budget and Foundry inference "
            "costs, regardless of FINOPS_MODEL_PROVIDER or FINOPS_BACKEND.",
        ],
    }


def _quota_snapshots(result: AccountGetQuotaResult) -> dict[str, Any]:
    snapshots = {}
    for kind, snapshot in result.quota_snapshots.items():
        if not kind.strip():
            raise ValueError("Quota type must not be blank")
        if not all(
            math.isfinite(value)
            for value in (snapshot.overage, snapshot.remaining_percentage)
        ):
            raise ValueError("Quota counters must be finite")
        if snapshot.reset_date is not None:
            datetime.fromisoformat(snapshot.reset_date)
        snapshots[kind] = snapshot.to_dict()
    return snapshots
