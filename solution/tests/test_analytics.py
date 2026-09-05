import pytest

from finops_agent.clients import MockGitHubFinOpsClient
from finops_agent.recommendations import build_recommendations
from finops_agent.tools import FinOpsToolbox


def toolbox() -> FinOpsToolbox:
    return FinOpsToolbox(MockGitHubFinOpsClient())


def test_month_to_date_cost_summary() -> None:
    result = toolbox().get_cost_summary()

    assert result["period"]["label"] == "month_to_date"
    assert result["net_quantity"] == 4760
    assert result["net_amount"] == 44.88
    assert result["as_of"] == "2026-09-03T23:59:59Z"
    assert result["unit"] == "AI credits"
    assert "not raw model tokens" in result["quantity_note"]
    assert result["coverage"] == {
        "start": "2026-08-07",
        "end": "2026-09-03",
        "kind": "sparse_training_samples",
    }
    assert result["granularity"] == "daily_samples"
    assert "not actual GitHub" in result["pricing_note"]


def test_department_ranking_keeps_unallocated_usage() -> None:
    result = toolbox().rank_department_consumption()

    assert result["ranking"][0] == {
        "rank": 1,
        "department": "AI Lab",
        "net_quantity": 2400,
        "net_amount": 26,
        "user_count": 2,
    }
    assert result["unallocated_quantity"] == 90
    unallocated = next(
        row for row in result["ranking"] if row["department"] == "Unallocated"
    )
    assert unallocated["user_count"] == 1
    assert "Resolved explicit" in result["attribution_method"]
    assert "no live cost-center lookup" in result["attribution_method"]


def test_model_breakdown_and_forecast() -> None:
    tools = toolbox()

    breakdown = tools.break_down_usage("model")
    forecast = tools.forecast_budget(80)

    assert breakdown["items"][0]["model"] == "gpt-5.4"
    assert forecast["projected_month_end_amount"] == 448.8
    assert forecast["projected_over_budget"] is True
    assert forecast["scenario_only"] is True
    assert "run-rate" in forecast["method"]
    assert "not an actual budget balance or final invoice" in forecast["forecast_note"]


def test_recommendations_are_evidence_backed() -> None:
    result = toolbox().recommend_optimizations()

    categories = {item["category"] for item in result["recommendations"]}
    assert {"model_routing", "seat_utilization", "prompt_efficiency"} <= categories
    assert result["period"]["label"] == "month_to_date"
    by_category = {item["category"]: item for item in result["recommendations"]}
    seats = by_category["seat_utilization"]
    assert seats["evidence"]["users"] == ["ivan"]
    assert seats["evidence"]["as_of"] == "2026-09-03T23:59:59Z"
    assert "unquantified" in seats["estimated_impact"]
    assert "19" not in seats["estimated_impact"]
    assert any("missing telemetry" in note for note in result["caveats"])
    prompts = by_category["prompt_efficiency"]
    assert "does not prove token waste" in prompts["recommendation"]
    for user in prompts["evidence"]["users"]:
        assert user["period"] == {
            "label": "last_28_days",
            "start": "2026-08-07",
            "end": "2026-09-03",
        }
        assert "synthetic users-28-day" in user["source"]
    assert "does not show" in by_category["model_routing"]["recommendation"]


@pytest.mark.parametrize(
    ("period", "start", "end", "quantity", "amount"),
    [
        ("today", None, None, 1390, 14.34),
        ("last_28_days", None, None, 5060, 47.88),
        ("custom", "2026-08-31", "2026-08-31", 300, 3),
        ("custom", "2026-09-01", "2026-09-01", 2240, 20.72),
    ],
)
def test_supported_sample_periods(period, start, end, quantity, amount) -> None:
    result = toolbox().get_cost_summary(period, start, end)

    assert result["net_quantity"] == quantity
    assert result["net_amount"] == amount
    assert any(
        "missing days are not observed zeros" in s for s in result["limitations"]
    )


@pytest.mark.parametrize(
    ("period", "start", "end"),
    [
        ("previous_month", None, None),
        ("custom", "2026-08-06", "2026-09-01"),
        ("custom", "2026-09-01", "2026-09-04"),
        ("custom", "2026-08-08", "2026-08-10"),
    ],
)
def test_missing_coverage_is_unavailable_not_zero(period, start, end) -> None:
    with pytest.raises(ValueError, match="unavailable"):
        toolbox().get_cost_summary(period, start, end)


@pytest.mark.parametrize(
    ("period", "start", "end"),
    [
        ("custom", None, "2026-09-01"),
        ("custom", "2026-09-03", "2026-09-01"),
        ("custom", "not-a-date", "2026-09-01"),
        ("today", "2026-09-01", "2026-09-03"),
        ("yesterday", None, None),
    ],
)
def test_invalid_reporting_periods_fail(period, start, end) -> None:
    with pytest.raises(ValueError):
        toolbox().get_cost_summary(period, start, end)


def test_department_drilldown_and_limit_preserve_totals() -> None:
    tools = toolbox()
    result = tools.break_down_usage("user", department="ai lab")

    assert result["total_net_quantity"] == 2400
    assert result["total_net_amount"] == 26
    assert {row["user"] for row in result["items"]} == {"carol", "dave"}
    limited = tools.break_down_usage("model", limit=1)
    assert len(limited["items"]) == 1
    assert limited["total_net_quantity"] == 4760


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_rank_and_breakdown_reject_invalid_limits(limit) -> None:
    tools = toolbox()
    with pytest.raises(ValueError, match="positive integer"):
        tools.rank_department_consumption(limit=limit)
    with pytest.raises(ValueError, match="positive integer"):
        tools.break_down_usage(limit=limit)


def test_unknown_dimension_or_department_fails() -> None:
    tools = toolbox()
    with pytest.raises(ValueError, match="dimension"):
        tools.break_down_usage("tokens")
    with pytest.raises(ValueError, match="unavailable"):
        tools.break_down_usage(department="Missing department")
    with pytest.raises(ValueError, match="non-empty"):
        tools.break_down_usage(department="")


@pytest.mark.parametrize(
    "amount", [-1, float("nan"), float("inf"), -float("inf"), True, "80"]
)
def test_forecast_rejects_non_finite_or_invalid_budget(amount) -> None:
    with pytest.raises(ValueError, match="finite non-negative"):
        toolbox().forecast_budget(amount)


@pytest.mark.parametrize(
    ("period", "start", "end"),
    [
        ("today", None, None),
        ("last_28_days", None, None),
        ("custom", "2026-09-01", "2026-09-02"),
        ("custom", "2026-08-31", "2026-09-03"),
    ],
)
def test_forecast_requires_month_start_to_snapshot_date(period, start, end) -> None:
    with pytest.raises(ValueError, match="month-start-to-date"):
        toolbox().forecast_budget(80, period, start, end)


def test_forecast_accepts_an_equivalent_fixed_mtd_window() -> None:
    result = toolbox().forecast_budget(80, "custom", "2026-09-01", "2026-09-03")
    assert result["projected_month_end_amount"] == 448.8


def test_empty_loaded_report_is_not_zero(monkeypatch) -> None:
    client = MockGitHubFinOpsClient()
    monkeypatch.setattr(client, "get_usage_items", lambda: [])
    with pytest.raises(ValueError, match="no records"):
        FinOpsToolbox(client).get_cost_summary()


def test_seat_inactivity_uses_seat_snapshot_not_wall_clock() -> None:
    client = MockGitHubFinOpsClient()
    client._seat_as_of = "2026-08-14T23:59:59Z"
    result = FinOpsToolbox(client).recommend_optimizations()
    assert "seat_utilization" not in {
        rec["category"] for rec in result["recommendations"]
    }


def test_model_share_does_not_treat_truncated_models_as_exhaustive() -> None:
    tools = toolbox()
    breakdown = tools.break_down_usage("model", limit=1)
    breakdown["items"][0]["net_quantity"] = 100
    breakdown["total_net_quantity"] = 1000
    result = build_recommendations(
        department_ranking=tools.rank_department_consumption(),
        model_breakdown=breakdown,
        user_metrics=None,
        seats=[],
    )
    assert "model_routing" not in {rec["category"] for rec in result["recommendations"]}
