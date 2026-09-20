from __future__ import annotations

from typing import Any

from .analytics import FinOpsAnalyzer
from .approvals import ApprovalWorkflow
from .clients import GitHubFinOpsClient, MockGitHubFinOpsClient
from .investigation import InvestigationEvidence
from .models import ActionKind, ReportingPeriod
from .recommendations import build_recommendations


class FinOpsToolbox:
    def __init__(self, client: GitHubFinOpsClient) -> None:
        self.client = client
        self._analyzer: FinOpsAnalyzer | None = None
        self.approvals = ApprovalWorkflow(client)

    @property
    def analyzer(self) -> FinOpsAnalyzer:
        if self._analyzer is None:
            records = self.client.get_usage_items()
            self._analyzer = FinOpsAnalyzer(
                records,
                self.client.get_department_assignments(),
                as_of=self.client.as_of,
                currency=self.client.currency,
                metadata=self.client.usage_metadata,
            )
        return self._analyzer

    def get_cost_summary(
        self,
        period: str = "month_to_date",
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        resolved = self._resolve_period(period, start=start, end=end)
        return self.analyzer.cost_summary(resolved)

    def rank_department_consumption(
        self,
        period: str = "month_to_date",
        limit: int = 10,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        resolved = self._resolve_period(period, start=start, end=end)
        return self.analyzer.rank_departments(resolved, limit=limit)

    def get_daily_usage(
        self,
        period: str = "month_to_date",
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        return self.analyzer.daily_usage(
            self._resolve_period(period, start=start, end=end)
        )

    def _investigation(self) -> InvestigationEvidence:
        if not isinstance(self.client, MockGitHubFinOpsClient):
            raise ValueError("workshop investigation context is mock-only")
        return InvestigationEvidence(self.client)

    def get_daily_usage_trend(self) -> dict[str, Any]:
        return self._investigation().daily_trend(self.analyzer)

    def get_team_roster(self, department: str) -> dict[str, Any]:
        return self._investigation().team_roster(department)

    def get_workflow_evidence(self, department: str, limit: int = 6) -> dict[str, Any]:
        return self._investigation().workflow_evidence(department, limit)

    def compare_improvement_options(self) -> dict[str, Any]:
        return self._investigation().improvement_options()

    def break_down_usage(
        self,
        dimension: str = "model",
        period: str = "month_to_date",
        limit: int = 10,
        start: str | None = None,
        end: str | None = None,
        department: str | None = None,
    ) -> dict[str, Any]:
        resolved = self._resolve_period(period, start=start, end=end)
        return self.analyzer.usage_breakdown(
            resolved, dimension=dimension, limit=limit, department=department
        )

    def forecast_budget(
        self,
        budget_amount: float,
        period: str = "month_to_date",
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        FinOpsAnalyzer.validate_budget_amount(budget_amount)
        resolved = self._resolve_period(period, start=start, end=end)
        return self.analyzer.forecast_budget(resolved, budget_amount=budget_amount)

    def recommend_optimizations(
        self,
        period: str = "month_to_date",
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        resolved = self._resolve_period(period, start=start, end=end)
        metrics_metadata = self.client.user_metrics_metadata
        metrics = (
            self.client.get_user_metrics()
            if metrics_metadata["status"] == "available"
            else None
        )
        seats = self.client.list_seats()
        return build_recommendations(
            department_ranking=self.analyzer.rank_departments(resolved),
            model_breakdown=self.analyzer.usage_breakdown(resolved, dimension="model"),
            user_metrics=metrics,
            seats=seats,
            user_metrics_metadata=metrics_metadata,
            seat_metadata=self.client.seat_metadata,
        )

    def list_seats(self) -> dict[str, Any]:
        seats = self.client.list_seats()
        return {
            "organization": self.client.organization,
            **self.client.seat_metadata,
            "seats": seats,
        }

    def list_budgets(self) -> dict[str, Any]:
        budgets = self.client.list_budgets()
        return {
            "organization": self.client.organization,
            **self.client.budget_metadata,
            "budgets": budgets,
        }

    def plan_action(
        self,
        kind: ActionKind,
        target: str,
        payload: dict[str, Any],
        actor: str = "workshop-user",
    ) -> dict[str, Any]:
        return self.approvals.create_plan(kind, target, payload, actor=actor)

    def list_action_plans(self) -> list[dict[str, Any]]:
        return self.approvals.list_plans()

    def get_action_plan(self, plan_id: str) -> dict[str, Any]:
        return self.approvals.get_plan(plan_id)

    def approve_action(
        self,
        plan_id: str,
        actor: str = "workshop-approver",
        *,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        return self.approvals.approve(plan_id, actor=actor, confirmed=confirmed)

    def execute_approved_action(
        self,
        plan_id: str,
        approval_token: str,
        actor: str = "workshop-executor",
    ) -> dict[str, Any]:
        return self.approvals.execute(plan_id, approval_token, actor=actor)

    def get_audit_log(self) -> dict[str, Any]:
        return {"events": self.approvals.get_audit_log()}

    def _resolve_period(
        self,
        period: str,
        *,
        start: str | None,
        end: str | None,
    ) -> ReportingPeriod:
        if period not in self.client.supported_periods:
            supported = ", ".join(sorted(self.client.supported_periods))
            raise ValueError(f"{type(self.client).__name__} supports only: {supported}")
        return self.analyzer.resolve_period(period, start=start, end=end)
