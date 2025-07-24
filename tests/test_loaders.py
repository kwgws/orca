import pytest

from orca_chat.loaders.load_json import load_json
from orca_chat.loaders.load_toml import load_toml, to_namespace


def test_load_json_errors(tmp_path):
    file = tmp_path / "bad.json"
    with pytest.raises(FileNotFoundError):
        load_json(file, not_exist_ok=False)

    file.write_text("[1]")
    with pytest.raises(ValueError):
        load_json(file)


def test_load_toml(tmp_path, monkeypatch):
    file = tmp_path / "test.toml"
    monkeypatch.setenv("FOO", "BAR")
    file.write_text("key='${FOO}'")

    data = load_toml(file)
    assert data["key"] == "BAR"

    ns = to_namespace(data)
    assert ns.key == "BAR"
