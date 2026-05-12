"""Camada `LlmBackend` pluggable para o servico IA Core.

Fase D (IA-D1 a IA-D4) conforme `docs/sdd/ia-core/design.md` §8:

- `LlmBackend`: interface comum com `model_version` e `generate` assincrono.
- `StubSafeBackend`: backend deterministico para avaliacao local (IA-D1).
- `OpenAICompatibleBackend`: provedores OpenAI-compatible via env vars (IA-D2).
- `OllamaBackend`: alias semantico apontado para Ollama/local (IA-D3).
- `LocalLoraBackend`: placeholder explicito para LoRA fine-tuned (IA-D4).
- `create_backend`: factory que combina `config/model_backends.yaml` e env vars.

Princípios:

- Safety e fluxo nao podem depender exclusivamente do LLM.
- Nunca expor chaves de API; tudo vem de env vars referenciadas no YAML.
- Backends carregados sob demanda - a falta da lib `openai` so quebra
  quando o backend especifico e instanciado.
- LangGraph fala apenas com `LlmBackend`; nada de provider especifico.

CLI:
    python -m fase3_orquestracao.llm_backend --backend stub_safe --prompt "..."
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    import yaml
except ImportError as exc:  # pragma: no cover - tratada apenas sem dependencia
    raise RuntimeError(
        "Dependencia `pyyaml` ausente. Rode `python -m pip install -r requirements.txt`."
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "model_backends.yaml"

BACKEND_ENV_VAR = "IA_LLM_BACKEND"
DEFAULT_FALLBACK_BACKEND = "stub_safe"


class LlmBackendError(RuntimeError):
    """Erro recuperavel da camada de backends de LLM."""


class LlmBackend(ABC):
    """Interface unica para backends de LLM.

    Subclasses devem definir `model_version` (string visivel em logs, sem
    incluir chaves) e implementar `generate` assincrono.
    """

    model_version: str

    @abstractmethod
    async def generate(self, prompt: str, *, temperature: float = 0.2) -> str:
        """Gera a resposta para `prompt` respeitando `temperature`."""
        raise NotImplementedError


class StubSafeBackend(LlmBackend):
    """Backend deterministico para testes locais e avaliacao sem modelo real.

    Nao realiza chamadas externas. Retorna uma resposta conservadora com
    disclaimers clinicos, mantendo o contrato `generate()` para que LangGraph
    e os testes nao precisem distinguir o backend.
    """

    def __init__(self, *, model_version: str = "stub-safe-0.1.0") -> None:
        self.model_version = model_version

    async def generate(self, prompt: str, *, temperature: float = 0.2) -> str:
        normalized = " ".join((prompt or "").split())
        tokens = len(normalized.split())
        head = normalized[:160] + ("..." if len(normalized) > 160 else "")
        return (
            "Resposta gerada em modo stub seguro. "
            "Esta saida nao usa modelo real e serve apenas para avaliacao local. "
            "Encaminhe para profissional habilitado e nao prescreva. "
            f"[modo:stub] [temperatura:{temperature:.2f}] [tokens_recebidos:{tokens}] "
            f"[prompt_resumido:{head!r}]"
        )


class OpenAICompatibleBackend(LlmBackend):
    """Backend OpenAI-compatible para provedores que seguem o protocolo da API OpenAI.

    Variaveis de ambiente usadas (todas configuraveis pelo YAML):
    - `api_key_env`  -> chave de API (default `OPENAI_API_KEY`).
    - `base_url_env` -> base URL alternativa (default `OPENAI_BASE_URL`).
    - `model_env`    -> nome do modelo (default `OPENAI_MODEL`).

    A chave nunca aparece em `model_version`, logs ou erros. Para ambientes
    de teste sem dependencia `openai`, e possivel injetar `client` diretamente.
    """

    def __init__(
        self,
        *,
        api_key_env: str = "OPENAI_API_KEY",
        base_url_env: str = "OPENAI_BASE_URL",
        model_env: str = "OPENAI_MODEL",
        default_model: str = "gpt-4o-mini",
        default_base_url: str | None = None,
        default_api_key: str | None = None,
        timeout_seconds: float = 30.0,
        environ: Mapping[str, str] | None = None,
        client: Any | None = None,
        provider_label: str = "openai_compatible",
    ) -> None:
        env: Mapping[str, str] = environ if environ is not None else os.environ
        api_key = env.get(api_key_env) or default_api_key
        base_url = env.get(base_url_env) or default_base_url
        model = env.get(model_env) or default_model

        if not api_key:
            raise LlmBackendError(
                f"Variavel `{api_key_env}` ausente. Configure-a ou selecione o backend "
                "`stub_safe` para avaliacao local."
            )
        if not model:
            raise LlmBackendError(
                f"Modelo nao definido. Defina `{model_env}` ou `default_model` no YAML."
            )

        if client is None:
            try:
                from openai import AsyncOpenAI  # type: ignore[import-not-found]
            except ImportError as exc:
                raise LlmBackendError(
                    "Dependencia `openai` ausente. Rode `python -m pip install -r requirements.txt`."
                ) from exc

            client_kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout_seconds}
            if base_url:
                client_kwargs["base_url"] = base_url
            client = AsyncOpenAI(**client_kwargs)

        self._client = client
        self._model = model
        self._provider_label = provider_label
        self.model_version = f"{provider_label}:{model}"

    async def generate(self, prompt: str, *, temperature: float = 0.2) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise LlmBackendError("Resposta do provedor LLM em formato inesperado.") from exc
        return (content or "").strip()


def _ensure_openai_compat_suffix(url: str | None) -> str | None:
    """Normaliza a base URL do Ollama para a API OpenAI-compatible.

    O Ollama expoe `/v1/chat/completions` no mesmo host do `/api/tags`.
    Como guides oficiais (incluindo `docs/sdd/ia-core/tasks.md`) pedem somente
    `http://127.0.0.1:11434`, anexamos `/v1` automaticamente para evitar
    falhas silenciosas em `chat.completions.create` quando o usuario esquece.
    URLs ja contendo `/v1`, `/v2`, etc., ou qualquer outro path explicito,
    permanecem intactas.
    """

    if not url:
        return url
    trimmed = url.rstrip("/")
    if not trimmed:
        return url

    if trimmed.startswith("https://"):
        host_and_path = trimmed[len("https://"):]
    elif trimmed.startswith("http://"):
        host_and_path = trimmed[len("http://"):]
    else:
        host_and_path = trimmed

    if "/" not in host_and_path:
        # nao tem path - anexar /v1
        return f"{trimmed}/v1"

    last_segment = host_and_path.rsplit("/", 1)[-1]
    if last_segment.startswith("v") and last_segment[1:].isdigit():
        # ja termina em /v<n> - manter
        return trimmed
    # path customizado distinto de /v<n>: nao mexer (caller sabe o que faz)
    return trimmed


class OllamaBackend(OpenAICompatibleBackend):
    """Alias semantico para servidores Ollama via API OpenAI-compatible.

    Mantem `provider_label='ollama'` para que logs e `model_version` deixem
    claro qual provedor respondeu, sem mudar a interface. Aceita tambem
    `OLLAMA_BASE_URL` sem o sufixo `/v1`, normalizando antes de instanciar
    o cliente OpenAI.
    """

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("provider_label", "ollama")
        base_url_env = kwargs.get("base_url_env", "OLLAMA_BASE_URL")
        environ: Mapping[str, str] | None = kwargs.get("environ")
        env_map: Mapping[str, str] = environ if environ is not None else os.environ
        raw_env = env_map.get(base_url_env)
        if raw_env:
            normalized = _ensure_openai_compat_suffix(raw_env)
            if normalized and normalized != raw_env:
                if environ is None:
                    # roda em producao - atualiza os.environ para refletir a
                    # base URL real usada pelo cliente OpenAI a partir daqui.
                    os.environ[base_url_env] = normalized
                else:
                    # testes ou chamadas controladas - geramos uma copia para
                    # nao mutar o dict do caller.
                    kwargs["environ"] = {**dict(environ), base_url_env: normalized}
        default_base_url = kwargs.get("default_base_url")
        if default_base_url:
            kwargs["default_base_url"] = _ensure_openai_compat_suffix(default_base_url)
        super().__init__(**kwargs)


class LocalLoraBackend(LlmBackend):
    """Placeholder explicito para fine-tuned LoRA. Carregamento real e da Fase H.

    Mantemos o backend disponivel no factory para evidenciar o slot na arquitetura
    (IA-D4), mas qualquer chamada falha com mensagem clara apontando para a
    documentacao - nada de simular resposta como se houvesse modelo treinado.
    """

    def __init__(self, *, model_version: str = "local_lora:placeholder") -> None:
        self.model_version = model_version

    async def generate(self, prompt: str, *, temperature: float = 0.2) -> str:
        raise LlmBackendError(
            "Backend `local_lora` ainda nao tem artefato carregado. "
            "Veja docs/llm-backends.md (Fase H) para instrucoes de carregamento."
        )


def _read_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise LlmBackendError(f"Configuracao nao encontrada: {config_path}")
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise LlmBackendError(f"Configuracao invalida em {config_path}")
    backends = payload.get("backends")
    if not isinstance(backends, dict) or not backends:
        raise LlmBackendError(f"`backends` ausente ou invalido em {config_path}")
    return payload


def list_backends(*, config_path: Path | None = None) -> list[str]:
    """Lista os backends configurados, util para tooling/CLI."""
    payload = _read_config(config_path)
    return sorted(payload.get("backends", {}))


def resolve_backend_name(
    *,
    requested: str | None = None,
    config_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve o nome do backend ativo segundo prioridade: arg > env > YAML > fallback.

    A chave preferida no YAML e `default_provider` (alinhada com
    `docs/sdd/ia-core/design.md` secao 8). `default` permanece aceita por
    compatibilidade com configuracoes antigas.
    """
    payload = _read_config(config_path)
    env: Mapping[str, str] = environ if environ is not None else os.environ
    return (
        requested
        or env.get(BACKEND_ENV_VAR)
        or payload.get("default_provider")
        or payload.get("default")
        or DEFAULT_FALLBACK_BACKEND
    )


def create_backend(
    name: str | None = None,
    *,
    config_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
    client: Any | None = None,
) -> LlmBackend:
    """Cria um backend baseado em `config/model_backends.yaml`.

    `client` permite injetar um cliente OpenAI ja construido (uso em testes).
    """
    payload = _read_config(config_path)
    selected = resolve_backend_name(requested=name, config_path=config_path, environ=environ)
    backends = payload.get("backends", {})
    if selected not in backends:
        raise LlmBackendError(
            f"Backend desconhecido: {selected!r}. Disponiveis: {sorted(backends)}"
        )

    spec = dict(backends[selected])
    backend_type = spec.get("type", selected)

    if backend_type == "stub":
        return StubSafeBackend(model_version=spec.get("model_version", "stub-safe-0.1.0"))

    if backend_type == "openai_compatible":
        kwargs: dict[str, Any] = {
            "api_key_env": spec.get("api_key_env", "OPENAI_API_KEY"),
            "base_url_env": spec.get("base_url_env", "OPENAI_BASE_URL"),
            "model_env": spec.get("model_env", "OPENAI_MODEL"),
            "default_model": spec.get("default_model", "gpt-4o-mini"),
            "default_base_url": spec.get("default_base_url"),
            "default_api_key": spec.get("default_api_key"),
            "timeout_seconds": float(spec.get("timeout_seconds", 30.0)),
            "environ": environ,
            "client": client,
            "provider_label": spec.get("provider_label", selected),
        }
        if selected == "ollama":
            return OllamaBackend(**{k: v for k, v in kwargs.items() if k != "provider_label"})
        return OpenAICompatibleBackend(**kwargs)

    if backend_type == "placeholder":
        return LocalLoraBackend()

    raise LlmBackendError(f"Tipo de backend desconhecido em {selected}: {backend_type!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI manual para testar LlmBackend.")
    parser.add_argument("--backend", help="Nome do backend (default: env IA_LLM_BACKEND ou YAML).")
    parser.add_argument("--prompt", help="Prompt enviado ao backend (obrigatorio se nao for --list).")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--list", action="store_true", help="Apenas lista os backends configurados.")
    args = parser.parse_args()

    if args.list:
        for name in list_backends():
            print(name)
        return

    if not args.prompt:
        parser.error("--prompt e obrigatorio quando --list nao e usado.")

    backend = create_backend(args.backend)
    response = asyncio.run(backend.generate(args.prompt, temperature=args.temperature))
    output = {
        "backend": backend.__class__.__name__,
        "model_version": backend.model_version,
        "response": response,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
