# Contrato HTTP — BFF Next.js ↔ orquestração Python

Versão: **0.2.0**  
Audiência: implementadores do front (`web/`) e do serviço Python (LangChain/LangGraph).

## Variáveis de ambiente (Next servidor)

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `AUTH_SECRET` | **Sim** (prod e CI) | Segredo JWT (mínimo **32** caracteres) para o cookie `mw_session`. |
| `DATABASE_PATH` | Não | Caminho do SQLite (default: `data/app.db` relativo ao cwd do processo `web/`). |
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

## Autenticação (MVP)

### POST `/api/auth/login`

**Body:**

```json
{ "email": "demo@exemplo.org", "password": "demo12345" }
```

**200:** `{ "ok": true, "user": { "id", "email", "name" } }` e `Set-Cookie: mw_session=…` (`HttpOnly`).

**401:** credenciais inválidas.

### POST `/api/auth/logout`

**200:** `{ "ok": true }` e remove o cookie `mw_session`.

### GET `/api/auth/me`

**200:** `{ "user": { "id", "email", "name" } }`  
**401:** sem sessão.

---

## Atendimentos / auditoria (SQLite)

Todas as rotas abaixo exigem sessão válida (cookie `mw_session`).

### GET `/api/atendimentos`

**Query:**

- `filtro`: `todas` \| `medico` \| `fora_escopo` \| `emergencia` \| `bloqueado` (default `todas`)
- `page` (default `1`)
- `pageSize` (default `10`, máx `50`)
- `so_emergencias=1` (AND adicional em `urgencia`)

**200:**

```json
{
  "page": 1,
  "pageSize": 10,
  "total": 123,
  "agregados": { "total": 123, "emergencias": 2, "bloqueados": 0 },
  "items": [
    {
      "id": "uuid",
      "createdAt": 1710000000000,
      "flowId": "triagemGinecologica",
      "perguntaText": "…",
      "categoria": "Saúde da mulher / GO",
      "categoriaConfidence": 0.6,
      "segurancaStatus": "ok",
      "fontesCount": 1,
      "duracaoMs": 1200,
      "requestId": "uuid",
      "urgencia": "nenhuma",
      "bloqueado": false,
      "sensitiveRedacted": false
    }
  ]
}
```

### GET `/api/atendimentos/:id`

**200:** objeto detalhado (lista + `promptText`, `respostaBruta`, `classificacaoJson`, `langgraphTraceJson`).  
**404:** inexistente ou não pertence ao utilizador.

### POST `/api/atendimentos`

Cria registo **idempotente** por `request_id` único.

**Body (mínimo):**

```json
{
  "requestId": "uuid",
  "flowId": "triagemGinecologica",
  "perguntaText": "…",
  "duracaoMs": 1200,
  "urgencia": "nenhuma",
  "promptText": "{...json...}",
  "respostaBruta": "…",
  "classificacaoJson": "{...explain...}",
  "langgraphTraceJson": null
}
```

**201:** `{ "ok": true, "id": "…" }`  
**200:** `{ "ok": true, "id": "…", "idempotent": true }` quando `request_id` já existia.

**Nota:** para `flowId = violenciaDomestica`, o servidor **redige** prompt/resposta persistidos (política MVP).

---

## OpenAPI

Arquivo gerável: `docs/openapi/web-bff.yaml` (opcional). Este `api.md` é a fonte normativa até exportação automática.
