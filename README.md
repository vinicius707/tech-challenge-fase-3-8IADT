# tech-challenge-fase-3-8IADT

Tech Challenge Fase 3 (8IADT — Secretaria): assistente em saúde da mulher com fine-tuning, LangChain e LangGraph.

## Especificações (refinamento SDD)

Documentação de requisitos alinhada ao PDF do desafio, com rastreio por página, histórias P1–P3, critérios **WHEN/ENTÃO** e **TBD** para SDD: ver [docs/specs/README.md](docs/specs/README.md).

## Front-end (Next.js)

Aplicação em [web/](web/) — BFF + UI com streaming SSE, seletor de fluxos LangGraph, explainability e trilha de logs. Spec TLC: [.specs/features/web-ui/spec.md](.specs/features/web-ui/spec.md). Contrato: [docs/api.md](docs/api.md).

### Correr o front localmente

```bash
cd web
npm install
npm run setup:local
npm run dev
```

Detalhes, variáveis de ambiente e utilizador demo: [web/README.md](web/README.md).