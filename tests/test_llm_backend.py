"""Testes da camada `LlmBackend` (Fase D)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
import yaml

from fase3_orquestracao.llm_backend import (
    BACKEND_ENV_VAR,
    DEFAULT_FALLBACK_BACKEND,
    LlmBackend,
    LlmBackendError,
    LocalLoraBackend,
    OllamaBackend,
    OpenAICompatibleBackend,
    StubSafeBackend,
    create_backend,
    list_backends,
    resolve_backend_name,
)


@pytest.fixture
def config_yaml(tmp_path: Path) -> Path:
    config = {
        "default_provider": "stub_safe",
        "backends": {
            "stub_safe": {"type": "stub", "model_version": "stub-safe-test"},
            "openai_compatible": {
                "type": "openai_compatible",
                "api_key_env": "TEST_OPENAI_KEY",
                "base_url_env": "TEST_OPENAI_BASE",
                "model_env": "TEST_OPENAI_MODEL",
                "default_model": "gpt-test",
                "timeout_seconds": 5,
            },
            "ollama": {
                "type": "openai_compatible",
                "api_key_env": "TEST_OLLAMA_KEY",
                "base_url_env": "TEST_OLLAMA_BASE",
                "model_env": "TEST_OLLAMA_MODEL",
                "default_model": "llama-test",
                "default_base_url": "http://127.0.0.1:11434/v1",
                "default_api_key": "ollama",
            },
            "local_lora": {"type": "placeholder"},
        },
    }
    path = tmp_path / "model_backends.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self) -> None:
        self.last_call: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> _FakeResponse:
        self.last_call = kwargs
        return _FakeResponse("resposta-fake")


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeAsyncOpenAI:
    def __init__(self) -> None:
        self.chat = _FakeChat()


def _run(coro):
    return asyncio.run(coro)


def test_llm_backend_eh_abstrato():
    with pytest.raises(TypeError):
        LlmBackend()  # type: ignore[abstract]


def test_stub_safe_responde_com_disclaimer():
    backend = StubSafeBackend()
    text = _run(backend.generate("Paciente com dor pelvica?", temperature=0.1))
    assert "stub seguro" in text
    assert "[modo:stub]" in text
    assert "Encaminhe" in text
    assert backend.model_version == "stub-safe-0.1.0"


def test_stub_safe_eh_deterministico():
    backend = StubSafeBackend()
    a = _run(backend.generate("ola", temperature=0.2))
    b = _run(backend.generate("ola", temperature=0.2))
    assert a == b


def test_openai_compatible_usa_env_e_oculta_chave():
    fake = _FakeAsyncOpenAI()
    backend = OpenAICompatibleBackend(
        api_key_env="X_API_KEY",
        base_url_env="X_BASE",
        model_env="X_MODEL",
        default_model="model-default",
        environ={"X_API_KEY": "shh-secret", "X_MODEL": "model-from-env"},
        client=fake,
    )
    text = _run(backend.generate("prompt", temperature=0.3))
    assert text == "resposta-fake"
    assert backend.model_version == "openai_compatible:model-from-env"
    assert "shh-secret" not in backend.model_version

    call = fake.chat.completions.last_call
    assert call is not None
    assert call["model"] == "model-from-env"
    assert call["temperature"] == 0.3
    assert call["messages"] == [{"role": "user", "content": "prompt"}]


def test_openai_compatible_falha_sem_api_key():
    with pytest.raises(LlmBackendError, match="ausente"):
        OpenAICompatibleBackend(
            api_key_env="X_API_KEY",
            base_url_env="X_BASE",
            model_env="X_MODEL",
            environ={},
            client=_FakeAsyncOpenAI(),
        )


def test_ollama_marca_provider_label():
    backend = OllamaBackend(
        api_key_env="OLLAMA_API_KEY",
        base_url_env="OLLAMA_BASE_URL",
        model_env="OLLAMA_MODEL",
        default_api_key="ollama",
        default_base_url="http://127.0.0.1:11434/v1",
        default_model="llama-test",
        environ={},
        client=_FakeAsyncOpenAI(),
    )
    assert backend.model_version == "ollama:llama-test"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("http://127.0.0.1:11434", "http://127.0.0.1:11434/v1"),
        ("http://127.0.0.1:11434/", "http://127.0.0.1:11434/v1"),
        ("http://127.0.0.1:11434/v1", "http://127.0.0.1:11434/v1"),
        ("http://127.0.0.1:11434/v1/", "http://127.0.0.1:11434/v1"),
        ("https://api.openai.com/v1", "https://api.openai.com/v1"),
        ("https://api.openai.com/v2", "https://api.openai.com/v2"),
        ("http://my.host:1234/custom/path", "http://my.host:1234/custom/path"),
        ("", ""),
    ],
)
def test_ensure_openai_compat_suffix_normaliza_base_url(raw: str, expected: str):
    from fase3_orquestracao.llm_backend import _ensure_openai_compat_suffix

    assert _ensure_openai_compat_suffix(raw) == expected


def test_ensure_openai_compat_suffix_none():
    from fase3_orquestracao.llm_backend import _ensure_openai_compat_suffix

    assert _ensure_openai_compat_suffix(None) is None


def test_ollama_aceita_base_url_sem_v1_via_env():
    """OLLAMA_BASE_URL sem `/v1` deve ser normalizada antes de chegar ao cliente."""
    fake = _FakeAsyncOpenAI()
    environ_passed = {
        "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        "OLLAMA_API_KEY": "ollama",
        "OLLAMA_MODEL": "llama3.2:1b",
    }
    backend = OllamaBackend(
        api_key_env="OLLAMA_API_KEY",
        base_url_env="OLLAMA_BASE_URL",
        model_env="OLLAMA_MODEL",
        default_api_key="ollama",
        default_model="llama-test",
        environ=environ_passed,
        client=fake,
    )
    assert backend.model_version == "ollama:llama3.2:1b"
    # dict do caller nao deve ser mutado pela normalizacao
    assert environ_passed["OLLAMA_BASE_URL"] == "http://127.0.0.1:11434"


def test_ollama_aceita_default_base_url_sem_v1():
    """Mesmo o `default_base_url` informado sem `/v1` deve ser normalizado."""
    backend = OllamaBackend(
        api_key_env="OLLAMA_API_KEY",
        base_url_env="OLLAMA_BASE_URL",
        model_env="OLLAMA_MODEL",
        default_api_key="ollama",
        default_base_url="http://127.0.0.1:11434",
        default_model="llama-test",
        environ={},
        client=_FakeAsyncOpenAI(),
    )
    assert backend.model_version == "ollama:llama-test"


def test_local_lora_recusa_sem_artefato():
    backend = LocalLoraBackend()
    with pytest.raises(LlmBackendError, match="local_lora"):
        _run(backend.generate("x"))


def test_resolve_backend_name_prioriza_argumento(config_yaml: Path):
    name = resolve_backend_name(requested="ollama", config_path=config_yaml, environ={})
    assert name == "ollama"


def test_resolve_backend_name_usa_env(config_yaml: Path):
    name = resolve_backend_name(
        config_path=config_yaml,
        environ={BACKEND_ENV_VAR: "openai_compatible"},
    )
    assert name == "openai_compatible"


def test_resolve_backend_name_cai_para_default_provider_yaml(config_yaml: Path):
    name = resolve_backend_name(config_path=config_yaml, environ={})
    assert name == "stub_safe"


def test_resolve_backend_name_aceita_default_legado(tmp_path: Path):
    legacy = tmp_path / "legacy.yaml"
    legacy.write_text(
        yaml.safe_dump({"default": "stub_safe", "backends": {"stub_safe": {"type": "stub"}}}),
        encoding="utf-8",
    )
    assert resolve_backend_name(config_path=legacy, environ={}) == "stub_safe"


def test_resolve_backend_name_fallback_final(tmp_path: Path):
    minimal = tmp_path / "min.yaml"
    minimal.write_text(yaml.safe_dump({"backends": {"stub_safe": {"type": "stub"}}}), encoding="utf-8")
    assert resolve_backend_name(config_path=minimal, environ={}) == DEFAULT_FALLBACK_BACKEND


def test_create_backend_stub(config_yaml: Path):
    backend = create_backend("stub_safe", config_path=config_yaml, environ={})
    assert isinstance(backend, StubSafeBackend)
    assert backend.model_version == "stub-safe-test"


def test_create_backend_openai_compatible_injecta_cliente(config_yaml: Path):
    fake = _FakeAsyncOpenAI()
    backend = create_backend(
        "openai_compatible",
        config_path=config_yaml,
        environ={"TEST_OPENAI_KEY": "k", "TEST_OPENAI_MODEL": "m1"},
        client=fake,
    )
    assert isinstance(backend, OpenAICompatibleBackend)
    assert backend.model_version == "openai_compatible:m1"


def test_create_backend_ollama_usa_defaults_yaml(config_yaml: Path):
    backend = create_backend(
        "ollama",
        config_path=config_yaml,
        environ={},
        client=_FakeAsyncOpenAI(),
    )
    assert isinstance(backend, OllamaBackend)
    assert backend.model_version == "ollama:llama-test"


def test_create_backend_local_lora(config_yaml: Path):
    backend = create_backend("local_lora", config_path=config_yaml, environ={})
    assert isinstance(backend, LocalLoraBackend)


def test_create_backend_recusa_nome_desconhecido(config_yaml: Path):
    with pytest.raises(LlmBackendError, match="Backend desconhecido"):
        create_backend("inexistente", config_path=config_yaml, environ={})


def test_list_backends_inclui_default_do_projeto():
    names = list_backends()
    assert "stub_safe" in names
    assert "openai_compatible" in names
    assert "ollama" in names
    assert "local_lora" in names


def test_create_backend_real_default_do_projeto_e_ollama():
    """O default do projeto (decisao D9 da Fase D) e o Ollama local.

    Como o cliente Ollama nao faz chamadas de rede no construtor, o backend
    pode ser instanciado mesmo sem servidor rodando. A chamada real (`generate`)
    e que dispararia a rede.
    """
    backend = create_backend(environ={})
    assert isinstance(backend, OllamaBackend)
    assert backend.model_version.startswith("ollama:")


def test_create_backend_via_env_var_seleciona_stub_safe():
    """`IA_LLM_BACKEND=stub_safe` permite gates locais offline."""
    backend = create_backend(environ={BACKEND_ENV_VAR: "stub_safe"})
    assert isinstance(backend, StubSafeBackend)
