from __future__ import annotations

import importlib.resources
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from math import isfinite
from pathlib import Path
from typing import Any, Protocol

from .models import DepartmentAssignment, ReportingPeriod, UsageItem, UserMetric

_USAGE_FIELDS = {
    "product": "product",
    "sku": "sku",
    "model": "model",
    "unit_type": "unitType",
    "price_per_unit": "pricePerUnit",
    "gross_quantity": "grossQuantity",
    "gross_amount": "grossAmount",
    "discount_quantity": "discountQuantity",
    "discount_amount": "discountAmount",
    "net_quantity": "netQuantity",
    "net_amount": "netAmount",
}
_TOTAL_FIELDS = (
    "gross_quantity",
    "gross_amount",
    "discount_quantity",
    "discount_amount",
    "net_quantity",
    "net_amount",
)


class GitHubFinOpsClient(Protocol):
    @property
    def organization(self) -> str: ...

    @property
    def as_of(self) -> str | None: ...

    @property
    def retrieved_at(self) -> str | None: ...

    @property
    def currency(self) -> str: ...

    @property
    def supported_periods(self) -> set[str]: ...

    @property
    def coverage(self) -> dict[str, Any] | None: ...

    @property
    def usage_metadata(self) -> dict[str, Any]: ...

    @property
    def user_metrics_metadata(self) -> dict[str, Any]: ...

    @property
    def seat_metadata(self) -> dict[str, Any]: ...

    @property
    def budget_metadata(self) -> dict[str, Any]: ...

    def get_usage_items(self) -> list[UsageItem]: ...

    def get_department_assignments(self) -> list[DepartmentAssignment]: ...

    def get_user_metrics(self) -> list[UserMetric]: ...

    def list_seats(self) -> list[dict[str, Any]]: ...

    def list_budgets(self) -> list[dict[str, Any]]: ...

    def execute_action(
        self,
        kind: str,
        target: str,
        payload: dict[str, Any],
        *,
        human_approved: bool = False,
    ) -> dict[str, Any]: ...


class MockGitHubFinOpsClient:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        root = Path(data_dir) if data_dir else _default_data_dir()
        usage = _read_json(root / "ai-credit-usage.json")
        mappings = _read_json(root / "department-mapping.json")
        seats = _read_json(root / "seats.json")
        budgets = _read_json(root / "budgets.json")

        self._organization = _text(usage.get("organization"), "usage.organization")
        self._as_of = _timestamp(usage.get("as_of"), "usage.as_of")
        self._currency = _text(usage.get("currency"), "usage.currency")
        self._simulation_basis = deepcopy(usage.get("simulation_basis"))
        self._retrieved_at = datetime.now(UTC).isoformat()
        for name, snapshot in (("seats", seats), ("budgets", budgets)):
            if (
                _text(snapshot.get("organization"), f"{name}.organization").casefold()
                != self._organization.casefold()
            ):
                raise ValueError(f"{name} organization does not match usage")
            if _text(snapshot.get("currency"), f"{name}.currency") != self._currency:
                raise ValueError(f"{name} currency does not match usage")
        self._seat_as_of = _timestamp(seats.get("as_of"), "seats.as_of")
        self._budget_as_of = _timestamp(budgets.get("as_of"), "budgets.as_of")
        metric_end = datetime.fromisoformat(self._as_of).date()
        self._coverage = deepcopy(
            usage.get(
                "coverage",
                {
                    "start": (metric_end - timedelta(days=27)).isoformat(),
                    "end": metric_end.isoformat(),
                    "kind": "sparse_training_samples",
                },
            )
        )
        self._usage_items = [
            UsageItem.from_dict(item)
            for item in _objects(usage.get("usage_items"), "usage_items")
        ]
        self._metric_period = ReportingPeriod(
            metric_end - timedelta(days=27), metric_end, "last_28_days"
        )
        self._user_metrics = [
            UserMetric.from_dict(
                item,
                period=self._metric_period,
                source="synthetic users-28-day.ndjson workshop metrics",
                as_of=self._as_of,
            )
            for item in _read_ndjson(root / "users-28-day.ndjson")
        ]
        if len({metric.user for metric in self._user_metrics}) != len(
            self._user_metrics
        ):
            raise ValueError("duplicate case-insensitive users in user metrics")
        self._assignments = _department_assignments(mappings)
        self._seats = [
            _normalize_seat(item, real=False)
            for item in _objects(seats.get("seats"), "seats")
        ]
        if len({seat["user"] for seat in self._seats}) != len(self._seats):
            raise ValueError("duplicate case-insensitive users in seats")
        self._budgets = deepcopy(_objects(budgets.get("budgets"), "budgets"))

    @property
    def organization(self) -> str:
        return self._organization

    @property
    def as_of(self) -> str:
        return self._as_of

    @property
    def retrieved_at(self) -> str:
        return self._retrieved_at

    @property
    def currency(self) -> str:
        return self._currency

    @property
    def supported_periods(self) -> set[str]:
        return {
            "today",
            "month_to_date",
            "last_28_days",
            "previous_month",
            "custom",
        }

    @property
    def coverage(self) -> dict[str, Any]:
        """Inclusive sample range, not a claim that missing days had zero usage."""
        return deepcopy(self._coverage)

    @property
    def usage_metadata(self) -> dict[str, Any]:
        return {
            "source": "synthetic GitHub billing AI credit usage (workshop fixture)",
            "retrieved_at": self.retrieved_at,
            "granularity": "daily_samples",
            "coverage": self.coverage,
            "pricing_note": "Teaching figures only; not actual GitHub model rates.",
            "simulation_basis": deepcopy(self._simulation_basis),
            "rounding_note": (
                "Totals use unrounded records before rounding to two decimal places. "
                "Independently rounded rows can differ slightly from displayed totals."
            ),
            "limitations": [
                "Intentionally sparse training data. Totals describe supplied samples, "
                "not a complete organization; missing days are not observed zeros.",
                "Snapshot dates belong to a pre-simulated teaching scenario, "
                "not real usage observed today.",
                "Department/cost_center pairs are resolved organizer mappings, "
                "not a live cost-center lookup.",
            ],
        }

    @property
    def user_metrics_metadata(self) -> dict[str, Any]:
        return {
            "status": "available",
            "source": "synthetic users-28-day.ndjson workshop metrics",
            "period": self._metric_period.as_dict(),
            "as_of": self.as_of,
            "retrieved_at": self.retrieved_at,
            "limitations": [
                "Fixed 28-day sample metrics, separate from the billing query period.",
                "Credit volume extends the synthetic three-day per-user baseline "
                "over 28 days; activity and completion counts are separate examples.",
                "Acceptance rate is not raw-token usage or proof of waste.",
            ],
        }

    @property
    def seat_metadata(self) -> dict[str, Any]:
        return {
            "source": "synthetic seats.json workshop snapshot",
            "as_of": self._seat_as_of,
            "retrieved_at": self.retrieved_at,
            "pricing_note": (
                "Fixture seat prices are teaching assumptions, not live rates."
            ),
            "limitations": ["Missing last activity means unknown, not unused."],
        }

    @property
    def budget_metadata(self) -> dict[str, Any]:
        return {
            "source": "synthetic budgets.json workshop snapshot",
            "as_of": self._budget_as_of,
            "retrieved_at": self.retrieved_at,
            "currency": self.currency,
            "limitations": [
                "Use each budget's own consumed_amount and scope, not an MTD "
                "billing summary or scenario forecast."
            ],
        }

    def get_usage_items(self) -> list[UsageItem]:
        return list(self._usage_items)

    def get_department_assignments(self) -> list[DepartmentAssignment]:
        return list(self._assignments)

    def get_user_metrics(self) -> list[UserMetric]:
        return list(self._user_metrics)

    def list_seats(self) -> list[dict[str, Any]]:
        return deepcopy(self._seats)

    def list_budgets(self) -> list[dict[str, Any]]:
        return [
            _annotate_budget(budget, self.budget_metadata) for budget in self._budgets
        ]

    def execute_action(
        self,
        kind: str,
        target: str,
        payload: dict[str, Any],
        *,
        human_approved: bool = False,
    ) -> dict[str, Any]:
        if kind in {"assign_seats", "remove_seats"}:
            usernames = _require_usernames(payload)
            return self._change_seats(kind, usernames)
        if kind == "create_budget":
            budget = deepcopy(payload)
            budget["id"] = f"mock-budget-{len(self._budgets) + 1}"
            self._budgets.append(budget)
            return {"budget": deepcopy(budget), "mock": True}
        if kind == "update_budget":
            for budget in self._budgets:
                if budget["id"] == target:
                    budget.update(deepcopy(payload))
                    return {"budget": deepcopy(budget), "mock": True}
            raise KeyError(f"budget not found: {target}")
        raise ValueError(f"unsupported action kind: {kind}")

    def _change_seats(self, kind: str, usernames: list[str]) -> dict[str, Any]:
        seats_by_user = {seat["user"]: seat for seat in self._seats}
        changed = 0
        for username in usernames:
            if kind == "assign_seats":
                if username not in seats_by_user:
                    seat = {
                        "user": username,
                        "plan_type": "business",
                        "status": "active",
                        "last_activity_at": None,
                    }
                    self._seats.append(seat)
                    seats_by_user[username] = seat
                    changed += 1
                elif seats_by_user[username]["status"] != "active":
                    seats_by_user[username]["status"] = "active"
                    changed += 1
            elif (
                username in seats_by_user
                and seats_by_user[username]["status"] != "pending_cancellation"
            ):
                seats_by_user[username]["status"] = "pending_cancellation"
                changed += 1
        return {
            "mock": True,
            "action": kind,
            "users": usernames,
            "changed": changed,
        }


class RealGitHubFinOpsClient:
    def __init__(
        self,
        organization: str,
        token: str,
        *,
        allow_writes: bool = False,
        api_version: str = "2026-03-10",
        department_assignments: list[DepartmentAssignment] | None = None,
    ) -> None:
        self._organization = _text(organization, "organization")
        self._token = _text(token, "token")
        self._allow_writes = allow_writes
        self._api_version = api_version
        self._assignments = list(
            DepartmentAssignment.index(department_assignments or []).values()
        )
        self._currency = "USD"
        self._coverage: dict[str, Any] | None = None
        self._usage_retrieved_at: str | None = None
        self._seat_retrieved_at: str | None = None
        self._budget_retrieved_at: str | None = None
        self._reconciliation: dict[str, Any] | None = None

    @classmethod
    def from_environment(cls) -> RealGitHubFinOpsClient:
        mapping_path = os.getenv("FINOPS_DEPARTMENT_MAPPING")
        assignments = (
            _load_department_assignments(Path(mapping_path)) if mapping_path else []
        )
        return cls(
            organization=os.environ["GITHUB_ORG"],
            token=os.environ["GITHUB_ADMIN_TOKEN"],
            allow_writes=os.getenv("FINOPS_ALLOW_REAL_WRITES") == "true",
            department_assignments=assignments,
        )

    @property
    def organization(self) -> str:
        return self._organization

    @property
    def as_of(self) -> None:
        return None

    @property
    def retrieved_at(self) -> str | None:
        return self._usage_retrieved_at

    @property
    def currency(self) -> str:
        return self._currency

    @property
    def supported_periods(self) -> set[str]:
        return {"month_to_date"}

    @property
    def coverage(self) -> dict[str, Any] | None:
        return deepcopy(self._coverage)

    @property
    def usage_metadata(self) -> dict[str, Any]:
        return {
            "status": "available" if self.retrieved_at else "not_loaded",
            "source": (
                "GitHub GET /organizations/{org}/settings/billing/ai_credit/usage; "
                "independent organization aggregate plus per-known-user reports"
            ),
            "retrieved_at": self.retrieved_at,
            "granularity": "month_to_date_aggregate",
            "coverage": self.coverage,
            "reconciliation": deepcopy(self._reconciliation),
            "pricing_note": (
                "Provider billing amounts in USD; no seat pricing or final invoice "
                "is inferred."
            ),
            "limitations": [
                "Only the current month's aggregate is supported; no daily dates "
                "are supplied or invented.",
                "Provider as_of is unknown. The requested window ends on the "
                "retrieval date, which does not establish data freshness.",
                "Known users are current seat holders plus the resolved organizer "
                "mapping. Former or otherwise unknown users remain in Unallocated "
                "through reconciliation with the organization report.",
                "Reports are fetched sequentially, not as an atomic provider snapshot. "
                "Inconsistent totals fail rather than being clamped.",
            ],
        }

    @property
    def user_metrics_metadata(self) -> dict[str, Any]:
        return {
            "status": "unsupported",
            "source": None,
            "period": None,
            "as_of": None,
            "retrieved_at": None,
            "reason": (
                "28-day user metrics are not loaded by this adapter. This does not "
                "mean that the organization has no metrics."
            ),
        }

    @property
    def seat_metadata(self) -> dict[str, Any]:
        return {
            "source": "GitHub GET /orgs/{org}/copilot/billing/seats (all pages)",
            "as_of": None,
            "retrieved_at": self._seat_retrieved_at,
            "pricing_note": "No applicable seat price was retrieved.",
            "limitations": [
                "Provider snapshot as_of is unknown; retrieved_at is not freshness.",
                "Missing last activity means unknown, not unused.",
            ],
        }

    @property
    def budget_metadata(self) -> dict[str, Any]:
        return {
            "source": (
                "GitHub GET /organizations/{org}/settings/billing/budgets (all pages)"
            ),
            "as_of": None,
            "retrieved_at": self._budget_retrieved_at,
            "currency": self.currency,
            "limitations": [
                "Provider snapshot as_of is unknown; retrieved_at is not freshness.",
                "Missing consumed_amount means unknown remaining balance.",
                "Budgets have independent scopes; do not subtract a generic billing "
                "summary or scenario forecast from a budget.",
            ],
        }

    def get_usage_items(self) -> list[UsageItem]:
        now = datetime.now(UTC)
        period = ReportingPeriod(now.date().replace(day=1), now.date(), "month_to_date")
        aggregate = _billing_items(
            self.get_ai_credit_usage(year=now.year, month=now.month),
            period=period,
            user=None,
        )
        known_users = {seat["user"] for seat in self.list_seats()}
        known_users.update(assignment.user for assignment in self._assignments)
        attributed: list[UsageItem] = []
        for username in sorted(known_users):
            response = self.get_ai_credit_usage(
                year=now.year, month=now.month, user=username
            )
            attributed.extend(_billing_items(response, period=period, user=username))
        residual = _reconcile_usage(aggregate, attributed, period)
        retrieved = datetime.now(UTC)
        if retrieved.date() != now.date():
            raise ValueError("reporting date changed during usage collection; retry")
        self._usage_retrieved_at = retrieved.isoformat()
        self._coverage = {
            "start": period.start.isoformat(),
            "end": period.end.isoformat(),
            "kind": "requested_month_to_date",
            "organization_totals": "independently reported",
            "user_attribution": "partial; remaining totals are Unallocated",
        }
        self._reconciliation = {
            "known_users_queried": len(known_users),
            "organization_net_quantity": _total(aggregate, "net_quantity"),
            "organization_net_amount": _total(aggregate, "net_amount"),
            "unattributed_net_quantity": _total(residual, "net_quantity"),
            "unattributed_net_amount": _total(residual, "net_amount"),
        }
        return attributed + residual

    def get_department_assignments(self) -> list[DepartmentAssignment]:
        return list(self._assignments)

    def get_user_metrics(self) -> list[UserMetric]:
        raise NotImplementedError(self.user_metrics_metadata["reason"])

    def get_ai_credit_usage(
        self,
        *,
        year: int,
        month: int,
        day: int | None = None,
        user: str | None = None,
        model: str | None = None,
        product: str | None = None,
    ) -> dict[str, Any]:
        if type(year) is not int or not 1000 <= year <= 9999:
            raise ValueError("year must be a four-digit integer")
        if type(month) is not int or not 1 <= month <= 12:
            raise ValueError("month must be an integer from 1 to 12")
        if day is not None:
            if type(day) is not int:
                raise ValueError("day must be an integer")
            date(year, month, day)
        params: dict[str, Any] = {"year": year, "month": month}
        if day is not None:
            params["day"] = day
        for field, value in (("user", user), ("model", model), ("product", product)):
            if value is not None:
                params[field] = _text(value, field)
        organization = urllib.parse.quote(self._organization, safe="")
        response = self._request(
            "GET",
            f"/organizations/{organization}/settings/billing/"
            f"ai_credit/usage?{urllib.parse.urlencode(params)}",
        )
        report_org = _text(response.get("organization"), "usage.organization")
        if report_org.casefold() != self._organization.casefold():
            raise ValueError("billing report organization does not match the request")
        time_period = response.get("timePeriod")
        if not isinstance(time_period, dict):
            raise ValueError("billing report requires a timePeriod object")
        for field, expected in (("year", year), ("month", month), ("day", day)):
            actual = time_period.get(field)
            if actual != expected or (actual is not None and type(actual) is not int):
                raise ValueError(
                    f"billing report timePeriod.{field} mismatches request"
                )
        for field in ("user", "model", "product"):
            expected = params.get(field)
            actual = response.get(field)
            if expected is None:
                if actual is not None:
                    raise ValueError(f"billing report has an unexpected {field} filter")
            elif actual is not None and (
                _text(actual, f"usage.{field}").casefold() != expected.casefold()
            ):
                raise ValueError(f"billing report {field} does not match the request")
        _objects(response.get("usageItems"), "billing report usageItems")
        return response

    def list_seats(self) -> list[dict[str, Any]]:
        organization = urllib.parse.quote(self._organization, safe="")
        records = self._paginate(
            f"/orgs/{organization}/copilot/billing/seats",
            "seats",
            "total_seats",
            lambda seat: _seat_login(seat, real=True),
            require_total=True,
        )
        normalized = [_normalize_seat(item, real=True) for item in records]
        self._seat_retrieved_at = datetime.now(UTC).isoformat()
        return normalized

    def list_budgets(self) -> list[dict[str, Any]]:
        organization = urllib.parse.quote(self._organization, safe="")
        records = self._paginate(
            f"/organizations/{organization}/settings/billing/budgets",
            "budgets",
            "total_count",
            lambda budget: _text(budget.get("id"), "budget.id"),
        )
        self._budget_retrieved_at = datetime.now(UTC).isoformat()
        return [_annotate_budget(budget, self.budget_metadata) for budget in records]

    def _paginate(
        self,
        path: str,
        collection: str,
        total_field: str,
        identifier: Callable[[dict[str, Any]], str],
        *,
        require_total: bool = False,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        total: int | None = None
        page = 1
        promised_next = False
        while True:
            response = self._request("GET", f"{path}?per_page=100&page={page}")
            rows = _objects(response.get(collection), collection)
            if len(rows) > 100:
                raise ValueError(f"{collection} page exceeds requested page size")
            if total_field in response or require_total:
                reported_total = response.get(total_field)
                if type(reported_total) is not int or reported_total < 0:
                    raise ValueError(f"{total_field} must be a non-negative integer")
                if total is not None and total != reported_total:
                    raise ValueError(f"{collection} total changed during pagination")
                total = reported_total
            has_next = response.get("has_next_page")
            if "has_next_page" in response and type(has_next) is not bool:
                raise ValueError("has_next_page must be a boolean")
            if not rows and (has_next is True or promised_next):
                raise ValueError(
                    f"{collection} pagination promised a missing next page"
                )
            for row in rows:
                key = identifier(row)
                if key in seen:
                    raise ValueError(
                        f"duplicate {collection} identity during pagination"
                    )
                seen.add(key)
                result.append(row)
            if total is not None:
                if len(result) > total:
                    raise ValueError(f"{collection} count exceeds reported total")
                if len(result) == total:
                    if has_next is True:
                        raise ValueError(f"{collection} next page conflicts with total")
                    break
                if not rows or has_next is False:
                    raise ValueError(f"{collection} pages do not match reported total")
            elif has_next is False or (has_next is None and len(rows) < 100):
                break
            promised_next = has_next is True
            page += 1
        return result

    def execute_action(
        self,
        kind: str,
        target: str,
        payload: dict[str, Any],
        *,
        human_approved: bool = False,
    ) -> dict[str, Any]:
        if (
            human_approved is not True
            or self._allow_writes is not True
            or os.getenv("FINOPS_ALLOW_REAL_WRITES") != "true"
        ):
            raise PermissionError(
                "Real GitHub writes are disabled. Instructor execution requires "
                "human_approved=True, allow_writes=True, and "
                "FINOPS_ALLOW_REAL_WRITES=true."
            )
        if kind in {"assign_seats", "remove_seats"}:
            method = "POST" if kind == "assign_seats" else "DELETE"
            return self._request(
                method,
                f"/orgs/{self._organization}/copilot/billing/selected_users",
                {"selected_usernames": _require_usernames(payload)},
            )
        if kind == "create_budget":
            return self._request(
                "POST",
                f"/organizations/{self._organization}/settings/billing/budgets",
                payload,
            )
        if kind == "update_budget":
            return self._request(
                "PATCH",
                f"/organizations/{self._organization}/settings/billing/budgets/"
                f"{urllib.parse.quote(target, safe='')}",
                payload,
            )
        raise ValueError(f"unsupported action kind: {kind}")

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = (
            json.dumps(body, allow_nan=False).encode("utf-8")
            if body is not None
            else None
        )
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": self._api_version,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API {method} {path} failed with {error.code}: {details}"
            ) from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"GitHub API {method} {path} transport failed: {error.reason}"
            ) from error
        if not content:
            if method == "GET":
                raise ValueError(f"GitHub API GET {path} returned an empty response")
            return {}
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(
                f"GitHub API {method} {path} returned invalid JSON"
            ) from error
        if not isinstance(parsed, dict):
            raise ValueError(f"GitHub API {method} {path} must return a JSON object")
        return parsed


def _default_data_dir() -> Path:
    configured = os.getenv("FINOPS_DATA_DIR")
    if configured:
        return Path(configured)
    for candidate in (
        Path(__file__).resolve().parents[2] / "data",
        Path(__file__).resolve().parents[3] / "data",
    ):
        if candidate.exists():
            return candidate
    try:
        return Path(str(importlib.resources.files("finops_demo_data")))
    except ModuleNotFoundError as error:
        raise FileNotFoundError(
            "FinOps demo data is unavailable: no source-tree data directory and "
            "finops_demo_data is not installed. Install the packaged solution or "
            "set FINOPS_DATA_DIR."
        ) from error


def create_finops_client(
    data_dir: str | Path | None = None,
) -> GitHubFinOpsClient:
    backend = os.getenv("FINOPS_BACKEND", "mock").lower()
    if backend == "mock":
        return MockGitHubFinOpsClient(data_dir)
    if backend == "github":
        if data_dir is not None:
            raise ValueError("data_dir is only valid when FINOPS_BACKEND=mock")
        return RealGitHubFinOpsClient.from_environment()
    raise ValueError("FINOPS_BACKEND must be mock or github")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"FinOps data file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"FinOps data file must contain a JSON object: {path}")
    return value


def _load_department_assignments(path: Path) -> list[DepartmentAssignment]:
    return _department_assignments(_read_json(path))


def _department_assignments(data: dict[str, Any]) -> list[DepartmentAssignment]:
    assignments = [
        DepartmentAssignment(
            user=_text(item.get("user"), "mapping.user"),
            department=_text(item.get("department"), "mapping.department"),
            cost_center=item.get("cost_center"),
        )
        for item in _objects(data.get("users"), "department mapping users")
    ]
    return list(DepartmentAssignment.index(assignments).values())


def _read_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"FinOps data file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _objects(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"{field} must be an array of objects")
    return value


def _number(value: Any, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{field} must be a finite non-negative number")
    return float(value)


def _timestamp(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    text = _text(value, field)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return text


def _seat_login(seat: dict[str, Any], *, real: bool) -> str:
    if real:
        assignee = seat.get("assignee")
        if not isinstance(assignee, dict):
            raise ValueError("seat.assignee must be an object")
        return _text(assignee.get("login"), "seat.assignee.login").casefold()
    return _text(seat.get("user"), "seat.user").casefold()


def _normalize_seat(seat: dict[str, Any], *, real: bool) -> dict[str, Any]:
    pending = seat.get("pending_cancellation_date")
    if pending is not None:
        date.fromisoformat(_text(pending, "seat.pending_cancellation_date"))
    activity = _timestamp(
        seat.get("last_activity_at"), "seat.last_activity_at", nullable=True
    )
    result = {
        "user": _seat_login(seat, real=real),
        "plan_type": (
            _text(seat["plan_type"], "seat.plan_type")
            if seat.get("plan_type") is not None
            else "unknown"
        ),
        "status": (
            ("pending_cancellation" if pending is not None else "active")
            if real
            else _text(seat.get("status"), "seat.status")
        ),
        "last_activity_at": activity,
        "activity_status": "reported" if activity is not None else "unknown",
    }
    for field in ("created_at", "updated_at"):
        if field in seat:
            result[field] = _timestamp(seat[field], f"seat.{field}", nullable=True)
    if "pending_cancellation_date" in seat:
        result["pending_cancellation_date"] = pending
    return result


def _annotate_budget(
    budget: dict[str, Any], metadata: dict[str, Any]
) -> dict[str, Any]:
    result = deepcopy(budget)
    for field in ("id", "budget_type", "budget_product_sku", "budget_scope"):
        result[field] = _text(budget.get(field), f"budget.{field}")
    if result["budget_type"] not in {"BundlePricing", "ProductPricing", "SkuPricing"}:
        raise ValueError(f"unsupported budget type: {result['budget_type']}")
    scope = result["budget_scope"]
    if scope not in {
        "enterprise",
        "organization",
        "repository",
        "cost_center",
        "multi_user_customer",
        "multi_user_cost_center",
        "user",
    }:
        raise ValueError(f"unsupported budget scope: {scope}")
    if type(budget.get("prevent_further_usage")) is not bool:
        raise ValueError("budget.prevent_further_usage must be a boolean")
    if scope == "user":
        result["user"] = _text(budget.get("user"), "budget.user").casefold()
    amount = _number(budget.get("budget_amount"), "budget.budget_amount")
    consumed = budget.get("consumed_amount")
    if consumed is not None:
        consumed = _number(consumed, "budget.consumed_amount")
    remaining = (
        float(Decimal(str(amount)) - Decimal(str(consumed)))
        if consumed is not None
        else None
    )
    basis, note = {
        "organization": (
            "organization_metered_spend",
            "Organization metered spending for this product/SKU, not a user's "
            "total AI-credit allowance.",
        ),
        "user": (
            "user_total_spend",
            "This user's total consumption for the budgeted product/SKU, "
            "not organization metered-only spending.",
        ),
        "multi_user_customer": (
            "per_user_total_limit",
            "A universal limit applied per user, not one pooled organization budget.",
        ),
    }.get(
        scope,
        (
            "scope_specific_provider_consumption",
            "Consumption for the named provider scope and product/SKU only.",
        ),
    )
    ai_budget = result["budget_product_sku"] in {"ai_credits", "premium_requests"}
    if not ai_budget:
        basis = "scope_specific_provider_consumption"
        note = (
            "This budget's own scope and product/SKU only. Its amount unit was not "
            "verified; license-based budgets may count licenses instead of USD."
        )
    result.update(
        {
            "budget_amount": amount,
            "consumed_amount": consumed,
            "remaining_amount": round(remaining, 2) if remaining is not None else None,
            "remaining_status": "known" if consumed is not None else "unknown",
            "consumption_basis": basis,
            "scope_note": note,
            "currency": metadata["currency"] if ai_budget else None,
            "amount_unit": metadata["currency"]
            if ai_budget
            else "provider_budget_units",
            "as_of": metadata["as_of"],
            "retrieved_at": metadata["retrieved_at"],
            "source": metadata["source"],
        }
    )
    return result


def _billing_items(
    response: dict[str, Any], *, period: ReportingPeriod, user: str | None
) -> list[UsageItem]:
    records = []
    for row in _objects(response.get("usageItems"), "billing report usageItems"):
        missing = set(_USAGE_FIELDS.values()) - row.keys()
        if missing:
            raise ValueError(f"billing usage item missing fields: {sorted(missing)}")
        records.append(
            UsageItem.from_dict(
                {
                    "date": None,
                    "user": user,
                    **{name: row[provider] for name, provider in _USAGE_FIELDS.items()},
                },
                period=period,
            )
        )
    return records


def _usage_key(item: UsageItem) -> tuple[Any, ...]:
    return (
        item.product,
        item.sku,
        item.model,
        item.unit_type,
        Decimal(str(item.price_per_unit)),
    )


def _reconcile_usage(
    aggregate: list[UsageItem], attributed: list[UsageItem], period: ReportingPeriod
) -> list[UsageItem]:
    prototypes: dict[tuple[Any, ...], UsageItem] = {}
    remaining: dict[tuple[Any, ...], dict[str, Decimal]] = {}
    for item in aggregate:
        key = _usage_key(item)
        prototypes[key] = item
        bucket = remaining.setdefault(key, dict.fromkeys(_TOTAL_FIELDS, Decimal(0)))
        for field in _TOTAL_FIELDS:
            bucket[field] += Decimal(str(getattr(item, field)))
    for item in attributed:
        key = _usage_key(item)
        if key not in remaining:
            raise ValueError(
                "user billing bucket is absent from organization aggregate"
            )
        for field in _TOTAL_FIELDS:
            remaining[key][field] -= Decimal(str(getattr(item, field)))
    attributed_keys = {_usage_key(item) for item in attributed}
    residual: list[UsageItem] = []
    for key, totals in remaining.items():
        for field, value in totals.items():
            if value < 0:
                raise ValueError(
                    f"inconsistent organization/user totals: {field} exceeds "
                    "the organization aggregate; retry a consistent snapshot"
                )
        if not any(totals.values()) and key in attributed_keys:
            continue
        prototype = prototypes[key]
        residual.append(
            UsageItem(
                date=None,
                user=None,
                period=period,
                product=prototype.product,
                sku=prototype.sku,
                model=prototype.model,
                unit_type=prototype.unit_type,
                price_per_unit=prototype.price_per_unit,
                **{field: float(value) for field, value in totals.items()},
            )
        )
    return residual


def _total(records: list[UsageItem], field: str) -> float:
    return float(
        sum((Decimal(str(getattr(item, field))) for item in records), start=Decimal(0))
    )


def _require_usernames(payload: dict[str, Any]) -> list[str]:
    usernames = payload.get("selected_usernames")
    if not isinstance(usernames, list) or not usernames:
        raise ValueError("selected_usernames must be a non-empty list")
    normalized = [str(username).strip() for username in usernames]
    if any(not username for username in normalized):
        raise ValueError("selected_usernames must not contain blank values")
    return normalized
