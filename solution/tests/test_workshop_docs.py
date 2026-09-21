import ast
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]


def workshop_documents() -> list[Path]:
    return [
        ROOT / "README.md",
        ROOT / "intro.md",
        *sorted((ROOT / "docs").glob("*.md")),
        ROOT / "data" / "README.md",
        ROOT / "starter" / "checkpoints" / "README.md",
        *sorted((ROOT / ".github" / "skills").rglob("*.md")),
    ]


def student_guide() -> str:
    return (ROOT / "docs" / "student-lab.md").read_text(encoding="utf-8")


def markdown_table_rows(text: str) -> dict[str, list[str]]:
    rows = {}
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            rows[cells[0]] = cells[1:]
    return rows


def test_workshop_keeps_exactly_three_labs_and_checkpoints() -> None:
    text = student_guide()
    assert re.findall(r"^## Lab (\d)[:：]", text, re.MULTILINE) == ["1", "2", "3"]
    assert re.findall(r"\*\*Checkpoint (\d)[:：]", text) == ["1", "2", "3"]


def test_student_guide_uses_short_skill_requests_instead_of_full_prompts() -> None:
    text = student_guide()
    lab1 = text.split("## Lab 1", 1)[1].split("## Lab 2", 1)[0]
    assert len(text.splitlines()) <= 270
    assert len(lab1) < 3000
    prompts = re.findall(r"```text\n(.*?)```", lab1, re.DOTALL)
    assert len(prompts) == 2
    assert all(len(prompt.strip()) <= 160 for prompt in prompts)
    assert "/finops-investigation" in prompts[0]
    assert "/finops-dashboard" in prompts[1]
    assert "本月 AI credits 成長異常" in prompts[0]
    for technical_detail in (
        "schema_version",
        "input_revision",
        "result_digest",
        "observed_period_opportunity_usd",
        "remaining_month_credit_savings",
        "0.953333",
    ):
        assert technical_detail not in lab1
    assert "選兩個" in lab1 and "理由" in lab1
    assert "工作量" in lab1 and "成功成果" in lab1
    assert "安裝、改原始碼或連外" in lab1


def test_optional_dashboard_stays_after_investigation_and_group_choice() -> None:
    text = student_guide()
    markers = (
        "/finops-investigation",
        "workshop-output/finops-review.md",
        "**Checkpoint 1",
        "### 選做",
        "brief --include-investigation",
        "/finops-dashboard",
        "## Lab 2",
    )
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions)
    assert "跳過也能進 Lab 2" in text
    assert "檔案已存在就換新名字" in text
    assert "用頁面的選檔鈕載入 JSON" in text
    assert "不覆蓋原檔" in text


def test_skill_discovery_has_a_simple_manual_fallback() -> None:
    text = student_guide()
    for required in (
        "repo 根目錄",
        ".github/skills/",
        "/skills",
        "調查 SKILL.md",
        "請照這份 skill 調查",
        "GitHub Copilot Chat",
        "Agent",
    ):
        assert required in text
    for name in ("finops-investigation", "finops-dashboard"):
        assert f"../.github/skills/{name}/SKILL.md" in text


def test_current_data_is_explained_without_dataset_revision_history() -> None:
    for path in workshop_documents():
        text = path.read_text(encoding="utf-8")
        for pattern in (
            r"2026-09-03",
            r"(?<!\d)9/3(?!\d)",
            r"22\s*/\s*3",
            r"原始三天|三天基準|三天模式|三天平均|7 個週期",
            r"(?i)three-day|September 1[–-]3",
            r"(?<!\d)(?:4,?760|44\.88)(?!\d)",
        ):
            assert not re.search(pattern, text), (path.name, pattern)
    text = student_guide().replace(",", "")
    assert "2026/9/1–9/22" in text
    assert "模擬資料" in text
    assert "34906.67" in text and "329.12" in text
    assert "AI credits" in text and "tokens" in text


def test_lab1_has_no_new_tool_implementation_requirement() -> None:
    for path in workshop_documents():
        text = path.read_text(encoding="utf-8").casefold()
        for emphasis in ("免寫程式", "no coding", "no-coding", "先不寫程式"):
            assert emphasis not in text, (path.name, emphasis)
    for name in ("analytics.py", "investigation.py"):
        text = (ROOT / "starter" / "src" / "finops_agent" / name).read_text("utf-8")
        assert "TODO(Lab 1)" not in text


def test_first_time_setup_creates_environment_before_activation() -> None:
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
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        for language, commands in sequences.items():
            block = re.search(rf"```{language}\n(.*?)```", text, re.DOTALL)
            assert block is not None, (name, language)
            positions = [block[1].index(command) for command in commands]
            assert positions == sorted(positions), (name, language)


def test_lab2_example_matches_the_scoped_solution_factory() -> None:
    text = student_guide()
    lab2 = text.split("## Lab 2", 1)[1].split("## Lab 3", 1)[0]
    example = re.search(r"```python\n(.*?)```", lab2, re.DOTALL)
    assert example is not None
    solution = (
        ROOT / "solution" / "src" / "finops_agent" / "demo_connection.py"
    ).read_text(encoding="utf-8")
    assert ast.dump(ast.parse(example[1])) == ast.dump(ast.parse(solution))
    for required in (
        "demo_connection.py",
        "python -m finops_agent demo",
        "pending",
        "approved",
        "220",
        "102.67",
        "117.33",
        "管理者",
        "模型不能代替人核准",
    ):
        assert required in lab2


def test_lab3_preserves_model_switch_and_links_optional_hosting() -> None:
    lab3 = student_guide().split("## Lab 3", 1)[1].split("## 卡住時", 1)[0]
    for required in (
        "Foundry Model",
        "foundry-identity",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "MODEL_NAME",
        "python -m finops_agent demo",
        "FINOPS_BACKEND",
        "FINOPS_ALLOW_REAL_WRITES",
        "不加入 Toolbox 或其他服務",
        "重啟",
        "hosted-deployment.md",
        "觀摩",
    ):
        assert required in lab3
    assert "azd deploy" not in student_guide()


def test_hosted_reference_retains_safe_deployment_and_failure_handling() -> None:
    text = (ROOT / "docs" / "hosted-deployment.md").read_text(encoding="utf-8")
    for required in (
        "主辦方已配好",
        "starter/.azure/",
        "InvocationAgentServerHost",
        "ResponsesAgentServerHost",
        "host: azure.ai.agent",
        "runtime: python_3_13",
        "AZURE_DEV_USER_AGENT",
        "microsoft_foundry_skill",
        "finally",
        "$LASTEXITCODE",
        "azd deploy finops-agent --no-prompt",
        "--protocol invocations",
        "--protocol responses",
        "Playground",
        "response.failed",
        "不載入過去 conversation",
        "request.example.json",
        "backend=mock",
        "每次 invocation",
        "不要對共用 resource group",
    ):
        assert required in text


def test_detailed_references_keep_current_financial_and_case_evidence() -> None:
    data_notes = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    rows = markdown_table_rows(data_notes.replace(",", ""))
    for label, amounts in {
        "全體": ["34906.67", "329.12"],
        "AI Lab": ["17600.00", "190.67"],
        "Platform Engineering": ["5866.67", "50.75"],
        "Security": ["5646.67", "52.95"],
        "Mobile": ["5133.33", "30.80"],
        "Unallocated": ["660.00", "3.96"],
    }.items():
        assert rows[label] == amounts
    for required in (
        "usage-comparison.json",
        "team-roster.json",
        "workflow-runs.json",
        "model-pilots.json",
        "2026-08-01",
        "2026-08-22T23:59:59Z",
        "2026-09-22T23:59:59Z",
        "previous_month",
        "62.18%",
        "0.953333",
        "0.882444",
        "1.764889",
        "rounding_note",
        "quality_gate_failed",
        "not_cheaper",
        "9.63",
        "5.65",
        "15.28",
        "164.27",
    ):
        assert required in data_notes, required


def test_generator_check_is_not_a_learner_prerequisite() -> None:
    notes = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    assert "維護者" in notes
    assert re.search(r"generate_workshop_data\.py\s+--check", notes)
    assert "generate_workshop_data.py" not in student_guide()


def test_workshop_uses_progress_instead_of_fixed_teaching_times() -> None:
    patterns = (
        r"\|\s*\d+\s*[–-]\s*\d+\s*(?:分(?:鐘)?)?\s*\|",
        r"第\s*\d+(?:[–-]\d+)?\s*分",
        r"^#{1,6} .*(?:\d+|[一二三四五六七八九十百]+)\s*分鐘",
        r"T[−-]\d+\s*天",
        r"\d+\s*分鐘內",
        r"\b\d+[- ]minute\b",
    )
    for path in workshop_documents():
        for pattern in patterns:
            assert not re.search(
                pattern, path.read_text(encoding="utf-8"), re.MULTILINE
            ), (path.name, pattern)


def test_all_document_and_skill_links_resolve_locally() -> None:
    for path in workshop_documents():
        for target in re.findall(
            r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")
        ):
            if target.startswith(("https://", "http://", "#")):
                continue
            destination = path.parent / target.split("#", 1)[0]
            assert destination.exists(), f"{path.name} -> {target}"


def test_retired_live_quota_command_is_not_advertised() -> None:
    paths = [
        *workshop_documents(),
        ROOT / "starter" / ".env.example",
        ROOT / "solution" / ".env.example",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for retired in (
            "copilot-usage --live",
            "`copilot-usage`",
            "copilot_usage.py",
            "account.getQuota",
        ):
            assert retired not in text, (path.name, retired)
