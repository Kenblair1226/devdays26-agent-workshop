import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_recovery_preserves_edits_and_completes_all_three_labs(tmp_path) -> None:
    root = Path(__file__).parents[2]
    for project in ("starter", "solution"):
        for folder in ("src", "data"):
            shutil.copytree(
                root / project / folder,
                tmp_path / project / folder,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
    shutil.copytree(root / "starter" / "checks", tmp_path / "starter" / "checks")
    shutil.copy2(root / "starter" / "main.py", tmp_path / "starter" / "main.py")
    spec = importlib.util.spec_from_file_location(
        "checkpoint", root / "scripts" / "checkpoint.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    learner_file = tmp_path / "starter" / "src" / "finops_agent" / "demo_connection.py"
    original = learner_file.read_text(encoding="utf-8")
    dashboard = tmp_path / "workshop-output" / "finops-dashboard.html"
    dashboard.parent.mkdir()
    dashboard.write_text("learner-generated dashboard", encoding="utf-8")
    assert module.restore_checkpoint(tmp_path, "1") == []
    assert not (tmp_path / ".workshop-backups").exists()
    module.restore_checkpoint(tmp_path, "all")
    backups = list((tmp_path / ".workshop-backups").glob("*/demo_connection.py"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == original
    assert dashboard.read_text(encoding="utf-8") == "learner-generated dashboard"
    env = dict(os.environ, FINOPS_BACKEND="mock", OTEL_SDK_DISABLED="true")
    env.pop("FINOPS_DATA_DIR", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(tmp_path / "starter" / "checks"), "-q"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_deployment_fixtures_equal_the_workshop_data() -> None:
    def load_fixture(path):
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".ndjson":
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        return json.loads(text)

    root = Path(__file__).parents[2]
    fixtures = [
        *(root / "data").glob("*.json"),
        *(root / "data").glob("*.ndjson"),
    ]
    for path in fixtures:
        expected = load_fixture(path)
        for project in ("starter", "solution"):
            actual = load_fixture(root / project / "data" / path.name)
            assert actual == expected, (project, path.name)


def test_shared_starter_code_uses_the_solution_interfaces() -> None:
    root = Path(__file__).parents[2]
    exercise_files = {"demo_connection.py"}
    for source in (root / "solution" / "src" / "finops_agent").glob("*.py"):
        if source.name not in exercise_files:
            starter = root / "starter" / "src" / "finops_agent" / source.name
            assert starter.read_bytes() == source.read_bytes(), source.name
    source_html = root / "solution" / "src" / "finops_agent" / "demo.html"
    starter_html = root / "starter" / "src" / "finops_agent" / "demo.html"
    assert source_html.read_bytes() == starter_html.read_bytes()
