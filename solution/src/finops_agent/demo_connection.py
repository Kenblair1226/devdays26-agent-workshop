from .budget_demo import USER_INSTRUCTIONS, BudgetDemo
from .harness import CopilotFinOpsHarness


def build_demo_harness(service: BudgetDemo) -> CopilotFinOpsHarness:
    return CopilotFinOpsHarness(
        service.toolbox,
        custom_tools=service.user_tools(),
        instructions=USER_INSTRUCTIONS,
    )
