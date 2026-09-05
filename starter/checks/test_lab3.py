import importlib.util
from pathlib import Path


def test_lab3_hosted_entrypoint_checkpoint(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("FINOPS_DATA_DIR", str(Path(__file__).parents[1] / "data"))
    main_path = Path(__file__).parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("starter_main", main_path)

    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.app is not None
