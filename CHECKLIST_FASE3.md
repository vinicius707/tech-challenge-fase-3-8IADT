# Checklist Fase 3 - Tech Challenge 8IADT (FemCare IA Core)

Documento de entrega académica. Cada linha aponta o requisito (PDF Secretaria + specs SDD), o estado atual no repositório e onde está a evidência reproduzível. Use este checklist como índice da auditoria.

- Branch da entrega: `main` (todas as fases A-J mergeadas; ver [PRs #1 a #18 no GitHub](https://github.com/vinicius707/tech-challenge-fase-3-8IADT/pulls?q=is%3Apr+is%3Aclosed)).
- Roteiro de demonstração: [`docs/roteiro_video.md`](docs/roteiro_video.md).
- Relatório técnico detalhado: [`docs/relatorio_tecnico.md`](docs/relatorio_tecnico.md).
- Diagrama de arquitetura final: [`docs/diagrama_arquitetura.md`](docs/diagrama_arquitetura.md).
- Diagramas dos quatro fluxos LangGraph: [`docs/diagramas_fluxos.md`](docs/diagramas_fluxos.md).

## 1. Repositório Git (entregáveis obrigatórios do PDF p. 7)

| Requisito do PDF | Status | Evidência | Comando para reproduzir |
|---|---|---|---|
| Pipeline de **fine-tuning** para saúde da mulher | Pronto | [`fase2_finetuning/train_lora.py`](fase2_finetuning/train_lora.py), [`fase2_finetuning/FemCare_FineTuning_Colab.ipynb`](fase2_finetuning/FemCare_FineTuning_Colab.ipynb), [`outputs/model/metadata.json`](outputs/model/metadata.json) (`mode=trained`, `train_loss=1.229`, `eval_loss=1.192`, base `meta-llama/Llama-3.2-1B-Instruct`) | `python fase2_finetuning/train_lora.py --dry-run` ou treino real em Apple Silicon descrito em [`docs/fine-tuning.md`](docs/fine-tuning.md) §2.3 |
| Integração **LangChain** especializada (RAG sobre corpus curado) | Pronto | [`fase3_orquestracao/rag_chain.py`](fase3_orquestracao/rag_chain.py), [`data/rag_documents.jsonl`](data/rag_documents.jsonl) (13 355 docs com `domain/source/version/sensitivity/citation`), [`outputs/vectorstore/rag_index.json`](outputs/vectorstore/) | `python fase3_orquestracao/rag_chain.py --build` |
| Quatro fluxos **LangGraph** clínicos | Pronto | [`fase3_orquestracao/graphs/triagem_ginecologica.py`](fase3_orquestracao/graphs/triagem_ginecologica.py), [`fase3_orquestracao/graphs/violencia_domestica.py`](fase3_orquestracao/graphs/violencia_domestica.py), [`fase3_orquestracao/graphs/obstetrico.py`](fase3_orquestracao/graphs/obstetrico.py), [`fase3_orquestracao/graphs/prevencao.py`](fase3_orquestracao/graphs/prevencao.py), router em [`fase3_orquestracao/clinical_router.py`](fase3_orquestracao/clinical_router.py) | `python fase5_avaliacao/graph_tests.py` (executa os quatro fluxos com casos reais) |
| **Dataset** anonimizado / sintético + instruções de uso | Pronto | [`data/synthetic/womens_health_curated.jsonl`](data/synthetic/womens_health_curated.jsonl) versionado; pipeline MedQuAD em [`fase1_dados/`](fase1_dados/); curadoria em [`docs/dados-e-curadoria.md`](docs/dados-e-curadoria.md); relatório em [`outputs/reports/data_validation.md`](outputs/reports/data_validation.md) | `python fase1_dados/download_medquad.py && python fase1_dados/build_dataset.py && python fase1_dados/validate_data.py` |
| Módulos de **segurança e validação** (guardrails / logs) | Pronto | [`config/safety_rules.yaml`](config/safety_rules.yaml), [`fase4_seguranca/safety_guard.py`](fase4_seguranca/safety_guard.py), [`fase4_seguranca/response_validator.py`](fase4_seguranca/response_validator.py), [`fase4_seguranca/explainability.py`](fase4_seguranca/explainability.py), [`fase4_seguranca/audit.py`](fase4_seguranca/audit.py) | `python fase5_avaliacao/safety_tests.py` |

## 2. Mapeamento das tasks SDD da IA Core

Origem: [`docs/sdd/ia-core/tasks.md`](docs/sdd/ia-core/tasks.md). Evidência principal por fase a seguir; o relatório técnico expande cada ponto.

### Fase A - Estrutura Python

| ID | Status | Evidência | Gate executado |
|---|---|---|---|
| IA-A1 | OK | Pastas `fase1_dados/`, `fase2_finetuning/`, `fase3_orquestracao/`, `fase4_seguranca/`, `fase5_avaliacao/`, `data/`, `outputs/`, `logs/`, `config/` versionadas | `find . -maxdepth 2 -type d` |
| IA-A2 | OK | [`requirements.txt`](requirements.txt) e [`requirements-finetuning.txt`](requirements-finetuning.txt) | `python -m pip install -r requirements.txt` |
| IA-A3 | OK | [`fase3_orquestracao/app.py`](fase3_orquestracao/app.py) com `GET /health` | `uvicorn fase3_orquestracao.app:app --reload --port 8000` + `curl :8000/health` |
| IA-A4 | OK | [`fase3_orquestracao/sse.py`](fase3_orquestracao/sse.py) | `pytest tests/test_sse.py` |
| IA-A5 | OK | [`fase3_orquestracao/schemas.py`](fase3_orquestracao/schemas.py) | `pytest tests/test_schemas.py` |

### Fase B - Dados (MedQuAD + curadoria)

| ID | Status | Evidência | Gate executado |
|---|---|---|---|
| IA-B1 | OK | [`fase1_dados/download_medquad.py`](fase1_dados/download_medquad.py) usa `kagglehub.dataset_download("pythonafroz/medquad-medical-question-answer-for-ai-research")` | `python fase1_dados/download_medquad.py` |
| IA-B2 | OK | [`fase1_dados/explore_dataset.py`](fase1_dados/explore_dataset.py) | `python fase1_dados/explore_dataset.py` |
| IA-B3 | OK | [`fase1_dados/build_dataset.py`](fase1_dados/build_dataset.py) gera `data/processed/medquad_normalized.jsonl` (16 358 registros) | `python fase1_dados/build_dataset.py` |
| IA-B4 | OK | Recorte por domínio em [`outputs/reports/data_validation.md`](outputs/reports/data_validation.md) (`obstetrico`, `prevencao`, `triagemGinecologica`, `violenciaDomestica`, `medicinaGeral`, `excluir`) | Validação registra distribuição |
| IA-B5 | OK | [`data/synthetic/womens_health_curated.jsonl`](data/synthetic/womens_health_curated.jsonl) (8 registros) preenche lacunas | Inspeção manual |
| IA-B6 | OK | `data/rag_documents.jsonl` (13 355 docs) com `doc_id/domain/source/version/sensitivity/citation` | `python fase1_dados/validate_data.py` |
| IA-B7 | OK | `data/train.jsonl` (2 231) e `data/val.jsonl` (557) com sha256 em [`outputs/model/metadata.json`](outputs/model/metadata.json) | `python fase1_dados/build_dataset.py` |
| IA-B8 | OK | [`fase1_dados/validate_data.py`](fase1_dados/validate_data.py); status `PASS` em [`outputs/reports/data_validation.md`](outputs/reports/data_validation.md) | `python fase1_dados/validate_data.py` |
| IA-B9 | OK | [`docs/dados-e-curadoria.md`](docs/dados-e-curadoria.md) cita URL, slug Kaggle, licença e limitações | Revisão documental |

### Fase C - RAG com LangChain

| ID | Status | Evidência | Gate executado |
|---|---|---|---|
| IA-C1 | OK | Loader em [`fase3_orquestracao/rag_chain.py`](fase3_orquestracao/rag_chain.py) (`load_rag_documents`) | `pytest tests/test_rag_chain.py` |
| IA-C2 | OK | Vector store determinístico em `outputs/vectorstore/rag_index.json` | `python fase3_orquestracao/rag_chain.py --build` |
| IA-C3 | OK | `retrieve_context(query, flow_id, k)` retorna fonte/score/trecho | `python fase5_avaliacao/rag_tests.py` |
| IA-C4 | OK | [`fase5_avaliacao/rag_tests.py`](fase5_avaliacao/rag_tests.py) cobre os quatro domínios | `python fase5_avaliacao/rag_tests.py` |

### Fase D - LLM Backend

| ID | Status | Evidência | Gate executado |
|---|---|---|---|
| IA-D1 | OK | Interface `LlmBackend` em [`fase3_orquestracao/llm_backend.py`](fase3_orquestracao/llm_backend.py) | `pytest tests/test_llm_backend.py` |
| IA-D2 | OK | `OllamaBackend` padrão; `OLLAMA_BASE_URL` aceita `http://host:11434` e `http://host:11434/v1` (normalização automática). [`config/model_backends.yaml`](config/model_backends.yaml) | `ollama list && curl -s http://127.0.0.1:8000/v1/chat/stream ...` |
| IA-D3 | OK | Backend `openai_compatible` parametrizável | Teste documentado em [`docs/llm-backends.md`](docs/llm-backends.md) |
| IA-D4 | OK | LoRA fine-tuned é servido via Ollama como `femcare:v0.1` (slot `local_lora` documentado) | `ollama list` e `metadata.json` |

### Fase E - Safety, Explainability e Auditoria

| ID | Status | Evidência | Gate executado |
|---|---|---|---|
| IA-E1 | OK | [`config/safety_rules.yaml`](config/safety_rules.yaml) com `prescription_request`, `definitive_diagnosis`, `self_harm`, `domestic_violence`, `obstetric_emergency`, `clinical_emergency` | Revisão documental |
| IA-E2 | OK | [`fase4_seguranca/safety_guard.py`](fase4_seguranca/safety_guard.py) compila regras YAML e produz `SafetyVerdict` | `python fase5_avaliacao/safety_tests.py` |
| IA-E3 | OK | [`fase4_seguranca/response_validator.py`](fase4_seguranca/response_validator.py) bloqueia/rewrite saídas proibidas | `pytest tests/test_response_validator.py` |
| IA-E4 | OK | [`fase4_seguranca/explainability.py`](fase4_seguranca/explainability.py) monta `ExplainBlock` com `fonte/confianca/lacunas/raciocinioClinico` | `pytest tests/test_explainability.py` |
| IA-E5 | OK | [`fase4_seguranca/audit.py`](fase4_seguranca/audit.py) grava `logs/audit.log` em JSON Lines minimizado | `pytest tests/test_audit.py` |

### Fase F - LangGraph clínico

| ID | Status | Evidência | Gate executado |
|---|---|---|---|
| IA-F1 | OK | [`fase3_orquestracao/graph_helpers.py`](fase3_orquestracao/graph_helpers.py) (estado tipado, trace seguro) | `pytest tests/test_graph_helpers.py` |
| IA-F2 | OK | Grafo `triagemGinecologica` com 7 estados + `validate` | `python fase5_avaliacao/graph_tests.py --flow triagemGinecologica` |
| IA-F3 | OK | Grafo `violenciaDomestica` minimiza logs e força encaminhamento humano | `python fase5_avaliacao/graph_tests.py --flow violenciaDomestica` |
| IA-F4 | OK | Grafo `obstetrico` detecta red flags (sangramento, bolsa rota, redução de movimentos) | `python fase5_avaliacao/graph_tests.py --flow obstetrico` |
| IA-F5 | OK | Grafo `prevencao` separa rastreamento de rotina, sintoma e alto risco | `python fase5_avaliacao/graph_tests.py --flow prevencao` |
| IA-F6 | OK | [`fase3_orquestracao/clinical_router.py`](fase3_orquestracao/clinical_router.py) roteia por `flowId` | `python fase5_avaliacao/graph_tests.py` |

### Fase G - Serviço Python SSE e integração com BFF

| ID | Status | Evidência | Gate executado |
|---|---|---|---|
| IA-G1 | OK | `POST /v1/chat/stream` em [`fase3_orquestracao/chat_stream.py`](fase3_orquestracao/chat_stream.py) emite `meta/log/token/explain/trace/done/error` | `uvicorn fase3_orquestracao.app:app --port 8000` + `curl -N http://127.0.0.1:8000/v1/chat/stream ...` |
| IA-G2 | OK | `modelVersion` real `ollama:femcare:v0.1`; nunca `stub-0.1.0` na demo principal | Painel de logs do BFF (print `04-prevencao-final.png`) |
| IA-G3 | OK | Evento `trace` enviado com snapshot dos nodes | `pytest tests/test_chat_stream.py::test_trace_event_emitted` |
| IA-G4 | OK | Frontend captura/persistente `langgraphTraceJson` em `POST /api/atendimentos` | Detail page `/atendimentos/[id]` mostra trace |
| IA-G5 | OK | UI em modo proxy (`mode:"proxy"` em `/api/health`) com `ORCHESTRATION_API_URL=http://127.0.0.1:8000` | Prints em [`docs/sdd/ia-core/README.md`](docs/sdd/ia-core/README.md) §Demo guiada |

### Fase H - Fine-tuning real

| ID | Status | Evidência | Gate executado |
|---|---|---|---|
| IA-H1 | OK | [`fase2_finetuning/FemCare_FineTuning_Colab.ipynb`](fase2_finetuning/FemCare_FineTuning_Colab.ipynb) referencia `train.jsonl`/`val.jsonl` + MedQuAD/Kaggle | Revisão do notebook |
| IA-H2 | OK | [`fase2_finetuning/train_lora.py`](fase2_finetuning/train_lora.py) (TRL + LoRA, Apple Silicon MPS detectado automaticamente) | `python fase2_finetuning/train_lora.py --dry-run` |
| IA-H3 | OK | [`outputs/model/metadata.json`](outputs/model/metadata.json) versionado (`mode=trained`, sha256 de splits, adapter e GGUF) | Inspeção |
| IA-H4 | OK | [`fase2_finetuning/validate_adapters.py`](fase2_finetuning/validate_adapters.py) | `python fase2_finetuning/validate_adapters.py` |
| IA-H5 | OK | [`docs/fine-tuning.md`](docs/fine-tuning.md) descreve release [`ia-core-phase-h-v0.1`](https://github.com/vinicius707/tech-challenge-fase-3-8IADT/releases/tag/ia-core-phase-h-v0.1) + import GGUF Q4_K_M no Ollama (`femcare:v0.1`) | Revisão e `ollama list` |

### Fase I - Avaliação automatizada

| ID | Status | Evidência | Gate executado |
|---|---|---|---|
| IA-I1 | OK | [`data/evaluation_cases.jsonl`](data/evaluation_cases.jsonl) (20 casos versionados, 5 por fluxo) | `python fase1_dados/validate_data.py` valida schema/cobertura |
| IA-I2 | OK | [`fase5_avaliacao/safety_tests.py`](fase5_avaliacao/safety_tests.py) consumindo casos comuns | `python fase5_avaliacao/safety_tests.py` |
| IA-I3 | OK | [`fase5_avaliacao/graph_tests.py`](fase5_avaliacao/graph_tests.py) executa 4 fluxos por padrão | `python fase5_avaliacao/graph_tests.py` |
| IA-I4 | OK | [`fase5_avaliacao/benchmark.py`](fase5_avaliacao/benchmark.py) + saída [`outputs/reports/benchmark_results.json`](outputs/reports/benchmark_results.json) (latência média 2 244 ms, p95 2 905 ms, pass-rate 100%) | `python fase5_avaliacao/benchmark.py` (e opcional `--via-http`) |
| IA-I5 | OK | [`fase5_avaliacao/generate_report.py`](fase5_avaliacao/generate_report.py) gera [`outputs/reports/avaliacao.md`](outputs/reports/avaliacao.md) | `python fase5_avaliacao/generate_report.py` |

### Fase J - Documentação e vídeo

| ID | Status | Evidência | Gate executado |
|---|---|---|---|
| IA-J1 | OK | Este `CHECKLIST_FASE3.md` | Revisão de links/IDs |
| IA-J2 | OK | [`docs/relatorio_tecnico.md`](docs/relatorio_tecnico.md) | Revisão acadêmica |
| IA-J3 | OK | [`docs/diagrama_arquitetura.md`](docs/diagrama_arquitetura.md) | Diagrama Mermaid reflete código atual |
| IA-J4 | OK | [`docs/diagramas_fluxos.md`](docs/diagramas_fluxos.md) | Quatro diagramas Mermaid alinhados ao código |
| IA-J5 | OK | [`docs/roteiro_video.md`](docs/roteiro_video.md) (15 min) | Ensaio + cobertura UI / IA Core / RAG / LangGraph / safety / avaliação |

## 3. Relatório técnico (PDF p. 7)

| Item exigido | Status | Onde está | Comando para reproduzir evidência |
|---|---|---|---|
| Metodologia de curadoria | OK | [`docs/relatorio_tecnico.md` §3](docs/relatorio_tecnico.md#3-dados-curadoria-e-anonimizacao); [`docs/dados-e-curadoria.md`](docs/dados-e-curadoria.md) | `python fase1_dados/build_dataset.py && python fase1_dados/validate_data.py` |
| Técnicas de anonimização | OK | [`docs/relatorio_tecnico.md` §3.4](docs/relatorio_tecnico.md#34-anonimizacao-e-minimizacao); regex de emails/telefones em [`fase1_dados/extract_medquad.py`](fase1_dados/extract_medquad.py); redação em [`fase4_seguranca/audit.py`](fase4_seguranca/audit.py) | Inspeção + `python fase5_avaliacao/safety_tests.py` |
| Métricas para domínio médico feminino | OK | [`docs/relatorio_tecnico.md` §7](docs/relatorio_tecnico.md#7-avaliacao-do-modelo) com base em [`outputs/reports/avaliacao.md`](outputs/reports/avaliacao.md) | `python fase5_avaliacao/benchmark.py && python fase5_avaliacao/generate_report.py` |
| Validação por especialistas (processo) | Limitação documentada | [`docs/relatorio_tecnico.md` §7.4](docs/relatorio_tecnico.md#74-feedback-de-especialistas-e-limitacoes-academicas) - protocolo preparado, painel de revisão não conduzido nesta entrega académica | n/a |
| Capacidades específicas e limitações | OK | [`docs/relatorio_tecnico.md` §5](docs/relatorio_tecnico.md#5-capacidades-clinicas-implementadas) e §8 | Demo + relatório |
| Integração com sistemas hospitalares | OK (simulada) | [`docs/relatorio_tecnico.md` §6](docs/relatorio_tecnico.md#6-integracao-com-sistemas-hospitalares-simulada) - BFF Next.js, SQLite, SSE | `cd web && npm run dev` |
| Diagramas dos quatro fluxos | OK | [`docs/diagramas_fluxos.md`](docs/diagramas_fluxos.md) | Render Mermaid |
| Análise de bias e equidade demográfica | OK (limitação) | [`docs/relatorio_tecnico.md` §7.3](docs/relatorio_tecnico.md#73-bias-equidade-e-cobertura-demografica) | n/a |
| Avaliação de segurança e ética | OK | [`docs/relatorio_tecnico.md` §4](docs/relatorio_tecnico.md#4-seguranca-explainability-e-auditoria) e [`outputs/reports/avaliacao.md`](outputs/reports/avaliacao.md) | `python fase5_avaliacao/safety_tests.py` |

## 4. Vídeo (PDF p. 8, até 15 min)

Roteiro completo em [`docs/roteiro_video.md`](docs/roteiro_video.md). Checagem dos itens obrigatórios:

| Item do PDF | Coberto no roteiro? | Onde aparece |
|---|---|---|
| Treinamento e funcionamento da LLM personalizada | Sim | Cenas 2 e 3 (terminal `ollama list`, `metadata.json` aberto, recap do `train_lora.py`) |
| Execução de **um** fluxo automatizado (LangGraph) | Sim | Cena 4 (prevenção end-to-end) + cena 5 (gate de violência doméstica) |
| Perguntas clínicas contextualizadas | Sim | Cena 4: `patientContext` rica em JSON usada na UI |
| Logs e validação | Sim | Cena 4 (painel Explainability + Logs com `x-request-id` e `trace`), cena 6 (`outputs/reports/avaliacao.md`) |
| Duração ≤ 15 minutos | Sim | Resumo de cronômetro: 0:00 → 14:30 com 0:30 de margem |

## 5. Gates finais executados nesta entrega

```bash
python fase1_dados/validate_data.py        # outputs/reports/data_validation.md PASS
python fase5_avaliacao/safety_tests.py     # 20 cenarios da Fase E + casos da Fase I
python fase5_avaliacao/graph_tests.py      # 4 fluxos, 5 casos cada, todos PASS
python fase5_avaliacao/benchmark.py        # outputs/reports/benchmark_results.json
python fase5_avaliacao/generate_report.py  # outputs/reports/avaliacao.md
python fase2_finetuning/validate_adapters.py
python fase3_orquestracao/rag_chain.py --build
pytest                                     # suite completa (Fases A-I)
cd web && npm run lint && npm run build
```

Comando único de auditoria contínua (a executar antes do vídeo):

```bash
make -n   # nao usamos Makefile; comandos individuais acima formam o gate final
```

Última execução versionada do gate de avaliação: `outputs/reports/benchmark_results.json` (`generated_at: 2026-05-12T20:21:01Z`, `pass_rate: 1.0`).

## 6. Onde está cada coisa - mapa rápido

```text
.
├── CHECKLIST_FASE3.md            <- este documento
├── README.md                     <- visão alto nível
├── config/                       <- safety_rules.yaml + model_backends.yaml
├── data/
│   ├── evaluation_cases.jsonl    <- 20 cenários (versionados)
│   ├── synthetic/                <- corpus curado (versionado)
│   └── (raw/processed/rag/train/val são gerados localmente)
├── docs/
│   ├── api.md                    <- contrato HTTP BFF <-> IA Core
│   ├── dados-e-curadoria.md      <- fontes Fase B
│   ├── diagrama_arquitetura.md   <- IA-J3
│   ├── diagramas_fluxos.md       <- IA-J4
│   ├── fine-tuning.md            <- Fase H ponta a ponta
│   ├── llm-backends.md           <- Fase D + polish LLM
│   ├── relatorio_tecnico.md      <- IA-J2
│   ├── roteiro_video.md          <- IA-J5
│   └── sdd/ia-core/              <- specs e demo com prints
├── fase1_dados/                  <- Fase B
├── fase2_finetuning/             <- Fase H
├── fase3_orquestracao/           <- Fases A, C, D, F, G
├── fase4_seguranca/              <- Fase E
├── fase5_avaliacao/              <- Fase I
├── outputs/
│   ├── model/metadata.json       <- evidência Fase H (versionada)
│   └── reports/                  <- data_validation.md, avaliacao.md, benchmark_results.json (versionados)
└── web/                          <- BFF / UI Next.js (proxy para IA Core)
```

## 7. Como o avaliador roda tudo em 5 minutos

```bash
# 1. clonar e instalar
git clone https://github.com/vinicius707/tech-challenge-fase-3-8IADT.git
cd tech-challenge-fase-3-8IADT
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. (opcional) baixar adapter LoRA + importar femcare:v0.1 no Ollama
# ver docs/fine-tuning.md §6 (download via GitHub Release + GGUF + Modelfile)

# 3. subir IA Core
IA_LLM_BACKEND=ollama OLLAMA_MODEL=femcare:v0.1 \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
.venv/bin/uvicorn fase3_orquestracao.app:app --port 8000

# 4. subir BFF em modo proxy (outra aba)
cd web && npm install && npm run setup:local
ORCHESTRATION_API_URL=http://127.0.0.1:8000 npm run dev

# 5. abrir http://127.0.0.1:3000 e seguir o roteiro de docs/roteiro_video.md
```

Caso o avaliador não tenha o adapter LoRA, basta omitir o passo 2 e usar o `OLLAMA_MODEL=llama3.2:3b` padrão (mantém a arquitetura, troca apenas a "voz" do modelo).
