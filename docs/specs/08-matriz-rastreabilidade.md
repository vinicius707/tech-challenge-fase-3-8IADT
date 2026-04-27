# Matriz de rastreabilidade (spec → PDF → SDD)

**Documento oficial:** `8IADT - Fase 3 - Tech challenge Secretaria.pdf`  
**Legenda:** cada linha liga um artefato desta pasta à **página** do PDF e a um entregável típico do **SDD** (a detalhar na implementação).

Formato: **ID** — citação do PDF — **artefato SDD (TBD)**.

---

## Visão e índice

- [00-visao-e-escopo.md](00-visao-e-escopo.md) — Contexto, desafio, objetivo, grupo/prazo/nota (p. 2) — *SDD:* PROJECT.md / visão arquitetural.
- [README.md](README.md) (esta pasta) — Navegação e convenções — *SDD:* onboarding do time.

## Front-end Next.js (`web/` + `.specs/features/web-ui/`)

| ID FE | Requisito backend (RF/RNF) | Artefato |
|-------|-----------------------------|----------|
| FE-INT-01 | RF-LC-01 | `web/src/app/api/chat/stream/route.ts`, `AssistantExperience` |
| FE-INT-02 | RF-LG-00 … RF-LG-04 | Seletor `flowId` + payload |
| FE-INT-03 | RF-LC-03, RF-LC-04 | Formulário `patientContext` |
| FE-UI-01 | RF-SEC-04 | Painel explainability |
| FE-UI-02 | RF-SEC-01, RNF-ETH-01 | Faixa de avisos |
| FE-INT-04 | RF-SEC-03 | Painel de logs / `x-request-id` |
| FE-SEC-01 | RF-SEC-02 | Gate fluxo violência (mock) |
| FE-INT-05 | RF-LC-06 | Lista de fontes quando presentes |
| FE-UI-03 | RNF-REL-02 | Estados vazios/erro/timeout |
| FE-UI-04 | RNF-ETH-03 | Landmarks / labels |
| FE-UI-05 | — | pt-BR nas cópias |
| FE-AUTH-01 … FE-AUTH-03 | RNF-SEG-01, RF-SEC-03 | `web/src/app/api/auth/*`, `middleware.ts`, `LoginForm` |
| FE-LIST-01 … FE-LIST-03 | RNF-OBS-01, RF-SEC-03 | `AtendimentosDashboard`, `GET /api/atendimentos` |
| FE-DET-01 … FE-DET-02 | RF-SEC-04, RNF-OBS-02 | painel detalhe, `GET /api/atendimentos/:id` |
| FE-Persist-01 | RF-SEC-03, RNF-REG-01 | `AssistantExperience` persist + `POST /api/atendimentos`, redação violência |

Especificação TLC: [.specs/features/web-ui/spec.md](../../.specs/features/web-ui/spec.md) — contrato HTTP: [docs/api.md](../api.md).

## RF / RNF → PDF p. 3–7 (entregas técnicas)

- **RF-FT-01 … RF-FT-04** — Item **1** Fine-tuning (p. 3–4) — *SDD:* pipeline de dados, versão de modelo, licenças de corpus.
- **RF-LC-01 … RF-LC-06** — Item **2** LangChain (p. 4–5), incluindo protocolos de sociedades (terceiro bullet do pipeline) — *SDD:* diagrama de componentes, contratos de tools, config de RAG/FT.
- **RF-LG-00** — Frase “LangGraph **e os dados relevantes** para cada um” (p. 5) — *SDD:* matriz dado↔fluxo, fixtures.
- **RF-LG-01 … RF-LG-04** — Quatro fluxos textuais (p. 5–6) — *SDD:* implementação LangGraph, testes de caminho, diagramas exportados.
- **RF-SEC-01 … RF-SEC-04** — Item **4** Segurança e validação (p. 6–7) — *SDD:* políticas, middleware de validação, esquema de logs, formato de explainability.

## RNF → PDF p. 6–10

- **RNF-SEG-01 … RNF-SEG-04** — Item 4 + privacidade (p. 6–7, 9) — *SDD:* threat model, criptografia, segregação.
- **RNF-REG-01 … RNF-REG-02** — LGPD e conformidade (p. 9–10 item 6) — *SDD:* DPIA resumida, matriz legal.
- **RNF-ETH-01 … RNF-ETH-03** — Considerações éticas (p. 9) — *SDD:* guia de linguagem, plano de avaliação de bias.
- **RNF-REL-01 … RNF-REL-03** — Avaliação do modelo no relatório + critérios p. 10 itens 1–2 — *SDD:* golden set, métricas, testes de segurança de saída.
- **RNF-OBS-01 … RNF-OBS-02** — Logging e auditoria (p. 6–7) — *SDD:* observabilidade, retenção, relatórios.

## Dados e integração

- [03-dados-e-fine-tuning.md](03-dados-e-fine-tuning.md) — Datasets sugeridos (p. 8–9) — *SDD:* data lineage, licenças.
- [04-langchain-e-integracao.md](04-langchain-e-integracao.md) — Pipeline (p. 4) — *SDD:* sequência LCEL ou equivalente.

## Entregáveis e vídeo

- [07-entregaveis-e-aceite.md](07-entregaveis-e-aceite.md) — Repositório, relatório, diagramas, vídeo ≤15 min (p. 7–8) — *SDD:* checklist de release, roteiro de vídeo.

## Segurança e ética (documento dedicado)

- [06-seguranca-e-etica.md](06-seguranca-e-etica.md) — Item 4 + ética + critérios 1–6 (p. 6–7, 9–10) — *SDD:* runbooks, revisão clínica.

---

## Open questions para SDD

- Ferramenta de gestão de requisitos (Issues, Notion, ReqIF) vs apenas Markdown.
- Política de versionamento ao decompor requisitos (ex.: `RF-LC-05a`).
