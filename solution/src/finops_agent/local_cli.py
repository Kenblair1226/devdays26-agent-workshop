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

    forecast = subparsers.add_parser("forecast")
    forecast.add_argument("budget_amount", type=float)
    forecast.add_argument("--period", default="month_to_date")

    ask = subparsers.add_parser("ask")
    ask.add_argument("prompt")
    subparsers.add_parser("chat", help="Multi-turn chat with human approval commands")
    subparsers.add_parser("seats")
    subparsers.add_parser("budgets")
    usage = subparsers.add_parser(
        "copilot-usage",
        help="Read your real Copilot account quota without a model call",
    )
    usage.add_argument(
        "--live",
        action="store_true",
        required=True,
        help="Allow a live, read-only lookup using COPILOT_GITHUB_TOKEN.",
    )
    demo = subparsers.add_parser("demo", help="Start the local user/admin budget demo")
    demo.add_argument("--port", type=int, default=8098)
    demo.add_argument("--user", default="carol", help="Bound mock user (default carol)")
    brief = subparsers.add_parser(
        "brief", help="Collect mock FinOps evidence for analysis in Copilot Chat"
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
    parser = build_parser()
    args = parser.parse_args()
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.is_file():
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    if args.command == "copilot-usage":
        if args.instructor or args.data_dir is not None:
            parser.error(
                "copilot-usage uses only your Copilot credential, not org data"
            )
        from .copilot_usage import CopilotUsageError, read_copilot_usage

        try:
            usage = asyncio.run(read_copilot_usage(live=args.live))
        except CopilotUsageError as error:
            parser.exit(1, f"Copilot account quota unavailable: {error}\n")
        print(json.dumps(usage, indent=2, ensure_ascii=False, allow_nan=False))
        return
    backend = os.getenv("FINOPS_BACKEND", "mock").lower()
    if args.command == "demo":
        if backend != "mock" or args.instructor or args.data_dir is not None:
            raise ValueError("demo uses bundled mock data only; no instructor backend")
        from .demo_server import run_demo

        run_demo(port=args.port, user=args.user)
        return
    if args.command == "brief" and backend != "mock":
        raise ValueError("brief is mock-only; set FINOPS_BACKEND=mock")
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
        result = toolbox.break_down_usage(args.dimension, args.period)
    elif args.command == "forecast":
        result = toolbox.forecast_budget(args.budget_amount, args.period)
    elif args.command == "recommend":
        result = toolbox.recommend_optimizations(args.period)
    elif args.command == "seats":
        result = toolbox.list_seats()
    elif args.command == "budgets":
        result = toolbox.list_budgets()
    elif args.command == "brief":
        from .brief import build_analysis_brief

        result = build_analysis_brief(toolbox)
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
                "budget_amount": 30,
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
