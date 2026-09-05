# Repository guidance

This project was built with the microsoft-foundry skill. Before working on or
answering questions about Foundry agents, read the microsoft-foundry skill first.

## Safety

- Keep `FINOPS_BACKEND=mock` as the default.
- Never commit GitHub tokens, Foundry keys, organization data, or generated audit
  logs.
- Real seat and budget writes are instructor-only and require both explicit human
  approval and `FINOPS_ALLOW_REAL_WRITES=true`.
- Preserve the three-lab flow: local tools, local Copilot SDK harness, then optional
  Foundry deployment.

## Validation

- Use Python 3.13.
- Run solution tests before changing starter checkpoints.
- Lab 1 and Lab 2 must remain usable without Azure credentials.
