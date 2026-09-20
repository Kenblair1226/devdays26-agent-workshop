from __future__ import annotations

import calendar
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from math import fsum, isclose
from typing import Any

from .analytics import FinOpsAnalyzer
from .clients import MockGitHubFinOpsClient, _number, _objects, _text, _timestamp
from .models import ReportingPeriod, UsageItem


@dataclass(frozen=True)
class WorkflowRun:
    run_id: str
    period: str
    date: date
    started_at: datetime
    user: str
    department: str
    workflow: str
    task_id: str
    input_revision: str
    result_digest: str | None
    trigger: str
    status: str
    model: str
    net_quantity: float
    net_amount: float

    @property
    def outcome_key(self) -> tuple[str, str, str]:
        return self.workflow, self.task_id, self.input_revision

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "date": self.date.isoformat(),
            "started_at": self.started_at.isoformat(),
        }

    @classmethod
    def from_dict(
        cls, row: dict[str, Any], periods: dict[str, ReportingPeriod]
    ) -> WorkflowRun:
        period = _text(row.get("period"), "run.period")
        if period not in periods:
            raise ValueError("workflow run has an unknown reporting period")
        day = date.fromisoformat(_text(row.get("date"), "run.date"))
        timestamp = _timestamp(row.get("started_at"), "run.started_at")
        assert timestamp is not None
        started = datetime.fromisoformat(timestamp).astimezone(UTC)
        if started.date() != day or not periods[period].contains(day):
            raise ValueError("workflow run is outside its declared date or period")
        status = _text(row.get("status"), "run.status")
        if status not in {"success", "failure"}:
            raise ValueError("unsupported workflow status")
        digest = row.get("result_digest")
        if status == "success" or digest is not None:
            digest = _text(digest, "run.result_digest")
        return cls(
            run_id=_text(row.get("run_id"), "run.run_id"),
            period=period,
            date=day,
            started_at=started,
            user=_text(row.get("user"), "run.user").casefold(),
            department=_text(row.get("department"), "run.department"),
            workflow=_text(row.get("workflow"), "run.workflow"),
            task_id=_text(row.get("task_id"), "run.task_id"),
            input_revision=_text(row.get("input_revision"), "run.input_revision"),
            result_digest=digest,
            trigger=_text(row.get("trigger"), "run.trigger"),
            status=status,
            model=_text(row.get("model"), "run.model"),
            net_quantity=_number(row.get("net_quantity"), "run.net_quantity"),
            net_amount=_number(row.get("net_amount"), "run.net_amount"),
        )


def _run_summary(runs: list[WorkflowRun]) -> dict[str, Any]:
    if not runs:
        raise ValueError("workflow evidence is unavailable; no runs in this scope")
    successful_outcomes = set()
    seen_results = set()
    duplicates = []
    for run in sorted(runs, key=lambda row: (row.started_at, row.run_id)):
        if run.status != "success":
            continue
        successful_outcomes.add(run.outcome_key)
        result_key = (*run.outcome_key, run.model, run.result_digest)
        if result_key in seen_results:
            duplicates.append(run)
        else:
            seen_results.add(result_key)
    amount = fsum(run.net_amount for run in runs)
    quantity = fsum(run.net_quantity for run in runs)
    successes = len(successful_outcomes)
    return {
        "run_count": len(runs),
        "successful_attempts": sum(run.status == "success" for run in runs),
        "successful_tasks": successes,
        "net_quantity": round(quantity, 2),
        "net_amount": round(amount, 2),
        "cost_per_successful_task_usd": round(amount / successes, 6)
        if successes
        else None,
        "credits_per_successful_task": round(quantity / successes, 6)
        if successes
        else None,
        "duplicate_success_candidates": len(duplicates),
        "duplicate_candidate_credits": round(
            fsum(run.net_quantity for run in duplicates), 2
        ),
        "duplicate_candidate_amount": round(
            fsum(run.net_amount for run in duplicates), 2
        ),
        "duplicate_run_ids": [run.run_id for run in duplicates],
    }


class InvestigationEvidence:
    """On-demand mock business context, never an organization API adapter."""

    def __init__(self, client: MockGitHubFinOpsClient) -> None:
        if not isinstance(client, MockGitHubFinOpsClient):
            raise ValueError("investigation context is available only for mock data")
        self.client = client
        self._departments = {
            row.user: row.department for row in client.get_department_assignments()
        }
        snapshot = datetime.fromisoformat(client.as_of).date()
        self.period = ReportingPeriod(
            snapshot.replace(day=1), snapshot, "month_to_date"
        )

    def _context(self, document: dict[str, Any]) -> dict[str, Any]:
        if (
            type(document.get("schema_version")) is not int
            or document["schema_version"] != 1
        ):
            raise ValueError("unsupported investigation evidence schema")
        if document.get("organization") != self.client.organization:
            raise ValueError("investigation organization does not match billing")
        if document.get("as_of") != self.client.as_of:
            raise ValueError("investigation snapshot does not match billing")
        limitations = document.get("limitations")
        if not isinstance(limitations, list) or any(
            not isinstance(note, str) for note in limitations
        ):
            raise ValueError("investigation limitations must be an array of strings")
        return {
            "backend": "mock",
            "organization": self.client.organization,
            "as_of": self.client.as_of,
            "source": _text(document.get("source"), "investigation.source"),
            "currency": self.client.currency,
            "unit": "AI credits",
            "limitations": deepcopy(limitations),
        }

    @staticmethod
    def _period(value: Any, label: str) -> ReportingPeriod:
        if not isinstance(value, dict):
            raise ValueError(f"{label} period must be an object")
        return ReportingPeriod(
            date.fromisoformat(_text(value.get("start"), f"{label}.start")),
            date.fromisoformat(_text(value.get("end"), f"{label}.end")),
            label,
        )

    def _department(self, value: str) -> str:
        name = _text(value, "department").casefold()
        for department in set(self._departments.values()):
            if department.casefold() == name:
                return department
        raise ValueError("team context is unavailable for this department")

    def _baseline(
        self,
    ) -> tuple[dict[str, Any], ReportingPeriod, list[UsageItem], FinOpsAnalyzer]:
        document = self.client.get_investigation_fixture("usage-comparison")
        context = self._context(document)
        current = self._period(document.get("current_period"), "current")
        if (current.start, current.end) != (self.period.start, self.period.end):
            raise ValueError("comparison current period does not match billing")
        baseline = document.get("baseline")
        if not isinstance(baseline, dict):
            raise ValueError("comparison baseline is unavailable")
        period = self._period(baseline.get("period"), "matched_baseline")
        if period.end >= self.period.start or (
            period.end - period.start != self.period.end - self.period.start
        ):
            raise ValueError("comparison requires earlier, equal-length periods")
        records = [
            UsageItem.from_dict(row)
            for row in _objects(baseline.get("usage_items"), "baseline.usage_items")
        ]
        timestamp = _timestamp(baseline.get("as_of"), "baseline.as_of")
        analyzer = FinOpsAnalyzer(
            records,
            self.client.get_department_assignments(),
            as_of=timestamp,
            currency=self.client.currency,
            metadata={
                "source": context["source"],
                "granularity": "daily_samples",
                "coverage": {
                    "start": period.start.isoformat(),
                    "end": period.end.isoformat(),
                    "kind": "matched_synthetic_period",
                },
                "limitations": context["limitations"],
            },
        )
        return context, period, records, analyzer

    def daily_trend(self, analyzer: FinOpsAnalyzer) -> dict[str, Any]:
        context, baseline_period, baseline_records, reference = self._baseline()
        current = analyzer.cost_summary(self.period)
        baseline = reference.cost_summary(baseline_period)
        current_records = [
            item
            for item in self.client.get_usage_items()
            if item.date is not None and self.period.contains(item.date)
        ]
        current_quantity = fsum(row.net_quantity for row in current_records)
        baseline_quantity = fsum(row.net_quantity for row in baseline_records)
        current_amount = fsum(row.net_amount for row in current_records)
        baseline_amount = fsum(row.net_amount for row in baseline_records)
        current_groups = analyzer.rank_departments(self.period, limit=50)["ranking"]
        prior_groups = {
            row["department"]: row
            for row in reference.rank_departments(baseline_period, limit=50)["ranking"]
        }
        changes = []
        for row in current_groups:
            previous = prior_groups.get(row["department"])
            if previous is None:
                raise ValueError("comparison attribution is incomplete")
            current_department = [
                item
                for item in current_records
                if self._departments.get(item.user, "Unallocated") == row["department"]
            ]
            baseline_department = [
                item
                for item in baseline_records
                if self._departments.get(item.user, "Unallocated") == row["department"]
            ]
            changes.append(
                {
                    "department": row["department"],
                    "current_net_quantity": row["net_quantity"],
                    "baseline_net_quantity": previous["net_quantity"],
                    "credit_change": round(
                        fsum(item.net_quantity for item in current_department)
                        - fsum(item.net_quantity for item in baseline_department),
                        2,
                    ),
                    "current_net_amount": row["net_amount"],
                    "baseline_net_amount": previous["net_amount"],
                    "amount_change": round(
                        fsum(item.net_amount for item in current_department)
                        - fsum(item.net_amount for item in baseline_department),
                        2,
                    ),
                }
            )
        changes.sort(key=lambda row: (-row["credit_change"], row["department"]))
        return {
            **context,
            "current": analyzer.daily_usage(self.period),
            "baseline": reference.daily_usage(baseline_period),
            "current_summary": current,
            "baseline_summary": baseline,
            "change": {
                "net_quantity": round(current_quantity - baseline_quantity, 2),
                "net_amount": round(current_amount - baseline_amount, 2),
                "credits_percent": (
                    round((current_quantity / baseline_quantity - 1) * 100, 2)
                    if baseline_quantity
                    else None
                ),
                "amount_percent": (
                    round((current_amount / baseline_amount - 1) * 100, 2)
                    if baseline_amount
                    else None
                ),
            },
            "department_changes": changes,
            "next_evidence": (
                "Compare users/models, then request relevant team and workflow context "
                "before treating growth or a high rank as waste."
            ),
        }

    def team_roster(self, department: str) -> dict[str, Any]:
        department = self._department(department)
        document = self.client.get_investigation_fixture("team-roster")
        context = self._context(document)
        teams = [
            row
            for row in _objects(document.get("teams"), "teams")
            if row.get("department") == department
        ]
        if len(teams) != 1:
            raise ValueError("team roster must contain one matching department")
        team = teams[0]
        members = team.get("members")
        expected = {
            user for user, name in self._departments.items() if name == department
        }
        if (
            not isinstance(members, list)
            or any(not isinstance(user, str) for user in members)
            or len(members) != len(set(members))
            or set(members) != expected
        ):
            raise ValueError("team roster conflicts with the financial mapping")
        _text(team.get("initiative"), "team.initiative")
        _text(team.get("success_definition"), "team.success_definition")
        deadline = team.get("deadline")
        if deadline is not None:
            date.fromisoformat(_text(deadline, "team.deadline"))
        for plan in _objects(
            team.get("planned_remaining_tasks"), "planned_remaining_tasks"
        ):
            if plan.get("user") not in expected:
                raise ValueError("planned work belongs to an unknown team member")
            _text(plan.get("workflow"), "planned_work.workflow")
            _count(plan.get("count"), "planned_work.count")
        return {**context, "team": deepcopy(team)}

    def _runs(
        self,
    ) -> tuple[dict[str, Any], dict[str, ReportingPeriod], list[WorkflowRun]]:
        document = self.client.get_investigation_fixture("workflow-runs")
        context = self._context(document)
        raw_periods = document.get("periods")
        if not isinstance(raw_periods, dict) or set(raw_periods) != {
            "current",
            "baseline",
        }:
            raise ValueError("workflow periods must identify current and baseline")
        periods = {
            name: self._period(value, name) for name, value in raw_periods.items()
        }
        _, baseline_period, baseline_records, _ = self._baseline()
        for actual, expected in (
            (periods["current"], self.period),
            (periods["baseline"], baseline_period),
        ):
            if (actual.start, actual.end) != (expected.start, expected.end):
                raise ValueError("workflow period does not match the billing evidence")
        runs = [
            WorkflowRun.from_dict(row, periods)
            for row in _objects(document.get("runs"), "workflow runs")
        ]
        if len({run.run_id for run in runs}) != len(runs):
            raise ValueError("workflow run IDs must be unique")
        for run in runs:
            if run.department != self._departments.get(run.user, "Unallocated"):
                raise ValueError("workflow department conflicts with financial mapping")
        for name, records in (
            ("current", self.client.get_usage_items()),
            ("baseline", baseline_records),
        ):
            expected_totals = defaultdict(lambda: [[], []])
            actual_totals = defaultdict(lambda: [[], []])
            for item in records:
                if item.date is not None and periods[name].contains(item.date):
                    key = item.date, item.user, item.model
                    expected_totals[key][0].append(item.net_quantity)
                    expected_totals[key][1].append(item.net_amount)
            for run in runs:
                if run.period == name:
                    key = run.date, run.user, run.model
                    actual_totals[key][0].append(run.net_quantity)
                    actual_totals[key][1].append(run.net_amount)
            if actual_totals.keys() != expected_totals.keys():
                raise ValueError("workflow coverage does not reconcile with billing")
            for key, totals in expected_totals.items():
                if any(
                    not isclose(fsum(expected), fsum(actual), rel_tol=0, abs_tol=1e-6)
                    for expected, actual in zip(totals, actual_totals[key], strict=True)
                ):
                    raise ValueError("workflow costs do not reconcile with billing")
        return context, periods, runs

    def workflow_evidence(self, department: str, limit: int = 6) -> dict[str, Any]:
        department = self._department(department)
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("workflow sample limit must be an integer from 1 to 20")
        context, periods, runs = self._runs()
        result = {**context, "department": department}
        for name, period in periods.items():
            selected = [
                run
                for run in runs
                if run.period == name and run.department == department
            ]
            sample = sorted(selected, key=lambda run: (run.started_at, run.run_id))[
                :limit
            ]
            result[name] = {
                "period": period.as_dict(),
                "summary": _run_summary(selected),
                "by_user": [
                    {
                        "user": user,
                        **_run_summary([run for run in selected if run.user == user]),
                    }
                    for user in sorted({run.user for run in selected})
                ],
                "by_workflow": [
                    {
                        "workflow": workflow,
                        **_run_summary(
                            [run for run in selected if run.workflow == workflow]
                        ),
                    }
                    for workflow in sorted({run.workflow for run in selected})
                ],
                "runs": [run.as_dict() for run in sample],
                "returned_runs": len(sample),
                "total_runs": len(selected),
                "truncated": len(sample) != len(selected),
                "summary_scope": "all validated runs for this department and period",
            }
        result["interpretation"] = (
            "Successful tasks are distinct workflow/task/input-revision outcomes, not "
            "attempt counts. Duplicate candidates also require the same successful "
            "result digest and model; failed retries or changed revisions are "
            "not duplicates. "
            "Confirm workflow policy before changing triggers. Compare like-for-like "
            "task definitions, not different teams' productivity."
        )
        return result

    def improvement_options(self) -> dict[str, Any]:
        context, periods, runs = self._runs()
        current = [run for run in runs if run.period == "current"]
        days = (self.period.end - self.period.start).days + 1
        remaining_days = (
            calendar.monthrange(self.period.end.year, self.period.end.month)[1]
            - self.period.end.day
        )
        remaining_start = (
            self.period.end + timedelta(days=1) if remaining_days else None
        )
        review = [
            run
            for run in current
            if run.department == "Security" and run.workflow == "automated-review"
        ]
        review_summary = _run_summary(review)
        review_roster = self.team_roster("Security")
        duplicate_ids = set(review_summary["duplicate_run_ids"])
        duplicate_amount = fsum(
            run.net_amount for run in review if run.run_id in duplicate_ids
        )
        duplicate_credits = fsum(
            run.net_quantity for run in review if run.run_id in duplicate_ids
        )

        pilot_document = self.client.get_investigation_fixture("model-pilots")
        pilot_context = self._context(pilot_document)
        pilots = [
            row
            for row in _objects(pilot_document.get("pilots"), "model pilots")
            if row.get("department") == "Platform Engineering"
            and row.get("workflow") == "simple-maintenance"
        ]
        if len(pilots) != 1:
            raise ValueError("a matched simple-task model pilot is required")
        pilot = pilots[0]
        sample_tasks = _count(pilot.get("sample_tasks"), "pilot.sample_tasks")
        if sample_tasks == 0 or pilot.get("currency") != self.client.currency:
            raise ValueError("pilot needs sampled tasks and matching currency")
        successes = [
            _count(
                pilot.get(f"{name}_successful_tasks"), f"pilot.{name}_successful_tasks"
            )
            for name in ("baseline", "candidate")
        ]
        if any(count > sample_tasks for count in successes):
            raise ValueError("pilot successes exceed the sample size")
        quality_passed = all(count == sample_tasks for count in successes)
        base_cost = _number(
            pilot.get("baseline_net_amount"), "pilot.baseline_net_amount"
        )
        candidate_cost = _number(
            pilot.get("candidate_net_amount"), "pilot.candidate_net_amount"
        )
        if base_cost == 0:
            raise ValueError("pilot baseline cost must be positive")
        baseline_model = _text(pilot.get("baseline_model"), "pilot.baseline_model")
        candidate_model = _text(pilot.get("candidate_model"), "pilot.candidate_model")
        if baseline_model == candidate_model:
            raise ValueError("pilot must compare different models")
        eligible = [
            run
            for run in current
            if run.department == "Platform Engineering"
            and run.workflow == "simple-maintenance"
            and run.model == baseline_model
        ]
        if not eligible:
            raise ValueError("pilot has no matching observed workload")
        eligible_cost = fsum(run.net_amount for run in eligible)
        ratio = candidate_cost / base_cost
        routing_amount = (
            eligible_cost * (1 - ratio) if quality_passed and ratio < 1 else None
        )

        roster = self.team_roster("AI Lab")
        plans = [
            row
            for row in roster["team"]["planned_remaining_tasks"]
            if row["user"] == "carol" and row["workflow"] == "migration"
        ]
        if len(plans) != 1:
            raise ValueError("one remaining-work estimate is required for carol")
        personal_runs = [
            run
            for run in current
            if run.user == "carol" and run.workflow == "migration"
        ]
        personal_summary = _run_summary(personal_runs)
        if not personal_summary["successful_tasks"]:
            raise ValueError(
                "migration has no successful tasks for a unit-cost estimate"
            )
        future_cost = (
            fsum(run.net_amount for run in personal_runs)
            / personal_summary["successful_tasks"]
            * plans[0]["count"]
        )
        budgets = [
            budget
            for budget in self.client.list_budgets()
            if budget["budget_scope"] == "user" and budget.get("user") == "carol"
        ]
        if len(budgets) != 1 or budgets[0]["consumed_amount"] is None:
            raise ValueError("carol's budget consumption is unavailable")
        budget = budgets[0]
        if (
            budget["currency"] != self.client.currency
            or budget["budget_product_sku"] != "ai_credits"
        ):
            raise ValueError("migration headroom requires a monetary AI-credit budget")
        proposed_limit = 220
        projected_user_cost = budget["consumed_amount"] + future_cost
        deadline = roster["team"]["deadline"]
        if deadline is None or date.fromisoformat(deadline) <= self.period.end:
            raise ValueError("remaining migration work needs a future deadline")
        if proposed_limit <= budget["budget_amount"]:
            raise ValueError("the case's proposed budget is not an increase")
        return {
            **context,
            "period": periods["current"].as_dict(),
            "remaining_period": {
                "start": remaining_start.isoformat() if remaining_start else None,
                "end": self.period.end.replace(
                    day=self.period.end.day + remaining_days
                ).isoformat(),
                "days": remaining_days,
            },
            "options": [
                {
                    "id": "deduplicate_triggers",
                    "scope": "Security / automated-review / same successful artifact",
                    "success_definition": review_roster["team"]["success_definition"],
                    "policy_source": review_roster["source"],
                    "duplicate_success_candidates": len(duplicate_ids),
                    "observed_period_opportunity_usd": round(duplicate_amount, 2),
                    "observed_period_opportunity_credits": round(duplicate_credits, 2),
                    "remaining_month_savings_usd": round(
                        duplicate_amount / days * remaining_days, 2
                    ),
                    "remaining_month_credit_savings": round(
                        duplicate_credits / days * remaining_days, 2
                    ),
                    "assumptions": [
                        "Only redundant successful outputs are removed; required "
                        "checks and failed retries remain.",
                        "The observed duplicate rate continues over the remaining "
                        "days.",
                        "Past spend is not refunded; validate the deduplication key "
                        "and rollout with the workflow owner.",
                    ],
                },
                {
                    "id": "simple_task_model",
                    "scope": "Platform Engineering / simple-maintenance only",
                    "baseline_model": baseline_model,
                    "candidate_model": candidate_model,
                    "pilot": deepcopy(pilot),
                    "pilot_source": pilot_context["source"],
                    "quality_gate_passed": quality_passed,
                    "estimate_status": (
                        "quality_gate_failed"
                        if not quality_passed
                        else "not_cheaper"
                        if ratio >= 1
                        else "conditional_pilot_estimate"
                    ),
                    "eligible_observed_spend_usd": round(eligible_cost, 2),
                    "observed_period_opportunity_usd": (
                        round(routing_amount, 2) if routing_amount is not None else None
                    ),
                    "remaining_month_savings_usd": (
                        round(routing_amount / days * remaining_days, 2)
                        if routing_amount is not None
                        else None
                    ),
                    "estimated_credit_savings": None,
                    "assumptions": [
                        "The small matched-task pilot must generalize with the same "
                        "quality checks and rollback criteria.",
                        "Apply only to the eligible simple-task cohort, not "
                        "migration or complex reviews.",
                        "No token or credit reduction is inferred from the "
                        "monetary pilot ratio.",
                    ],
                },
                {
                    "id": "temporary_budget",
                    "scope": "carol / AI Lab migration",
                    "current_limit_usd": budget["budget_amount"],
                    "proposed_limit_usd": proposed_limit,
                    "additional_headroom_usd": proposed_limit - budget["budget_amount"],
                    "remaining_migration_tasks": plans[0]["count"],
                    "estimated_remaining_work_cost_usd": round(future_cost, 2),
                    "projected_user_spend_usd": round(projected_user_cost, 2),
                    "proposed_limit_covers_plan": proposed_limit >= projected_user_cost,
                    "projected_gap_at_current_limit_usd": round(
                        max(0, projected_user_cost - budget["budget_amount"]), 2
                    ),
                    "review_or_expiry_date": deadline,
                    "estimated_savings_usd": 0,
                    "assumptions": [
                        "The remaining migration tasks have a comparable success "
                        "rate and unit cost.",
                        "Headroom is permission to spend, not savings or "
                        "guaranteed consumption.",
                        "A human must approve the limit and review/expiry; "
                        "this estimate performs no budget write.",
                    ],
                },
            ],
            "combination": {
                "savings_options": ["deduplicate_triggers", "simple_task_model"],
                "disjoint_scopes": True,
                "remaining_month_savings_usd": (
                    round(
                        (duplicate_amount + routing_amount) / days * remaining_days, 2
                    )
                    if routing_amount is not None
                    else None
                ),
                "note": (
                    "The cohorts do not overlap. Never add budget headroom to savings."
                ),
            },
            "decision": (
                "Choose two proposals and explain evidence, assumptions, quality "
                "gates and the human owner. No action is executed."
            ),
            "projection_note": (
                "Remaining-month savings extrapolate observed rates. The migration "
                "budget estimate uses planned tasks instead; do not mix these "
                "assumptions into a guaranteed month-end invoice."
            ),
        }


def _count(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value
