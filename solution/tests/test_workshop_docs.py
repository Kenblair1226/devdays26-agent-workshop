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
