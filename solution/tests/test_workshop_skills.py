import json
import re
import shlex
from pathlib import Path

import pytest

from finops_agent.local_cli import build_parser

ROOT = Path(__file__).parents[2]
SKILLS = ROOT / ".github" / "skills"


def skill_text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def skill_content(name: str) -> str:
    folder = SKILLS / name
    return "\n".join(path.read_text(encoding="utf-8") for path in folder.rglob("*.md"))


@pytest.mark.parametrize("name", ["finops-investigation", "finops-dashboard"])
def test_project_skill_metadata_matches_the_discoverable_directory(name) -> None:
    text = skill_text(name)
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert frontmatter is not None
    fields = {}
    for line in frontmatter[1].splitlines():
        key, separator, value = line.partition(":")
        assert separator and key not in fields
        fields[key] = value.strip()
    assert fields["name"] == name
    assert set(fields) <= {
        "name",
        "description",
        "argument-hint",
        "user-invocable",
        "disable-model-invocation",
    }
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
    assert len(name) <= 64
    description = json.loads(fields["description"])
    assert isinstance(description, str) and 30 <= len(description) <= 1024
    assert "Use" in description
    assert fields["user-invocable"] == "true"
    assert json.loads(fields["argument-hint"])
    assert "context" not in fields
    assert "allowed-tools" not in fields


@pytest.mark.parametrize("name", ["finops-investigation", "finops-dashboard"])
def test_skill_references_are_explicit_local_and_resolve(name) -> None:
    path = SKILLS / name / "SKILL.md"
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", skill_text(name))
    references = [target for target in links if target.startswith("references/")]
    assert references
    for target in links:
        assert not target.startswith(("~", "file:", "http:"))
        assert (path.parent / target.split("#", 1)[0]).resolve().is_file(), target
    for resource in (path.parent / "references").glob("*.md"):
        assert f"references/{resource.name}" in references


def test_investigation_preserves_progressive_disclosure_and_read_only_scope() -> None:
    content = skill_content("finops-investigation")
    body = skill_text("finops-investigation")
    for required in (
        "本月 AI credits 成長異常",
        "trend",
        "roster",
        "workflows",
        "forecast 600",
        "options",
        "successful_tasks",
        "cost_per_successful_task_usd",
        "input_revision",
        "result_digest",
        "model",
        "truncated",
        "summary_scope",
        "FINOPS_BACKEND",
        "FINOPS_ALLOW_REAL_WRITES",
        "--data-dir data",
        "不安裝",
        "不改 source",
        "不讀憑證",
        "不建立 plan 或 approval",
        "Ask",
    ):
        assert required in content, required
    assert (
        body.index("**確認成長") < body.index("**補齊背景") < body.index("**比較方案")
    )
    assert "不要先跑 `options` 或完整 `brief`" in body
    assert "講師解答" in body and "完整 fixtures" in body
    assert "workshop-output/finops-review.md" in body
    assert "學員確認並要求儲存後" in body
    assert "不覆蓋" in body
    for spoiler in ("AI Lab", "Security", "migration", "pull_request", "0.953333"):
        assert spoiler not in content, spoiler


def test_skill_command_catalog_matches_actual_cli_without_running_it() -> None:
    text = (SKILLS / "finops-investigation" / "references" / "commands.md").read_text(
        encoding="utf-8"
    )
    commands = re.findall(r"python -m finops_agent ([^\n`]+)", text)
    assert len(commands) == 8
    expected = {
        "trend",
        "departments",
        "breakdown",
        "roster",
        "workflows",
        "forecast",
        "options",
    }
    observed = set()
    for command in commands:
        args = build_parser().parse_args(shlex.split(command))
        assert args.data_dir == "data"
        assert args.instructor is False
        assert args.command in expected
        observed.add(args.command)
    assert observed == expected


def test_investigation_keeps_quality_and_decision_rules() -> None:
    content = skill_content("finops-investigation")
    for required in (
        "高用量不等於浪費",
        "成功成果",
        "不做個人生產力排名",
        "失敗重試",
        "獨立檢查",
        "quality_gate_failed",
        "not_cheaper",
        "null",
        "不是節省",
        "選兩個",
        "負責人",
        "衡量",
        "未選方案",
        "不自動匯出整包證據",
    ):
        assert required in content, required


def test_dashboard_requires_explicit_invocation_and_a_reviewed_single_file() -> None:
    body = skill_text("finops-dashboard")
    for required in (
        "disable-model-invocation: true",
        "已完成調查與選案",
        "workshop-output/lab1-evidence.json",
        "workshop-output/finops-dashboard.html",
        "不覆蓋",
        "明確要求修正",
        "單一自含 HTML",
        "File API",
        "file://",
        "不要 `fetch`",
        "CDN",
        "server",
        "localStorage",
        "不執行命令",
        "不自動開啟",
        "上傳",
        "textContent",
        "不使用 `innerHTML`",
        "鍵盤",
        "資料表",
        "role=alert",
        "temporary_budget",
        "approval tools",
    ):
        assert required in body, required
    assert "不是新的 Lab" in body
    assert "不需要安裝或 build" in body


def test_dashboard_reuses_theme_without_copying_the_admin_application() -> None:
    body = skill_text("finops-dashboard")
    for required in (
        "../../../starter/src/finops_agent/demo.html",
        "唯讀",
        "--cp-*",
        "var(--cp-*)",
        "light/dark",
        "scoutTheme",
        "prefers-color-scheme",
        "Segoe UI",
        "Consolas",
        "不要複製",
        "admin",
        "輪詢",
    ):
        assert required in body


def test_dashboard_contract_keeps_accounting_and_evidence_checks() -> None:
    text = skill_content("finops-dashboard")
    for required in (
        "schema_version=2",
        "cost_summary",
        "daily_usage.items",
        "net_quantity",
        "net_amount",
        "department_ranking.ranking",
        "model_breakdown.items",
        "budget_review.budgets",
        "seat_inventory.seats",
        "run_rate_scenario",
        "Unallocated",
        "missing_dates",
        "rounding_note",
        "0.01",
        "cents",
        "加總不一致",
        "不補零或插值",
        "不改寫全體總數",
        "不可臆造跨圖篩選",
        "investigation_evidence",
        "--include-investigation",
        "run_count",
        "successful_tasks",
        "cost_per_successful_task_usd",
        "returned_runs",
        "total_runs",
        "summary_scope",
        "truncated",
        "observed_period_opportunity_usd",
        "remaining_month_savings_usd",
        "remaining_month_credit_savings",
        "additional_headroom_usd",
        "estimated_savings_usd",
        "estimated_credit_savings=null",
        "conditional_pilot_estimate",
        "quality_gate_failed",
        "not_cheaper",
    ):
        assert required in text, required


def test_dashboard_validates_each_source_period_instead_of_one_global_timestamp() -> (
    None
):
    text = skill_content("finops-dashboard")
    for required in (
        "daily_comparison.baseline.as_of",
        "daily_comparison.current",
        "2026-08-01",
        "2026-08-22T23:59:59Z",
        "2026-09-01",
        "2026-09-22T23:59:59Z",
        "baseline.period",
        "不要求所有巢狀 as_of",
        "previous_month",
    ):
        assert required in text, required


def test_project_skills_do_not_enable_sdk_skill_discovery() -> None:
    content = skill_text("finops-investigation")
    assert "不是 Python SDK 的 skill" in content
    for project in ("starter", "solution"):
        harness = (ROOT / project / "src" / "finops_agent" / "harness.py").read_text(
            encoding="utf-8"
        )
        assert "enable_skills=False" in harness
        assert "enable_config_discovery=False" in harness
