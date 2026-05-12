# Web — Next.js (BFF + UI)

> Este documento cobre **apenas** o pacote `web/`. A documentação principal do projeto (visão geral, arquitetura, demo com imagens, setup multi-terminal, fluxos LangGraph, RAG, fine-tuning, avaliação e troubleshooting) está centralizada no [README raiz](../README.md). Consulte-o antes deste para entender o contexto.

Interface do assistente clínico descrita em [.specs/features/web-ui/spec.md](../.specs/features/web-ui/spec.md).

## Requisitos

- Node.js 20+

## Arranque local (clone → a correr)

Na pasta `web/`:

```bash
npm install
npm run setup:local
npm run dev
```

Abra `http://localhost:3000`. O ficheiro **`.env`** inclui um `AUTH_SECRET` só para demo local (o Next carrega `.env` em `dev` e `build`). Para valores próprios ou integração Python, use **`.env.local`** (sobrepõe `.env`; não é versionado).

## Variáveis de ambiente

| Origem | Uso |
|--------|-----|
| `.env` | Valores padrão do repositório para desenvolvimento local. |
| `.env.local` | Opcional: segredos e URLs reais (copie de `.env.example` como modelo). |

| Variável | Descrição |
|----------|-----------|
| `AUTH_SECRET` | Segredo JWT (≥ 32 caracteres) para o cookie `mw_session`. |
| `DATABASE_PATH` | Opcional: caminho do ficheiro SQLite (default `data/app.db` dentro de `web/`). |
| `ORCHESTRATION_API_URL` | Base URL do Python. Se vazio, o BFF usa **stub** SSE (demo local). |
| `ORCHESTRATION_API_KEY` | Opcional: Bearer para o serviço Python. |
| `NEXT_PUBLIC_SITE_URL` | Opcional: URL pública (ex.: `https://dominio.org`) para `metadataBase`, sitemap e robots. |

Contrato HTTP: [docs/api.md](../docs/api.md).

## Base de dados (SQLite)

`npm run setup:local` executa migrações e seed. Ou manualmente:

```bash
npm run db:migrate
npm run db:seed
```

Credenciais demo após seed:

- Email: `demo@exemplo.org`
- Palavra-passe: `demo12345`

## Comandos

```bash
npm install
npm run dev
```

Abra `http://localhost:3000`.

## Roteiro rápido para vídeo (Fase 3)

1. Mostrar avisos legais e seletor de fluxo.  
2. Opcional: preencher JSON de contexto (dados fictícios).  
3. Enviar mensagem e mostrar streaming + painel **Explainability**.  
4. Mostrar painel de **logs** e `x-request-id`.  
5. Fluxo **violência doméstica**: demonstrar **gate** de confirmação profissional antes do envio.

## Gates de qualidade

```bash
npm run lint
npm run build
```
