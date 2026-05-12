# Context - IA Core e Orquestracao Clinica

## 1. Situacao atual

O projeto atual ja possui uma camada web/BFF em Next.js com:

- Login local com JWT em cookie `HttpOnly`.
- Chat com streaming SSE.
- Seletor dos quatro fluxos clinicos.
- Campo de contexto da paciente em JSON.
- Painel de explainability.
- Painel de logs de demo.
- Persistencia SQLite de atendimentos.
- Redacao basica para fluxo de violencia domestica.
- Contrato HTTP documentado em `docs/api.md`.

O nucleo de IA ainda nao esta versionado no projeto. O `README.md` declara que o servico Python de LangGraph nao esta neste clone e que o BFF usa `stub` quando `ORCHESTRATION_API_URL` nao esta configurado.

## 2. Problema a resolver

Para atender o Tech Challenge Fase 3, o projeto precisa deixar de ser apenas uma UI/BFF com stub e passar a ter uma camada executavel de IA com:

- Dados curados e/ou sinteticos de saude da mulher.
- Pipeline de fine-tuning demonstravel.
- LangChain/RAG com fontes rastreaveis.
- LangGraph real para os quatro fluxos obrigatorios.
- Guardrails clinicos e regulatorios.
- Logs, traces, auditoria e avaliacao.

## 3. Objetivo do fluxo SDD

Criar um plano SDD implementavel para adicionar a camada `IA Core` ao projeto existente, preservando o BFF Next.js e conectando o novo backend Python via `ORCHESTRATION_API_URL`.

O resultado esperado e:

- O front continua consumindo `POST /api/chat/stream`.
- O BFF faz proxy para `POST /v1/chat/stream` no servico Python.
- O servico Python executa RAG, LangGraph, safety e LLM backend.
- Os eventos SSE retornam `meta`, `token`, `explain`, `log`, `done` e, quando necessario, `error`.
- A UI passa a exibir fontes reais, trace real e logs reais da orquestracao.

## 4. Principios de produto

- Segurança da paciente acima de completude da resposta.
- IA como apoio, nunca como substituto de profissional.
- Fluxos deterministas para cenarios sensiveis.
- RAG-first para conhecimento clinico versionado.
- Fine-tuning como evidencia tecnica e ajuste de formato/linguagem, nao como unica fonte de conhecimento.
- Dados reais identificaveis fora do escopo sem aprovacao institucional.
- Logs minimizados para violencia domestica.

## 5. Decisoes iniciais

| ID | Decisao | Racional |
|---|---|---|
| D1 | Manter Next.js como UI+BFF | Ja esta implementado e documentado. |
| D2 | Adicionar servico Python separado | LangChain/LangGraph e stack de IA ficam isolados da UI. |
| D3 | Usar SSE ponta a ponta | Ja e o contrato do BFF e facilita demo. |
| D4 | Criar quatro grafos LangGraph separados | Reduz risco de parecer grafo generico e melhora rastreabilidade. |
| D5 | Usar dados sinteticos/publicos por padrao | Evita risco LGPD e acelera entrega academica. |
| D6 | Persistir trace resumido, nao chain-of-thought | Gera auditabilidade sem expor raciocinio sensivel. |
| D7 | Permitir LLM backend pluggable | Ollama/local, OpenAI-compatible e modelo fine-tuned podem compartilhar interface. |
| D8 | Usar MedQuAD do Kaggle como corpus base | Dataset definido pela equipe; deve ser baixado via `kagglehub` e curado para saude da mulher. |
| D9 | Usar Ollama local como backend LLM padrao | Reduz dependencia externa, custo e risco de chave API para a demo academica. |

## 6. Fora de escopo

- Integracao real com prontuario hospitalar.
- Uso de dados reais identificaveis.
- Acionamento real de equipes de emergencia.
- RBAC institucional completo.
- Deploy produtivo com alta disponibilidade.
- Certificacao como software medico.

## 7. Assumptions

- O projeto sera demonstrado localmente ou em ambiente academico controlado.
- A demo pode usar dados sinteticos.
- O dataset base sera o Kaggle MedQuAD `pythonafroz/medquad-medical-question-answer-for-ai-research`.
- O ambiente de desenvolvimento tera credenciais/permissao Kaggle quando necessario para `kagglehub.dataset_download`.
- O MedQuAD e um corpus medico geral; portanto, nao substitui curadoria especifica de ginecologia, obstetricia, prevencao e violencia domestica.
- A demo principal usara um modelo local simples via Ollama, selecionado por `OLLAMA_MODEL`.
- O Ollama estara rodando localmente em `http://127.0.0.1:11434` ou URL equivalente configurada por `OLLAMA_BASE_URL`.
- O fine-tuning pode ser executado em Colab e os artefatos podem ser documentados ou disponibilizados por instrucao se forem grandes demais para Git.
- A UI atual sera reaproveitada.
- O BFF atual continuara aceitando modo stub para fallback, mas o video deve demonstrar o modo proxy com Python.

## 8. Riscos

| Risco | Impacto | Mitigacao |
|---|---|---|
| Implementar apenas stub | Alto | Priorizar servico Python P0. |
| Usar corpus generico demais | Alto | Filtrar MedQuAD por topicos relevantes e complementar com exemplos curados de saude da mulher. |
| Fine-tuning atrasar por GPU | Medio | Preparar notebook Colab e fallback com artefatos/metadados. |
| Modelo Ollama simples ter baixa qualidade clinica | Alto | Usar RAG, respostas curtas, guardrails deterministas e encaminhamento humano para casos sensiveis. |
| LangGraph virar fluxo cosmetico | Alto | Implementar estados, transicoes, trace e testes por fluxo. |
| Vazamento de conteudo sensivel | Alto | Redacao, logs minimizados e safety flags. |
| Falta de relatorio final | Alto | Gerar relatorio como saida de `fase5_avaliacao/generate_report.py`. |

## 9. Definition of Ready

Antes de implementar:

- `docs/api.md` deve ser tratado como contrato do BFF.
- Este pacote SDD deve estar revisado.
- A equipe deve validar acesso ao Kaggle e registrar licenca/termos do dataset MedQuAD em `docs/dados-e-curadoria.md`.
- A equipe deve escolher nome da pasta Python: recomendacao `ia-core/`.
- A equipe deve escolher o modelo Ollama inicial e registrar o valor recomendado de `OLLAMA_MODEL`.
- A equipe deve confirmar se adaptadores LoRA serao versionados, anexados como release ou documentados por link.

## 10. Definition of Done

O fluxo IA Core esta pronto quando:

- `ORCHESTRATION_API_URL` conectado faz a UI sair do stub.
- Os quatro fluxos LangGraph executam com trace resumido.
- O RAG recupera fontes reais ou fixtures versionadas.
- O dataset sintetico/anonimizado esta validado.
- Existe evidencia de fine-tuning ou artefatos LoRA documentados.
- Guardrails bloqueiam/escalam cenarios criticos.
- A avaliacao gera relatorio.
- O relatorio tecnico final consegue citar evidencias reais do repositorio.
