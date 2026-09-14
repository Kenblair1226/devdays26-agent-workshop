import re
from pathlib import Path


def test_three_labs_fit_the_ninety_minute_session() -> None:
    root = Path(__file__).parents[2]
    text = (root / "docs" / "student-lab.md").read_text(encoding="utf-8")
    assert re.findall(r"^## Lab (\d)[:：]", text, re.MULTILINE) == ["1", "2", "3"]
    slots = [
        (int(start), int(end))
        for start, end in re.findall(r"\|\s*(\d+)[–-](\d+)\s*分\s*\|", text)
    ]
    assert slots[0][0] == 0 and slots[-1][1] == 90
    assert sum(end - start for start, end in slots) == 90
    assert all(left[1] == right[0] for left, right in zip(slots, slots[1:]))


def test_workshop_local_markdown_links_exist() -> None:
    root = Path(__file__).parents[2]
    paths = [
        root / "README.md",
        root / "intro.md",
        *sorted((root / "docs").glob("*.md")),
    ]
    for path in paths:
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


def test_lab2_live_quota_is_optional_and_separate_from_mock_budgets() -> None:
    root = Path(__file__).parents[2]
    text = (root / "docs" / "student-lab.md").read_text(encoding="utf-8")
    lab2 = text.split("## Lab 2", 1)[1].split("## Lab 3", 1)[0]
    for required in (
        "配額查詢選配",
        "python -m finops_agent copilot-usage --live",
        "COPILOT_GITHUB_TOKEN",
        "FINOPS_BACKEND=mock",
        "FINOPS_ALLOW_REAL_WRITES=false",
        "account.getQuota",
        "usedRequests",
        "remainingPercentage",
        "resetDate",
        "as_of",
        "per-key",
        "不呼叫模型",
        "延遲",
        "不要附到 Copilot Chat",
        "另外開一個終端",
    ):
        assert required in lab2
    for name in ("environment-prep.md", "instructor-guide.md", "architecture.md"):
        doc = (root / "docs" / name).read_text(encoding="utf-8")
        assert "copilot-usage --live" in doc, name
        assert "account.getQuota" in doc, name
