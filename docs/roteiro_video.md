# Roteiro de Vídeo - FemCare IA Core (≤ 15 min)

Roteiro acadêmico para a demonstração da Fase 3. Atende os itens obrigatórios do PDF Secretaria (p. 8): treinamento e funcionamento da LLM personalizada, execução de um fluxo automatizado, perguntas clínicas contextualizadas, logs e validação. Cobre também o checklist de [`CHECKLIST_FASE3.md`](../CHECKLIST_FASE3.md) §4.

- Idioma: **pt-BR**.
- Duração-alvo: **14:30** (margem de 30 s sobre o limite de 15:00).
- Resolução: 1920×1080 / 30 fps; áudio mono.
- Apresentadora(s): equipe 8IADT.
- Ferramentas de gravação sugeridas: OBS Studio + ScreenFlow ou QuickTime + microfone de mesa.

Documentos relacionados:

- [`CHECKLIST_FASE3.md`](../CHECKLIST_FASE3.md)
- [`docs/relatorio_tecnico.md`](relatorio_tecnico.md)
- [`docs/diagrama_arquitetura.md`](diagrama_arquitetura.md)
- [`docs/diagramas_fluxos.md`](diagramas_fluxos.md)
- [`docs/sdd/ia-core/README.md`](sdd/ia-core/README.md) (guia visual com prints)

## Antes de gravar (pré-flight)

```bash
# 1. Repositorio atualizado
git status                         # tree limpo, branch main
git pull --ff-only

# 2. Dependencias
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Ollama com modelo fine-tuned
ollama list                        # esperado: femcare:v0.1 (~807 MB)
# Se ausente: docs/fine-tuning.md §6 (download release + import GGUF)

# 4. Servico Python pronto para subir
IA_LLM_BACKEND=ollama OLLAMA_MODEL=femcare:v0.1 \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
.venv/bin/uvicorn fase3_orquestracao.app:app --port 8000

# 5. BFF / UI pronto para subir
cd web && npm install && npm run setup:local
ORCHESTRATION_API_URL=http://127.0.0.1:8000 npm run dev
```

Abrir antes de gravar (e deixar em abas separadas do navegador para facilitar a transição):

- `http://127.0.0.1:3000/login`
- `http://127.0.0.1:3000/atendimentos/novo` (já logada)
- `http://127.0.0.1:3000/atendimentos` (listagem)
- IDE com [`outputs/model/metadata.json`](../outputs/model/metadata.json), [`outputs/reports/avaliacao.md`](../outputs/reports/avaliacao.md), [`outputs/reports/benchmark_results.json`](../outputs/reports/benchmark_results.json) e [`config/safety_rules.yaml`](../config/safety_rules.yaml) abertos.
- Terminal 1 (Ollama logs), Terminal 2 (Uvicorn), Terminal 3 (Next.js), Terminal 4 (livre para gates).

## Cronograma do vídeo

| Cena | Tempo | Foco | Tela |
|---|---|---|---|
| 1 | 0:00 - 1:00 | Abertura + visão | Slide ou navegador no README |
| 2 | 1:00 - 3:00 | Treino e modelo personalizado | IDE + terminal Ollama |
| 3 | 3:00 - 4:30 | Arquitetura ponta a ponta | IDE com diagramas |
| 4 | 4:30 - 9:00 | Fluxo LangGraph executado (Prevenção) | UI Next.js + logs |
| 5 | 9:00 - 11:30 | Safety / violência doméstica + gate profissional | UI + IDE |
| 6 | 11:30 - 13:30 | Avaliação automatizada e métricas | Terminal + avaliacao.md |
| 7 | 13:30 - 14:30 | Limitações, encerramento, próximos passos | Slide final |

Os tempos abaixo seguem este cronograma; ajuste de ±10 s entre cenas mantém a margem.

## Cena 1 - Abertura (0:00 - 1:00)

**Tela:** [`README.md`](../README.md) renderizado + logo do projeto.

**Roteiro narrado:**

> "Bom dia! Sou da equipe 8IADT. Este vídeo demonstra o FemCare IA Core - nosso assistente clínico em saúde da mulher para o Tech Challenge Fase 3. Em até 15 minutos vou mostrar: o pipeline de dados, o fine-tuning real do Llama-3.2-1B, os quatro fluxos LangGraph, o RAG sobre o MedQuAD curado, os guardrails clínicos, a integração com a UI Next.js e a avaliação automatizada com métricas objetivas."

**Ação:** mostrar rapidamente [`CHECKLIST_FASE3.md`](../CHECKLIST_FASE3.md) e dizer "todo o conteúdo desse vídeo aponta para evidências reais no repositório".

## Cena 2 - LLM personalizada / fine-tuning (1:00 - 3:00)

**Tela A (1:00 - 1:30):** terminal com `ollama list`.

```bash
ollama list
# femcare:v0.1     <hash>     807 MB     <timestamp>
```

**Narração:**

> "Nosso modelo está servido localmente no Ollama como `femcare:v0.1`, com **807 MB** em Q4_K_M. Ele é o Llama-3.2-1B-Instruct com o nosso adapter LoRA mesclado e quantizado."

**Tela B (1:30 - 2:30):** abrir [`outputs/model/metadata.json`](../outputs/model/metadata.json) no IDE; destacar `mode: "trained"`, `training.results.train_loss = 1.229`, `eval_loss = 1.192`, sha256 dos arquivos do adapter, e o link do GitHub Release.

**Narração:**

> "Este metadata é versionado. Mostra os hiperparâmetros (LoRA r=16, alpha=32, lr=2e-4, 2 épocas), os sha256 dos splits `train.jsonl` (2 231 exemplos) e `val.jsonl` (557 exemplos), o device usado (`mps`, Apple Silicon) e o canal de distribuição: o adapter é publicado como asset do GitHub Release `ia-core-phase-h-v0.1`. Treino real, reprodutível em workstation com GPU **ou** modo dry-run sem GPU para o avaliador."

**Tela C (2:30 - 3:00):** rolar [`fase2_finetuning/train_lora.py`](../fase2_finetuning/train_lora.py) mostrando `detect_device()` e o uso de `trl.SFTTrainer`. Citar [`docs/fine-tuning.md`](fine-tuning.md) §2.3 (receita Apple Silicon).

**Narração:**

> "O script detecta automaticamente o dispositivo (MPS ou CUDA), evita `bitsandbytes` quando não disponível e produz adapter + `metadata.json`. A receita completa - download Kaggle, treino, merge, conversão GGUF, import no Ollama - está em `docs/fine-tuning.md`."

## Cena 3 - Arquitetura ponta a ponta (3:00 - 4:30)

**Tela A (3:00 - 3:45):** abrir [`docs/diagrama_arquitetura.md`](diagrama_arquitetura.md) (render Mermaid) e seguir o flowchart de componentes.

**Narração:**

> "Aqui está a stack final. O browser fala com o BFF Next.js. O BFF faz proxy SSE para o endpoint `POST /v1/chat/stream` do IA Core em `:8000`. O IA Core executa o `clinical_router`, que dispara um dos quatro grafos LangGraph - `graphs/triagem_ginecologica.py`, `graphs/violencia_domestica.py`, `graphs/obstetrico.py` e `graphs/prevencao.py` - cada um com 6-8 nós reais. Esses grafos consultam o RAG via `rag_chain.py` chamando `retrieve_context(query, flow_id, k)` sobre `data/rag_documents.jsonl`, aplicam `SafetyGuard` e `ResponseValidator`, e opcionalmente pedem ao Ollama para polir o texto. Tudo isso é versionado e re-rodável."

**Tela B (3:45 - 4:30):** mostrar [`docs/diagramas_fluxos.md`](diagramas_fluxos.md), com destaque para o diagrama de violência doméstica e o de triagem (ramificação `emergencyGuidance` vs `suggestExams`).

**Narração:**

> "Esses diagramas espelham o código real: os nomes dos nós são exatamente os mesmos usados em `graph.add_node(...)`. Em segundos vamos ver isso aparecendo na UI."

## Cena 4 - Fluxo LangGraph executado: Prevenção (4:30 - 9:00)

> **Critério do PDF:** "Execução de um fluxo automatizado" + "Perguntas clínicas contextualizadas" + "Logs e validação".

**Tela A (4:30 - 4:50):** Browser em `http://127.0.0.1:3000/login`. Logar com `demo@exemplo.org` / `demo12345`.

**Narração:**

> "Login local com JWT em cookie `HttpOnly`. Esse usuário vem do seed em `web/scripts/`."

**Tela B (4:50 - 5:20):** Tela `/atendimentos/novo`. Em outra aba, abrir terminal e mostrar:

```bash
curl -s http://127.0.0.1:3000/api/health
# {"ok":true,"mode":"proxy"}
```

**Narração:**

> "Repare que o BFF está em `mode:'proxy'`, ou seja, **não é stub**. Toda a resposta vem do Python real."

**Tela C (5:20 - 7:30):** Selecionar o chip **Prevenção / rastreamento**. Colar a pergunta com `patientContext`:

```text
Tenho 42 anos e a minha mãe teve câncer de mama aos 50. 
Última mamografia há 3 anos. O que devo fazer agora?
```

E no campo de contexto, em JSON:

```json
{
  "resumo": "Paciente fictícia de 42 anos, mãe com CA mama aos 50.",
  "preventivos": { "ultimaMamografia": "2023" },
  "historicoReprodutivo": { "menarcaAnos": 12, "menopausa": false }
}
```

Enviar.

**Narração (durante o streaming):**

> "Repare nos eventos chegando: primeiro o `meta` com `modelVersion: ollama:femcare:v0.1`, depois um `log` por cada nó do grafo - `loadPatientHistory`, `identifyDueExams`, `preventiveGuidance`, `autoSchedulePrevention`, `personalizedReminders`. Os tokens vão chegando enquanto isso. No final, o evento `explain` preenche o painel de **Explainability** com a fonte do RAG, a confiança, as lacunas - aqui ele já identifica que falta exame físico - e o `trace` mostra todos os nós executados."

**Tela D (7:30 - 8:30):** Após o streaming, expandir o painel de **Logs** e mostrar:

- O `x-request-id` correlacionado.
- O evento `trace` com os nomes dos nós (`loadPatientHistory → identifyDueExams → preventiveGuidance → autoSchedulePrevention → personalizedReminders → validate`).
- A urgência classificada (`moderada` por alto risco familiar).

**Narração:**

> "Esse trace é exatamente o que aparece em `outputs/reports/benchmark_results.json` quando o benchmark roda esses mesmos cenários. Auditabilidade real."

**Tela E (8:30 - 9:00):** Ir para `/atendimentos` e abrir o atendimento recém-criado. Mostrar que o detalhe persistiu `langgraphTraceJson` no SQLite.

**Narração:**

> "O BFF persistiu o atendimento, incluindo o trace LangGraph completo, no SQLite. Isso fecha o ciclo: input clínico → IA Core → safety/RAG/LLM → resposta + trace → persistência auditável."

## Cena 5 - Safety: violência doméstica + gate profissional (9:00 - 11:30)

> **Critério do PDF:** "Logs e validação" + responsabilidade ética.

**Tela A (9:00 - 9:30):** Voltar a `/atendimentos/novo`. Selecionar o chip **Violência doméstica**. Mostrar o gate FE-SEC-01: a área de envio fica bloqueada com a mensagem "confirme perfil profissional".

**Narração:**

> "A UI nunca deixa um usuário não-profissional disparar este fluxo. Quando confirmamos, ele libera, mas o servidor também aplica regras independentes."

**Tela B (9:30 - 10:00):** No IDE, abrir [`config/safety_rules.yaml`](../config/safety_rules.yaml) e destacar as regras `domestic_violence`, `self_harm` e `prescription_request`.

**Narração:**

> "Essas regras são declarativas. Cada uma tem `severity`, `action`, `safety_flags`, padrões regex e o `replacement` que será injetado. Não dependemos do LLM para sair de uma situação crítica - se a paciente disser, por exemplo, 'meu marido me agrediu', o `SafetyGuard` injeta o protocolo Disque 180 + Polícia 190 antes da geração."

**Tela C (10:00 - 11:00):** Voltar à UI, enviar mensagem fictícia (ex.: "Preciso de ajuda urgente, meu companheiro me ameaça e está aqui fora agora"). Mostrar a resposta entrando com os encaminhamentos certos e a urgência `alta`.

**Narração:**

> "Repare: a resposta não usa o conteúdo livre da paciente; ela aplica o protocolo. O painel de logs mostra `human_review_required`, `violence_protocol` e `sensitive`. Em `logs/audit.log`, esse atendimento aparece com `sensitive_redacted: true` - texto livre **não** é gravado em claro."

**Tela D (11:00 - 11:30):** Mostrar (no terminal) a última linha de `logs/audit.log`:

```bash
tail -n 1 logs/audit.log | jq
```

**Narração:**

> "Auditoria minimizada, JSON Lines, sem PII livre. Esse é o requisito IA-SAFE-02 + IA-AUD-01."

## Cena 6 - Avaliação automatizada e métricas (11:30 - 13:30)

> **Critério do PDF:** "Logs e validação" + objetividade.

**Tela A (11:30 - 12:00):** Terminal 4, rodar:

```bash
python fase5_avaliacao/safety_tests.py   # ~10 s
```

**Narração:**

> "Esse gate roda **20 casos sintéticos** definidos em `data/evaluation_cases.jsonl`, 5 por fluxo, cobrindo prescrição, urgência, violência, autoagressão e lacunas clínicas. Tudo aprova."

**Tela B (12:00 - 12:30):** Rodar:

```bash
python fase5_avaliacao/graph_tests.py
```

**Narração:**

> "Aqui os mesmos cenários atravessam os quatro grafos LangGraph reais. O script verifica nós, urgência, fontes e palavras esperadas/proibidas na resposta."

**Tela C (12:30 - 13:10):** Rodar:

```bash
python fase5_avaliacao/benchmark.py
python fase5_avaliacao/generate_report.py
```

Depois abrir [`outputs/reports/avaliacao.md`](../outputs/reports/avaliacao.md) e mostrar:

- Pass rate 100% nos 20 casos.
- Safety, RAG, LangGraph e Resposta final pass rates.
- Latência média ~2 244 ms, p95 ~2 905 ms.
- Tabelas por fluxo.

**Narração:**

> "O relatório é gerado automaticamente. As métricas são objetivas: taxas de aprovação e latência por caso, com tabelas separadas para cada fluxo. O JSON bruto também está versionado em `outputs/reports/benchmark_results.json`."

**Tela D (13:10 - 13:30):** Mostrar rapidamente que o benchmark também tem modo HTTP:

```bash
ORCHESTRATION_API_URL=http://127.0.0.1:8000 \
python fase5_avaliacao/benchmark.py --via-http
```

**Narração:**

> "Com o IA Core rodando, conseguimos validar o contrato SSE end-to-end - eventos `meta`, `explain`, `trace`, `done` - exatamente como o BFF Next.js consome."

## Cena 7 - Limitações, encerramento (13:30 - 14:30)

**Tela A (13:30 - 14:00):** abrir [`docs/relatorio_tecnico.md` §9](relatorio_tecnico.md#9-limitacoes-e-protocolos-de-seguranca-explicitos) e §7.4.

**Narração:**

> "Honestidade técnica: o LoRA é leve (Llama-3.2-1B), por isso é um ajuste de formato/linguagem - **nunca** a única fonte clínica. Não fizemos painel formal com especialistas nem análise quantitativa de bias demográfico nesta entrega académica, mas deixamos o protocolo pronto. Próximos passos: re-treino com revisão clínica, instrumentação demográfica em `evaluation_cases.jsonl` e tracing distribuído entre BFF e IA Core."

**Tela B (14:00 - 14:30):** voltar ao [`CHECKLIST_FASE3.md`](../CHECKLIST_FASE3.md) e correr a vista pela tabela final.

**Narração de encerramento:**

> "Todas as fases SDD - de A a J - estão verdes, com evidência apontada caso por caso. O repositório é a fonte da verdade desta entrega. Obrigada!"

Fade out até **14:30**.

## Cobertura dos itens obrigatórios do PDF

| Critério (PDF p. 8) | Cena | Tempo |
|---|---|---|
| Treinamento e funcionamento da LLM personalizada | 2 | 1:00 - 3:00 |
| Execução de um fluxo automatizado (LangGraph) | 4 | 4:30 - 9:00 |
| Perguntas clínicas contextualizadas | 4 (com `patientContext`) | 5:20 - 7:30 |
| Logs e validação das respostas | 4 (logs UI + trace), 5 (audit.log), 6 (avaliacao.md) | 7:30 - 13:30 |
| Duração ≤ 15 min | Cronograma total 14:30 | - |

## Plano de contingência

| Sintoma | Mitigação durante a gravação |
|---|---|
| Ollama não está rodando | Mostrar `IA_LLM_BACKEND=stub_safe` em ação (`mode:"proxy"` com `modelVersion: "stub-safe-0.1.0"`); explicar que o sistema continua **seguro** com fallback determinístico. |
| Erro no Next.js | Reiniciar com `npm run dev` em terminal separado; mostrar o `/api/health` voltando a `mode:"proxy"`. |
| Latência alta no Ollama | Comentar latência média do benchmark (já documentada) e seguir; é esperado em 1B + Q4_K_M em hardware modesto. |
| Timeout no polish via LLM | Apontar para `_polish_response_with_llm` e o fallback determinístico - o caminho seguro é mostrado em tempo real. |
| Falta de tempo | Cortar a cena 7 para 30 s e/ou condensar a 3 em 60 s. |

## Checklist final antes do upload

- [ ] Tempo total ≤ 15:00.
- [ ] Áudio sem ruído / cortado nos silêncios.
- [ ] Telas com fonte legível (mínimo 14 pt).
- [ ] Todos os comandos citados existem (`./web/`, `fase*/`, `outputs/`).
- [ ] Link do GitHub Release (`ia-core-phase-h-v0.1`) mostrado em vídeo.
- [ ] Disclaimer clínico aparece pelo menos uma vez (vem do app).
- [ ] Sem mostrar credenciais reais ou PII.
- [ ] Vídeo legendado em pt-BR (opcional, recomendado).
