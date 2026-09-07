# Checkpoint recovery

Lab 1 tools are complete: learners use them with GitHub Copilot Chat to produce a
FinOps decision brief. No source edits or restore steps are needed for Lab 1.
Only Lab 2's `build_demo_harness()` in `demo_connection.py` is incomplete.
The user tools, role checks, administrator approval, and browser UI are prebuilt.

Starter and solution share the same interfaces. From the repository root, restore
only the lab you need (your edits are backed up in `.workshop-backups/`):

```text
python scripts/checkpoint.py --lab 2
python -m pytest starter/checks -q
```

`--lab all` restores the Lab 2 exercises; `--lab 1` is a compatibility no-op.
This never removes the source directory or overwrites `.env` or the learner's
analysis deliverable. Lab 3 has no code TODO; it is deployment or instructor demo.
