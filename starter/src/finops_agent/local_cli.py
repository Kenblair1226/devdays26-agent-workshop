from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from .clients import MockGitHubFinOpsClient, create_finops_client
from .tools import FinOpsToolbox


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Copilot FinOps workshop agent")
    parser.add_argument(
        "--data-dir",
        help="Path containing the synthetic workshop data files.",
    )
    parser.add_argument(
        "--instructor",
        action="store_true",
        help="Explicitly enable the configured real backend on instructor machines.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("cost", "departments", "recommend"):
        command = subparsers.add_parser(name)
        command.add_argument(
            "--period",
            default="month_to_date",
            choices=[
                "today",
                "month_to_date",
                "last_28_days",
                "previous_month",
            ],
        )

    breakdown = subparsers.add_parser("breakdown")
    breakdown.add_argument(
        "--dimension",
        default="model",
        choices=["model", "user", "department", "product"],
    )
    breakdown.add_argument("--period", default="month_to_date")
    breakdown.add_argument("--department", help="Drill down into one department.")

    forecast = subparsers.add_parser("forecast")
    forecast.add_argument("budget_amount", type=float)
    forecast.add_argument("--period", default="month_to_date")

    ask = subparsers.add_parser("ask")
    ask.add_argument("prompt")
    subparsers.add_parser("chat", help="Multi-turn chat with human approval commands")
    subparsers.add_parser("seats")
    subparsers.add_parser("budgets")
    subparsers.add_parser(
        "trend", help="Read mock daily usage and comparison-period growth"
    )
    roster = subparsers.add_parser(
        "roster", help="Read one mock team's business context"
    )
    roster.add_argument("department")
    workflows = subparsers.add_parser(
        "workflows", help="Read one team's mock workflow evidence"
    )
    workflows.add_argument("department")
    workflows.add_argument(
        "--limit", type=int, default=6, help="Run sample size (1-20)."
    )
    subparsers.add_parser(
        "options", help="Compare mock improvement scenarios without writes"
    )
    demo = subparsers.add_parser("demo", help="Start the local user/admin budget demo")
    demo.add_argument("--port", type=int, default=8098)
    demo.add_argument("--user", default="carol", help="Bound mock user (default carol)")
    brief = subparsers.add_parser(
        "brief", help="Collect mock FinOps evidence for analysis in Copilot Chat"
    )
    brief.add_argument(
        "--include-investigation",
        action="store_true",
        help="Include business context and scenarios after the investigation.",
    )
    brief.add_argument(
        "--output",
        type=Path,
        help="Write a new UTF-8 JSON file; never overwrite an existing file.",
    )

    approval = subparsers.add_parser("approval-demo")
    approval.add_argument("--action", choices=["seat", "budget"], default="seat")
    approval.add_argument(
        "--rehearse",
        action="store_true",
        help="Simulate human approval against mock data only (never real writes).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.is_file():
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    backend = os.getenv("FINOPS_BACKEND", "mock").lower()
    if args.command == "demo":
        if backend != "mock" or args.instructor or args.data_dir is not None:
            raise ValueError("demo uses bundled mock data only; no instructor backend")
        from .demo_server import run_demo

        run_demo(port=args.port, user=args.user)
        return
    if args.command == "brief" and backend != "mock":
        raise ValueError("brief is mock-only; set FINOPS_BACKEND=mock")
    if (
        args.command in {"trend", "roster", "workflows", "options"}
        and backend != "mock"
    ):
        raise ValueError("workshop investigation commands are mock-only")
    if backend != "mock" and args.command != "approval-demo" and not args.instructor:
        raise ValueError("real GitHub access requires the --instructor option")
    client = (
        MockGitHubFinOpsClient(args.data_dir)
        if args.command == "approval-demo"
        else create_finops_client(args.data_dir)
    )
    toolbox = FinOpsToolbox(client)
    result: Any
    if args.command == "cost":
        result = toolbox.get_cost_summary(args.period)
    elif args.command == "departments":
        result = toolbox.rank_department_consumption(args.period)
    elif args.command == "breakdown":
        result = toolbox.break_down_usage(
            args.dimension, args.period, department=args.department
        )
    elif args.command == "forecast":
        result = toolbox.forecast_budget(args.budget_amount, args.period)
    elif args.command == "recommend":
        result = toolbox.recommend_optimizations(args.period)
    elif args.command == "seats":
        result = toolbox.list_seats()
    elif args.command == "budgets":
        result = toolbox.list_budgets()
    elif args.command == "trend":
        result = toolbox.get_daily_usage_trend()
    elif args.command == "roster":
        result = toolbox.get_team_roster(args.department)
    elif args.command == "workflows":
        result = toolbox.get_workflow_evidence(args.department, args.limit)
    elif args.command == "options":
        result = toolbox.compare_improvement_options()
    elif args.command == "brief":
        from .brief import build_analysis_brief

        result = build_analysis_brief(
            toolbox, include_investigation=args.include_investigation
        )
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
                handle.write("\n")
            print(f"Mock analysis brief written to {args.output}")
            return
    elif args.command == "approval-demo":
        result = _run_approval_demo(toolbox, action=args.action, rehearse=args.rehearse)
    elif args.command == "chat":
        asyncio.run(_chat(toolbox))
        return
    else:
        from .harness import CopilotFinOpsHarness

        result = asyncio.run(CopilotFinOpsHarness(toolbox).ask(args.prompt))

    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


def _run_approval_demo(
    toolbox: FinOpsToolbox, *, action: str = "seat", rehearse: bool = False
) -> dict[str, Any]:
    if not isinstance(toolbox.client, MockGitHubFinOpsClient):
        raise PermissionError("approval-demo must use the mock backend")
    if action == "budget":
        plan = toolbox.plan_action(
            "create_budget",
            toolbox.client.organization,
            {
                "budget_scope": "user",
                "user": "carol",
                "budget_amount": 220,
                "budget_type": "BundlePricing",
                "budget_product_sku": "ai_credits",
                "prevent_further_usage": True,
            },
        )
    else:
        plan = toolbox.plan_action(
            "remove_seats",
            toolbox.client.organization,
            {"selected_usernames": ["judy"]},
        )
    execution = _confirm_and_execute(toolbox, plan["plan_id"], rehearse=rehearse)
    return {
        "plan": plan,
        "execution": execution,
        "approval_mode": "simulated_mock_only" if rehearse else "human_console",
        "audit": toolbox.get_audit_log(),
    }


def _confirm_and_execute(
    toolbox: FinOpsToolbox, plan_id: str, *, rehearse: bool = False
) -> dict[str, Any]:
    plan = toolbox.approvals.get_plan(plan_id)
    if not rehearse:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        confirmation = input(f'Type "APPROVE {plan_id}" to execute this exact plan: ')
        if confirmation != f"APPROVE {plan_id}":
            return {"plan_id": plan_id, "status": "not_approved", "writes": 0}
    elif not isinstance(toolbox.client, MockGitHubFinOpsClient):
        raise PermissionError("simulated approval is only allowed for mock data")
    approved = toolbox.approve_action(
        plan_id,
        actor="mock-rehearsal" if rehearse else "local-human",
        confirmed=True,
    )
    executed = toolbox.execute_approved_action(
        plan_id, approved["approval_token"], actor="local-human-executor"
    )
    return executed


async def _chat(toolbox: FinOpsToolbox) -> None:
    from .harness import CopilotFinOpsHarness

    print("FinOps chat. Commands: /plans, /approve PLAN_ID, /audit, /quit.")
    harness = CopilotFinOpsHarness(toolbox)
    async with harness.conversation():
        while True:
            try:
                prompt = await asyncio.to_thread(input, "finops> ")
            except EOFError:
                break
            if prompt.strip() == "/quit":
                break
            if not prompt.strip():
                continue
            try:
                if prompt == "/plans":
                    result = toolbox.approvals.list_plans()
                elif prompt == "/audit":
                    result = toolbox.get_audit_log()
                elif prompt.startswith("/approve "):
                    result = await asyncio.to_thread(
                        _confirm_and_execute, toolbox, prompt.split(maxsplit=1)[1]
                    )
                elif prompt.startswith("/"):
                    print(
                        "Unknown command. Use /plans, /approve PLAN_ID, /audit, /quit."
                    )
                    continue
                else:
                    print(await harness.ask(prompt))
                    continue
                print(json.dumps(result, indent=2, ensure_ascii=False))
            except (KeyError, ValueError, PermissionError) as error:
                print(f"Request rejected: {error}")


if __name__ == "__main__":
    main()
