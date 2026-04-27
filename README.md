# tech-challenge-fase-3-8IADT

Tech Challenge **Fase 3** (8IADT — Secretaria): assistente em saúde da mulher com integração a orquestração **LangChain / LangGraph** (fine-tuning e fluxos descritos nas specs). Este repositório entrega sobretudo o **BFF + interface web** em Next.js, com contratos HTTP documentados e specs alinhadas ao desafio.

## O que está no repositório

| Área | Conteúdo |
|------|-----------|
| [`web/`](web/) | Aplicação **Next.js 14** (App Router): BFF (`app/api`), UI com streaming **SSE**, autenticação por cookie, SQLite para auditoria de atendimentos. |
| [`docs/`](docs/) | Contrato HTTP ([`docs/api.md`](docs/api.md)), OpenAPI opcional ([`docs/openapi/web-bff.yaml`](docs/openapi/web-bff.yaml)), especificações SDD em [`docs/specs/`](docs/specs/README.md). |
| [`.specs/features/web-ui/`](.specs/features/web-ui/spec.md) | Spec, design e tasks no formato **Tech Lead's Club** para a UI/BFF. |

O serviço **Python** (LangGraph) não está versionado neste clone; o BFF corre em **modo stub** quando `ORCHESTRATION_API_URL` está vazio, permitindo demo local completa.

## Funcionalidades da aplicação web

- **Login** (`/login`) — sessão JWT em cookie `mw_session`; utilizador demo criado pelo seed.
- **Novo atendimento** (`/atendimentos/novo`) — chat com escolha de **fluxo clínico** (chips), contexto opcional em JSON, avisos legais, **gate** de confirmação profissional no fluxo de violência doméstica, streaming de tokens, painel de **explainability** e trilha de **logs** (inclui `x-request-id`).
- **Listagem de atendimentos** (`/atendimentos`) — tabela com filtros por categoria/tipo, destaque visual por **gravidade** (rotina a crítico), paginação e painel de **detalhe** (classificação, prompt, resposta, trace).
- **APIs** — ver [`docs/api.md`](docs/api.md): `POST /api/chat/stream` (SSE), auth, CRUD de auditoria `POST/GET /api/atendimentos`, `GET /api/health`.

## Stack técnica (implementado)

- **Runtime:** Node.js 20+.
- **Framework:** Next.js 14, React 18, TypeScript.
- **Dados:** SQLite via `better-sqlite3`; migrações e seed em `web/scripts/`.
- **Auth:** `jose` + `bcryptjs` para passwords.

## Início rápido

Na pasta `web/`:

```bash
cd web
npm install
npm run setup:local
npm run dev
```

Abra [http://localhost:3000](http://localhost:3000). A raiz redireciona para `/login` ou `/atendimentos` consoante a sessão.

**Credenciais demo** (após `npm run setup:local`): email `demo@exemplo.org`, palavra-passe `demo12345` — ver [web/README.md](web/README.md).

## Variáveis de ambiente e integração

Resumo: `AUTH_SECRET` (obrigatório em produção), `DATABASE_PATH`, `ORCHESTRATION_API_URL` / `ORCHESTRATION_API_KEY`, `NEXT_PUBLIC_SITE_URL` para metadata/sitemap. Tabela completa e ficheiros `.env` / `.env.local` em [web/README.md](web/README.md) e em [docs/api.md](docs/api.md).

## Documentação de requisitos (SDD)

Documentação de requisitos alinhada ao PDF do desafio, com rastreio por página, histórias P1–P3, critérios **WHEN/ENTÃO** e **TBD**: [docs/specs/README.md](docs/specs/README.md).

## Qualidade e build

Dentro de `web/`:

```bash
npm run lint
npm run build
```

## Especificação da UI (TLC)

Spec da feature web: [.specs/features/web-ui/spec.md](.specs/features/web-ui/spec.md). Contrato HTTP normativo até exportação automática a partir do OpenAPI: [docs/api.md](docs/api.md).
