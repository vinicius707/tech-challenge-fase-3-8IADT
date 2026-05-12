# SDD — IA Core

Este pacote de especificações transforma as lacunas de `LACUNAS_IMPLEMENTACAO_TECH_CHALLENGE_FASE3.md` num fluxo SDD implementável e serve, neste documento, como **guia operacional de demo** para o IA Core já entregue.

## Arquivos do pacote SDD

- [`context.md`](./context.md) — contexto, decisões, escopo, restrições.
- [`spec.md`](./spec.md) — requisitos funcionais, histórias, critérios testáveis, rastreabilidade.
- [`design.md`](./design.md) — arquitetura técnica, contratos, schemas, fluxos, integração com o BFF existente.
- [`tasks.md`](./tasks.md) — backlog por fases, dependências, gates de validação.

Uso recomendado das specs: ler na ordem **context → spec → design → tasks**, e executar `tasks.md` fase a fase, sem pular gates.

## Escopo principal já implementado

- Pipeline de dados de saúde da mulher (Fase B).
- RAG com LangChain sobre fontes curadas (Fase C).
- Camada `LlmBackend` pluggable com Ollama como default (Fase D).
- Guardrails clínicos, validação de resposta, explainability e auditoria minimizada (Fase E).
- Quatro fluxos LangGraph reais — triagem, violência, obstétrico, prevenção (Fase F).
- Endpoint `POST /v1/chat/stream` (SSE) integrado ao BFF Next.js (Fase G).
- Fine-tuning LoRA real do Llama-3.2-1B servido como `femcare:v0.1` via Ollama (Fase H).

## Stack da demo

| Camada | Componente | Endpoint |
|---|---|---|
| Modelo | Ollama servindo `femcare:v0.1` (LoRA + base merged, Q4_K_M, 807 MB) | `http://127.0.0.1:11434/v1` |
| IA Core | FastAPI + LangGraph + Safety + RAG | `http://127.0.0.1:8000/v1/chat/stream` |
| BFF / UI | Next.js (App Router) em modo `proxy` | `http://127.0.0.1:3000` |

## Subindo a demo em três terminais

> Pré-requisitos: Python 3.12 com `.venv` instalada (`requirements.txt`), Node 20+, Ollama instalado, e o release [`ia-core-phase-h-v0.1`](https://github.com/vinicius707/tech-challenge-fase-3-8IADT/releases/tag/ia-core-phase-h-v0.1) baixado conforme `docs/fine-tuning.md` §4.2 e §6.

### Terminal 1 — Ollama com o modelo fine-tuned

```bash
# se ainda nao importou o femcare:v0.1, siga docs/fine-tuning.md §6.2 e §6.3
ollama list             # esperado: femcare:v0.1 (~807 MB, Q4_K_M)
```

### Terminal 2 — IA Core (Python)

```bash
IA_LLM_BACKEND=ollama \
OLLAMA_MODEL=femcare:v0.1 \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
OLLAMA_API_KEY=ollama \
.venv/bin/uvicorn fase3_orquestracao.app:app --port 8000
```

> A partir desta entrega o IA Core aceita tanto `http://127.0.0.1:11434` quanto `http://127.0.0.1:11434/v1` em `OLLAMA_BASE_URL` — o sufixo `/v1` é anexado automaticamente quando ausente. Se preferir desativar o polish via LLM (uso somente do rascunho determinístico) defina `IA_LLM_POLISH=0`; consulte `docs/llm-backends.md` para todos os parâmetros (`IA_LLM_POLISH_TIMEOUT_S`, `IA_LLM_POLISH_TEMPERATURE`).

Verifique:

```bash
curl -s http://127.0.0.1:8000/health
# {"ok":true,"service":"ia-core","version":"0.1.0"}
```

### Terminal 3 — BFF / UI Next.js em modo proxy

```bash
cd web
npm install
npm run setup:local     # migrate + seed (credenciais demo: demo@exemplo.org / demo12345)
ORCHESTRATION_API_URL=http://127.0.0.1:8000 npm run dev
```

Verifique:

```bash
curl -s http://127.0.0.1:3000/api/health
# {"ok":true,"mode":"proxy"}    # se aparecer "stub", a env nao foi lida
```

Abra `http://127.0.0.1:3000` e siga a jornada documentada abaixo.

## Demo guiada com evidências

Todos os prints foram capturados nesta entrega com `femcare:v0.1` servindo o tráfego (`modelVersion: "ollama:femcare:v0.1"` no SSE).

### Passo 1 — Login com utilizador de seed

Após `npm run setup:local`, o banco SQLite traz o utilizador demo `demo@exemplo.org` / `demo12345`. A página de login (`/login`) faz POST para `/api/auth/login` e grava o cookie `mw_session` (JWT HS256).

![Tela de login do BFF Next.js](./assets/01-login.png)

### Passo 2 — Tela de novo atendimento (proxy ativo)

`/atendimentos/novo` mostra o disclaimer clínico, o seletor de fluxo LangGraph (FE-INT-02), área de mensagem, contexto livre, painel de **Explainability** e **Logs**. Quando o `/api/health` retorna `mode:"proxy"`, a UI direciona o stream para o IA Core na 8000 — todas as respostas que aparecem aqui vêm do modelo real.

![Novo atendimento com seletor de fluxo](./assets/02-assistente-novo-atendimento.png)

### Passo 3 — Streaming SSE no fluxo de prevenção

Selecionando o chip **Prevenção / rastreamento** e enviando uma pergunta clínica curta, a UI recebe a sequência de eventos prevista no contrato da Fase G:

```
event: meta     → { modelVersion: "ollama:femcare:v0.1", flowId, urgencia }
event: log      → um por node do LangGraph (loadPatientHistory, identifyDueExams, …)
event: token    → streaming incremental da resposta
event: explain  → fonte, confiança, lacunas, raciocínio de alto nível
event: trace    → snapshot dos nodes do grafo com status
event: done
```

O print abaixo foi tirado **durante** o streaming — repare no botão **Cancelar** habilitado, e nos logs já contendo as marcações `info` dos nodes que rodaram antes do primeiro token:

![Streaming SSE em andamento no fluxo prevenção](./assets/03-prevencao-streaming.png)

### Passo 4 — Estado final com explainability e trace

Quando o stream termina (ou é interrompido pelo utilizador), o painel **Explainability** é preenchido com a `fonte` (Protocolo prevenção 2026), o nível de **confiança**, a lista de **lacunas** (sem resumo clínico, sem histórico de exames, sem sinais vitais) e o **raciocínio clínico** em alto nível (sem chain-of-thought). O painel de **Logs** mostra `x-request-id` e o evento `trace` com a lista dos nodes do grafo (`loadPatientHistory → identifyDueExams → preventiveGuidance → autoSchedulePrevention → personalizedReminders → validate`, todos `ok` neste caso).

![Estado final com explainability e logs do LangGraph](./assets/04-prevencao-final.png)

### Passo 5 — Gate de identidade no fluxo de violência doméstica

Selecionar o chip **Violência doméstica** ativa o gate FE-SEC-01 / RF-SEC-02: o envio fica bloqueado até confirmação explícita de perfil profissional. Esse fluxo também minimiza logs e força encaminhamento humano, conforme `config/safety_rules.yaml` (regra `violence_escalation`) e o grafo `fase3_orquestracao/graphs/violencia_domestica.py`.

![Gate de profissional habilitado no fluxo de violência doméstica](./assets/05-violencia-gate-profissional.png)

## Como regenerar os prints

A captura é automatizada com Playwright. Mantenha os três terminais da seção anterior rodando e execute, na raiz do repo:

```bash
# 1. instalar playwright sob web/node_modules (nao versionado)
cd web && npm install --no-save playwright && npx playwright install chromium

# 2. rodar o script de captura (gera/atualiza docs/sdd/ia-core/assets/*.png)
cd ..
node .tools/capture-demo.mjs
```

O script vive em `.tools/capture-demo.mjs` (diretório ignorado pelo Git, junto com outras ferramentas locais). Variáveis úteis:

- `DEMO_BASE_URL` — default `http://127.0.0.1:3000`.
- `DEMO_EMAIL` / `DEMO_PASSWORD` — defaults batem com o seed.

## Evidências relacionadas em outras pastas

- `docs/api.md` — contrato SSE completo (entrada do BFF + eventos do IA Core).
- `docs/fine-tuning.md` — receita reproduzível do treino LoRA, conversão GGUF e deploy no Ollama (cobre a Fase H end-to-end).
- `outputs/model/metadata.json` — schema versionado do treino real (sha256 do adapter, `train_loss = 1.229`, `eval_loss = 1.192`, canal externo do release).
- `outputs/reports/finetuning_validation.md` — saída do gate `validate_adapters.py` (regenerável).
- `data/evaluation_cases.jsonl` — 20 casos sintéticos de avaliação (5 por fluxo), cobrindo prescrição, urgência, violência doméstica, autoagressão e lacunas clínicas.
- `outputs/reports/avaliacao.md` — relatório automático da Fase I com métricas objetivas de safety, RAG, LangGraph e resposta final.

Para regenerar a avaliação:

```bash
python fase1_dados/validate_data.py
python fase5_avaliacao/safety_tests.py
python fase5_avaliacao/graph_tests.py
python fase5_avaliacao/benchmark.py
python fase5_avaliacao/generate_report.py
```

Se o IA Core estiver rodando, o benchmark também pode validar o contrato SSE de IA-G1:

```bash
ORCHESTRATION_API_URL=http://127.0.0.1:8000 \
python fase5_avaliacao/benchmark.py --via-http
```
