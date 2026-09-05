from __future__ import annotations

import hashlib
import json
import secrets
from copy import deepcopy
from datetime import UTC, datetime
from time import monotonic
from typing import Any
from uuid import uuid4

from .clients import GitHubFinOpsClient
from .models import ActionKind, ActionPlan, AuditEvent
from .policy import validate_action


class ApprovalWorkflow:
    def __init__(
        self, client: GitHubFinOpsClient, *, approval_ttl_seconds: int = 300
    ) -> None:
        if approval_ttl_seconds <= 0:
            raise ValueError("approval TTL must be positive")
        self._client = client
        self._plans: dict[str, ActionPlan] = {}
        self._audit_events: list[AuditEvent] = []
        self._proofs: dict[str, tuple[str, str, float]] = {}
        self._ttl = approval_ttl_seconds

    def create_plan(
        self,
        kind: ActionKind,
        target: str,
        payload: dict[str, Any],
        *,
        actor: str = "workshop-user",
    ) -> dict[str, Any]:
        payload = validate_action(
            kind,
            target,
            payload,
            self._client.organization,
            self._client.list_budgets() if kind == "update_budget" else [],
        )
        plan = ActionPlan(
            id=str(uuid4()),
            kind=kind,
            target=target,
            payload=payload,
            summary=self._summarize(kind, target, payload),
            created_at=datetime.now(UTC),
        )
        self._plans[plan.id] = plan
        self._record("plan_created", plan.id, actor, {"kind": kind})
        return deepcopy(plan.public_view())

    def approve(
        self,
        plan_id: str,
        *,
        actor: str = "workshop-approver",
        confirmed: bool = False,
    ) -> dict[str, Any]:
        plan = self._get_plan(plan_id)
        if confirmed is not True:
            self._record("approval_denied", plan.id, actor)
            raise PermissionError("explicit human confirmation is required")
        if plan.status == "executed":
            raise ValueError("executed plans cannot be approved again")
        if plan.status == "approved":
            raise ValueError("plan is already approved")
        plan.approval_token = secrets.token_urlsafe(24)
        self._proofs[plan.id] = (
            self._token_hash(plan.approval_token),
            self._fingerprint(plan),
            monotonic() + self._ttl,
        )
        plan.status = "approved"
        self._record("plan_approved", plan.id, actor)
        return {
            **deepcopy(plan.public_view()),
            "approval_token": plan.approval_token,
            "warning": "Treat this token as a one-time approval secret.",
        }

    def execute(
        self,
        plan_id: str,
        approval_token: str,
        *,
        actor: str = "workshop-executor",
    ) -> dict[str, Any]:
        plan = self._get_plan(plan_id)
        proof = self._proofs.get(plan.id)
        if plan.status == "planned" or proof is None:
            self._record("execution_denied", plan.id, actor, {"reason": "unapproved"})
            raise PermissionError("the plan must be approved before execution")
        if not isinstance(approval_token, str) or not secrets.compare_digest(
            proof[0], self._token_hash(approval_token)
        ):
            self._record("execution_denied", plan.id, actor, {"reason": "bad_token"})
            raise PermissionError("approval token does not match")
        if proof[1] != self._fingerprint(plan):
            self._record("execution_denied", plan.id, actor, {"reason": "changed_plan"})
            raise PermissionError("approved plan contents changed")
        if plan.status == "executed":
            return {
                **deepcopy(plan.public_view()),
                "result": deepcopy(plan.result),
                "idempotent_replay": True,
            }
        if monotonic() > proof[2]:
            self._record("execution_denied", plan.id, actor, {"reason": "expired"})
            plan.status = "planned"
            plan.approval_token = None
            del self._proofs[plan.id]
            raise PermissionError("approval expired; review and approve again")

        try:
            plan.result = self._client.execute_action(
                plan.kind, plan.target, deepcopy(plan.payload), human_approved=True
            )
        except (OSError, RuntimeError, ValueError, KeyError):
            self._record("execution_failed", plan.id, actor, {"retry": "manual_review"})
            plan.status = "planned"
            plan.approval_token = None
            del self._proofs[plan.id]
            raise
        plan.status = "executed"
        plan.approval_token = None
        self._record("plan_executed", plan.id, actor)
        return {
            **deepcopy(plan.public_view()),
            "result": deepcopy(plan.result),
            "idempotent_replay": False,
        }

    def get_audit_log(self) -> list[dict[str, Any]]:
        return deepcopy([event.as_dict() for event in self._audit_events])

    def get_plan(self, plan_id: str) -> dict[str, Any]:
        return deepcopy(self._get_plan(plan_id).public_view())

    def list_plans(self) -> list[dict[str, Any]]:
        return [self.get_plan(plan_id) for plan_id in self._plans]

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _fingerprint(plan: ActionPlan) -> str:
        content = json.dumps(
            [plan.kind, plan.target, plan.payload], sort_keys=True, allow_nan=False
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _get_plan(self, plan_id: str) -> ActionPlan:
        try:
            return self._plans[plan_id]
        except KeyError as error:
            raise KeyError(f"unknown plan: {plan_id}") from error

    def _record(
        self,
        event: str,
        plan_id: str,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._audit_events.append(
            AuditEvent(
                timestamp=datetime.now(UTC),
                event=event,
                plan_id=plan_id,
                actor=actor,
                details=details or {},
            )
        )

    @staticmethod
    def _summarize(kind: ActionKind, target: str, payload: dict[str, Any]) -> str:
        if kind in {"assign_seats", "remove_seats"}:
            users = ", ".join(payload.get("selected_usernames", []))
            return f"{kind} for {target}: {users}"
        if kind == "create_budget":
            return (
                f"create {payload.get('budget_scope', 'unknown')} budget for "
                f"{target}: {payload.get('budget_amount')} "
                f"{payload.get('budget_product_sku', '')}"
            )
        return f"update budget {target}: {payload}"
