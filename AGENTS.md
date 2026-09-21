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
- Lab 1 uses ready-made tools and GitHub Copilot Chat for analysis; do not re-add
  a mandatory tool-implementation exercise.
- Lab 2 uses one harness factory connection and the local user/admin budget demo.
  Keep its user tools scoped; never expose approval to the model or host the demo
  approval API as a production/Foundry authorization service.
- Lab 2 may optionally switch the same harness to a Foundry model. Lab 3 is the
  optional Hosted Agent deployment. Keep Toolbox and other new services out of
  scope, and preserve the Azure-free Lab 1/2 core path.

## Validation

- Use Python 3.13.
- Run solution tests before changing starter checkpoints.
- Lab 1 and Lab 2 must remain usable without Azure credentials.
