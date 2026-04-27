# Matriz de rastreabilidade (spec → PDF → SDD)

**Legenda:** cada linha liga um ID desta suite de specs ao conteúdo do PDF *Tech Challenge Fase 3* e ao artefato esperado no **fluxo futuro de SDD** (a preencher).

Formato: `ID spec` — trecho do PDF — artefato SDD (TBD).

---

## Visão e escopo

- `00-visao-e-escopo.md` — Contexto, desafio, objetivo (págs. 2–3) — *SDD:* visão de arquitetura, stakeholders, escopo técnico.

## Requisitos funcionais

- `RF-FT-01` … `RF-FT-04` — Item 1 Fine-tuning: protocolos, FAQ, documentos, preparação de dados (págs. 3–4) — *SDD:* esquema de dados, pipeline ETL, contrato de treino, versão de modelo.
- `RF-LC-01` … `RF-LC-05` — Item 2 LangChain: pipeline, consultas contextualizadas, funcionalidades (págs. 4–5) — *SDD:* diagrama C4, interfaces de serviços, catálogo de tools.
- `RF-LG-01` … `RF-LG-04` — Item 3 LangGraph: quatro fluxos (págs. 5–6) — *SDD:* desenho de grafo implementável, estados persistidos, políticas de transição.
- `RF-SEC-01` … `RF-SEC-04` — Item 4 Segurança e validação (págs. 6–7) — *SDD:* threat model, políticas IAM, formato de resposta estruturada, testes de segurança.

## Requisitos não funcionais

- `RNF-SEG-*`, `RNF-REG-*` — Considerações éticas, LGPD, privacidade (págs. 9–10) — *SDD:* controles técnicos, DPIA, matriz de compliance.
- `RNF-ETH-*` — Bias, equidade, responsabilidade, cultura (pág. 9) — *SDD:* plano de avaliação ética, guidelines de linguagem.
- `RNF-REL-*`, `RNF-OBS-*`, `RNF-PER-*` — Avaliação, logging, performance implícita — *SDD:* SLOs, observabilidade, painéis.

## Dados e integração

- `03-dados-e-fine-tuning.md` — Datasets sugeridos (págs. 8–9) — *SDD:* data lineage, licenças, armazenamento.
- `04-langchain-e-integracao.md` — Pipeline LangChain (pág. 4) — *SDD:* sequência de chains, erros e retries.

## Fluxos

- `05-langgraph-fluxos.md` — Descrição linear dos quatro fluxos (págs. 5–6) — *SDD:* código LangGraph, testes de caminho, fixtures.

## Entregáveis

- `07-entregaveis-e-aceite.md` — Entregáveis da Fase 3, vídeo, relatório (págs. 7–8, 10) — *SDD:* checklist de release, roteiro do vídeo, template do relatório.

## Segurança e ética (documento dedicado)

- `06-seguranca-e-etica.md` — Itens 4 + considerações éticas + critérios de avaliação (págs. 6–7, 9–10) — *SDD:* runbooks de incidente, revisão clínica.

---

## Open questions para SDD

- Ferramenta de gestão de requisitos (GitHub Issues, Notion, ReqIF) vs manter só Markdown.
- Política de versionamento dos IDs (`RF-*`) quando requisitos forem decompostos (ex.: `RF-LC-05a`).
