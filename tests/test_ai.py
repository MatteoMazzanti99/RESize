import io
import json
import tempfile
import urllib.error
from pathlib import Path

import pytest

from resize_energy.core.pv_design import PVInputs, size_pv_system
from resize_energy.tutor import ai, ai_settings
from resize_energy.tutor.ai import AIError, AISettings, Message, ask
from resize_energy.tutor.checker import check_pv_design
from resize_energy.tutor.context import build_project_context


def fake_server(reply, captured):
    """A urlopen stand-in that records the request and returns ``reply`` as JSON."""

    def urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = {k.lower(): v for k, v in request.header_items()}
        captured["body"] = json.loads(request.data.decode())
        return io.BytesIO(json.dumps(reply).encode())

    return urlopen


def http_error(code, body=b""):
    def urlopen(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, code, "err", {}, io.BytesIO(body))

    return urlopen


QUESTION = [Message("user", "Why is N_max 22?")]


def test_anthropic_request_and_reply():
    captured = {}
    reply = {"content": [{"type": "text", "text": "Because "}, {"type": "text", "text": "of Vmp."}]}
    settings = AISettings("anthropic", api_key="sk-test")
    text = ask(settings, "SYSTEM", QUESTION, urlopen=fake_server(reply, captured))
    assert text == "Because of Vmp."
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "sk-test"
    assert captured["headers"]["anthropic-version"] == ai.ANTHROPIC_VERSION
    body = captured["body"]
    assert body["model"] == "claude-sonnet-5-5"
    assert body["system"] == "SYSTEM"
    assert body["messages"] == [{"role": "user", "content": "Why is N_max 22?"}]
    assert body["max_tokens"] == 1024


def test_openai_compatible_request_and_reply():
    captured = {}
    reply = {"choices": [{"message": {"content": "  Use the cold Vmp. "}}]}
    settings = AISettings("openai", model="my-model", api_key="sk-x")
    text = ask(settings, "SYSTEM", QUESTION, urlopen=fake_server(reply, captured))
    assert text == "Use the cold Vmp."
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer sk-x"
    assert captured["body"]["messages"][0] == {"role": "system", "content": "SYSTEM"}
    assert captured["body"]["messages"][1]["role"] == "user"


def test_ollama_needs_no_key_and_uses_local_address():
    captured = {}
    reply = {"choices": [{"message": {"content": "ok"}}]}
    ask(AISettings("ollama"), "S", QUESTION, urlopen=fake_server(reply, captured))
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert "authorization" not in captured["headers"]
    assert captured["body"]["model"] == "llama3.1"


def test_missing_key_model_and_question_are_reported_before_any_request():
    def never(*a, **k):
        raise AssertionError("no request should be made")

    with pytest.raises(AIError) as info:
        ask(AISettings("anthropic"), "S", QUESTION, urlopen=never)
    assert "API key" in str(info.value)
    with pytest.raises(AIError) as info:
        ask(AISettings("openai", api_key="k"), "S", QUESTION, urlopen=never)
    assert "model" in str(info.value)
    with pytest.raises(AIError):
        ask(AISettings("anthropic", api_key="k"), "S", [], urlopen=never)
    with pytest.raises(AIError):
        ask(AISettings("nope", api_key="k"), "S", QUESTION, urlopen=never)


def test_http_errors_become_readable_messages():
    settings = AISettings("anthropic", api_key="k")
    body = json.dumps({"error": {"type": "authentication_error", "message": "invalid x-api-key"}})
    with pytest.raises(AIError) as info:
        ask(settings, "S", QUESTION, urlopen=http_error(401, body.encode()))
    assert "rejected the API key" in str(info.value) and "invalid x-api-key" in str(info.value)
    with pytest.raises(AIError) as info:
        ask(settings, "S", QUESTION, urlopen=http_error(404))
    assert "model" in str(info.value).lower()
    with pytest.raises(AIError) as info:
        ask(settings, "S", QUESTION, urlopen=http_error(429))
    assert "429" in str(info.value)
    with pytest.raises(AIError) as info:
        ask(settings, "S", QUESTION, urlopen=http_error(500, b"boom"))
    assert "500" in str(info.value) and "boom" in str(info.value)


def test_network_failure_mentions_ollama_hint():
    def offline(request, timeout=None):
        raise urllib.error.URLError("connection refused")

    with pytest.raises(AIError) as info:
        ask(AISettings("ollama"), "S", QUESTION, urlopen=offline)
    text = str(info.value)
    assert "Ollama" in text and "localhost" in text
    assert "ollama serve" in text and "ollama pull llama3.1" in text and "ollama.com" in text


def test_ollama_missing_model_says_how_to_download_it():
    with pytest.raises(AIError) as info:
        ask(AISettings("ollama", model="mistral"), "S", QUESTION,
            urlopen=http_error(404, b'{"error": "model not found"}'))
    assert "ollama pull mistral" in str(info.value)


def test_bad_replies_are_rejected():
    settings = AISettings("anthropic", api_key="k")
    for reply in ({"content": []}, {"content": "x"}, {"other": 1}):
        with pytest.raises(AIError):
            ask(settings, "S", QUESTION, urlopen=fake_server(reply, {}))
    with pytest.raises(AIError):
        ask(AISettings("ollama"), "S", QUESTION,
            urlopen=fake_server({"choices": []}, {}))


def test_normalize_messages():
    msgs = [
        Message("assistant", "stray"),
        Message("user", "a"),
        Message("user", "b"),
        Message("assistant", "   "),
        Message("assistant", "c"),
    ]
    out = ai.normalize_messages(msgs)
    assert out == [Message("user", "a\n\nb"), Message("assistant", "c")]


def test_system_prompt_contains_context_and_rules():
    prompt = ai.build_system_prompt("CONTEXT-123 {not a placeholder}")
    assert "CONTEXT-123 {not a placeholder}" in prompt
    assert "Never invent results" in prompt
    assert "not instructions" in prompt


def test_project_context_has_numbers_and_checks():
    inp = PVInputs(annual_demand_kwh=4500, annual_irradiation_kwh_m2=1500, performance_ratio=0.8)
    design = size_pv_system(inp)
    text = build_project_context(inp, design, check_pv_design(inp, design))
    assert "Annual electricity demand: 4,500 kWh" in text
    assert "Target peak power: 3.75 kWp (10 modules)" in text
    assert "10 in series x 1 in parallel = 10 modules" in text
    assert "DESIGN CHECKS" in text and "[OK]" in text
    prompt = ai.build_chatbot_prompt(text)
    assert prompt.endswith(text) and "tutor" in prompt


class FakeKeyring:
    def __init__(self, fail=False):
        self.store, self.fail = {}, fail

    def get_password(self, service, name):
        if self.fail:
            raise RuntimeError("no backend")
        return self.store.get((service, name))

    def set_password(self, service, name, value):
        if self.fail:
            raise RuntimeError("no backend")
        self.store[(service, name)] = value

    def delete_password(self, service, name):
        self.store.pop((service, name), None)


def test_settings_round_trip_never_stores_the_key():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "sub" / "ai.json"
        s = AISettings("openai", model="m", base_url="https://x/v1", api_key="SECRET")
        assert ai_settings.save_settings(s, path)
        assert "SECRET" not in path.read_text()
        loaded = ai_settings.load_settings(path)
        assert (loaded.provider, loaded.model, loaded.base_url) == ("openai", "m", "https://x/v1")
        assert loaded.api_key == ""


def test_load_settings_falls_back_to_defaults():
    with tempfile.TemporaryDirectory() as folder:
        assert ai_settings.load_settings(Path(folder) / "missing.json") == AISettings()
        bad = Path(folder) / "bad.json"
        bad.write_text("{not json")
        assert ai_settings.load_settings(bad) == AISettings()
        odd = Path(folder) / "odd.json"
        odd.write_text(json.dumps({"provider": "weird"}))
        assert ai_settings.load_settings(odd).provider == "anthropic"


def test_api_key_keyring_and_environment():
    kr = FakeKeyring()
    assert ai_settings.save_api_key("anthropic", "KEY", kr)
    assert ai_settings.load_api_key("anthropic", kr, {}) == "KEY"
    # keyring wins over the environment; environment is the fallback
    assert ai_settings.load_api_key("anthropic", kr, {"ANTHROPIC_API_KEY": "ENV"}) == "KEY"
    assert ai_settings.load_api_key("openai", kr, {"OPENAI_API_KEY": " ENV2 "}) == "ENV2"
    assert ai_settings.load_api_key("ollama", kr, {}) == ""
    assert ai_settings.delete_api_key("anthropic", kr)
    assert ai_settings.load_api_key("anthropic", kr, {}) == ""


def test_broken_keyring_does_not_crash():
    kr = FakeKeyring(fail=True)
    assert ai_settings.save_api_key("anthropic", "KEY", kr) is False
    assert ai_settings.load_api_key("anthropic", kr, {"ANTHROPIC_API_KEY": "ENV"}) == "ENV"

