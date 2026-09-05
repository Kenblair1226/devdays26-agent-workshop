from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime
from typing import Any

from .models import UserMetric


def build_recommendations(
    *,
    department_ranking: dict[str, Any],
    model_breakdown: dict[str, Any],
    user_metrics: Iterable[UserMetric] | None,
    seats: list[dict[str, Any]],
    minimum_inactive_days: int = 14,
    user_metrics_metadata: dict[str, Any] | None = None,
    seat_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if type(minimum_inactive_days) is not int or minimum_inactive_days < 1:
        raise ValueError("minimum_inactive_days must be a positive integer")
    metrics_info = (
        deepcopy(user_metrics_metadata)
        if user_metrics_metadata
        else {
            "status": "not_loaded" if user_metrics is None else "available",
            "source": "caller-provided user metrics",
            "period": None,
        }
    )
    if metrics_info.get("status") != "available":
        user_metrics = None
    seats_info = (
        deepcopy(seat_metadata)
        if seat_metadata
        else {
            "source": "caller-provided seat snapshot",
            "as_of": department_ranking["as_of"],
        }
    )
    billing_evidence = {
        "source": department_ranking.get("source", "caller-provided billing records"),
        "period": department_ranking["period"],
        "as_of": department_ranking["as_of"],
    }
    caveats = list(department_ranking.get("limitations", []))
    caveats.extend(metrics_info.get("limitations", []))
    caveats.extend(seats_info.get("limitations", []))
    if seats_info.get("pricing_note"):
        caveats.append(seats_info["pricing_note"])
    recommendations: list[dict[str, Any]] = []
    models = model_breakdown["items"]
    total_model_credits = model_breakdown.get("total_net_quantity")
    share_basis = "all model usage in the billing period"
    if total_model_credits is None:
        total_model_credits = sum(item["net_quantity"] for item in models)
        share_basis = "only the displayed models; complete coverage is unknown"
    if models and total_model_credits:
        leading = models[0]
        share = leading["net_quantity"] / total_model_credits
        if share >= 0.4:
            recommendations.append(
                {
                    "category": "model_routing",
                    "title": f"Review model concentration in {leading['model']}",
                    "evidence": {
                        **billing_evidence,
                        "model": leading["model"],
                        "ai_credits": leading["net_quantity"],
                        "share": round(share, 3),
                        "share_basis": share_basis,
                    },
                    "recommendation": (
                        "Concentration alone does not show that a model is expensive. "
                        "Compare effective prices and task quality with approved "
                        "alternatives in a controlled routing experiment before "
                        "changing policy."
                    ),
                    "estimated_impact": (
                        "unquantified; pricing and quality validation needed"
                    ),
                    "confidence": "low",
                }
            )

    inactive_users = _inactive_seat_users(
        seats, seats_info.get("as_of"), minimum_inactive_days
    )
    unknown_activity = [
        seat["user"]
        for seat in seats
        if seat.get("status") == "active" and seat.get("last_activity_at") is None
    ]
    if unknown_activity:
        caveats.append(
            f"{len(unknown_activity)} active seat(s) have unknown last activity; "
            "missing telemetry is not evidence for reclamation."
        )
    if seats_info.get("as_of") is None:
        caveats.append(
            "Seat snapshot as_of is unknown. Inactivity recommendations are skipped "
            "rather than treating retrieval time as provider freshness."
        )
    if inactive_users:
        recommendations.append(
            {
                "category": "seat_utilization",
                "title": "Review inactive Copilot seats",
                "evidence": {
                    "source": seats_info["source"],
                    "as_of": seats_info["as_of"],
                    "users": inactive_users,
                    "seat_count": len(inactive_users),
                    "minimum_inactive_days": minimum_inactive_days,
                },
                "recommendation": (
                    "Validate activity telemetry and business need with users and "
                    "managers. Consider a seat change only through a separately "
                    "approved plan; inactivity is not automatic authorization."
                ),
                "estimated_impact": (
                    "unquantified; no applicable live seat price or billing-cycle "
                    "savings evidence"
                ),
                "confidence": "medium",
            }
        )

    low_efficiency = []
    if user_metrics is None:
        caveats.append(
            metrics_info.get(
                "reason",
                "User metrics are unsupported or not loaded; metric-dependent "
                "recommendations are skipped, not interpreted as zero usage.",
            )
        )
    unknown_metric_period = False
    for metric in user_metrics if user_metrics is not None else ():
        metric_period = (
            metric.period.as_dict()
            if metric.period is not None
            else metrics_info.get("period")
        )
        metric_source = metric.source or metrics_info.get("source")
        if metric_period is None or metric_source is None:
            unknown_metric_period = True
            continue
        if metric.lines_suggested == 0:
            continue
        acceptance_rate = metric.lines_accepted / metric.lines_suggested
        if metric.ai_credits_used >= 1000 and acceptance_rate < 0.35:
            low_efficiency.append(
                {
                    "user": metric.user,
                    "ai_credits_used": metric.ai_credits_used,
                    "acceptance_rate": round(acceptance_rate, 3),
                    "period": metric_period,
                    "as_of": metric.as_of or metrics_info.get("as_of"),
                    "source": metric_source,
                }
            )
    if unknown_metric_period:
        caveats.append(
            "Metrics without an identified source/reporting period were skipped."
        )
    if low_efficiency:
        recommendations.append(
            {
                "category": "prompt_efficiency",
                "title": "Test workflow improvements in high-credit samples",
                "evidence": {"users": low_efficiency},
                "recommendation": (
                    "Experiment with narrower tasks and relevant context, and compare "
                    "task quality with a baseline. Completion acceptance rate alone "
                    "does not prove token waste or explain chat usage. No raw-token "
                    "data or causal savings estimate is available."
                ),
                "estimated_impact": "unquantified; validate quality and actual usage",
                "confidence": "low",
            }
        )

    rankings = department_ranking["ranking"]
    if rankings:
        top = rankings[0]
        recommendations.append(
            {
                "category": "budget_guardrail",
                "title": f"Review budget evidence for {top['department']}",
                "evidence": {
                    **billing_evidence,
                    "department": top["department"],
                    "ai_credits": top["net_quantity"],
                    "net_amount": top["net_amount"],
                },
                "recommendation": (
                    "Resolve any Unallocated attribution and compare with actual "
                    "scope-specific budgets using list_budgets before proposing a "
                    "guardrail. A department ranking is not an actual budget balance."
                ),
                "estimated_impact": "risk reduction",
                "confidence": "medium",
            }
        )

    return {
        "as_of": department_ranking["as_of"],
        "retrieved_at": department_ranking.get("retrieved_at"),
        "period": department_ranking["period"],
        "sources": {
            "billing": billing_evidence,
            "user_metrics": metrics_info,
            "seats": seats_info,
        },
        "recommendations": recommendations,
        "caveats": caveats,
        "method_note": (
            "Rules-based hypotheses, not quantified savings or authorization. "
            "Billing periods and fixed 28-day metric periods are separate evidence. "
            "Net credits are not raw tokens; every change requires human review."
        ),
    }


def _inactive_seat_users(
    seats: list[dict[str, Any]], as_of: str | None, minimum_inactive_days: int
) -> list[str]:
    if as_of is None:
        return []
    snapshot_time = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    if snapshot_time.utcoffset() is None:
        raise ValueError("seat as_of must include a timezone")
    inactive: list[str] = []
    for seat in seats:
        if seat.get("status") != "active":
            continue
        last_activity = seat.get("last_activity_at")
        if last_activity is None:
            continue
        activity = datetime.fromisoformat(str(last_activity).replace("Z", "+00:00"))
        if activity.utcoffset() is None:
            raise ValueError("seat last_activity_at must include a timezone")
        if (snapshot_time - activity).days >= minimum_inactive_days:
            inactive.append(str(seat["user"]))
    return inactive
