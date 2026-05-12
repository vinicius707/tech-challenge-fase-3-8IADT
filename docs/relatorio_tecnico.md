# Relatório Técnico - FemCare IA Core (Tech Challenge Fase 3)

Pós-graduação 8IADT - Tech Challenge Fase 3. Este relatório descreve, com **evidências do próprio repositório**, a entrega do *FemCare IA Core*: o backend Python (FastAPI + LangChain + LangGraph), o pipeline de dados de saúde da mulher, o fine-tuning LoRA, os guardrails clínicos, a avaliação automatizada e a integração com a UI Next.js já existente.

Documentos complementares:

- [`CHECKLIST_FASE3.md`](../CHECKLIST_FASE3.md) - mapa rápido de evidências.
- [`docs/diagrama_arquitetura.md`](diagrama_arquitetura.md) - arquitetura final.
- [`docs/diagramas_fluxos.md`](diagramas_fluxos.md) - quatro grafos LangGraph.
- [`docs/roteiro_video.md`](roteiro_video.md) - roteiro de gravação (≤ 15 min).
- [`docs/sdd/ia-core/`](sdd/ia-core/) - pacote SDD (context, spec, design, tasks).
- [`docs/api.md`](api.md) - contrato HTTP BFF ↔ IA Core.

## 1. Visão geral da entrega

O projeto entrega o que o desafio pede: um assistente clínico em saúde da mulher capaz de executar quatro fluxos especializados, com fine-tuning, RAG, LangChain/LangGraph, guardrails, logs/auditoria e UI funcional. O ponto de partida era uma UI Next.js em **modo stub**; a entrega final é uma **stack ponta a ponta**:

1. **UI** Next.js consumindo `POST /api/chat/stream` ([`web/`](../web/)).
2. **BFF** Next.js fazendo proxy SSE para o Python ([`docs/api.md`](api.md)).
3. **IA Core** FastAPI rodando RAG + LangGraph + safety + LLM backend pluggable ([`fase3_orquestracao/`](../fase3_orquestracao/)).
4. **Modelo** servido localmente pelo Ollama (`femcare:v0.1`, LoRA fine-tuned + base merged em Q4_K_M, 807 MB).
5. **Avaliação** automatizada com 20 cenários sintéticos versionados ([`data/evaluation_cases.jsonl`](../data/evaluation_cases.jsonl)).

A entrega foi conduzida em **dez fases SDD** (`A` a `J`), com 18 PRs mergeados em `main` ([histórico de PRs](https://github.com/vinicius707/tech-challenge-fase-3-8IADT/pulls?q=is%3Apr+is%3Aclosed)).

## 2. Arquitetura técnica

Resumo (detalhe completo em [`docs/diagrama_arquitetura.md`](diagrama_arquitetura.md)):

| Camada | Componente | Endpoint / artefato |
|---|---|---|
| Browser | UI Next.js (App Router, React 18, SSE) | `http://127.0.0.1:3000` |
| BFF | Next.js API routes + SQLite (`data/app.db`) | `/api/chat/stream`, `/api/atendimentos`, `/api/auth/login` |
| IA Core | FastAPI + Uvicorn ([`fase3_orquestracao/app.py`](../fase3_orquestracao/app.py)) | `http://127.0.0.1:8000/v1/chat/stream` |
| Roteamento clínico | [`fase3_orquestracao/clinical_router.py`](../fase3_orquestracao/clinical_router.py) | Mapa `flowId → build_graph` |
| LangGraph | [`fase3_orquestracao/graphs/*.py`](../fase3_orquestracao/graphs/) | 4 grafos com 6-8 nós cada |
| RAG | [`fase3_orquestracao/rag_chain.py`](../fase3_orquestracao/rag_chain.py) | `outputs/vectorstore/rag_index.json` |
| Safety | [`fase4_seguranca/*.py`](../fase4_seguranca/) | YAML declarativo em [`config/safety_rules.yaml`](../config/safety_rules.yaml) |
| LLM | [`fase3_orquestracao/llm_backend.py`](../fase3_orquestracao/llm_backend.py) | Ollama (`http://127.0.0.1:11434`) + OpenAI-compatible (opcional) + stub_safe |
| Auditoria | [`fase4_seguranca/audit.py`](../fase4_seguranca/audit.py) | `logs/audit.log` (JSON Lines minimizado) |
| Avaliação | [`fase5_avaliacao/*.py`](../fase5_avaliacao/) | `outputs/reports/avaliacao.md` + `benchmark_results.json` |

Decisões arquiteturais explícitas no [SDD](sdd/ia-core/context.md) §5:

- **D1**: manter Next.js como UI+BFF (sem reescrita).
- **D3**: SSE end-to-end (já era o contrato).
- **D4**: quatro grafos LangGraph separados (rastreabilidade).
- **D7**: `LlmBackend` pluggable (Ollama / OpenAI-compatible / LoRA local).
- **D8**: MedQuAD Kaggle como corpus base.
- **D9**: Ollama local como default (evita custo/risco de chave externa na demo).

## 3. Dados, curadoria e anonimização

### 3.1 Corpus base e curadoria

- Dataset: **MedQuAD** (`pythonafroz/medquad-medical-question-answer-for-ai-research`), baixado via `kagglehub` em [`fase1_dados/download_medquad.py`](../fase1_dados/download_medquad.py).
- Pipeline normaliza para `data/processed/medquad_normalized.jsonl` (16 358 registros após curadoria - veja [`outputs/reports/data_validation.md`](../outputs/reports/data_validation.md)).
- Recorte por domínio:

  | Domínio | Registros |
  |---|---:|
  | `medicinaGeral` | 10 567 |
  | `excluir` | 3 011 |
  | `obstetrico` | 2 026 |
  | `triagemGinecologica` | 349 |
  | `prevencao` | 315 |
  | `violenciaDomestica` | 90 |

- Para complementar lacunas do MedQuAD em **violência doméstica, obstetrícia contextual brasileira e prevenção alinhada ao SUS**, criamos [`data/synthetic/womens_health_curated.jsonl`](../data/synthetic/womens_health_curated.jsonl) (versionado, 8 registros marcados como `source = synthetic_protocol_v1`).
- Pipeline e decisões em [`docs/dados-e-curadoria.md`](dados-e-curadoria.md).

### 3.2 Corpus de RAG e treino

- RAG: [`data/rag_documents.jsonl`](../data/rag_documents.jsonl) (13 355 documentos, todos com `doc_id/domain/source/version/sensitivity/citation`).
- Treino: `data/train.jsonl` (2 231 ex.) e `data/val.jsonl` (557 ex.). Hashes sha256 em [`outputs/model/metadata.json`](../outputs/model/metadata.json) (`train.sha256 = f20844a0…`, `val.sha256 = 3e8bd045…`).
- Distribuição obrigatória: todos os quatro domínios clínicos presentes nos splits.

### 3.3 Gate de validação

Comando:

```bash
python fase1_dados/validate_data.py
```

Saída versionada: [`outputs/reports/data_validation.md`](../outputs/reports/data_validation.md). Estado atual: **PASS, 0 erros, 0 avisos**. O script aplica:

- Schema obrigatório (`question`, `answer`, `domain`, `source`, `citation`).
- Detecção de duplicatas por `id`.
- Validação dos quatro domínios obrigatórios + cobertura mínima.
- Verificação do schema de [`data/evaluation_cases.jsonl`](../data/evaluation_cases.jsonl) (Fase I).

### 3.4 Anonimização e minimização

- **Não há PII real no repositório**. O dataset MedQuAD original não contém pacientes identificados; mesmo assim, mantemos redação simples de emails/telefones em [`fase1_dados/extract_medquad.py`](../fase1_dados/extract_medquad.py) ao gerar amostras de exploração.
- O cache bruto Kaggle nunca é commitado (`data/raw/medquad/*` está no [`.gitignore`](../.gitignore)).
- Registros `sensitivity = high` (violência doméstica) só entram em RAG e nunca em `train.jsonl` sem revisão.
- Logs minimizam violência doméstica: [`fase4_seguranca/audit.py`](../fase4_seguranca/audit.py) (`redact_text`, `audit_summary={"sensitive_redacted": true, "summary": "[REDACTED:sensitive_content]"}`).
- Casos de avaliação são todos **sintéticos** ([`data/evaluation_cases.jsonl`](../data/evaluation_cases.jsonl)).

## 4. Segurança, explainability e auditoria

### 4.1 Guardrails declarativos

[`config/safety_rules.yaml`](../config/safety_rules.yaml) define seis regras P0 com `severity`, `applies_to`, `action`, `safety_flags`, `replacement` e `patterns` (regex compilados em [`fase4_seguranca/safety_guard.py`](../fase4_seguranca/safety_guard.py)):

| Regra | Categoria | Ação | Flags |
|---|---|---|---|
| `prescription_request` | prescrição | `block_with_human_review` | `prescription_blocked`, `human_review_required` |
| `definitive_diagnosis` | diagnóstico | `rewrite_with_uncertainty` | `definitive_diagnosis_blocked`, `human_review_required` |
| `self_harm` | autoagressão | `crisis_escalation` | `self_harm_escalation`, `human_review_required`, `sensitive` |
| `domestic_violence` | violência | `violence_protocol` | `violence_protocol`, `human_review_required`, `sensitive` |
| `obstetric_emergency` | urgência | `urgency_escalation` | `obstetric_emergency`, `urgent_referral`, `human_review_required` |
| `clinical_emergency` | urgência | `urgency_escalation` | `clinical_emergency`, `urgent_referral`, `human_review_required` |

### 4.2 Validação pré-resposta

[`fase4_seguranca/response_validator.py`](../fase4_seguranca/response_validator.py) é chamado em três momentos:

1. **Input guard** (`evaluate_input_safety` em [`fase3_orquestracao/graph_helpers.py`](../fase3_orquestracao/graph_helpers.py)).
2. **Output guard** (`validate_final_response`) ao final de cada grafo.
3. **Polish guard**: quando `IA_LLM_POLISH=auto` (default), o texto reescrito pelo LLM real (Ollama) é **revalidado** antes de virar tokens SSE em [`fase3_orquestracao/chat_stream.py`](../fase3_orquestracao/chat_stream.py) (`_polish_response_with_llm`). Em caso de timeout, erro de provider ou rejeição por regra, voltamos ao texto determinístico do grafo.

### 4.3 Explainability (ExplainBlock)

[`fase4_seguranca/explainability.py`](../fase4_seguranca/explainability.py) gera o `ExplainBlock` com `fonte` (citação RAG), `confianca` (score do retrieval), `lacunas` (sintomas, sinais vitais, histórico) e `raciocinioClinico` (resumo de alto nível, **sem chain-of-thought**). Esse bloco é emitido como evento SSE `explain` e renderizado na UI (painel "Explainability").

### 4.4 Auditoria minimizada (JSON Lines)

[`fase4_seguranca/audit.py`](../fase4_seguranca/audit.py) grava em `logs/audit.log`:

```jsonc
{
  "ts": "2026-05-12T20:21:01Z",
  "request_id": "5ad8c1a8-...",
  "flow_id": "violenciaDomestica",
  "model_version": "ollama:femcare:v0.1",
  "sources_count": 3,
  "safety_flags": ["violence_protocol", "human_review_required", "sensitive"],
  "urgency": "alta",
  "blocked": false,
  "sensitive_redacted": true,
  "duration_ms": 1380
}
```

Para violência doméstica, `sensitive_redacted=true` e o conteúdo textual não é gravado em claro.

## 5. Capacidades clínicas implementadas

Quatro grafos LangGraph reais com **estados explícitos** ([`docs/diagramas_fluxos.md`](diagramas_fluxos.md)):

### 5.1 Triagem ginecológica

7 nós (`collectSymptoms → analyzeRisk → classifyUrgency → suggestExams/emergencyGuidance → initialGuidance → scheduleAppointment → validate`). Detecta dor pélvica, sangramento, corrimento, ciclo irregular; aciona `emergencyGuidance` quando há `alarm_hits("bleeding","pain","self_harm")` ou `clinical_emergency` (dor no peito, AVC, infarto). Não prescreve.

### 5.2 Violência doméstica

7 nós sequenciais. Aplica `replacement_text` do `domestic_violence` com Disque 180, Polícia 190 e Casa da Mulher Brasileira; força `notifySpecializedTeam` e marca `audit_summary.sensitive_redacted=true`. Logs textuais são suprimidos.

### 5.3 Obstétrico

7 nós. Detecta idade gestacional por regex, classifica risco e dispara `emergencia` quando aparecem sangramento intenso, "não sinto mais o bebê", bolsa rota, convulsão ou pressão muito alta. Encaminha à maternidade.

### 5.4 Prevenção

6 nós. Separa **três cenários** antes de gerar resposta: rastreamento de rotina (ex.: preventivo aos 30), investigação por sintoma (ex.: nódulo de mama → não é apenas rastreamento) e alto risco (história familiar/imunossupressão). Bloqueia pedido de anticoncepcional via `prescription_request`.

Cada grafo retorna `final_response`, `urgency`, `safety_flags`, `trace`, `explain` via `ClinicalGraphResult` ([`fase3_orquestracao/clinical_router.py`](../fase3_orquestracao/clinical_router.py)).

## 6. Integração com sistemas hospitalares (simulada)

O desafio pede integração **real ou claramente simulada**. Nossa entrega é simulada e cobre o ciclo completo:

- **Autenticação** local via JWT em cookie `HttpOnly` ([`docs/api.md`](api.md) §Autenticação).
- **Atendimentos persistidos** em SQLite (`data/app.db`) através do BFF (`POST /api/atendimentos`), com schema cobrindo prompt, resposta, classificação, urgência, trace LangGraph (`langgraphTraceJson`) e `requestId`.
- **Listagem clínica** em `/atendimentos`, com filtros por categoria/tipo e destaque visual por gravidade.
- **Detalhe de atendimento** em `/atendimentos/[id]`, mostrando ExplainBlock e trace.
- **Gate profissional FE-SEC-01**: a UI exige confirmação explícita de perfil profissional antes de habilitar o fluxo de violência doméstica.

Não há integração com HIS/PEP reais (fora de escopo do desafio acadêmico, conforme [`docs/sdd/ia-core/context.md`](sdd/ia-core/context.md) §6).

### 6.1 Contrato BFF ↔ IA Core (SSE)

Especificação completa em [`docs/api.md`](api.md). Eventos emitidos pelo IA Core:

```
event: meta     { requestId, flowId, modelVersion: "ollama:femcare:v0.1", urgencia }
event: log      { level, message: "<node> ok", ts }
event: token    { delta: "texto parcial" }
event: explain  { fonte, confianca, lacunas, raciocinioClinico }
event: trace    { flowId, nodes: [{ name, status, summary, safetyFlags }], finalRisk }
event: done     {}
```

Eventos desconhecidos são ignorados pelo BFF (compatibilidade futura).

## 7. Avaliação do modelo

### 7.1 Conjunto de casos versionado

[`data/evaluation_cases.jsonl`](../data/evaluation_cases.jsonl) define **20 casos sintéticos** (5 por fluxo), com `expectations` para safety, RAG, graph e resposta. Cobertura por tag (veja [`outputs/reports/avaliacao.md`](../outputs/reports/avaliacao.md)):

| Tag | Quantidade |
|---|---:|
| `clinical_gap` | 9 |
| `urgency` | 9 |
| `prescription` | 3 |
| `prevention` | 5 |
| `triagem` | 5 |
| `violence` | 5 |
| `obstetric` | 5 |
| `self_harm` | 1 |

### 7.2 Métricas (in_process, backend `stub-safe-0.1.0`)

Fonte: [`outputs/reports/benchmark_results.json`](../outputs/reports/benchmark_results.json) (`generated_at = 2026-05-12T20:21:01Z`).

| Métrica | Valor |
|---|---:|
| Casos totais | 20 |
| Aprovados | 20 |
| Reprovados | 0 |
| Pass rate geral | 100.0% |
| Safety pass rate | 100.0% |
| RAG pass rate | 100.0% |
| LangGraph pass rate | 100.0% |
| Resposta final pass rate | 100.0% |
| Latência média | 2 243.79 ms |
| Latência p95 | 2 904.58 ms |

Latência por fluxo (média):

| Fluxo | Latência média (ms) |
|---|---:|
| `triagemGinecologica` | 2 003.7 |
| `violenciaDomestica` | 1 376.2 |
| `obstetrico` | 2 884.1 |
| `prevencao` | 2 711.2 |

> **Nota:** O benchmark roda offline com `stub_safe` para garantir determinismo e reprodutibilidade do gate. A integração com Ollama é validada separadamente em `python fase5_avaliacao/benchmark.py --via-http`, exercitando o contrato SSE de IA-G1 ponta a ponta.

### 7.3 Bias, equidade e cobertura demográfica

A entrega atual **não inclui análise quantitativa de bias demográfico**. As limitações intencionais:

- O MedQuAD é em inglês e foi traduzido/curado para os domínios de saúde da mulher. Não há rotulagem demográfica de quem fez as perguntas.
- Os casos sintéticos são propositalmente neutros (não incluem etnia, faixa socioeconómica ou comorbidades como variáveis controladas).
- Há cobertura **clínica** dos cenários críticos (prescrição, urgência, violência, autoagressão, alto risco, sintoma versus rastreamento), mas não há cobertura **demográfica** balanceada.

Mitigações implementadas que reduzem risco prático:

- Safety guardrails determinísticos disparam independentemente do tom/estilo do input.
- Encaminhamento humano obrigatório em violência, autoagressão e urgências.
- Resposta nunca depende exclusivamente do LLM (RAG-first + ResponseValidator).

Próximos passos sugeridos: instrumentar `evaluation_cases.jsonl` com tags demográficas e medir taxa de aprovação por subgrupo; rodar análise pareada com diferentes registros linguísticos.

### 7.4 Feedback de especialistas e limitações académicas

A entrega académica **não conduziu painel formal de revisão clínica por ginecologistas/obstetras**. O preparo deixado pronto:

- Conjunto reduzido de cenários revisáveis em [`data/evaluation_cases.jsonl`](../data/evaluation_cases.jsonl).
- Trace resumido e ExplainBlock por execução, prontos para revisão.
- Auditoria minimizada em JSON Lines.

O protocolo recomendado é: 3-5 profissionais avaliam cada caso (correção clínica + adequação ética) e atribuem rótulo binário; o `generate_report.py` pode ser estendido para consolidar essas avaliações.

### 7.5 Reproducibilidade

```bash
python fase1_dados/validate_data.py        # gate de dados
python fase5_avaliacao/safety_tests.py     # safety - regras YAML + casos compartilhados
python fase5_avaliacao/graph_tests.py      # 4 fluxos LangGraph, 5 casos cada
python fase5_avaliacao/benchmark.py        # outputs/reports/benchmark_results.json
python fase5_avaliacao/generate_report.py  # outputs/reports/avaliacao.md
python fase2_finetuning/validate_adapters.py
pytest                                     # suite unitária completa
```

Para o gate de Fase G end-to-end (Ollama servindo `femcare:v0.1`):

```bash
ORCHESTRATION_API_URL=http://127.0.0.1:8000 \
python fase5_avaliacao/benchmark.py --via-http
```

## 8. Fine-tuning LoRA - evidência reprodutível

Documentação completa em [`docs/fine-tuning.md`](fine-tuning.md). Resumo:

- **Modelo base**: `meta-llama/Llama-3.2-1B-Instruct` (acesso liberado para esta entrega).
- **Técnica**: LoRA via `trl.SFTTrainer` (`r=16`, `lora_alpha=32`, `target_modules=[q_proj,k_proj,v_proj,o_proj]`).
- **Hardware**: Apple Silicon M-series, **MPS** detectado automaticamente pelo `train_lora.py` (`detect_device()` → `mps`), sem `bitsandbytes`.
- **Hiperparâmetros**: `epochs=2`, `learning_rate=2e-4`, `batch=1`, `grad_accum=2`, `max_seq_length=512`, `lr_scheduler=cosine`, `bf16=true`, `seed=42`.
- **Resultados versionados** ([`outputs/model/metadata.json`](../outputs/model/metadata.json)):

  | Métrica | Valor |
  |---|---:|
  | `train_loss` | 1.229 |
  | `eval_loss` | 1.192 |
  | `eval_runtime_s` | 233.22 |
  | `train_examples` | 2 231 |
  | `val_examples` | 557 |

- **Distribuição**: adapter publicado como asset do GitHub Release [`ia-core-phase-h-v0.1`](https://github.com/vinicius707/tech-challenge-fase-3-8IADT/releases/tag/ia-core-phase-h-v0.1) (`femcare-lora-v0.1.tar.gz`, 15 MB, sha256 `e29c4908…`).
- **Deploy**: o adapter é mesclado ao base (`fase2_finetuning/merge_and_export.py`), convertido para GGUF Q4_K_M (807 MB) e importado no Ollama como `femcare:v0.1` (veja `docs/fine-tuning.md` §6).
- **Função**: ajuste de **formato e linguagem clínica em português**. Não é a única fonte de raciocínio (RAG + guardrails continuam a ser a "espinha dorsal").
- **Validação**: `python fase2_finetuning/validate_adapters.py` confere paths/hashes e existência do release.

## 9. Limitações e protocolos de segurança explícitos

| Limitação | Como é endereçada |
|---|---|
| Modelo pequeno (Llama-3.2-1B) pode "alucinar" | RAG-first; `ResponseValidator` bloqueia prescrição e diagnóstico definitivo. |
| Polish via LLM real pode falhar (timeout/erro) | Fallback determinístico para o rascunho do LangGraph; logs explicam o motivo. |
| Possível drift se o adapter mudar | Hashes sha256 em `metadata.json` + `validate_adapters.py` antes de cada release. |
| Conteúdo sensível de violência | `audit_summary.sensitive_redacted=true`, `replacement_text` + encaminhamento humano. |
| Cenários fora dos 4 fluxos | Router rejeita `flowId` desconhecido (`ClinicalRouterError`). |
| Saudações vazias / mensagens vazias | `route_clinical_flow` valida `message.strip()`. |
| Decisão clínica final | Disclaimer em todas as respostas; "validação por profissional habilitado" embutida em `defaults.default_disclaimer`. |

Fora de escopo (registrado em [`docs/sdd/ia-core/context.md`](sdd/ia-core/context.md) §6): integração real com prontuário, RBAC hospitalar, acionamento real de SAMU/Disque 180, certificação como software médico.

## 10. Como executar a demo (resumo executivo)

```bash
# 1. Ollama com modelo fine-tuned (ou llama3.2:3b base)
ollama list           # esperado: femcare:v0.1 (~807 MB Q4_K_M)

# 2. IA Core (terminal separado)
IA_LLM_BACKEND=ollama OLLAMA_MODEL=femcare:v0.1 \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
.venv/bin/uvicorn fase3_orquestracao.app:app --port 8000

# 3. BFF / UI Next.js em modo proxy
cd web
npm install && npm run setup:local      # cria SQLite + utilizador demo
ORCHESTRATION_API_URL=http://127.0.0.1:8000 npm run dev

# 4. Conferir
curl -s http://127.0.0.1:8000/health    # {"ok":true,"service":"ia-core","version":"0.1.0"}
curl -s http://127.0.0.1:3000/api/health # {"ok":true,"mode":"proxy"}
```

Acesso: `http://127.0.0.1:3000` (demo `demo@exemplo.org` / `demo12345`). Demo guiada com prints em [`docs/sdd/ia-core/README.md`](sdd/ia-core/README.md).

## 11. Rastreabilidade SDD → requisitos do PDF

| Item do PDF Secretaria (Fase 3) | Onde demonstramos no repositório |
|---|---|
| Código de fine-tuning | [`fase2_finetuning/train_lora.py`](../fase2_finetuning/train_lora.py), [`fase2_finetuning/FemCare_FineTuning_Colab.ipynb`](../fase2_finetuning/FemCare_FineTuning_Colab.ipynb) |
| Integração LangChain | [`fase3_orquestracao/rag_chain.py`](../fase3_orquestracao/rag_chain.py) + [`data/rag_documents.jsonl`](../data/rag_documents.jsonl) |
| Fluxos LangGraph | [`fase3_orquestracao/graphs/*.py`](../fase3_orquestracao/graphs/) + [`docs/diagramas_fluxos.md`](diagramas_fluxos.md) |
| Dataset anonimizado / sintético | [`data/synthetic/womens_health_curated.jsonl`](../data/synthetic/womens_health_curated.jsonl), [`docs/dados-e-curadoria.md`](dados-e-curadoria.md) |
| Módulos de segurança e validação | [`config/safety_rules.yaml`](../config/safety_rules.yaml) + [`fase4_seguranca/*.py`](../fase4_seguranca/) |
| Relatório técnico | este documento |
| Diagramas dos quatro fluxos | [`docs/diagramas_fluxos.md`](diagramas_fluxos.md) |
| Vídeo até 15 min | [`docs/roteiro_video.md`](roteiro_video.md) |
| Métricas | [`outputs/reports/avaliacao.md`](../outputs/reports/avaliacao.md) |
| Logs e validação | [`logs/audit.log`](../logs/.gitkeep) (run-time) + UI painel Logs |

## 12. Próximos passos sugeridos

1. **Painel real de especialistas** com pelo menos 30 casos avaliados (Cohen κ entre revisores).
2. **Métrica de bias** instrumentando `evaluation_cases.jsonl` com variáveis demográficas e medindo discrepâncias.
3. **Tracing distribuído** (OpenTelemetry) entre BFF e IA Core para correlacionar `x-request-id` com tempos de cada nó.
4. **Estresse de latência** com Ollama em modelo maior (8B) versus o atual 1B fine-tuned, comparando qualidade vs. tempo.
5. **Re-treino periódico** do LoRA quando o corpus curado ganhar revisão clínica supervisionada.

## 13. Créditos e licenças

- Dataset **MedQuAD**: ver Kaggle (`pythonafroz/medquad-medical-question-answer-for-ai-research`) e licenças associadas. Não redistribuímos o corpus bruto.
- Modelo base: **Llama-3.2-1B-Instruct** (Meta). Consulte o model card no Hugging Face Hub.
- Ferramentas: FastAPI, LangChain, LangGraph, TRL/PEFT, Next.js, better-sqlite3, Ollama.
- Equipe acadêmica: 8IADT - Tech Challenge Fase 3.
