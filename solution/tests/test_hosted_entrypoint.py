import importlib.util
from pathlib import Path

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def hosted(monkeypatch):
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    main_path = Path(__file__).parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("hosted_main", main_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("body", [None, [], {}, {"input": ""}, {"input": 4}])
def test_hosted_invalid_input_is_400(hosted, body) -> None:
    with TestClient(hosted.app) as client:
        assert client.post("/invocations", json=body).status_code == 400


def test_hosted_success_isolated_per_request(hosted, monkeypatch) -> None:
    toolboxes = []

    class Harness:
        tool_calls = ["get_cost_summary"]

        def __init__(self, toolbox):
            toolboxes.append(toolbox)

        async def ask(self, prompt):
            return "AI Lab: 2400 AI credits"

    monkeypatch.setattr(hosted, "CopilotFinOpsHarness", Harness)
    monkeypatch.setenv("FINOPS_BACKEND", "github")
    with TestClient(hosted.app) as client:
        for _ in range(2):
            response = client.post("/invocations", json={"input": "cost"})
            assert response.status_code == 200
            assert response.json()["backend"] == "mock"
            assert response.json()["tool_calls"] == ["get_cost_summary"]
    assert toolboxes[0] is not toolboxes[1]
    assert toolboxes[0].client is not toolboxes[1].client


@pytest.mark.parametrize(
    "exception,status",
    [
        (RuntimeError("private provider message"), 503),
        (TimeoutError("timeout"), 504),
    ],
)
def test_hosted_failure_is_never_completed(hosted, monkeypatch, exception, status):
    class Harness:
        def __init__(self, _toolbox):
            pass

        async def ask(self, _prompt):
            raise exception

    monkeypatch.setattr(hosted, "CopilotFinOpsHarness", Harness)
    with TestClient(hosted.app) as client:
        response = client.post("/invocations", json={"input": "hello"})
    assert response.status_code == status
    assert "error" in response.json()
    assert "reply" not in response.json()
    assert "private provider message" not in response.text
