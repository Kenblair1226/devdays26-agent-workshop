import asyncio
import importlib.util
import json
import re
import tomllib
from pathlib import Path

import pytest
from starlette.testclient import TestClient


@pytest.fixture(params=["solution", "starter"])
def hosted(monkeypatch, tmp_path, request):
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("AGENTSERVER_STATE_ROOT", str(tmp_path / "agentserver"))
    main_path = Path(__file__).parents[2] / request.param / "main.py"
    spec = importlib.util.spec_from_file_location("hosted_main", main_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "body",
    [None, [], {}, {"input": ""}, {"input": "  "}, {"input": 4}, {"input": "x" * 8001}],
)
def test_hosted_invalid_input_is_400(hosted, body) -> None:
    with TestClient(hosted.app) as client:
        assert client.post("/invocations", json=body).status_code == 400


@pytest.mark.parametrize("body", [b"not json", b"\xff"])
def test_hosted_malformed_body_is_400(hosted, body):
    with TestClient(hosted.app) as client:
        response = client.post("/invocations", content=body)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"
    assert "JSON" in response.json()["message"]


def test_hosted_success_isolated_per_request(hosted, monkeypatch) -> None:
    toolboxes = []

    class Harness:
        tool_calls = ["get_cost_summary"]

        def __init__(self, toolbox):
            toolboxes.append(toolbox)

        async def ask(self, prompt):
            return "AI Lab: 17600 AI credits"

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


@pytest.fixture
def harness_calls(hosted, monkeypatch):
    calls = []

    class Harness:
        tool_calls = ["get_cost_summary"]

        def __init__(self, toolbox):
            self.toolbox = toolbox

        async def ask(self, prompt):
            calls.append((prompt, self.toolbox))
            return "AI Lab: 17600 AI credits"

    monkeypatch.setattr(hosted, "CopilotFinOpsHarness", Harness)
    return calls


def sse_events(response):
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize(
    "input_value,prompt",
    [
        ("cost", "cost"),
        ("x" * 8000, "x" * 8000),
        ([{"role": "user", "content": "cost"}], "cost"),
        (
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "cost"},
                        {"type": "input_text", "text": "and limits"},
                    ],
                }
            ],
            "cost\nand limits",
        ),
    ],
)
def test_responses_success(hosted, harness_calls, input_value, prompt, stream):
    with TestClient(hosted.app) as client:
        response = client.post(
            "/responses",
            json={"input": input_value, "stream": stream, "store": False},
        )
    assert response.status_code == 200, response.text
    if stream:
        assert response.headers["content-type"].startswith("text/event-stream")
        events = sse_events(response)
        assert events[0]["type"] == "response.created"
        assert events[-1]["type"] == "response.completed"
        assert "response.failed" not in [event["type"] for event in events]
        body = events[-1]["response"]
    else:
        body = response.json()
    assert body["object"] == "response"
    assert body["status"] == "completed"
    assert body["output"][0]["role"] == "assistant"
    assert body["output"][0]["content"][0]["text"] == "AI Lab: 17600 AI credits"
    assert harness_calls[0][0] == prompt


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("prompt", ["", "  ", "x" * 8001])
def test_responses_invalid_input_never_calls_model(
    hosted, harness_calls, prompt, stream
):
    with TestClient(hosted.app) as client:
        response = client.post(
            "/responses", json={"input": prompt, "stream": stream, "store": False}
        )
    if stream:
        events = sse_events(response)
        assert events[-1]["type"] == "response.failed"
        assert "response.completed" not in [event["type"] for event in events]
        body = events[-1]["response"]
    else:
        body = response.json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "invalid_request"
    assert not harness_calls


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize(
    "exception,code",
    [
        (RuntimeError("private provider message"), "agent_unavailable"),
        (TimeoutError("private provider message"), "agent_timeout"),
    ],
)
def test_responses_failure_is_never_completed(
    hosted, monkeypatch, exception, code, stream
):
    class Harness:
        def __init__(self, _toolbox):
            pass

        async def ask(self, _prompt):
            raise exception

    monkeypatch.setattr(hosted, "CopilotFinOpsHarness", Harness)
    with TestClient(hosted.app) as client:
        response = client.post(
            "/responses", json={"input": "cost", "stream": stream, "store": False}
        )
    if stream:
        events = sse_events(response)
        assert events[-1]["type"] == "response.failed"
        assert "response.completed" not in [event["type"] for event in events]
        body = events[-1]["response"]
    else:
        body = response.json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == code
    assert not body["output"]
    assert "private provider message" not in response.text


def test_protocols_share_host_but_not_mock_state(hosted, harness_calls, monkeypatch):
    monkeypatch.setenv("FINOPS_BACKEND", "github")
    with TestClient(hosted.app) as client:
        assert client.get("/readiness").status_code == 200
        for route in ("/invocations", "/responses", "/invocations", "/responses"):
            response = client.post(route, json={"input": "cost", "store": False})
            assert response.status_code == 200
        assert response.json()["status"] == "completed"
    assert len({id(toolbox.client) for _, toolbox in harness_calls}) == 4
    assert all(
        isinstance(toolbox.client, hosted.MockGitHubFinOpsClient)
        for _, toolbox in harness_calls
    )


def test_invocations_preserves_contract_at_character_limit(hosted, harness_calls):
    with TestClient(hosted.app) as client:
        response = client.post("/invocations", json={"input": "x" * 8000})
    assert response.status_code == 200
    assert set(response.json()) == {"reply", "invocation_id", "tool_calls", "backend"}
    assert response.json()["invocation_id"]
    assert harness_calls[0][0] == "x" * 8000


@pytest.mark.parametrize("route", ["/invocations", "/responses"])
def test_utf8_example_request_works_on_both_protocols(hosted, harness_calls, route):
    example = Path(hosted.__file__).with_name("request.example.json").read_bytes()
    with TestClient(hosted.app) as client:
        response = client.post(
            route, content=example, headers={"content-type": "application/json"}
        )
    assert response.status_code == 200
    assert harness_calls[0][0] == json.loads(example)["input"]


def test_responses_rejects_mixed_nontext_input(hosted, harness_calls):
    with TestClient(hosted.app) as client:
        response = client.post(
            "/responses",
            json={
                "store": False,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "analyze this"},
                            {
                                "type": "input_image",
                                "image_url": "https://example.test/image.png",
                            },
                        ],
                    }
                ],
            },
        )
    assert response.json()["status"] == "failed"
    assert response.json()["error"]["code"] == "invalid_request"
    assert "Only text" in response.json()["error"]["message"]
    assert not harness_calls


def test_responses_history_does_not_reuse_harness_state(hosted, harness_calls):
    with TestClient(hosted.app) as client:
        first = client.post("/responses", json={"input": "first question"})
        assert first.json()["status"] == "completed"
        second = client.post(
            "/responses",
            json={
                "input": "second question",
                "previous_response_id": first.json()["id"],
            },
        )
    assert second.json()["status"] == "completed"
    assert [prompt for prompt, _ in harness_calls] == [
        "first question",
        "second question",
    ]
    assert harness_calls[0][1].client is not harness_calls[1][1].client


def test_responses_cancellation_cleans_up_harness(hosted, monkeypatch):
    async def run():
        started = asyncio.Event()
        cleaned_up = asyncio.Event()
        cancelled = asyncio.Event()

        class Harness:
            def __init__(self, _toolbox):
                pass

            async def ask(self, _prompt):
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cleaned_up.set()

        monkeypatch.setattr(hosted, "CopilotFinOpsHarness", Harness)
        task = asyncio.create_task(
            hosted._ask_response("cost", "test-response", cancelled)
        )
        await asyncio.wait_for(started.wait(), timeout=2)
        cancelled.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=2)
        assert cleaned_up.is_set()

    asyncio.run(run())


@pytest.mark.parametrize("project", ["solution", "starter"])
def test_hosted_manifest_uses_astra_and_explicit_deployment_binding(project):
    root = Path(__file__).parents[2]
    config = (root / project / "azure.yaml").read_text()
    model = re.search(
        r'- name: (\S+)\s+model:\s+format: OpenAI\s+name: (\S+)\s+version: "([^"]+)"',
        config,
    )
    assert model is not None
    assert model.groups() == ("gpt-6-astra", "gpt-6-astra", "2026-09-03")
    assert "MODEL_NAME: ${AZURE_AI_MODEL_DEPLOYMENT_NAME}" in config
    assert "FINOPS_MODEL_PROVIDER: foundry-identity" in config
    assert "FINOPS_BACKEND: mock" in config
    assert "FINOPS_OTEL_EXPORTER: azure-monitor" in config


def test_hosted_entrypoints_and_protocol_dependencies_stay_in_sync():
    root = Path(__file__).parents[2]
    assert (root / "starter/main.py").read_bytes() == (
        root / "solution/main.py"
    ).read_bytes()
    for project in ("starter", "solution"):
        folder = root / project
        config = (folder / "azure.yaml").read_text()
        assert re.findall(r"- protocol: (\w+)\s+version: ([\d.]+)", config) == [
            ("responses", "2.0.0"),
            ("invocations", "2.0.0"),
        ]
        dependencies = tomllib.loads((folder / "pyproject.toml").read_text())[
            "project"
        ]["dependencies"]
        requirements = (folder / "requirements.txt").read_text().splitlines()
        for dependency in (
            "azure-ai-agentserver-invocations==1.1.0",
            "azure-ai-agentserver-responses==2.1.0",
        ):
            assert dependency in dependencies
            assert dependency in requirements
