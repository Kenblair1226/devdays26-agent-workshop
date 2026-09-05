import inspect
import io
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from finops_agent import clients
from finops_agent.clients import (
    GitHubFinOpsClient,
    MockGitHubFinOpsClient,
    RealGitHubFinOpsClient,
)
from finops_agent.models import DepartmentAssignment
from finops_agent.tools import FinOpsToolbox


class FixedClock(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 9, 3, 12, 0, tzinfo=UTC)
        return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)


@pytest.fixture(autouse=True)
def no_live_requests(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Real GitHub requests are prohibited in these tests")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(clients, "datetime", FixedClock)


@pytest.fixture
def api(monkeypatch):
    def install(handler):
        requests = []

        def urlopen(request, timeout):
            assert request.full_url.startswith("https://api.github.com/")
            assert timeout == 30
            requests.append(request)
            value = handler(request) if callable(handler) else handler
            content = value if isinstance(value, bytes) else json.dumps(value).encode()
            return io.BytesIO(content)

        monkeypatch.setattr(urllib.request, "urlopen", urlopen)
        return requests

    return install


def usage_item(quantity=100, *, discount=0, model="model-a", price=0.01):
    gross = Decimal(str(quantity)) + Decimal(str(discount))
    rate = Decimal(str(price))
    return {
        "product": "copilot",
        "sku": "ai_credits",
        "model": model,
        "unitType": "AI credits",
        "pricePerUnit": price,
        "grossQuantity": float(gross),
        "grossAmount": float(gross * rate),
        "discountQuantity": discount,
        "discountAmount": float(Decimal(str(discount)) * rate),
        "netQuantity": quantity,
        "netAmount": float(Decimal(str(quantity)) * rate),
    }


def report(items, user=None):
    result = {
        "organization": "example",
        "timePeriod": {"year": 2026, "month": 9},
        "usageItems": items,
    }
    if user is not None:
        result["user"] = user
    return result


def seat(user, **fields):
    return {
        "assignee": {"login": user},
        "plan_type": "business",
        "last_activity_at": "2026-08-01T10:00:00Z",
        "pending_cancellation_date": None,
        **fields,
    }


def budget(identifier, **fields):
    return {
        "id": identifier,
        "budget_scope": "organization",
        "budget_amount": 80,
        "consumed_amount": 45.2,
        "prevent_further_usage": True,
        "budget_type": "BundlePricing",
        "budget_product_sku": "ai_credits",
        **fields,
    }


def billing_responses(aggregate, users, seat_users=None):
    def handler(request):
        url = urllib.parse.urlsplit(request.full_url)
        query = urllib.parse.parse_qs(url.query)
        if url.path == "/orgs/example/copilot/billing/seats":
            logins = list(users) if seat_users is None else seat_users
            return {
                "total_seats": len(logins),
                "seats": [seat(user) for user in logins],
            }
        assert url.path == "/organizations/example/settings/billing/ai_credit/usage"
        assert query["year"] == ["2026"]
        assert query["month"] == ["9"]
        assert "day" not in query
        user = query.get("user", [None])[0]
        return report(aggregate if user is None else users[user], user)

    return handler


def real_client(**kwargs):
    return RealGitHubFinOpsClient("example", "test-token", **kwargs)


def test_read_authentication_and_default_write_guard(api) -> None:
    requests = api({"total_seats": 0, "seats": []})
    client = real_client()
    assert client.list_seats() == []
    assert requests[0].get_header("Authorization") == "Bearer test-token"
    assert requests[0].get_method() == "GET"
    with pytest.raises(PermissionError, match="writes are disabled"):
        client.execute_action(
            "remove_seats", "example", {"selected_usernames": ["alice"]}
        )
    assert len(requests) == 1


@pytest.mark.parametrize(
    "client_type", [GitHubFinOpsClient, MockGitHubFinOpsClient, RealGitHubFinOpsClient]
)
def test_execute_action_human_approval_is_keyword_only_and_defaults_false(
    client_type,
) -> None:
    signature = inspect.signature(client_type.execute_action)
    parameter = signature.parameters["human_approved"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is False


@pytest.mark.parametrize("allow_writes", [False, True])
@pytest.mark.parametrize("human_approved", [False, True])
@pytest.mark.parametrize("environment", [None, "false", "true", "TRUE"])
def test_real_mutations_require_all_three_gates(
    api, monkeypatch, allow_writes, human_approved, environment
) -> None:
    if environment is None:
        monkeypatch.delenv("FINOPS_ALLOW_REAL_WRITES", raising=False)
    else:
        monkeypatch.setenv("FINOPS_ALLOW_REAL_WRITES", environment)
    requests = api({"seats_cancelled": 1})
    client = real_client(allow_writes=allow_writes)
    payload = {"selected_usernames": ["alice"]}
    if allow_writes and human_approved and environment == "true":
        result = client.execute_action(
            "remove_seats", "example", payload, human_approved=human_approved
        )
        assert result == {"seats_cancelled": 1}
        assert len(requests) == 1
        assert requests[0].get_method() == "DELETE"
        assert json.loads(requests[0].data) == payload
    else:
        with pytest.raises(PermissionError, match="writes are disabled"):
            client.execute_action(
                "remove_seats", "example", payload, human_approved=human_approved
            )
        assert requests == []


def test_real_default_call_is_rejected_even_when_both_write_switches_are_on(
    api, monkeypatch
) -> None:
    monkeypatch.setenv("FINOPS_ALLOW_REAL_WRITES", "true")
    requests = api({})
    with pytest.raises(PermissionError, match="human_approved=True"):
        real_client(allow_writes=True).execute_action(
            "remove_seats", "example", {"selected_usernames": ["alice"]}
        )
    assert requests == []


@pytest.mark.parametrize("approval", [1, "true", None])
def test_real_mutations_require_explicit_boolean_approval(
    api, monkeypatch, approval
) -> None:
    monkeypatch.setenv("FINOPS_ALLOW_REAL_WRITES", "true")
    requests = api({})
    with pytest.raises(PermissionError, match="human_approved=True"):
        real_client(allow_writes=True).execute_action(
            "remove_seats",
            "example",
            {"selected_usernames": ["alice"]},
            human_approved=approval,
        )
    assert requests == []


def test_real_write_environment_switch_is_rechecked_at_execution(
    api, monkeypatch
) -> None:
    monkeypatch.setenv("FINOPS_ALLOW_REAL_WRITES", "true")
    client = real_client(allow_writes=True)
    monkeypatch.delenv("FINOPS_ALLOW_REAL_WRITES")
    requests = api({})
    with pytest.raises(PermissionError, match="FINOPS_ALLOW_REAL_WRITES=true"):
        client.execute_action(
            "remove_seats",
            "example",
            {"selected_usernames": ["alice"]},
            human_approved=True,
        )
    assert requests == []


@pytest.mark.parametrize("approval", [False, True])
def test_mock_accepts_but_does_not_require_the_human_approval_flag(approval) -> None:
    result = MockGitHubFinOpsClient().execute_action(
        "remove_seats",
        "octo-demo",
        {"selected_usernames": ["ivan"]},
        human_approved=approval,
    )
    assert result["mock"] is True
    assert result["changed"] == 1


def test_real_mtd_reconciles_independent_org_total_and_known_former_users(api) -> None:
    requests = api(
        billing_responses(
            [usage_item(1000)],
            {
                "alice": [usage_item(300)],
                "bob": [usage_item(200)],
                "former": [usage_item(100)],
            },
            seat_users=["Alice", "bob"],
        )
    )
    client = real_client(
        department_assignments=[
            DepartmentAssignment("ALICE", "Platform", "CC-P"),
            DepartmentAssignment("former", "AI Lab", "CC-AI"),
        ]
    )
    tools = FinOpsToolbox(client)
    assert requests == []
    assert client.usage_metadata["status"] == "not_loaded"
    summary = tools.get_cost_summary()
    assert summary["net_quantity"] == 1000
    assert summary["net_amount"] == 10
    assert summary["user_count"] == 3
    assert summary["as_of"] is None
    assert summary["retrieved_at"] == "2026-09-03T12:00:00+00:00"
    assert summary["granularity"] == "month_to_date_aggregate"
    assert "synthetic" not in summary["source"]
    assert "Provider as_of is unknown" in summary["freshness_note"]
    assert summary["reconciliation"]["unattributed_net_quantity"] == 400
    assert summary["reconciliation"]["known_users_queried"] == 3
    assert summary["coverage"]["start"] == "2026-09-01"
    records = tools.analyzer._usage_items
    assert all(row.date is None for row in records)
    assert all(row.period.end == date(2026, 9, 3) for row in records)
    residual = [row for row in records if row.user is None]
    assert len(residual) == 1
    assert residual[0].net_quantity == 400
    unallocated = next(
        row
        for row in tools.rank_department_consumption()["ranking"]
        if row["department"] == "Unallocated"
    )
    assert unallocated["net_quantity"] == 600
    assert unallocated["user_count"] == 1
    usage_queries = [
        urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)
        for req in requests
        if "/ai_credit/usage?" in req.full_url
    ]
    assert sum("user" not in query for query in usage_queries) == 1
    assert {query["user"][0] for query in usage_queries if "user" in query} == {
        "alice",
        "bob",
        "former",
    }


def test_organization_usage_is_not_lost_when_no_current_seats_exist(api) -> None:
    api(billing_responses([usage_item(321)], {}))
    tools = FinOpsToolbox(real_client())
    assert tools.get_cost_summary()["net_quantity"] == 321
    unallocated = tools.rank_department_consumption()["ranking"][0]
    assert unallocated["department"] == "Unallocated"
    assert unallocated["user_count"] == 0


def test_decimal_reconciliation_does_not_create_rounding_residual(api) -> None:
    api(
        billing_responses(
            [usage_item(0.3)], {"alice": [usage_item(0.1)], "bob": [usage_item(0.2)]}
        )
    )
    client = real_client()
    records = client.get_usage_items()
    assert len(records) == 2
    assert client.usage_metadata["reconciliation"]["unattributed_net_quantity"] == 0


@pytest.mark.parametrize(
    ("organization_item", "user_item"),
    [
        (usage_item(100), usage_item(101)),
        (usage_item(90, discount=10), usage_item(85, discount=11)),
        (usage_item(100), {**usage_item(80), "grossAmount": 2, "netAmount": 2}),
    ],
)
def test_inconsistent_user_totals_are_rejected_not_clamped(
    api, organization_item, user_item
) -> None:
    api(billing_responses([organization_item], {"alice": [user_item]}))
    with pytest.raises(ValueError, match="inconsistent organization/user totals"):
        real_client().get_usage_items()


def test_unreported_model_or_price_bucket_is_not_silently_added(api) -> None:
    api(billing_responses([usage_item(100)], {"alice": [usage_item(40, price=0.02)]}))
    with pytest.raises(ValueError, match="absent from organization aggregate"):
        real_client().get_usage_items()


def test_paginated_seats_are_normalized_and_all_pages_are_read(api) -> None:
    def handler(request):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        assert query["per_page"] == ["100"]
        rows = (
            [seat(f"user-{index}", last_activity_at=None) for index in range(100)]
            if query["page"] == ["1"]
            else [seat("USER-100", pending_cancellation_date="2026-09-30")]
        )
        return {"total_seats": 101, "seats": rows}

    requests = api(handler)
    client = real_client()
    result = client.list_seats()
    assert len(result) == 101
    assert len(requests) == 2
    assert result[0]["user"] == "user-0"
    assert result[0]["status"] == "active"
    assert result[0]["last_activity_at"] is None
    assert result[0]["activity_status"] == "unknown"
    assert result[-1]["user"] == "user-100"
    assert result[-1]["status"] == "pending_cancellation"
    assert client.seat_metadata["as_of"] is None
    assert client.seat_metadata["retrieved_at"] is not None


def test_paginated_budgets_keep_actual_scope_and_consumption(api) -> None:
    def handler(request):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        first = query["page"] == ["1"]
        rows = (
            [budget(f"budget-{index}") for index in range(100)]
            if first
            else [
                budget(
                    "user-budget",
                    budget_scope="user",
                    user="Alice",
                    budget_amount=20,
                    consumed_amount=14,
                )
            ]
        )
        return {"budgets": rows, "total_count": 101, "has_next_page": first}

    requests = api(handler)
    result = FinOpsToolbox(real_client()).list_budgets()
    assert len(requests) == 2
    assert len(result["budgets"]) == 101
    assert result["budgets"][0]["remaining_amount"] == 34.8
    assert result["budgets"][-1]["remaining_amount"] == 6
    assert result["budgets"][-1]["consumption_basis"] == "user_total_spend"
    assert result["as_of"] is None
    assert result["retrieved_at"] == "2026-09-03T12:00:00+00:00"
    assert result["currency"] == "USD"


def test_real_budget_missing_consumption_is_explicitly_unknown(api) -> None:
    row = budget("missing")
    row.pop("consumed_amount")
    api({"budgets": [row]})
    result = real_client().list_budgets()[0]
    assert result["remaining_amount"] is None
    assert result["remaining_status"] == "unknown"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"seats": []},
        {"seats": [], "total_seats": True},
        {"seats": [], "total_seats": 1},
        {"seats": None, "total_seats": 0},
        {"seats": [{"assignee": None}], "total_seats": 1},
        {"seats": [seat("Alice"), seat("alice")], "total_seats": 2},
        {"seats": [seat("alice")], "total_seats": 0},
    ],
)
def test_invalid_seat_schema_or_pagination_fails(api, payload) -> None:
    api(payload)
    with pytest.raises(ValueError):
        real_client().list_seats()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"budgets": None},
        {"budgets": [], "has_next_page": True},
        {"budgets": [], "has_next_page": "false"},
        {"budgets": [], "total_count": 1, "has_next_page": False},
        {"budgets": [budget("same"), budget("same")]},
    ],
)
def test_invalid_budget_schema_or_pagination_fails(api, payload) -> None:
    api(payload)
    with pytest.raises(ValueError):
        real_client().list_budgets()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {**report([]), "organization": "other"},
        {**report([]), "timePeriod": {"year": 2026, "month": 8}},
        {**report([]), "timePeriod": {"year": 2026, "month": 9, "day": 3}},
        {**report([]), "usageItems": None},
        {**report([]), "user": "alice"},
        report([{"netQuantity": 100}]),
        report([{**usage_item(), "netQuantity": float("nan")}]),
    ],
)
def test_invalid_billing_schema_does_not_become_empty_success(api, payload) -> None:
    api(payload)
    with pytest.raises(ValueError):
        real_client().get_usage_items()


def test_mismatched_user_echo_is_rejected(api) -> None:
    handler = billing_responses([usage_item(100)], {"alice": [usage_item(50)]})

    def mismatched(request):
        result = handler(request)
        if "user=alice" in request.full_url:
            result["user"] = "somebody-else"
        return result

    api(mismatched)
    with pytest.raises(ValueError, match="user does not match"):
        real_client().get_usage_items()


def test_optional_user_echo_may_be_absent_in_a_valid_filtered_response(api) -> None:
    handler = billing_responses([usage_item(100)], {"alice": [usage_item(70)]})

    def without_echo(request):
        result = handler(request)
        result.pop("user", None)
        return result

    requests = api(without_echo)
    rows = real_client().get_usage_items()
    assert next(row for row in rows if row.user == "alice").net_quantity == 70
    assert any("user=alice" in req.full_url for req in requests)


def test_user_billing_errors_are_not_hidden_as_unallocated_usage(api) -> None:
    handler = billing_responses([usage_item(100)], {"alice": [usage_item(70)]})

    def denied_user(request):
        if "user=alice" in request.full_url:
            raise urllib.error.HTTPError(
                request.full_url, 403, "denied", {}, io.BytesIO(b"denied")
            )
        return handler(request)

    api(denied_user)
    with pytest.raises(RuntimeError, match="failed with 403"):
        real_client().get_usage_items()


def test_explicit_empty_billing_report_is_unavailable_not_zero(api) -> None:
    api(billing_responses([], {}))
    with pytest.raises(ValueError, match="no records"):
        FinOpsToolbox(real_client()).get_cost_summary()


def test_explicit_zero_aggregate_is_distinct_from_a_missing_report(api) -> None:
    api(billing_responses([usage_item(0)], {}))
    summary = FinOpsToolbox(real_client()).get_cost_summary()
    assert summary["net_quantity"] == 0
    assert summary["net_amount"] == 0
    assert summary["record_count"] == 1
    assert summary["user_count"] == 0


@pytest.mark.parametrize("payload", [b"", b"not-json", b"[]", b"null"])
def test_invalid_http_response_is_not_empty_success(api, payload) -> None:
    api(payload)
    with pytest.raises(ValueError):
        real_client().list_seats()


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500])
def test_http_errors_are_explicit_not_empty_reports(api, status) -> None:
    def denied(request):
        raise urllib.error.HTTPError(
            request.full_url, status, "denied", {}, io.BytesIO(b"access denied")
        )

    api(denied)
    with pytest.raises(RuntimeError, match=f"failed with {status}"):
        real_client().get_usage_items()


def test_real_unsupported_periods_fail_without_fetching(api) -> None:
    requests = api({})
    tools = FinOpsToolbox(real_client())
    for period in ("today", "custom", "previous_month", "last_28_days"):
        with pytest.raises(ValueError, match="supports only: month_to_date"):
            tools.get_cost_summary(period)
    assert requests == []


def test_invalid_forecast_amounts_do_not_trigger_real_usage_reads(api) -> None:
    requests = api({})
    tools = FinOpsToolbox(real_client())
    for amount in (float("nan"), float("inf"), -1):
        with pytest.raises(ValueError, match="finite non-negative"):
            tools.forecast_budget(amount)
    assert requests == []


def test_collection_totals_cannot_change_between_pages(api) -> None:
    def handler(request):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        first = query["page"] == ["1"]
        return {
            "total_seats": 101 if first else 102,
            "seats": [seat("alice")] if first else [seat("bob")],
        }

    requests = api(handler)
    with pytest.raises(ValueError, match="total changed during pagination"):
        real_client().list_seats()
    assert len(requests) == 2


def test_real_metrics_are_unsupported_not_an_empty_population(api) -> None:
    api(billing_responses([usage_item(100)], {"alice": [usage_item(70)]}))
    client = real_client()
    with pytest.raises(NotImplementedError, match="not loaded"):
        client.get_user_metrics()
    result = FinOpsToolbox(client).recommend_optimizations()
    assert result["sources"]["user_metrics"]["status"] == "unsupported"
    categories = {row["category"] for row in result["recommendations"]}
    assert "prompt_efficiency" not in categories
    assert "seat_utilization" not in categories
    assert any("not loaded" in note for note in result["caveats"])
    assert any("as_of is unknown" in note for note in result["caveats"])
