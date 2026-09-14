import re
from pathlib import Path


def workshop_documents() -> list[Path]:
    root = Path(__file__).parents[2]
    return [
        root / "README.md",
        root / "intro.md",
        *sorted((root / "docs").glob("*.md")),
    ]


def test_workshop_keeps_exactly_three_labs() -> None:
    root = Path(__file__).parents[2]
    text = (root / "docs" / "student-lab.md").read_text(encoding="utf-8")
    assert re.findall(r"^## Lab (\d)[:：]", text, re.MULTILINE) == ["1", "2", "3"]


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
