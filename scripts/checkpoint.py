"""Restore selected lab answers while keeping a backup of the learner's edits."""

import argparse
import shutil
from datetime import UTC, datetime
from pathlib import Path

CHECKPOINTS = {
    "1": (),
    "2": ("demo_connection.py",),
}


def restore_checkpoint(root: Path, lab: str) -> list[Path]:
    names = CHECKPOINTS["1"] + CHECKPOINTS["2"] if lab == "all" else CHECKPOINTS[lab]
    if not names:
        print("Lab 1 uses ready-made tools; no source files need restoring.")
        return []
    source = root / "solution" / "src" / "finops_agent"
    destination = root / "starter" / "src" / "finops_agent"
    for name in names:
        if not (source / name).is_file() or not (destination / name).is_file():
            raise FileNotFoundError(f"Missing checkpoint file: {name}")
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup = root / ".workshop-backups" / timestamp
    backup.mkdir(parents=True, exist_ok=False)
    restored = []
    for name in names:
        shutil.copy2(destination / name, backup / name)
        shutil.copy2(source / name, destination / name)
        restored.append(destination / name)
    print(f"Learner edits backed up to {backup}")
    return restored


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", choices=["1", "2", "all"], required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for path in restore_checkpoint(root, args.lab):
        print(f"Restored {path.relative_to(root)}")


if __name__ == "__main__":
    main()
