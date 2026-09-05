from __future__ import annotations

import re
from copy import deepcopy
from datetime import date
from typing import Any


def validate_action(
    kind: str,
    target: str,
    payload: dict[str, Any],
    organization: str,
    budgets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate a narrow workshop action before asking a human to approve it."""
    if not isinstance(payload, dict):
        raise ValueError("action payload must be an object")
    if kind not in {"assign_seats", "remove_seats", "create_budget", "update_budget"}:
        raise ValueError("unsupported action kind")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("action target is required")
    if kind != "update_budget" and target.casefold() != organization.casefold():
        raise ValueError("action target must match the configured organization")
    result = deepcopy(payload)
    if kind in {"assign_seats", "remove_seats"}:
        if set(result) != {"selected_usernames"}:
            raise ValueError("seat actions accept only selected_usernames")
        users = result["selected_usernames"]
        if not isinstance(users, list) or not 1 <= len(users) <= 10:
            raise ValueError("select between 1 and 10 users per workshop action")
        normalized = []
        for user in users:
            if not isinstance(user, str) or not re.fullmatch(
                r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", user
            ):
                raise ValueError("invalid GitHub username")
            normalized.append(user.casefold())
        if len(set(normalized)) != len(normalized):
            raise ValueError("duplicate usernames in action")
        result["selected_usernames"] = normalized
        return result

    if kind == "create_budget":
        allowed = {
            "budget_scope",
            "budget_entity_name",
            "budget_amount",
            "budget_type",
            "budget_product_sku",
            "prevent_further_usage",
            "user",
            "expires_at",
        }
        required = {
            "budget_scope",
            "budget_amount",
            "budget_type",
            "budget_product_sku",
            "prevent_further_usage",
        }
        if not required <= set(result) or set(result) - allowed:
            raise ValueError("invalid or missing budget fields")
        if result["budget_scope"] not in {"organization", "user"}:
            raise ValueError("workshop budgets support organization or user scope")
        if (
            result["budget_type"] != "BundlePricing"
            or result["budget_product_sku"] != "ai_credits"
        ):
            raise ValueError("only BundlePricing / ai_credits budgets are supported")
        if result.get("budget_entity_name", "") not in {"", organization}:
            raise ValueError("budget entity must match the configured organization")
        scope = result["budget_scope"]
        if scope == "user":
            user = result.get("user")
            validate_action(
                "assign_seats",
                organization,
                {"selected_usernames": [user]},
                organization,
                [],
            )
        elif "user" in result:
            raise ValueError("organization budgets cannot specify a user")
        result.setdefault("budget_entity_name", "")
    else:
        if not result or set(result) - {
            "budget_amount",
            "prevent_further_usage",
            "expires_at",
        }:
            raise ValueError("update only amount, hard-stop, or expiration")
        current = next((b for b in budgets if b["id"] == target), None)
        if current is None:
            raise ValueError("unknown budget ID")
        if current.get("budget_product_sku") != "ai_credits":
            raise ValueError("only AI-credit budgets can be updated")
        scope = current["budget_scope"]
        if scope not in {"organization", "user"}:
            raise ValueError("unsupported budget scope")
        if scope == "user" and current.get("prevent_further_usage") is not True:
            raise ValueError("user budgets must enforce a hard stop")

    if "budget_amount" in result:
        amount = result["budget_amount"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("budget_amount must be a non-negative whole USD amount")
    if "prevent_further_usage" in result:
        if not isinstance(result["prevent_further_usage"], bool):
            raise ValueError("prevent_further_usage must be a boolean")
        if scope == "user" and result["prevent_further_usage"] is not True:
            raise ValueError("user budgets must enforce a hard stop")
    if "expires_at" in result:
        if scope != "user":
            raise ValueError("only user budgets support expiration")
        expiration = result["expires_at"]
        if (
            not isinstance(expiration, str)
            or date.fromisoformat(expiration) <= date.today()
        ):
            raise ValueError("expires_at must be a future YYYY-MM-DD date")
    return result
