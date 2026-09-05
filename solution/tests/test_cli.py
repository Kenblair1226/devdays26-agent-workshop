import json
import os
import subprocess
import sys
from pathlib import Path


def process_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "SYSTEMDRIVE",
            "COMSPEC",
            "USERPROFILE",
            "HOME",
            "TEMP",
            "TMP",
            "LOCALAPPDATA",
            "APPDATA",
        }
    }


def test_lab1_runs_without_sdk_or_azure_packages() -> None:
    root = Path(__file__).parents[1]
    env = process_environment()
    env["PYTHONPATH"] = str(root / "src")
    env["FINOPS_BACKEND"] = "mock"
    env["FINOPS_DATA_DIR"] = str(root / "data")
    result = subprocess.run(
        [sys.executable, "-S", "-m", "finops_agent", "cost"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["net_quantity"] == 4760


def test_mock_rehearsal_never_uses_real_backend() -> None:
    root = Path(__file__).parents[1]
    env = process_environment()
    env["PYTHONPATH"] = str(root / "src")
    env["FINOPS_BACKEND"] = "github"
    env["FINOPS_ALLOW_REAL_WRITES"] = "true"
    env["FINOPS_DATA_DIR"] = str(root / "data")
    env.pop("GITHUB_ADMIN_TOKEN", None)
    result = subprocess.run(
        [sys.executable, "-m", "finops_agent", "approval-demo", "--rehearse"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    output = json.loads(result.stdout)
    assert output["approval_mode"] == "simulated_mock_only"
    assert output["execution"]["result"]["mock"] is True
    assert "approval_token" not in result.stdout
