# Spec - IA Core e Orquestracao Clinica

## 1. Problem statement

O projeto possui uma interface web funcional, mas ainda nao possui a camada executavel de IA exigida pelo Tech Challenge Fase 3. E necessario implementar um backend Python que execute dados, fine-tuning, RAG, LangChain, quatro fluxos LangGraph, safety, logs e avaliacao, mantendo compatibilidade com o contrato HTTP ja existente.

## 2. Goals

- [ ] Criar pipeline de dados com MedQuAD/Kaggle como corpus base e curadoria para saude da mulher.
- [ ] Criar pipeline de fine-tuning LoRA/QLoRA com validacao de artefatos.
- [ ] Criar servico Python com endpoint `POST /v1/chat/stream`.
- [ ] Implementar RAG com LangChain e fontes rastreaveis.
- [ ] Implementar os quatro fluxos LangGraph obrigatorios.
- [ ] Retornar eventos SSE compativeis com o BFF atual.
- [ ] Implementar guardrails clinicos e regulatorios no backend.
- [ ] Persistir/retornar trace resumido para auditoria.
- [ ] Criar avaliacao automatizada.
- [ ] Gerar evidencias para relatorio tecnico e video.

## 3. Non-goals

| Item | Motivo |
|---|---|
| Substituir o BFF Next.js | O BFF ja funciona e deve ser reaproveitado. |
| Fazer LangChain no browser | Segredos, CORS e requisito de stack Python. |
| Usar dados reais identificaveis | Risco LGPD sem aprovacao formal. |
| Criar RBAC hospitalar completo | Fora do MVP academico. |
| Prescrever medicamentos | Regra proibitiva do desafio. |

## 4. User stories

### P0 - Entrega obrigatoria

**US-IA-P0-01 - Servico Python conectado ao BFF**  
Como avaliador, quero ver a UI usando `ORCHESTRATION_API_URL`, para confirmar que a resposta nao vem apenas do stub.

**US-IA-P0-02 - RAG com fontes reais**  
Como profissional de saude, quero respostas com fontes recuperadas de uma base versionada, para auditar a recomendacao.

**US-IA-P0-03 - Quatro fluxos LangGraph**  
Como avaliador, quero executar triagem ginecologica, violencia domestica, obstetrico e prevencao, para validar os fluxos obrigatorios do PDF.

**US-IA-P0-04 - Dataset e fine-tuning demonstravel**  
Como avaliador, quero encontrar dataset, notebook/script e validacao de adaptadores, para comprovar o item de fine-tuning.

**US-IA-P0-05 - Guardrails clinicos**  
Como instituicao, quero que pedidos proibidos sejam bloqueados ou escalados, para reduzir risco clinico e etico.

### P1 - Robustez

**US-IA-P1-01 - Trace LangGraph resumido**  
Como auditor, quero ver quais nos do grafo foram executados, para entender o caminho de decisao sem expor chain-of-thought.

**US-IA-P1-02 - Avaliacao automatizada**  
Como equipe tecnica, quero rodar testes e gerar relatorio, para comprovar qualidade e seguranca.

**US-IA-P1-03 - Logs sensiveis minimizados**  
Como responsavel por privacidade, quero que violencia domestica nao grave conteudo sensivel em claro, para reduzir risco LGPD.

### P2 - Entrega academica forte

**US-IA-P2-01 - Relatorio tecnico final**  
Como avaliador, quero um relatorio com evidencias de execucao, para revisar a entrega sem precisar inferir do codigo.

**US-IA-P2-02 - Roteiro de video**  
Como equipe, quero roteiro com comandos e cenas, para gravar demonstracao dentro de 15 minutos.

## 5. Functional requirements

| ID | Prioridade | Requisito | Criterio de aceite |
|---|---|---|---|
| IA-DATA-01 | P0 | Baixar MedQuAD do Kaggle via `kagglehub` | `python fase1_dados/download_medquad.py` salva os arquivos em `data/raw/medquad` ou documenta o cache local. |
| IA-DATA-02 | P0 | Normalizar MedQuAD para JSONL interno | `data/processed/medquad_normalized.jsonl` existe com pergunta, resposta, fonte e metadados. |
| IA-DATA-03 | P0 | Criar recorte de saude da mulher | Registros relevantes sao classificados nos dominios `triagemGinecologica`, `violenciaDomestica`, `obstetrico`, `prevencao` ou marcados para exclusao. |
| IA-DATA-04 | P0 | Criar dados RAG com metadados | Documentos possuem `doc_id`, `domain`, `source`, `version`, `sensitivity`, `citation`. |
| IA-DATA-05 | P0 | Criar corpus de treino/validacao | `data/train.jsonl` e `data/val.jsonl` existem e validam. |
| IA-DATA-06 | P0 | Validar qualidade dos dados | `python fase1_dados/validate_data.py` gera relatorio sem erro critico. |
| IA-FT-01 | P0 | Criar notebook/script de LoRA/QLoRA | Notebook ou script documenta modelo, parametros e dataset. |
| IA-FT-02 | P0 | Validar artefatos LoRA | `python fase2_finetuning/validate_adapters.py` valida ou explica artefato externo. |
| IA-RAG-01 | P0 | Indexar documentos | `outputs/vectorstore` e criado por script. |
| IA-RAG-02 | P0 | Recuperar top-k com fonte | Consulta retorna fonte, score e trecho. |
| IA-SVC-01 | P0 | Expor `POST /v1/chat/stream` | Endpoint retorna SSE compativel com `docs/api.md`. |
| IA-SVC-02 | P0 | Suportar backend LLM pluggable | Interface unica para OpenAI-compatible, Ollama/local e fine-tuned. |
| IA-LG-01 | P0 | Implementar grafo de triagem ginecologica | Executa estados e retorna trace. |
| IA-LG-02 | P0 | Implementar grafo de violencia domestica | Executa com redacao/log minimo e encaminhamento humano. |
| IA-LG-03 | P0 | Implementar grafo obstetrico | Detecta red flags e escalona urgencia. |
| IA-LG-04 | P0 | Implementar grafo de prevencao | Identifica exames devidos e lembretes mock. |
| IA-SAFE-01 | P0 | Bloquear prescricao e diagnostico definitivo | Testes de safety passam. |
| IA-SAFE-02 | P0 | Escalar violencia, autoagressao e urgencia | Resposta nao depende apenas do LLM. |
| IA-EXP-01 | P0 | Retornar ExplainBlock | `fonte`, `confianca`, `lacunas`, `raciocinioClinico` alto nivel. |
| IA-AUD-01 | P1 | Retornar trace resumido | BFF consegue persistir `langgraphTraceJson`. |
| IA-EVAL-01 | P1 | Criar avaliacao automatizada | `python fase5_avaliacao/generate_report.py` gera Markdown. |
| IA-DOC-01 | P2 | Criar relatorio tecnico final | `docs/relatorio_tecnico.md` existe com evidencias. |
| IA-DOC-02 | P2 | Criar roteiro de video | `docs/roteiro_video.md` existe com cenas e comandos. |

## 6. Dataset contract

Fonte base definida:

```python
import kagglehub

path = kagglehub.dataset_download(
    "pythonafroz/medquad-medical-question-answer-for-ai-research"
)

print("Path to dataset files:", path)
```

O pipeline deve copiar ou referenciar o cache retornado por `kagglehub` sem versionar arquivos grandes desnecessarios. A saida versionavel esperada e:

- `data/processed/medquad_normalized.jsonl`
- `data/rag_documents.jsonl`
- `data/train.jsonl`
- `data/val.jsonl`
- `outputs/reports/data_profile.md`

Regras obrigatorias:

- O dataset original deve ser documentado em `docs/dados-e-curadoria.md` com URL, slug Kaggle, data de download, licenca/termos observados e limitacoes.
- Registros fora do recorte de saude da mulher podem ser usados apenas como conhecimento medico geral para RAG, nunca como evidencia principal dos quatro fluxos.
- Lacunas do MedQuAD para violencia domestica, obstetricia contextual e prevencao brasileira devem ser complementadas com exemplos sinteticos/curados e marcadas por `source`.

## 7. API contract

### Request

O servico Python deve aceitar o mesmo payload que o BFF envia:

```json
{
  "flowId": "triagemGinecologica",
  "threadId": "optional",
  "messages": [
    { "role": "user", "content": "texto" }
  ],
  "patientContext": {
    "resumo": "Paciente ficticia, sem PII real",
    "preventivos": {},
    "obstetrica": {},
    "cicloMenstrual": {},
    "historicoReprodutivo": {}
  }
}
```

### SSE events

Eventos obrigatorios:

- `meta`
- `token`
- `explain`
- `log`
- `done`
- `error`

Evento adicional recomendado:

- `trace`

### ExplainBlock

```json
{
  "fonte": "INCA 2025 / protocolo sintetico v1",
  "confianca": 0.72,
  "lacunas": ["sem exame fisico", "sem sinais vitais"],
  "raciocinioClinico": "Resumo alto nivel, sem chain-of-thought sensivel."
}
```

### Trace resumido

```json
{
  "flowId": "triagemGinecologica",
  "nodes": [
    {
      "name": "collectSymptoms",
      "status": "ok",
      "summary": "Sintomas normalizados",
      "safetyFlags": []
    }
  ],
  "finalRisk": "moderada"
}
```

## 8. Clinical flow requirements

### Triagem ginecologica

Estados minimos:

- `collectSymptoms`
- `analyzeRisk`
- `classifyUrgency`
- `suggestExams`
- `initialGuidance`
- `scheduleAppointment`
- `emergencyGuidance`

Critico: sintomas de alarme devem ir para `emergencyGuidance`.

### Violencia domestica

Estados minimos:

- `captureAlertSignals`
- `assessViolenceRisk`
- `applySafetyProtocol`
- `notifySpecializedTeam`
- `secureDocumentation`
- `followUpPlan`

Critico: nao gravar conteudo sensivel em claro; sempre encaminhar a equipe qualificada.

### Obstetrico

Estados minimos:

- `ingestPregnancyData`
- `assessObstetricRisk`
- `specificGuidance`
- `scheduleObstetricExams`
- `urgencyAlerts`
- `continuousSupport`

Critico: sinais de alarme gestacional devem gerar urgencia alta ou emergencia.

### Prevencao

Estados minimos:

- `loadPatientHistory`
- `identifyDueExams`
- `preventiveGuidance`
- `autoSchedulePrevention`
- `personalizedReminders`

Critico: diferenciar rastreamento populacional, investigacao por sintoma e alto risco.

## 9. Testable criteria

1. WHEN `ORCHESTRATION_API_URL` estiver configurado ENTÃO a UI deve receber eventos do Python e nao do stub.
2. WHEN uma pergunta de triagem for enviada ENTÃO o trace deve conter pelo menos tres nos LangGraph.
3. WHEN uma pergunta de violencia domestica for enviada ENTÃO o sistema deve marcar sensibilidade e recomendar encaminhamento humano.
4. WHEN o usuario pedir prescricao ENTÃO a resposta deve bloquear ou exigir validacao humana.
5. WHEN a resposta usar RAG ENTÃO `explain.fonte` deve conter fonte real do corpus.
6. WHEN o contexto estiver vazio ENTÃO a resposta deve registrar lacunas.
7. WHEN `fase1_dados/download_medquad.py` rodar ENTÃO deve baixar ou localizar o cache Kaggle do MedQuAD.
8. WHEN `fase1_dados/validate_data.py` rodar ENTÃO deve gerar relatorio.
9. WHEN `fase5_avaliacao/generate_report.py` rodar ENTÃO deve gerar `outputs/reports/avaliacao.md`.

## 10. Traceability

| Lacuna | Requisito nesta spec |
|---|---|
| Sem dataset | IA-DATA-01 a IA-DATA-06 |
| Sem fine-tuning | IA-FT-01, IA-FT-02 |
| Sem RAG | IA-RAG-01, IA-RAG-02 |
| Sem Python | IA-SVC-01, IA-SVC-02 |
| Sem LangGraph real | IA-LG-01 a IA-LG-04 |
| Guardrails stub | IA-SAFE-01, IA-SAFE-02 |
| Explainability ficticia | IA-EXP-01 |
| Trace null | IA-AUD-01 |
| Sem avaliacao | IA-EVAL-01 |
| Sem relatorio/video final | IA-DOC-01, IA-DOC-02 |

## 11. Success criteria

- [ ] UI demonstra modo proxy para Python.
- [ ] Quatro fluxos executam com trace.
- [ ] Dataset MedQuAD baixado, normalizado, curado e validado.
- [ ] Fine-tuning tem evidencia reproduzivel.
- [ ] RAG retorna fonte real.
- [ ] Safety tests passam.
- [ ] Relatorio de avaliacao gerado.
- [ ] Relatorio tecnico final cita evidencias.
