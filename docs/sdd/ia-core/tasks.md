# Tasks - IA Core e Orquestracao Clinica

Legenda:

- `[P]` pode ser executada em paralelo depois das dependencias.
- `Gate` e o comando ou evidencia minima para considerar a tarefa pronta.
- Prioridade: `P0` obrigatorio para entrega, `P1` robustez, `P2` acabamento.

## Fase A - Estrutura Python

| ID | Prioridade | Tarefa | Depende de | Feito quando | Gate |
|---|---|---|---|---|---|
| IA-A1 | P0 | Criar pastas `fase1_dados`, `fase2_finetuning`, `fase3_orquestracao`, `fase4_seguranca`, `fase5_avaliacao`, `data`, `outputs`, `logs`, `config` | - | Estrutura existe | `find . -maxdepth 2 -type d` |
| IA-A2 | P0 | Criar `requirements.txt` para Python IA incluindo `kagglehub` | IA-A1 | Dependencias listadas | `python -m pip install -r requirements.txt` |
| IA-A3 | P0 | Criar `fase3_orquestracao/app.py` com `GET /health` | IA-A2 | Uvicorn sobe | `curl :8000/health` |
| IA-A4 | P0 | Criar helpers SSE em `fase3_orquestracao/sse.py` | IA-A3 | Eventos formatados | teste unitario simples |
| IA-A5 | P0 | Criar schemas Pydantic em `fase3_orquestracao/schemas.py` | IA-A3 | Payload do BFF valida | `pytest` |

## Fase B - Dados

| ID | Prioridade | Tarefa | Depende de | Feito quando | Gate |
|---|---|---|---|---|---|
| IA-B1 | P0 | Implementar `fase1_dados/download_medquad.py` com `kagglehub.dataset_download("pythonafroz/medquad-medical-question-answer-for-ai-research")` | IA-A2 | dataset e localizado em cache ou copiado para `data/raw/medquad` | `python fase1_dados/download_medquad.py` |
| IA-B2 | P0 | Implementar `fase1_dados/explore_dataset.py` | IA-B1 | gera perfil com arquivos, colunas, contagens e exemplos anonimizados | `python fase1_dados/explore_dataset.py` |
| IA-B3 | P0 | Implementar normalizacao MedQuAD em `fase1_dados/build_dataset.py` | IA-B2 | `data/processed/medquad_normalized.jsonl` existe | comando gera arquivo |
| IA-B4 | P0 | Classificar/filtrar recorte de saude da mulher | IA-B3 | registros possuem dominio valido ou `excluir` | relatorio de distribuicao |
| IA-B5 | P0 | Criar complementos sinteticos/curados por dominio | IA-B4 | `data/synthetic/*.jsonl` cobre lacunas do MedQuAD | inspecao |
| IA-B6 | P0 | Criar `data/rag_documents.jsonl` com fontes e metadados | IA-B4, IA-B5 | docs possuem citation/version/domain/source | `python fase1_dados/validate_data.py` |
| IA-B7 | P0 | Gerar `data/train.jsonl` e `data/val.jsonl` | IA-B5 | arquivos existem em formato chat/instruction | comando gera arquivos |
| IA-B8 | P0 | Implementar `fase1_dados/validate_data.py` | IA-B6, IA-B7 | valida campos, duplicatas, dominios e sensibilidade | `python fase1_dados/validate_data.py` |
| IA-B9 | P1 | Documentar fontes em `docs/dados-e-curadoria.md` | IA-B8 | documento cita Kaggle URL, slug, data de download, licenca/termos e limitacoes | revisao |

## Fase C - RAG com LangChain

| ID | Prioridade | Tarefa | Depende de | Feito quando | Gate |
|---|---|---|---|---|---|
| IA-C1 | P0 | Implementar loader de `data/rag_documents.jsonl` | IA-B6 | docs carregados com metadados | `pytest` |
| IA-C2 | P0 | Implementar indexador de embeddings/vector store | IA-C1 | cria `outputs/vectorstore` | `python fase3_orquestracao/rag_chain.py --build` |
| IA-C3 | P0 | Implementar `retrieve_context(query, flow_id, k)` | IA-C2 | retorna top-k com fonte/score | teste manual |
| IA-C4 | P1 | Criar testes RAG | IA-C3 | consultas esperadas recuperam dominio correto | `python fase5_avaliacao/rag_tests.py` |

## Fase D - LLM Backend

| ID | Prioridade | Tarefa | Depende de | Feito quando | Gate |
|---|---|---|---|---|---|
| IA-D1 | P0 | Criar interface `LlmBackend` | IA-A5 | backend stub seguro responde | `pytest` |
| IA-D2 | P0 | Implementar backend OpenAI-compatible | IA-D1 | usa env sem expor chave | teste com env |
| IA-D3 | P1 | Implementar backend Ollama/local | IA-D1 | funciona com `OPENAI_BASE_URL` local | teste manual |
| IA-D4 | P1 | Implementar backend local LoRA ou documentar carregamento | IA-D1, IA-H | script ou doc existe | validacao de adaptadores |

## Fase E - Safety e Explainability

| ID | Prioridade | Tarefa | Depende de | Feito quando | Gate |
|---|---|---|---|---|---|
| IA-E1 | P0 | Criar `config/safety_rules.yaml` | IA-A1 | regras P0 existem | revisao |
| IA-E2 | P0 | Implementar `fase4_seguranca/safety_guard.py` | IA-E1 | detecta prescricao, violencia, urgencia, autoagressao | `python fase5_avaliacao/safety_tests.py` |
| IA-E3 | P0 | Implementar `response_validator.py` | IA-E2 | remove/ajusta saidas proibidas | `pytest` |
| IA-E4 | P0 | Implementar `explainability.py` | IA-C3 | monta ExplainBlock com fonte/lacunas/confianca | teste |
| IA-E5 | P1 | Implementar `audit.py` JSON Lines | IA-E2 | escreve `logs/audit.log` minimizado | teste |

## Fase F - LangGraph

| ID | Prioridade | Tarefa | Depende de | Feito quando | Gate |
|---|---|---|---|---|---|
| IA-F1 | P0 | Criar helper de estado e trace | IA-A5, IA-E2 | trace nao contem conteudo sensivel completo | `pytest` |
| IA-F2 | P0 | Implementar grafo triagem ginecologica | IA-F1, IA-C3, IA-D1 | executa fluxo e retorna trace | `python fase5_avaliacao/graph_tests.py --flow triagemGinecologica` |
| IA-F3 | P0 | Implementar grafo violencia domestica | IA-F1, IA-E2 | redige/log minimizado e escala humano | `python fase5_avaliacao/graph_tests.py --flow violenciaDomestica` |
| IA-F4 | P0 | Implementar grafo obstetrico | IA-F1, IA-C3 | detecta red flags | `python fase5_avaliacao/graph_tests.py --flow obstetrico` |
| IA-F5 | P0 | Implementar grafo prevencao | IA-F1, IA-C3 | identifica exames/lembretes mock | `python fase5_avaliacao/graph_tests.py --flow prevencao` |
| IA-F6 | P0 | Implementar `clinical_router.py` | IA-F2, IA-F3, IA-F4, IA-F5 | roteia por `flowId` | testes dos 4 fluxos |

## Fase G - Servico Python SSE

| ID | Prioridade | Tarefa | Depende de | Feito quando | Gate |
|---|---|---|---|---|---|
| IA-G1 | P0 | Implementar `POST /v1/chat/stream` | IA-F6 | retorna meta/log/token/explain/done | `curl -N` |
| IA-G2 | P0 | Retornar `modelVersion` real | IA-D2 | UI nao mostra `stub-0.1.0` | painel logs |
| IA-G3 | P1 | Retornar evento `trace` | IA-F1, IA-G1 | trace aparece no stream | `curl -N` |
| IA-G4 | P1 | Atualizar UI para capturar/persistir `trace` | IA-G3 | `langgraphTraceJson` deixa de ser null | DB/detail |
| IA-G5 | P0 | Testar integracao BFF via `ORCHESTRATION_API_URL` | IA-G1 | UI usa modo proxy | demo manual |

## Fase H - Fine-tuning

| ID | Prioridade | Tarefa | Depende de | Feito quando | Gate |
|---|---|---|---|---|---|
| IA-H1 | P0 | Criar notebook Colab `FemCare_FineTuning_Colab.ipynb` | IA-B7 | notebook referencia `train.jsonl`/`val.jsonl` e origem MedQuAD | revisao |
| IA-H2 | P0 | Criar script `train_lora.py` ou equivalente | IA-H1 | parametros documentados | dry-run ou Colab |
| IA-H3 | P0 | Gerar/adicionar metadados de treino | IA-H2 | `outputs/model/metadata.json` existe | inspecao |
| IA-H4 | P0 | Implementar `validate_adapters.py` | IA-H3 | valida artefatos ou link externo | `python fase2_finetuning/validate_adapters.py` |
| IA-H5 | P1 | Documentar como baixar/carregar artefatos grandes | IA-H4 | README explica Git LFS/release/link | revisao |

## Fase I - Avaliacao

| ID | Prioridade | Tarefa | Depende de | Feito quando | Gate |
|---|---|---|---|---|---|
| IA-I1 | P0 | Criar `data/evaluation_cases.jsonl` | IA-B8 | casos cobrem 4 fluxos e safety | validate_data |
| IA-I2 | P1 | Implementar `safety_tests.py` | IA-E2 | minimo 20 cenarios | comando passa |
| IA-I3 | P1 | Implementar `graph_tests.py` | IA-F6 | minimo 4 casos por fluxo | comando passa |
| IA-I4 | P1 | Implementar `benchmark.py` | IA-G1 | roda casos e salva resultados | comando passa |
| IA-I5 | P1 | Implementar `generate_report.py` | IA-I4 | gera `outputs/reports/avaliacao.md` | comando passa |

## Fase J - Documentacao final e video

| ID | Prioridade | Tarefa | Depende de | Feito quando | Gate |
|---|---|---|---|---|---|
| IA-J1 | P2 | Criar `CHECKLIST_FASE3.md` | IA-I5 | itens marcados com evidencia | revisao |
| IA-J2 | P2 | Criar `docs/relatorio_tecnico.md` | IA-I5, IA-H4 | relatorio cita resultados reais | revisao |
| IA-J3 | P2 | Criar `docs/diagrama_arquitetura.md` | IA-G5 | diagrama final reflete codigo | revisao |
| IA-J4 | P2 | Criar `docs/diagramas_fluxos.md` | IA-F6 | quatro diagramas finais | revisao |
| IA-J5 | P2 | Criar `docs/roteiro_video.md` | IA-G5, IA-I5 | roteiro ate 15 min | ensaio |

## Ordem recomendada

1. IA-A1 a IA-A5
2. IA-B1 a IA-B9
3. IA-C1 a IA-C3
4. IA-D1 e IA-D2
5. IA-E1 a IA-E4
6. IA-F1 a IA-F6
7. IA-G1, IA-G2 e IA-G5
8. IA-H1 a IA-H4
9. IA-I1 a IA-I5
10. IA-J1 a IA-J5

## Gates finais

Antes de considerar o fluxo SDD completo:

```bash
python fase1_dados/download_medquad.py
python fase1_dados/explore_dataset.py
python fase1_dados/validate_data.py
python fase2_finetuning/validate_adapters.py
python fase3_orquestracao/rag_chain.py --build
python fase5_avaliacao/safety_tests.py
python fase5_avaliacao/graph_tests.py
python fase5_avaliacao/generate_report.py
cd web && npm run lint && npm run build
```

Demo final:

```bash
uvicorn fase3_orquestracao.app:app --reload --port 8000
cd web
ORCHESTRATION_API_URL=http://127.0.0.1:8000 npm run dev
```

Critico para o video:

- Mostrar `/api/health` em modo proxy.
- Executar um fluxo LangGraph real.
- Mostrar fonte RAG real.
- Mostrar explainability.
- Mostrar logs/trace.
- Mostrar avaliacao ou checklist final.
