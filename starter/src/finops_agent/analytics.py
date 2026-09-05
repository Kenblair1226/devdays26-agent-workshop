from __future__ import annotations

import calendar
from collections import defaultdict
from collections.abc import Iterable
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from math import fsum, isfinite
from typing import Any

from .models import DepartmentAssignment, ReportingPeriod, UsageItem


class FinOpsAnalyzer:
    def __init__(
        self,
        usage_items: Iterable[UsageItem],
        assignments: Iterable[DepartmentAssignment],
        *,
        as_of: str | None,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._usage_items = list(usage_items)
        self._departments = {
            user: assignment.department
            for user, assignment in DepartmentAssignment.index(assignments).items()
        }
        self.as_of = as_of
        self.currency = currency
        aggregate_ranges = {
            (item.period.start, item.period.end)
            for item in self._usage_items
            if item.period is not None
        }
        if len(aggregate_ranges) > 1 or (
            aggregate_ranges
            and any(item.date is not None for item in self._usage_items)
        ):
            raise ValueError(
                "mixed daily/aggregate usage or aggregate periods unsupported"
            )
        self._metadata: dict[str, Any] = {
            "source": "caller-provided billing usage records",
            "retrieved_at": None,
            "granularity": "period_aggregate" if aggregate_ranges else "daily_records",
            "limitations": [
                "Completeness outside the supplied records is not established."
            ],
        }
        if metadata is not None:
            self._metadata.update(deepcopy(metadata))
        coverage = self._metadata.get("coverage")
        if coverage is None and self._usage_items:
            starts = [
                item.date if item.date is not None else item.period.start
                for item in self._usage_items
            ]
            ends = [
                item.date if item.date is not None else item.period.end
                for item in self._usage_items
            ]
            coverage = {
                "start": min(starts).isoformat(),
                "end": max(ends).isoformat(),
                "kind": "observed_record_bounds",
            }
            self._metadata["coverage"] = coverage
        self._coverage = (
            ReportingPeriod(
                date.fromisoformat(coverage["start"]),
                date.fromisoformat(coverage["end"]),
                "available_coverage",
            )
            if coverage is not None
            else None
        )
        for item in self._usage_items:
            unit = item.unit_type.casefold().replace("_", "").replace(" ", "")
            if unit not in {"aicredit", "aicredits", "credits"}:
                raise ValueError(
                    "AI-credit usage is required; raw tokens are not credits"
                )
            item_start = item.date if item.date is not None else item.period.start
            item_end = item.date if item.date is not None else item.period.end
            if self._coverage is not None and (
                item_start < self._coverage.start or item_end > self._coverage.end
            ):
                raise ValueError("usage record is outside declared coverage")
            if self.as_of is not None and item_end > self._reference_date():
                raise ValueError("usage record is after as_of")

    def resolve_period(
        self,
        period: str = "month_to_date",
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> ReportingPeriod:
        as_of_date = self._reference_date()
        if period != "custom" and (start is not None or end is not None):
            raise ValueError("start and end are only valid for a custom period")
        if period == "today":
            resolved = ReportingPeriod(as_of_date, as_of_date, "today")
        elif period == "month_to_date":
            resolved = ReportingPeriod(
                start=as_of_date.replace(day=1),
                end=as_of_date,
                label="month_to_date",
            )
        elif period == "last_28_days":
            resolved = ReportingPeriod(
                start=as_of_date - timedelta(days=27),
                end=as_of_date,
                label="last_28_days",
            )
        elif period == "previous_month":
            previous_end = as_of_date.replace(day=1) - timedelta(days=1)
            previous_start = previous_end.replace(day=1)
            resolved = ReportingPeriod(
                start=previous_start,
                end=previous_end,
                label="previous_month",
            )
        elif period == "custom":
            if not start or not end:
                raise ValueError("custom period requires start and end")
            resolved = ReportingPeriod(
                start=date.fromisoformat(start),
                end=date.fromisoformat(end),
                label="custom",
            )
        else:
            raise ValueError(
                "period must be today, month_to_date, last_28_days, previous_month, "
                "or custom"
            )
        self._validate_period(resolved)
        return resolved

    def cost_summary(self, period: ReportingPeriod) -> dict[str, Any]:
        records = self._records(period)
        return {
            **self._context(),
            "period": period.as_dict(),
            **{
                name: round(fsum(getattr(item, name) for item in records), 2)
                for name in (
                    "gross_quantity",
                    "net_quantity",
                    "discount_quantity",
                    "gross_amount",
                    "net_amount",
                    "discount_amount",
                )
            },
            "record_count": len(records),
            "user_count": len({item.user for item in records if item.user is not None}),
        }

    def rank_departments(
        self, period: ReportingPeriod, *, limit: int = 10
    ) -> dict[str, Any]:
        self._validate_limit(limit)
        # TODO(Lab 1): Group self._records(period) via self._department(item).
        # Sum net quantities/amounts; count distinct non-null users; sort and rank.
        # Preserve self._context(), period, and the full Unallocated total.
        raise NotImplementedError("Lab 1: implement department aggregation")

    def usage_breakdown(
        self,
        period: ReportingPeriod,
        *,
        dimension: str = "model",
        limit: int = 10,
        department: str | None = None,
    ) -> dict[str, Any]:
        if dimension not in {"model", "user", "department", "product"}:
            raise ValueError("dimension must be model, user, department, or product")
        self._validate_limit(limit)
        if department is not None and (
            not isinstance(department, str) or not department.strip()
        ):
            raise ValueError("department filter must be a non-empty string")
        records = self._records(period)
        if department is not None:
            records = [
                item
                for item in records
                if self._department(item).casefold() == department.strip().casefold()
            ]
            if not records:
                raise ValueError("usage data unavailable for the department filter")
        grouped: dict[str, dict[str, float]] = defaultdict(
            lambda: {"net_quantity": 0.0, "net_amount": 0.0}
        )
        for item in records:
            key = (
                self._department(item)
                if dimension == "department"
                else (getattr(item, dimension) or "Unallocated")
            )
            grouped[key]["net_quantity"] += item.net_quantity
            grouped[key]["net_amount"] += item.net_amount

        rows = [
            {
                dimension: key,
                "net_quantity": round(values["net_quantity"], 2),
                "net_amount": round(values["net_amount"], 2),
            }
            for key, values in grouped.items()
        ]
        rows.sort(key=lambda row: (-row["net_quantity"], str(row[dimension])))
        return {
            **self._context(),
            "period": period.as_dict(),
            "dimension": dimension,
            "department_filter": department,
            "total_net_quantity": round(fsum(item.net_quantity for item in records), 2),
            "total_net_amount": round(fsum(item.net_amount for item in records), 2),
            "items": rows[:limit],
        }

    def forecast_budget(
        self,
        period: ReportingPeriod,
        *,
        budget_amount: float,
    ) -> dict[str, Any]:
        self.validate_budget_amount(budget_amount)
        reference_date = self._reference_date()
        if (
            period.start != reference_date.replace(day=1)
            or period.end != reference_date
        ):
            raise ValueError("forecast requires a month-start-to-date reporting period")
        summary = self.cost_summary(period)
        elapsed_days = (period.end - period.start).days + 1
        days_in_month = calendar.monthrange(period.end.year, period.end.month)[1]
        projected_amount = summary["net_amount"] / elapsed_days * days_in_month
        remaining = budget_amount - summary["net_amount"]
        return {
            **self._context(),
            "period": period.as_dict(),
            "scenario_only": True,
            "budget_amount": round(budget_amount, 2),
            "consumed_amount": summary["net_amount"],
            "remaining_amount": round(remaining, 2),
            "projected_month_end_amount": round(projected_amount, 2),
            "projected_over_budget": projected_amount > budget_amount,
            "method": "month-to-date average daily run-rate projection to month end",
            "forecast_note": (
                "A scenario against the caller's amount, not an actual budget balance "
                "or final invoice. Assumes the observed run rate continues; excludes "
                "unreported usage and license fees. Use list_budgets for each budget's "
                "own consumed_amount and scope."
            ),
        }

    def _records(self, period: ReportingPeriod) -> list[UsageItem]:
        self._validate_period(period)
        records = [
            item
            for item in self._usage_items
            if (
                period.contains(item.date)
                if item.date is not None
                else (
                    item.period.start == period.start and item.period.end == period.end
                )
            )
        ]
        if not records:
            raise ValueError(
                "usage data unavailable: no records for this period; missing samples "
                "are not evidence of zero usage"
            )
        return records

    def _reference_date(self) -> date:
        if self.as_of is not None:
            parsed = datetime.fromisoformat(self.as_of.replace("Z", "+00:00"))
            if parsed.utcoffset() is None:
                raise ValueError("as_of must include a timezone")
            return parsed.astimezone(UTC).date()
        if self._coverage is not None:
            return self._coverage.end
        raise ValueError("usage data unavailable: no reporting date or coverage")

    def _validate_period(self, period: ReportingPeriod) -> None:
        if self._coverage is None:
            raise ValueError(
                "usage data unavailable: coverage has not been established"
            )
        if period.end > self._reference_date():
            raise ValueError("usage data unavailable after the reporting date")
        if period.start < self._coverage.start or period.end > self._coverage.end:
            raise ValueError(
                "usage data unavailable outside coverage "
                f"{self._coverage.start} through {self._coverage.end}"
            )
        if any(item.period is not None for item in self._usage_items) and (
            period.start != self._coverage.start or period.end != self._coverage.end
        ):
            raise ValueError(
                "usage data unavailable at daily granularity: only the complete "
                "reported aggregate period is supported"
            )

    def _department(self, item: UsageItem) -> str:
        return self._departments.get(item.user, "Unallocated")

    @staticmethod
    def validate_budget_amount(budget_amount: float) -> None:
        if (
            isinstance(budget_amount, bool)
            or not isinstance(budget_amount, int | float)
            or not isfinite(budget_amount)
            or budget_amount < 0
        ):
            raise ValueError("budget_amount must be a finite non-negative number")

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if type(limit) is not int or limit < 1:
            raise ValueError("limit must be a positive integer")

    def _context(self) -> dict[str, Any]:
        return {
            **deepcopy(self._metadata),
            "as_of": self.as_of,
            "currency": self.currency,
            "unit": "AI credits",
            "quantity_note": (
                "Net AI credits are a billing metric, not raw model tokens."
            ),
            "freshness_note": (
                "Snapshot as_of is known; this is not real-time usage."
                if self.as_of is not None
                else "Provider as_of is unknown; retrieved_at is retrieval time, "
                "not provider data freshness."
            ),
        }
