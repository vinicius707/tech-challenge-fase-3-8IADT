# Diagrama de Arquitetura - FemCare IA Core

Este documento consolida a arquitetura **final** entregue, refletindo o código versionado em `main` e não apenas a planta original do SDD ([`docs/sdd/ia-core/design.md`](sdd/ia-core/design.md)). Cada bloco do diagrama aponta para os ficheiros reais que o implementam.

Documentos irmãos:

- [`CHECKLIST_FASE3.md`](../CHECKLIST_FASE3.md) - mapa de evidências.
- [`docs/diagramas_fluxos.md`](diagramas_fluxos.md) - os quatro grafos LangGraph.
- [`docs/relatorio_tecnico.md`](relatorio_tecnico.md) - relatório técnico completo.
- [`docs/api.md`](api.md) - contrato HTTP normativo BFF ↔ IA Core.

## 1. Visão de processos (deployed components)

```mermaid
flowchart LR
  subgraph User["Operadora clinica"]
    browser["Browser /atendimentos/novo"]
  end

  subgraph BFF["Next.js BFF (web/)"]
    nextAPI["/api/chat/stream (proxy SSE)"]
    nextAuth["/api/auth/login (JWT cookie)"]
    nextAtend["/api/atendimentos (CRUD)"]
    sqlite[("SQLite better-sqlite3<br/>data/app.db")]
  end

  subgraph IACore["IA Core (FastAPI + Uvicorn :8000)"]
    appPy["fase3_orquestracao/app.py"]
    chat["POST /v1/chat/stream<br/>fase3_orquestracao/chat_stream.py"]
    router["clinical_router.py<br/>(GRAPH_FACTORIES)"]
    graphs["graphs/<br/>triagem · violencia · obstetrico · prevencao"]
    safety["fase4_seguranca/<br/>safety_guard · response_validator · audit · explainability"]
    rag["fase3_orquestracao/rag_chain.py<br/>HashingEmbeddings + JSON index"]
    backend["fase3_orquestracao/llm_backend.py<br/>OllamaBackend / OpenAICompat / StubSafe"]
  end

  subgraph LLMs["Modelos servidos"]
    ollama["Ollama :11434<br/>femcare:v0.1 (LoRA merged Q4_K_M)<br/>ou llama3.2:3b base"]
    openai["(Opcional) OpenAI-compatible<br/>OPENAI_BASE_URL / OPENAI_API_KEY"]
  end

  subgraph Storage["Artefatos versionaveis"]
    rag_jsonl["data/rag_documents.jsonl"]
    eval_jsonl["data/evaluation_cases.jsonl"]
    train_val["data/train.jsonl · data/val.jsonl"]
    vecstore["outputs/vectorstore/rag_index.json"]
    metadata["outputs/model/metadata.json"]
    reports["outputs/reports/<br/>data_validation · avaliacao · benchmark_results"]
    audit["logs/audit.log (JSON Lines)"]
  end

  subgraph Releases["GitHub Release"]
    rel["ia-core-phase-h-v0.1<br/>femcare-lora-v0.1.tar.gz"]
  end

  browser -->|"HTTPS"| nextAPI
  browser -->|"HTTPS"| nextAuth
  nextAPI -->|"SSE proxy /v1/chat/stream"| chat
  nextAtend --> sqlite
  nextAuth --> sqlite

  chat --> router
  router --> graphs
  graphs --> rag
  graphs --> safety
  chat -->|"polish opcional"| backend
  backend --> ollama
  backend -.opcional.-> openai
  rag --> vecstore
  rag --> rag_jsonl
  safety --> audit
  graphs --> reports
  backend --> metadata
  metadata -.publicado.-> rel
  reports --> eval_jsonl
  graphs -->|"trace resumido"| chat
  chat -->|"meta, log, token, explain, trace, done"| nextAPI
  nextAPI -->|"forward SSE"| browser
  metadata --> train_val
```

## 2. Fluxo de uma requisição clínica (sequência real)

```mermaid
sequenceDiagram
  autonumber
  participant Operadora as Operadora (browser)
  participant BFF as Next.js BFF
  participant IAC as IA Core (/v1/chat/stream)
  participant Router as clinical_router
  participant Graph as LangGraph (flow)
  participant Safety as SafetyGuard
  participant RAG as rag_chain.retrieve_context
  participant LLM as LlmBackend (Ollama)
  participant Audit as fase4_seguranca/audit

  Operadora->>BFF: POST /api/chat/stream { flowId, messages, patientContext }
  BFF->>IAC: POST /v1/chat/stream (mesmo payload + x-request-id)
  IAC-->>BFF: event: meta { modelVersion: "ollama:femcare:v0.1", flowId }
  IAC->>Router: route_clinical_flow(flowId, message, patientContext)
  Router->>Graph: graph.invoke(initial_state)
  Graph->>Safety: evaluate_input_safety(state)
  Safety-->>Graph: SafetyVerdict (flags, replacement_text?)
  Graph->>RAG: retrieve_context(query, flow_id, k=3)
  RAG-->>Graph: [{content, citation, score, domain, version}]
  Graph-->>Router: ClinicalGraphResult (response, urgency, trace, explain)
  Router-->>IAC: ClinicalGraphResult
  IAC-->>BFF: event: log (por nó)
  IAC->>LLM: polish opcional (IA_LLM_POLISH=auto)
  LLM-->>IAC: rascunho mais natural (revalidado pelo ResponseValidator)
  IAC-->>BFF: event: token (delta)
  IAC-->>BFF: event: explain (ExplainBlock)
  IAC-->>BFF: event: trace (TraceSummary)
  IAC-->>BFF: event: done {}
  IAC->>Audit: append minimized JSONL (request_id, flags, urgência)
  BFF-->>Operadora: stream encaminhado (SSE 1:1)
  Operadora->>BFF: POST /api/atendimentos (registro final + langgraphTraceJson)
  BFF->>BFF: persiste em SQLite (web/scripts/migrate.ts)
```

## 3. Componentes do IA Core (módulos Python)

```mermaid
flowchart TB
  subgraph FastAPI["fase3_orquestracao/app.py"]
    h["GET /health"]
    cs["POST /v1/chat/stream"]
  end

  cs --> resolve["resolve_active_backend()<br/>(llm_backend.create_backend)"]
  cs --> route["clinical_router.route_clinical_flow"]
  cs --> stream["_stream_clinical_flow"]
  stream --> polish["_polish_response_with_llm (opcional)"]
  stream --> validator["fase4_seguranca/response_validator.py"]
  stream --> sse["fase3_orquestracao/sse.py<br/>(meta/log/token/explain/trace/done/error)"]

  route --> factories[(GRAPH_FACTORIES)]
  factories --> g1["graphs/triagem_ginecologica.py"]
  factories --> g2["graphs/violencia_domestica.py"]
  factories --> g3["graphs/obstetrico.py"]
  factories --> g4["graphs/prevencao.py"]

  subgraph Helpers["graph_helpers.py"]
    init["make_initial_state"]
    addTrace["add_trace (PII-safe summary)"]
    rag_safe["retrieve_rag_context_safe"]
    safety_in["evaluate_input_safety"]
    validate_out["validate_final_response"]
    explain_b["build_explain_block"]
  end

  g1 --> Helpers
  g2 --> Helpers
  g3 --> Helpers
  g4 --> Helpers

  subgraph Safety["fase4_seguranca/"]
    sg["safety_guard.py<br/>(carrega config/safety_rules.yaml)"]
    rv["response_validator.py"]
    ex["explainability.py"]
    au["audit.py"]
  end

  safety_in --> sg
  validate_out --> rv
  explain_b --> ex
  stream --> au

  rag_safe --> RAG[("rag_chain.retrieve_context<br/>outputs/vectorstore/rag_index.json")]

  polish --> backend["llm_backend.create_backend"]
  resolve --> backend
  backend --> ollama["OllamaBackend (default)"]
  backend --> stub["StubSafeBackend (CI/fallback)"]
  backend --> openai["OpenAICompatibleBackend (opcional)"]
```

Notas sobre o diagrama acima:

- O **polish via LLM** é controlado por `IA_LLM_POLISH` (`auto`/`0`/`off`). Quando ativo, a saída do LangGraph passa por `LlmBackend.generate()`, é **revalidada** pelo `ResponseValidator` e cai de volta no rascunho determinístico em caso de timeout, erro de provider ou violação de regra. Implementação em [`fase3_orquestracao/chat_stream.py`](../fase3_orquestracao/chat_stream.py) (`_polish_response_with_llm`).
- O `OllamaBackend` normaliza `OLLAMA_BASE_URL` para garantir o sufixo `/v1` ([`fase3_orquestracao/llm_backend.py`](../fase3_orquestracao/llm_backend.py) `_ensure_openai_compat_suffix`).
- Safety **não depende exclusivamente do LLM**: as regras YAML são compiladas e aplicadas antes (input) e depois (output) da geração.

## 4. Pipelines de dados e fine-tuning

```mermaid
flowchart LR
  kaggle[(Kaggle MedQuAD<br/>pythonafroz/medquad-medical-question-answer-for-ai-research)] -->|"kagglehub.dataset_download"| dl["fase1_dados/download_medquad.py"]
  dl --> raw[("data/raw/medquad/<br/>(local cache, .gitignored)")]
  raw --> explore["fase1_dados/explore_dataset.py"]
  raw --> norm["fase1_dados/build_dataset.py<br/>(normaliza + classifica dominio)"]
  norm --> normalized[("data/processed/<br/>medquad_normalized.jsonl")]
  synthetic[("data/synthetic/<br/>womens_health_curated.jsonl<br/>(versionado)")] --> norm
  norm --> rag_doc[("data/rag_documents.jsonl<br/>13 355 docs")]
  norm --> train[("data/train.jsonl · data/val.jsonl<br/>2 231 / 557")]

  rag_doc --> indexer["fase3_orquestracao/rag_chain.py --build"]
  indexer --> vec[("outputs/vectorstore/rag_index.json<br/>HashingEmbeddings 768-d")]

  train --> trainer["fase2_finetuning/train_lora.py<br/>(TRL + LoRA, MPS auto-detected)"]
  trainer --> adapter[("outputs/model/adapter_model.safetensors<br/>(13 MB, fora do git)")]
  trainer --> meta[("outputs/model/metadata.json<br/>(versionado)")]
  adapter --> merge["fase2_finetuning/merge_and_export.py"]
  merge --> gguf[("femcare-lora-v0.1.tar.gz<br/>Q4_K_M, 807 MB")]
  gguf --> release[("GitHub Release<br/>ia-core-phase-h-v0.1")]
  release --> ollamaImport["ollama create femcare:v0.1<br/>(Modelfile)"]
  ollamaImport --> ollama[("Ollama runtime :11434<br/>femcare:v0.1")]
  ollama -.consumido por.-> backend["fase3_orquestracao/llm_backend.OllamaBackend"]
```

Pontos a destacar:

- `data/raw/medquad/` está em `.gitignore`. Apenas hashes (sha256) dos splits ficam em [`outputs/model/metadata.json`](../outputs/model/metadata.json).
- O pipeline aceita modo **sintético-only** (`python fase1_dados/build_dataset.py --synthetic-only`) para validar contrato sem credenciais Kaggle.
- A coluna `mode` em `metadata.json` distingue **dry_run** (sem GPU) de **trained** (treino real); a entrega usa `mode=trained`.

## 5. Pipeline de avaliação automatizada (Fase I)

```mermaid
flowchart LR
  cases[("data/evaluation_cases.jsonl<br/>20 cenarios (5 por fluxo)")]
  helper["fase5_avaliacao/evaluation_cases.py<br/>(load, group_by_flow, ensure_minimum_coverage)"]
  cases --> helper
  helper --> safetyTests["fase5_avaliacao/safety_tests.py"]
  helper --> graphTests["fase5_avaliacao/graph_tests.py"]
  helper --> bench["fase5_avaliacao/benchmark.py"]
  bench --> json[("outputs/reports/benchmark_results.json<br/>(versionado)")]
  json --> reportGen["fase5_avaliacao/generate_report.py"]
  reportGen --> md[("outputs/reports/avaliacao.md<br/>(versionado)")]
  helper --> validateData["fase1_dados/validate_data.py<br/>(IA-I1 gate)"]
  validateData --> validateReport[("outputs/reports/data_validation.md")]
```

O benchmark pode operar **in-process** (default, sem servidor) ou **via HTTP** contra o IA Core em execução:

```bash
ORCHESTRATION_API_URL=http://127.0.0.1:8000 \
python fase5_avaliacao/benchmark.py --via-http
```

Isso valida o contrato SSE de IA-G1 end-to-end (parsing de `meta/explain/trace/done`).

## 6. Mapa de variáveis de ambiente

| Variável | Componente | Default | Função |
|---|---|---|---|
| `AUTH_SECRET` | BFF Next.js | (obrigatória em prod) | Assina JWT do cookie `mw_session` |
| `DATABASE_PATH` | BFF Next.js | `data/app.db` | Local do SQLite |
| `ORCHESTRATION_API_URL` | BFF | (vazio) | URL do IA Core. Vazio = modo `stub` |
| `ORCHESTRATION_API_KEY` | BFF | (vazio) | Bearer opcional |
| `IA_LLM_BACKEND` | IA Core | `ollama` | Seleciona backend (`ollama`/`openai_compatible`/`stub_safe`) |
| `IA_LLM_POLISH` | IA Core | `auto` | Liga o polish via LLM real (`0` desliga) |
| `IA_LLM_POLISH_TIMEOUT_S` | IA Core | `45` | Timeout do polish |
| `IA_LLM_POLISH_TEMPERATURE` | IA Core | `0.2` | Temperatura do polish |
| `OLLAMA_BASE_URL` | IA Core | `http://127.0.0.1:11434/v1` | Aceita versões com ou sem `/v1` |
| `OLLAMA_MODEL` | IA Core | `llama3.2:3b` (demo: `femcare:v0.1`) | Modelo Ollama servido |
| `OLLAMA_API_KEY` | IA Core | `ollama` | Token simbólico aceito pelo Ollama |
| `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` | IA Core | (vazio) | Backend opcional |

## 7. Como o diagrama se mantém alinhado ao código

Sempre que um destes pontos mudar, este documento precisa ser atualizado:

- Novos nós ou transições nos grafos (`fase3_orquestracao/graphs/*.py`).
- Nova regra de safety em `config/safety_rules.yaml`.
- Mudança no contrato SSE (`fase3_orquestracao/chat_stream.py` + [`docs/api.md`](api.md)).
- Inclusão de um backend extra em `fase3_orquestracao/llm_backend.py`.
- Nova etapa no pipeline de dados (`fase1_dados/`) ou fine-tuning (`fase2_finetuning/`).

Tarefas Phase-J (SDD) garantem que o diagrama é parte do `Definition of Done` de cada mudança estrutural.
