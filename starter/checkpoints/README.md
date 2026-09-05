# Checkpoint recovery

The starter intentionally leaves the Lab 1 department aggregation and the Lab 2
Copilot SDK tool surface incomplete.

Starter and solution share the same interfaces. From the repository root, restore
only the lab you need (your edits are backed up in `.workshop-backups/`):

```text
python scripts/checkpoint.py --lab 1
python scripts/checkpoint.py --lab 2
python -m pytest starter/checks -q
```

Use `--lab all` for both. This never removes the source directory or overwrites
`.env`. Lab 3 has no code TODO; it is deployment or an instructor demonstration.
