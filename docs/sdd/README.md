# SDD Implementation Specs

Este diretorio organiza specs executaveis para transformar os requisitos e lacunas do projeto em fluxos de implementacao.

## Pacotes

| Pacote | Objetivo |
|---|---|
| [ia-core](ia-core/README.md) | Implementar dados, fine-tuning, RAG/LangChain, servico Python, LangGraph, safety, auditoria e avaliacao. |

## Como usar

Cada pacote segue o fluxo:

1. `context.md` - alinha premissas e restricoes.
2. `spec.md` - define comportamento, requisitos e criterios testaveis.
3. `design.md` - descreve arquitetura, contratos e schemas.
4. `tasks.md` - quebra o trabalho em fases implementaveis com gates.

O pacote `ia-core` foi criado a partir de `LACUNAS_IMPLEMENTACAO_TECH_CHALLENGE_FASE3.md` e deve guiar a proxima etapa de implementacao.

## Fonte de dados definida

O corpus base do projeto sera o dataset Kaggle `pythonafroz/medquad-medical-question-answer-for-ai-research`, baixado via `kagglehub.dataset_download(...)`. Como o MedQuAD e um dataset medico geral, o pacote `ia-core` tambem especifica uma etapa obrigatoria de filtragem, normalizacao e enriquecimento para o recorte de saude da mulher exigido pelo desafio.
