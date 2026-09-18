import re
from pathlib import Path


def workshop_documents() -> list[Path]:
    root = Path(__file__).parents[2]
    return [
        root / "README.md",
        root / "intro.md",
        *sorted((root / "docs").glob("*.md")),
        root / "data" / "README.md",
        root / "starter" / "checkpoints" / "README.md",
    ]


def lab1_dashboard_instructions() -> str:
    root = Path(__file__).parents[2]
    text = (root / "docs" / "student-lab.md").read_text(encoding="utf-8")
    return text.split("### 選做（optional）", 1)[1].split("**接著進 Lab 2", 1)[0]


def test_workshop_keeps_exactly_three_labs() -> None:
    root = Path(__file__).parents[2]
    text = (root / "docs" / "student-lab.md").read_text(encoding="utf-8")
    assert re.findall(r"^## Lab (\d)[:：]", text, re.MULTILINE) == ["1", "2", "3"]
    assert re.findall(r"\*\*Checkpoint (\d)[:：]", text) == ["1", "2", "3"]


def test_lab1_leads_with_investigation_without_no_coding_emphasis() -> None:
    for path in workshop_documents():
        text = path.read_text(encoding="utf-8").casefold()
        for emphasis in (
            "免寫程式",
            "no coding",
            "no-coding",
            "先不寫程式",
            "不需要改程式",
            "不用改 `analytics.py`",
        ):
            assert emphasis not in text, (path.name, emphasis)


def test_optional_dashboard_follows_the_decision_brief_not_a_new_checkpoint() -> None:
    root = Path(__file__).parents[2]
    text = (root / "docs" / "student-lab.md").read_text(encoding="utf-8")
    positions = [
        text.index(marker)
        for marker in (
            "**Checkpoint 1",
            "### 選做（optional）",
            "**接著進 Lab 2",
            "## Lab 2：",
        )
    ]
    assert positions == sorted(positions)
    assert "finops-review.md" in text[: positions[1]]
    dashboard = lab1_dashboard_instructions()
    assert "Checkpoint 1 仍然是一頁決策摘要" in dashboard
    assert "不是第四個 Lab" in dashboard
    assert "繳交要求" in dashboard


def test_dashboard_prompt_uses_reviewed_single_file_creation_and_local_loading() -> (
    None
):
    dashboard = lab1_dashboard_instructions()
    for required in (
        "Ask",
        "Agent",
        "workshop-output/lab1-evidence.json",
        "lab1-evidence-v2.json",
        "workshop-output/finops-dashboard.html",
        "starter/src/finops_agent/demo.html",
        "唯讀",
        "File API",
        "file://",
        "textContent",
        "不使用 innerHTML",
        "--cp-*",
        "scoutTheme",
        "Segoe UI",
    ):
        assert required in dashboard, required
    assert re.search(r"不要.*repo source.*\.env", dashboard)
    assert re.search(r"不要 npm.*CDN.*fetch.*server", dashboard)
    assert re.search(r"不要.*自動開啟或上傳", dashboard)


def test_dashboard_prompt_preserves_evidence_dimensions_and_failure_states() -> None:
    dashboard = lab1_dashboard_instructions()
    for required in (
        "schema_version=2",
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
        "空白狀態",
        "斷線",
        "鍵盤",
        "資料表",
        "role=alert",
        "加總不一致",
    ):
        assert required in dashboard, required
    assert "排序或單位切換不能改全體 KPI" in dashboard
    assert "不相加、不互換" in dashboard
    assert "不能自動判成可回收" in dashboard


def test_workshop_documents_use_the_fixed_resimulated_september_snapshot() -> None:
    root = Path(__file__).parents[2]
    for path in (
        root / "README.md",
        root / "docs" / "student-lab.md",
        root / "docs" / "environment-prep.md",
        root / "data" / "README.md",
    ):
        text = path.read_text(encoding="utf-8")
        for required in (
            "2026-09-22T23:59:59Z",
            "2026-09-01",
            "2026-09-22",
            "schema_version=2",
            "daily_usage",
            "預先模擬",
        ):
            assert required in text, (path.name, required)
    for path in workshop_documents():
        text = path.read_text(encoding="utf-8")
        for stale in ("2026-09-03", "2026-08-07", "448.80"):
            assert stale not in text, (path.name, stale)
    data_notes = (root / "data" / "README.md").read_text(encoding="utf-8")
    for required in (
        "2026-08-26",
        "2026-08-31",
        "sparse_training_samples",
        "daily_samples",
        "61.20",
        "projected_over_budget=false",
        "45.20",
        "34.80",
    ):
        assert required in data_notes, required


def test_optional_dashboard_is_visible_in_overviews_preparation_and_recovery() -> None:
    root = Path(__file__).parents[2]
    for path in (
        root / "README.md",
        root / "intro.md",
        root / "docs" / "environment-prep.md",
        root / "docs" / "instructor-guide.md",
        root / "starter" / "checkpoints" / "README.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "選做" in text, path.name
        assert "dashboard" in text, path.name
        assert "workshop-output/" in text, path.name


def test_fixture_generator_check_stays_in_maintainer_documentation() -> None:
    root = Path(__file__).parents[2]
    data_notes = (root / "data" / "README.md").read_text(encoding="utf-8")
    assert "維護者" in data_notes
    assert re.search(r"generate_workshop_data\.py\s+--check", data_notes)
    for name in ("student-lab.md", "environment-prep.md"):
        text = (root / "docs" / name).read_text(encoding="utf-8")
        assert "generate_workshop_data.py" not in text, name


def test_workshop_uses_progression_instead_of_fixed_teaching_times() -> None:
    schedule_patterns = (
        r"\|\s*\d+\s*[–-]\s*\d+\s*(?:分(?:鐘)?)?\s*\|",
        r"第\s*\d+(?:[–-]\d+)?\s*分",
        r"^#{1,6} .*(?:\d+|[一二三四五六七八九十百]+)\s*分鐘",
        r"T[−-]\d+\s*天",
        r"\d+\s*分鐘內",
        r"\b\d+[- ]minute\b",
        r"部署(?:等候|等待)?超過\s*\d+\s*分鐘",
    )
    for path in workshop_documents():
        text = path.read_text(encoding="utf-8")
        for pattern in schedule_patterns:
            assert not re.search(pattern, text, re.MULTILINE), (path.name, pattern)
    root = Path(__file__).parents[2] / "docs"
    for name in ("student-lab.md", "instructor-guide.md"):
        assert "| 階段 |" in (root / name).read_text(encoding="utf-8"), name
    assert "| 準備階段 |" in (root / "environment-prep.md").read_text(encoding="utf-8")


def test_workshop_local_markdown_links_exist() -> None:
    for path in workshop_documents():
        for target in re.findall(
            r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")
        ):
            if target.startswith(("https://", "http://", "#")):
                continue
            target_path = path.parent / target.split("#", 1)[0]
            assert target_path.exists(), f"{path.name} -> {target}"


def test_first_time_setup_creates_environment_before_activation() -> None:
    root = Path(__file__).parents[2]
    sequences = {
        "powershell": (
            "python --version",
            r"python -m venv .\starter\.venv",
            r"& .\starter\.venv\Scripts\Activate.ps1",
            r"python -m pip install -r .\starter\requirements.txt",
            r"python -m finops_agent --data-dir .\data cost",
        ),
        "bash": (
            "python3.13 --version",
            "python3.13 -m venv starter/.venv",
            "source starter/.venv/bin/activate",
            "python -m pip install -r starter/requirements.txt",
            "python -m finops_agent --data-dir data cost",
        ),
    }
    for name in ("student-lab.md", "environment-prep.md"):
        text = (root / "docs" / name).read_text(encoding="utf-8")
        for language, commands in sequences.items():
            block = re.search(rf"```{language}\n(.*?)```", text, re.DOTALL)
            assert block is not None, (name, language)
            positions = [block[1].index(command) for command in commands]
            assert positions == sorted(positions), (name, language)


def test_lab1_is_an_analysis_deliverable_not_a_coding_checkpoint() -> None:
    root = Path(__file__).parents[2]
    text = (root / "docs" / "student-lab.md").read_text(encoding="utf-8")
    lab1 = text.split("## Lab 1", 1)[1].split("## Lab 2", 1)[0]
    for required in (
        "Copilot Chat",
        "lab1-evidence.json",
        "finops-review.md",
        "決策摘要",
        "what-if",
        "budget_review",
        "seat",
    ):
        assert required in lab1
    assert "TODO(Lab 1)" not in lab1
    source = root / "starter" / "src" / "finops_agent" / "analytics.py"
    assert "TODO(Lab 1)" not in source.read_text(encoding="utf-8")


def test_lab2_is_one_connection_and_a_visible_approval_flow() -> None:
    root = Path(__file__).parents[2]
    text = (root / "docs" / "student-lab.md").read_text(encoding="utf-8")
    lab2 = text.split("## Lab 2", 1)[1].split("## Lab 3", 1)[0]
    for required in (
        "demo_connection.py",
        "python -m finops_agent demo",
        "pending",
        "approved",
        "30",
        "16",
        "管理者",
    ):
        assert required in lab2
    assert "編輯 `starter/src/finops_agent/sdk_tools.py`" not in lab2


def test_lab3_includes_model_switch_without_requiring_new_tool_services() -> None:
    root = Path(__file__).parents[2]
    text = (root / "docs" / "student-lab.md").read_text(encoding="utf-8")
    lab3 = text.split("## Lab 3", 1)[1].split("## 跟不上", 1)[0]
    for required in (
        "Foundry Model",
        "foundry-identity",
        "AZURE_OPENAI_ENDPOINT",
        "MODEL_NAME",
        "python -m finops_agent demo",
        "FINOPS_BACKEND",
        "FINOPS_ALLOW_REAL_WRITES",
        "pending",
        "Copilot",
        "重啟",
        "選配",
    ):
        assert required in lab3
    assert "先不加入 Toolbox 或其他服務" in lab3
    assert "azd ai toolbox" not in lab3


def test_workshop_no_longer_advertises_the_retired_quota_command() -> None:
    root = Path(__file__).parents[2]
    paths = [
        *workshop_documents(),
        root / "starter" / ".env.example",
        root / "solution" / ".env.example",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for retired in (
            "copilot-usage --live",
            "`copilot-usage`",
            "copilot_usage.py",
            "account.getQuota",
            "quota_snapshots",
            "Copilot account quota",
        ):
            assert retired not in text, (path.name, retired)
