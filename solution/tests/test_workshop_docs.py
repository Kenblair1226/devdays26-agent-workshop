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
