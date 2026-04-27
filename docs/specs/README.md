# Especificações — Tech Challenge Fase 3 (8IADT Secretaria)

Este diretório contém as **specs** derivadas do documento oficial do desafio, preparadas para refinamento em **SDD** e alinhadas às práticas **Tech Lead's Club — Spec-Driven Development** (granularidade, rastreio e critérios testáveis).

## Documento oficial

- Arquivo na raiz do repositório: `8IADT - Fase 3 - Tech challenge Secretaria.pdf`
- Estrutura do PDF: contexto e objetivo (p. 2–3); quatro blocos de entregas técnicas (p. 3–7); entregáveis e vídeo (p. 7–8); datasets sugeridos (p. 8–9); ética e LGPD (p. 9); critérios de avaliação (p. 10).

## Índice dos artefatos

| Arquivo | Conteúdo |
|---------|----------|
| [00-visao-e-escopo.md](00-visao-e-escopo.md) | Problema, metas, fora de escopo, restrições do PDF |
| [01-requisitos-funcionais.md](01-requisitos-funcionais.md) | RF-* com rastreio por página, histórias P1–P3, WHEN/ENTÃO/DEVE |
| [02-requisitos-nao-funcionais.md](02-requisitos-nao-funcionais.md) | RNF-* segurança, LGPD, ética, observabilidade |
| [03-dados-e-fine-tuning.md](03-dados-e-fine-tuning.md) | Corpus, curadoria, métricas, datasets sugeridos |
| [04-langchain-e-integracao.md](04-langchain-e-integracao.md) | Pipeline, bases, protocolos de sociedades |
| [05-langgraph-fluxos.md](05-langgraph-fluxos.md) | Quatro fluxos LangGraph + Mermaid |
| [06-seguranca-e-etica.md](06-seguranca-e-etica.md) | NUNCA/SEMPRE, logging, critérios de avaliação do PDF |
| [07-entregaveis-e-aceite.md](07-entregaveis-e-aceite.md) | Repositório, relatório, vídeo ≤15 min, DoD |
| [08-matriz-rastreabilidade.md](08-matriz-rastreabilidade.md) | RF/RNF → página PDF → artefato SDD |

## Front-end Next.js

- App: [web/README.md](../../web/README.md) — BFF + UI (streaming SSE).  
- Spec TLC: [.specs/features/web-ui/spec.md](../../.specs/features/web-ui/spec.md) — contrato: [api.md](../api.md).

## Convenções

- **DEVE** / **NÃO DEVE** / **DEVERIA**: obrigatoriedade alinhada ao enunciado.
- **WHEN … ENTÃO … DEVE**: critérios testáveis (formato TLC Specify).
- **TBD**: decisão reservada ao SDD ou à implementação.
- IDs **RF-***, **RNF-***: rastreio em design, tasks e validação.

## Fluxo sugerido após estas specs

1. **Specify** — congelar decisões em `context.md` (ou equivalente) para cada TBD crítico.  
2. **Design** — arquitetura e componentes onde houver ambiguidade.  
3. **Tasks** — quebras atômicas com verificação.  
4. **Execute** — implementação e evidências para o relatório e o vídeo.
