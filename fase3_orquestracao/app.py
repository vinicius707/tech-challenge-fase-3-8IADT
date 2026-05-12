"""FastAPI app para o servico IA Core.

Atende IA-A3 (Fase A) - cria a aplicacao com endpoint `GET /health` e
agora tambem IA-G1 ao plugar o router `chat_stream` em `POST /v1/chat/stream`.

Como executar localmente:
    uvicorn fase3_orquestracao.app:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fase3_orquestracao.chat_stream import router as chat_stream_router

SERVICE_NAME = "ia-core"
SERVICE_VERSION = "0.1.0"


def create_app() -> FastAPI:
    """Cria e configura a instancia FastAPI.

    Mantida como factory para facilitar testes (pytest pode importar e usar
    `TestClient(create_app())` sem efeitos globais).
    """

    app = FastAPI(
        title="IA Core - Saude da Mulher",
        version=SERVICE_VERSION,
        description=(
            "Servico Python (FastAPI) que executa RAG, LangGraph e safety guard "
            "para os quatro fluxos clinicos. Consumido pelo BFF Next.js via "
            "ORCHESTRATION_API_URL conforme docs/api.md."
        ),
    )

    # CORS deliberadamente permissivo apenas para localhost em desenvolvimento.
    # O acesso real e feito server-to-server pelo BFF (sem CORS), entao em
    # producao isto pode ser endurecido ou removido.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "ok": True,
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
        }

    app.include_router(chat_stream_router)

    return app


app = create_app()
