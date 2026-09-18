from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from finops_agent import clients
from finops_agent.analytics import FinOpsAnalyzer
from finops_agent.clients import MockGitHubFinOpsClient, RealGitHubFinOpsClient
from finops_agent.models import (
    DepartmentAssignment,
    ReportingPeriod,
    UsageItem,
    UserMetric,
)
from finops_agent.tools import FinOpsToolbox


def usage_dict() -> dict:
    return {
        "date": "2026-09-03",
        "user": "Alice",
        "product": "copilot",
        "sku": "ai_credits",
        "model": "model-a",
        "unit_type": "AI credits",
        "price_per_unit": 0.01,
        "gross_quantity": 12,
        "gross_amount": 0.12,
        "discount_quantity": 2,
        "discount_amount": 0.02,
        "net_quantity": 10,
        "net_amount": 0.10,
    }


def metric_dict() -> dict:
    return {
        "user": "Alice",
        "total_active_days": 2,
        "ai_credits_used": 1500,
        "chat_requests": 10,
        "code_completions": 20,
        "lines_suggested": 100,
        "lines_accepted": 20,
        "last_activity_at": None,
    }


@pytest.fixture
def mutate_snapshot(monkeypatch):
    read = clients._read_json

    def install(name, mutate):
        def changed(path):
            value = read(path)
            if path.name == name:
                mutate(value)
            return value

        monkeypatch.setattr(clients, "_read_json", changed)

    return install


@pytest.fixture
def packaged_layout(monkeypatch):
    location = (
        Path(__file__).resolve().parent
        / "_resource_lookup_contract"
        / "lib"
        / "site-packages"
        / "finops_agent"
        / "clients.py"
    )
    monkeypatch.setattr(clients, "__file__", str(location))
    monkeypatch.delenv("FINOPS_DATA_DIR", raising=False)


def test_configured_data_directory_keeps_highest_precedence(monkeypatch) -> None:
    monkeypatch.setenv("FINOPS_DATA_DIR", "workshop-data-overrides")
    assert clients._default_data_dir() == Path("workshop-data-overrides")


def test_source_tree_data_precedes_packaged_resource_lookup(monkeypatch) -> None:
    monkeypatch.delenv("FINOPS_DATA_DIR", raising=False)

    def forbidden(package):
        raise AssertionError("source data must not require a packaged resource")

    monkeypatch.setattr(clients.importlib.resources, "files", forbidden)
    assert clients._default_data_dir() == (
        Path(clients.__file__).resolve().parents[2] / "data"
    )


def test_packaged_data_is_the_last_fallback(monkeypatch, packaged_layout) -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    calls = []

    def files(package):
        calls.append(package)
        return data_dir

    monkeypatch.setattr(clients.importlib.resources, "files", files)
    assert clients._default_data_dir() == data_dir
    assert calls == ["finops_demo_data"]


def test_missing_data_package_has_an_actionable_error(
    monkeypatch, packaged_layout
) -> None:
    def missing(package):
        raise ModuleNotFoundError(f"No module named {package!r}")

    monkeypatch.setattr(clients.importlib.resources, "files", missing)
    with pytest.raises(
        FileNotFoundError, match="finops_demo_data is not installed"
    ) as err:
        clients._default_data_dir()
    assert "FINOPS_DATA_DIR" in str(err.value)
    assert isinstance(err.value.__cause__, ModuleNotFoundError)


@pytest.mark.parametrize("field", ["date", "user", "model", "net_amount", "unit_type"])
def test_usage_rejects_missing_fields(field) -> None:
    value = usage_dict()
    del value[field]
    with pytest.raises(ValueError, match="missing required fields"):
        UsageItem.from_dict(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, "10"])
@pytest.mark.parametrize("field", ["gross_quantity", "net_amount", "price_per_unit"])
def test_usage_rejects_invalid_numbers(field, value) -> None:
    data = usage_dict()
    data[field] = value
    with pytest.raises(ValueError, match="finite non-negative"):
        UsageItem.from_dict(data)


@pytest.mark.parametrize("field", ["net_quantity", "net_amount", "discount_quantity"])
def test_usage_rejects_inconsistent_totals(field) -> None:
    value = usage_dict()
    value[field] += 1
    with pytest.raises(ValueError, match="inconsistent usage"):
        UsageItem.from_dict(value)


def test_period_aggregates_have_no_invented_daily_date() -> None:
    value = usage_dict()
    value.update(date=None, user=None)
    period = ReportingPeriod(date(2026, 9, 1), date(2026, 9, 3), "month_to_date")
    record = UsageItem.from_dict(value, period=period)
    assert record.date is None
    assert record.user is None
    assert record.period == period
    with pytest.raises(ValueError, match="either a daily date or an aggregate period"):
        UsageItem.from_dict(value)
    with pytest.raises(ValueError, match="either a daily date or an aggregate period"):
        UsageItem.from_dict(usage_dict(), period=period)
    analyzer = FinOpsAnalyzer([record], [], as_of=None)
    summary = analyzer.cost_summary(analyzer.resolve_period())
    assert summary["granularity"] == "period_aggregate"
    with pytest.raises(ValueError, match="mixed daily/aggregate"):
        FinOpsAnalyzer([record, UsageItem.from_dict(usage_dict())], [], as_of=None)


def test_reporting_period_rejects_reversed_dates() -> None:
    with pytest.raises(ValueError, match="before start"):
        ReportingPeriod(date(2026, 9, 3), date(2026, 9, 1), "custom")


def test_mapping_deduplicates_identical_casefolded_logins_without_team_fanout() -> None:
    client = MockGitHubFinOpsClient()
    assignments = client.get_department_assignments()
    assignments.append(DepartmentAssignment("CAROL", "AI Lab", "CC-AI"))
    analyzer = FinOpsAnalyzer(
        client.get_usage_items(),
        assignments,
        as_of=client.as_of,
        metadata=client.usage_metadata,
    )
    ranking = analyzer.rank_departments(analyzer.resolve_period())
    assert ranking["ranking"][0]["net_quantity"] == 2400
    assert ranking["ranking"][0]["user_count"] == 2
    assert UsageItem.from_dict(usage_dict()).user == "alice"


@pytest.mark.parametrize(
    "conflict",
    [
        DepartmentAssignment("ALICE", "Another department", "CC-A"),
        DepartmentAssignment("ALICE", "Platform", "CC-OTHER"),
    ],
)
def test_conflicting_casefolded_assignments_are_rejected(conflict) -> None:
    assignments = [DepartmentAssignment("alice", "Platform", "CC-A"), conflict]
    with pytest.raises(ValueError, match="conflicting department assignments"):
        DepartmentAssignment.index(assignments)
    with pytest.raises(ValueError, match="conflicting department assignments"):
        RealGitHubFinOpsClient(
            "example", "test-token", department_assignments=assignments
        )


def test_unattributed_residual_does_not_count_as_a_person() -> None:
    value = usage_dict()
    value["user"] = None
    analyzer = FinOpsAnalyzer(
        [UsageItem.from_dict(value)], [], as_of="2026-09-03T23:59:59Z"
    )
    period = analyzer.resolve_period("today")
    assert analyzer.cost_summary(period)["user_count"] == 0
    assert analyzer.rank_departments(period)["ranking"][0]["user_count"] == 0
    assert analyzer.usage_breakdown(period, dimension="user")["items"][0]["user"] == (
        "Unallocated"
    )
    assert "synthetic" not in analyzer.cost_summary(period)["source"]


def test_raw_tokens_cannot_be_presented_as_net_credits() -> None:
    record = replace(UsageItem.from_dict(usage_dict()), unit_type="tokens")
    with pytest.raises(ValueError, match="raw tokens are not credits"):
        FinOpsAnalyzer([record], [], as_of="2026-09-03T23:59:59Z")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("total_active_days", 1.5),
        ("total_active_days", -1),
        ("ai_credits_used", float("nan")),
        ("ai_credits_used", True),
        ("chat_requests", "10"),
        ("lines_accepted", 101),
        ("last_activity_at", "2026-09-03T12:00:00"),
    ],
)
def test_user_metrics_reject_invalid_evidence(field, value) -> None:
    data = metric_dict()
    data[field] = value
    with pytest.raises(ValueError):
        UserMetric.from_dict(data)


def test_user_metrics_keep_null_activity_and_separate_28_day_period() -> None:
    client = MockGitHubFinOpsClient()
    metric = next(row for row in client.get_user_metrics() if row.user == "judy")
    assert metric.last_activity_at is None
    assert metric.period.start == date(2026, 8, 26)
    assert metric.period.end == date(2026, 9, 22)
    assert "synthetic" in metric.source
    assert client.user_metrics_metadata["status"] == "available"


def test_mock_rejects_missing_usage_array(mutate_snapshot) -> None:
    mutate_snapshot("ai-credit-usage.json", lambda data: data.pop("usage_items"))
    with pytest.raises(ValueError, match="usage_items must be an array"):
        MockGitHubFinOpsClient()


def test_mock_rejects_inconsistent_snapshot_organization(mutate_snapshot) -> None:
    mutate_snapshot("budgets.json", lambda data: data.update(organization="elsewhere"))
    with pytest.raises(ValueError, match="organization does not match"):
        MockGitHubFinOpsClient()


def test_mock_rejects_records_outside_declared_coverage(mutate_snapshot) -> None:
    mutate_snapshot(
        "ai-credit-usage.json",
        lambda data: data["usage_items"][0].update(date="2026-08-06"),
    )
    with pytest.raises(ValueError, match="outside declared coverage"):
        FinOpsToolbox(MockGitHubFinOpsClient()).get_cost_summary()


def test_mock_rejects_duplicate_casefolded_seats(mutate_snapshot) -> None:
    mutate_snapshot(
        "seats.json",
        lambda data: data["seats"].append({**data["seats"][0], "user": "ALICE"}),
    )
    with pytest.raises(ValueError, match="duplicate case-insensitive users"):
        MockGitHubFinOpsClient()


def test_coverage_and_source_metadata_are_defensive_copies() -> None:
    client = MockGitHubFinOpsClient()
    client.coverage["start"] = "1900-01-01"
    client.usage_metadata["limitations"].clear()
    assert client.coverage["start"] == "2026-08-26"
    assert client.usage_metadata["limitations"]


def test_legacy_fixture_coverage_follows_its_snapshot(mutate_snapshot) -> None:
    mutate_snapshot("ai-credit-usage.json", lambda data: data.pop("coverage"))
    client = MockGitHubFinOpsClient()
    assert client.coverage == {
        "start": "2026-08-26",
        "end": "2026-09-22",
        "kind": "sparse_training_samples",
    }
    assert FinOpsToolbox(client).get_cost_summary()["net_quantity"] == 4760


def test_budget_remaining_uses_budget_specific_consumption_and_scope() -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    result = tools.list_budgets()
    organization, user = result["budgets"]
    assert organization["consumed_amount"] == 45.2
    assert organization["remaining_amount"] == 34.8
    assert organization["consumption_basis"] == "organization_metered_spend"
    assert user["remaining_amount"] == 6
    assert user["consumption_basis"] == "user_total_spend"
    assert all(row["currency"] == "USD" for row in result["budgets"])
    assert all(row["as_of"] == result["as_of"] for row in result["budgets"])
    assert tools.forecast_budget(80)["remaining_amount"] == 35.12


@pytest.mark.parametrize("missing", [True, False])
def test_missing_consumed_amount_is_unknown_not_zero(missing) -> None:
    client = MockGitHubFinOpsClient()
    if missing:
        client._budgets[0].pop("consumed_amount")
    else:
        client._budgets[0]["consumed_amount"] = None
    budget = client.list_budgets()[0]
    assert budget["consumed_amount"] is None
    assert budget["remaining_amount"] is None
    assert budget["remaining_status"] == "unknown"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, "45"])
def test_invalid_consumed_amount_is_rejected(value) -> None:
    client = MockGitHubFinOpsClient()
    client._budgets[0]["consumed_amount"] = value
    with pytest.raises(ValueError, match="budget.consumed_amount"):
        client.list_budgets()


def test_overdrawn_budget_is_not_clamped() -> None:
    client = MockGitHubFinOpsClient()
    client._budgets[0]["consumed_amount"] = 85
    assert client.list_budgets()[0]["remaining_amount"] == -5


def test_unverified_budget_units_are_not_claimed_to_be_usd() -> None:
    client = MockGitHubFinOpsClient()
    client._budgets[0].update(
        budget_type="SkuPricing", budget_product_sku="license-based-example"
    )
    result = client.list_budgets()[0]
    assert result["remaining_amount"] == 34.8
    assert result["currency"] is None
    assert result["amount_unit"] == "provider_budget_units"
    assert "may count licenses" in result["scope_note"]


def test_seat_and_budget_planning_do_not_load_analytics(monkeypatch) -> None:
    client = MockGitHubFinOpsClient()

    def forbidden():
        raise AssertionError("planning must not fetch billing usage")

    monkeypatch.setattr(client, "get_usage_items", forbidden)
    tools = FinOpsToolbox(client)
    assert tools._analyzer is None
    assert tools.list_seats()["seats"]
    assert tools.list_budgets()["budgets"]
    plan = tools.plan_action(
        "remove_seats", "octo-demo", {"selected_usernames": ["ivan"]}
    )
    assert plan["status"] == "planned"
    assert tools.get_action_plan(plan["plan_id"])["plan_id"] == plan["plan_id"]
    assert tools.list_action_plans() == [tools.get_action_plan(plan["plan_id"])]
    assert tools._analyzer is None


def test_analyst_is_loaded_only_once_when_analytics_are_requested(monkeypatch) -> None:
    client = MockGitHubFinOpsClient()
    read = client.get_usage_items
    calls = []

    def counted():
        calls.append("usage")
        return read()

    monkeypatch.setattr(client, "get_usage_items", counted)
    tools = FinOpsToolbox(client)
    assert calls == []
    tools.get_cost_summary()
    tools.rank_department_consumption()
    tools.break_down_usage()
    assert calls == ["usage"]


def test_toolbox_forwards_keyword_only_confirmation_without_assuming_approval(
    monkeypatch,
) -> None:
    tools = FinOpsToolbox(MockGitHubFinOpsClient())
    calls = []

    def approve(plan_id, *, actor, confirmed):
        calls.append((plan_id, actor, confirmed))
        return {"plan_id": plan_id, "confirmed": confirmed}

    monkeypatch.setattr(tools.approvals, "approve", approve)
    assert tools.approve_action("plan-1")["confirmed"] is False
    assert (
        tools.approve_action("plan-1", actor="human-reviewer", confirmed=True)[
            "confirmed"
        ]
        is True
    )
    assert calls == [
        ("plan-1", "workshop-approver", False),
        ("plan-1", "human-reviewer", True),
    ]
    with pytest.raises(TypeError):
        tools.approve_action("plan-1", "human-reviewer", True)
    assert len(calls) == 2
