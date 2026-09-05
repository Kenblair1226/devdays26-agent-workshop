from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from math import isclose, isfinite
from typing import Any, Literal

ActionKind = Literal[
    "assign_seats",
    "remove_seats",
    "create_budget",
    "update_budget",
]


@dataclass(frozen=True)
class ReportingPeriod:
    start: date
    end: date
    label: str

    def __post_init__(self) -> None:
        if type(self.start) is not date or type(self.end) is not date:
            raise ValueError("reporting period start and end must be dates")
        if self.end < self.start:
            raise ValueError("period end must not be before start")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("reporting period label is required")

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end

    def as_dict(self) -> dict[str, str]:
        return {
            "label": self.label,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


@dataclass(frozen=True)
class UsageItem:
    """A daily sample or period aggregate; user=None is unattributed residual."""

    date: date | None
    user: str | None
    product: str
    sku: str
    model: str
    unit_type: str
    price_per_unit: float
    gross_quantity: float
    gross_amount: float
    discount_quantity: float
    discount_amount: float
    net_quantity: float
    net_amount: float
    period: ReportingPeriod | None = None

    def __post_init__(self) -> None:
        if (self.date is None) == (self.period is None):
            raise ValueError(
                "usage requires either a daily date or an aggregate period"
            )
        if self.date is not None and type(self.date) is not date:
            raise ValueError("usage date must be a date")
        if self.period is not None and not isinstance(self.period, ReportingPeriod):
            raise ValueError("usage period must be a ReportingPeriod")
        if self.user is not None:
            if not isinstance(self.user, str) or not self.user.strip():
                raise ValueError("usage user must be a non-empty login or null")
            object.__setattr__(self, "user", self.user.strip().casefold())
        for name in ("product", "sku", "model", "unit_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"usage {name} must be a non-empty string")
        for name in (
            "price_per_unit",
            "gross_quantity",
            "gross_amount",
            "discount_quantity",
            "discount_amount",
            "net_quantity",
            "net_amount",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not isfinite(value)
                or value < 0
            ):
                raise ValueError(f"usage {name} must be a finite non-negative number")
        for unit in ("quantity", "amount"):
            gross = getattr(self, f"gross_{unit}")
            discount = getattr(self, f"discount_{unit}")
            net = getattr(self, f"net_{unit}")
            if discount > gross or not isclose(
                gross - discount, net, rel_tol=1e-9, abs_tol=1e-6
            ):
                raise ValueError(f"inconsistent usage {unit}: gross - discount != net")

    @classmethod
    def from_dict(
        cls, value: dict[str, Any], *, period: ReportingPeriod | None = None
    ) -> UsageItem:
        if not isinstance(value, dict):
            raise ValueError("usage record must be an object")
        required = (
            "date",
            "user",
            "product",
            "sku",
            "model",
            "unit_type",
            "price_per_unit",
            "gross_quantity",
            "gross_amount",
            "discount_quantity",
            "discount_amount",
            "net_quantity",
            "net_amount",
        )
        missing = set(required) - value.keys()
        if missing:
            raise ValueError(f"usage record missing required fields: {sorted(missing)}")
        raw_date = value["date"]
        if raw_date is not None and not isinstance(raw_date, str):
            raise ValueError("usage date must be an ISO date string or null")
        fields = {name: value[name] for name in required}
        fields["date"] = date.fromisoformat(raw_date) if raw_date is not None else None
        return cls(**fields, period=period)


@dataclass(frozen=True)
class DepartmentAssignment:
    user: str
    department: str
    cost_center: str | None = None

    def __post_init__(self) -> None:
        for name in ("user", "department"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"department mapping {name} must be non-empty")
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "user", self.user.casefold())
        if self.cost_center is not None:
            if not isinstance(self.cost_center, str) or not self.cost_center.strip():
                raise ValueError("cost_center must be a non-empty string or null")
            object.__setattr__(self, "cost_center", self.cost_center.strip())

    @classmethod
    def index(
        cls, assignments: Iterable[DepartmentAssignment]
    ) -> dict[str, DepartmentAssignment]:
        """Deduplicate an already-resolved mapping, never fan out by team."""
        result: dict[str, DepartmentAssignment] = {}
        for assignment in assignments:
            previous = result.get(assignment.user)
            if previous is not None and previous != assignment:
                raise ValueError(
                    f"conflicting department assignments for {assignment.user}"
                )
            result[assignment.user] = assignment
        return result


@dataclass(frozen=True)
class UserMetric:
    user: str
    total_active_days: int
    ai_credits_used: float
    chat_requests: int
    code_completions: int
    lines_suggested: int
    lines_accepted: int
    last_activity_at: str | None
    period: ReportingPeriod | None = None
    source: str | None = None
    as_of: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.user, str) or not self.user.strip():
            raise ValueError("metric user must be a non-empty login")
        object.__setattr__(self, "user", self.user.strip().casefold())
        for name in (
            "total_active_days",
            "chat_requests",
            "code_completions",
            "lines_suggested",
            "lines_accepted",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"metric {name} must be a non-negative integer")
        if (
            isinstance(self.ai_credits_used, bool)
            or not isinstance(self.ai_credits_used, int | float)
            or not isfinite(self.ai_credits_used)
            or self.ai_credits_used < 0
        ):
            raise ValueError("metric ai_credits_used must be finite and non-negative")
        if self.lines_accepted > self.lines_suggested:
            raise ValueError("lines_accepted must not exceed lines_suggested")
        if self.period is not None:
            if not isinstance(self.period, ReportingPeriod):
                raise ValueError("metric period must be a ReportingPeriod")
            days = (self.period.end - self.period.start).days + 1
            if self.total_active_days > days:
                raise ValueError(
                    "total_active_days exceeds the metric reporting period"
                )
        for name in ("last_activity_at", "as_of"):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, str):
                    raise ValueError(f"metric {name} must be a timestamp or null")
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.utcoffset() is None:
                    raise ValueError(f"metric {name} must include a timezone")

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any],
        *,
        period: ReportingPeriod | None = None,
        source: str | None = None,
        as_of: str | None = None,
    ) -> UserMetric:
        if not isinstance(value, dict):
            raise ValueError("user metric must be an object")
        required = (
            "user",
            "total_active_days",
            "ai_credits_used",
            "chat_requests",
            "code_completions",
            "lines_suggested",
            "lines_accepted",
        )
        missing = set(required) - value.keys()
        if missing:
            raise ValueError(f"user metric missing required fields: {sorted(missing)}")
        return cls(
            **{name: value[name] for name in required},
            last_activity_at=value.get("last_activity_at"),
            period=period,
            source=source,
            as_of=as_of,
        )


@dataclass
class ActionPlan:
    id: str
    kind: ActionKind
    target: str
    payload: dict[str, Any]
    summary: str
    created_at: datetime
    status: Literal["planned", "approved", "executed"] = "planned"
    approval_token: str | None = None
    result: dict[str, Any] | None = None

    def public_view(self) -> dict[str, Any]:
        return {
            "plan_id": self.id,
            "kind": self.kind,
            "target": self.target,
            "payload": self.payload,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "requires_approval": self.status == "planned",
        }


@dataclass(frozen=True)
class AuditEvent:
    timestamp: datetime
    event: str
    plan_id: str
    actor: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event": self.event,
            "plan_id": self.plan_id,
            "actor": self.actor,
            "details": self.details,
        }
