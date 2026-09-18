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


def markdown_table_rows(text: str) -> dict[str, list[str]]:
    rows = {}
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            rows[cells[0]] = cells[1:]
    return rows


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
        "lab1-evidence-v3.json",
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


def test_workshop_documents_extrapolate_the_original_three_day_baseline() -> None:
    root = Path(__file__).parents[2]
    for path in (
        root / "README.md",
        root / "docs" / "student-lab.md",
        root / "docs" / "environment-prep.md",
        root / "data" / "README.md",
    ):
        text = path.read_text(encoding="utf-8").replace(",", "")
        for required in (
            "2026-09-22T23:59:59Z",
            "2026-09-01",
            "2026-09-03",
            "2026-09-22",
            "schema_version=2",
            "daily_usage",
            "22 / 3",
            "34906.67",
            "329.12",
            "線性外推",
            "預先模擬",
            "user/model",
        ):
            assert required in text, (path.name, required)
        assert re.search(r"不是.*實測", text), path.name
        assert "沒有平日／週末季節性模型" in text, path.name


def test_original_totals_are_labelled_as_baseline_not_current_mtd() -> None:
    for path in workshop_documents():
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if re.search(r"(?<!\d)(?:4,?760|44\.88)(?!\d)", line):
                assert "22 / 3" in line, (path.name, line)
                assert re.search(r"2026-09-01～2026-09-03|September 1–3", line), (
                    path.name,
                    line,
                )
        for stale in (
            "2026-08-07",
            "61.20",
            "35.12",
            "保留既有 MTD 總數",
            "總量維持",
        ):
            assert stale not in text, (path.name, stale)


def test_data_notes_document_scaled_department_and_model_totals() -> None:
    root = Path(__file__).parents[2]
    text = (root / "data" / "README.md").read_text(encoding="utf-8")
    rows = markdown_table_rows(text.replace(",", ""))
    expected = {
        "全體": ["34906.67", "329.12"],
        "AI Lab": ["17600.00", "190.67"],
        "Platform Engineering": ["5866.67", "50.75"],
        "Security": ["5646.67", "52.95"],
        "Mobile": ["5133.33", "30.80"],
        "Unallocated": ["660.00", "3.96"],
        "`gpt-5.4`": ["18920.00", "189.20"],
        "`gpt-5-mini`": ["8653.33", "51.92"],
        "`claude-opus-5`": ["7333.33", "88.00"],
    }
    for label, values in expected.items():
        assert rows[label] == values, label


def test_data_notes_separate_billing_budgets_and_observation_windows() -> None:
    root = Path(__file__).parents[2]
    data_notes = (root / "data" / "README.md").read_text(encoding="utf-8")
    for required in (
        "2026-08-26",
        "2026-08-31",
        "sparse_training_samples",
        "daily_samples",
        "7 個週期",
        "三天平均",
        "13,066.67",
        "active_days",
        "forecast 600",
        "329.12 ÷ 22",
        "448.80",
        "projected_over_budget=false",
        "600 − 329.12 = 270.88",
        "限額 600／已用 331.47／剩餘 268.53",
        "限額 150／已用 102.67／剩餘 47.33",
        "限額 220／已用 102.67 不變／剩餘 117.33",
        "USD 19.07",
        "下個月回收 1 seat",
    ):
        assert required in data_notes, required


def test_rounding_notes_do_not_replace_totals_with_rounded_subtotal_sums() -> None:
    root = Path(__file__).parents[2]
    for path in (
        root / "data" / "README.md",
        root / "docs" / "student-lab.md",
        root / "docs" / "instructor-guide.md",
    ):
        text = path.read_text(encoding="utf-8").replace(",", "")
        for required in (
            "rounding_note",
            "四捨五入",
            "0.01",
            "34906.66",
            "34906.67",
            "329.13",
            "329.12",
        ):
            assert required in text, (path.name, required)
    dashboard = lab1_dashboard_instructions()
    for required in ("百分之一 credit", "cents", "容差", "每日顯示值恰好對回全體"):
        assert required in dashboard, required


def test_workshop_requires_fresh_evidence_despite_unchanged_schema_and_date() -> None:
    for path in workshop_documents():
        text = path.read_text(encoding="utf-8")
        for required in ("lab1-evidence-v3.json", "舊檔", "新檔", "9/22"):
            assert required in text, (path.name, required)
        assert re.search(r"schema(?:_version=|\s*)2", text), path.name
        assert re.search(r"重新(?:產生|執行)|另產生新檔", text), path.name


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
        "150",
        "220",
        "102.67",
        "47.33",
        "117.33",
        "管理者",
    ):
        assert required in lab2
    assert "編輯 `starter/src/finops_agent/sdk_tools.py`" not in lab2
    rows = markdown_table_rows(lab2)
    assert rows["開始"] == ["150", "102.67", "47.33", "尚未申請"]
    assert rows["使用者申請"] == ["150", "102.67", "47.33", "pending"]
    assert rows["管理者核准"] == ["220", "102.67", "117.33", "approved"]


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
        "150",
        "220",
        "102.67",
        "47.33",
        "117.33",
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
