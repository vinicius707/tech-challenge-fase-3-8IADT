# Contrato HTTP — BFF Next.js ↔ orquestração Python

Versão: **0.1.0**  
Audiência: implementadores do front (`web/`) e do serviço Python (LangChain/LangGraph).

## Variáveis de ambiente (Next servidor)

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `ORCHESTRATION_API_URL` | Não | Base URL do Python (ex.: `http://127.0.0.1:8000`). Se ausente, o BFF usa **modo stub** para demo local. |
| `ORCHESTRATION_API_KEY` | Não | Bearer opcional para o Python em ambientes fechados. |

## Cabeçalhos

- **`x-request-id`**: UUID v4; o browser envia, o BFF repassa ao Python como `x-request-id` (ou `X-Request-ID`).  
- **`Content-Type`**: `application/json` nos POST.

---

## POST `/api/chat/stream`

**Descrição:** inicia uma resposta assistida com **SSE** (`text/event-stream`).

### Request body

```json
{
  "flowId": "triagemGinecologica",
  "threadId": "opcional-id-de-thread",
  "messages": [
    { "role": "user", "content": "texto" }
  ],
  "patientContext": {
    "resumo": "string opcional",
    "preventivos": {},
    "obstetrica": {},
    "cicloMenstrual": {},
    "historicoReprodutivo": {}
  }
}
```

### `flowId` (enum)

| Valor | Descrição |
|-------|-----------|
| `triagemGinecologica` | RF-LG-01 |
| `violenciaDomestica` | RF-LG-02 |
| `obstetrico` | RF-LG-03 |
| `prevencao` | RF-LG-04 |

### Eventos SSE (`text/event-stream`)

Cada evento segue o formato:

```
event: <nome>
data: <json>
```

| `event` | `data` (JSON) |
|---------|----------------|
| `meta` | `{ "requestId": "uuid", "flowId": "...", "modelVersion"?: string, "urgencia"?: "nenhuma" \| "moderada" \| "alta" \| "emergencia" }` |
| `token` | `{ "delta": "texto parcial" }` |
| `explain` | Objeto **ExplainBlock** (parcial ou completo) |
| `log` | `{ "level": "info", "message": "...", "ts": "ISO-8601" }` |
| `done` | `{}` |
| `error` | `{ "code": "string", "message": "string" }` |

#### ExplainBlock (RF-SEC-04)

```json
{
  "fonte": "protocolo interno X / guideline Y",
  "confianca": 0.72,
  "lacunas": ["ausência de exame físico", "..."],
  "raciocinioClinico": "texto curto opcional"
}
```

### Respostas HTTP não-SSE

| Código | Situação |
|--------|----------|
| 400 | JSON inválido ou `flowId` desconhecido |
| 401 | Reservado futuro (auth) |
| 502 | Python indisponível **e** stub desativado (futuro); hoje cai em stub se URL ausente |

### Encaminhamento ao Python (quando `ORCHESTRATION_API_URL` definido)

O BFF deve fazer **POST** `${ORCHESTRATION_API_URL}/v1/chat/stream` com o mesmo corpo (ou mapeamento documentado lado Python) e repassar o stream SSE **sem** alterar o significado dos eventos.  
_TBD equipe:_ path exato no FastAPI/Starlette.

---

## GET `/api/health`

**Descrição:** verificação simples do BFF.

### Response 200

```json
{ "ok": true, "mode": "stub" | "proxy" }
```

---

## OpenAPI

Arquivo gerável: `docs/openapi/web-bff.yaml` (opcional). Este `api.md` é a fonte normativa até exportação automática.
