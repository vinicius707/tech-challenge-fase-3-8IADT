# Dados e fine-tuning

**Documento oficial:** PDF Secretaria — item **1** (p. 3–4) e tabela **Sugestão de Datasets Especializados** (p. 8–9).  
Ver também requisitos RF-FT-* em [01-requisitos-funcionais.md](01-requisitos-funcionais.md).

## 1. Domínio do corpus

O fine-tuning deve cobrir, no mínimo, as categorias já listadas em [01-requisitos-funcionais.md](01-requisitos-funcionais.md) (RF-FT-01 a RF-FT-04).

## 2. Preparação e curadoria (requisitos de processo)

- **Preprocessing:** normalização e enriquecimento voltados a terminologia médica feminina (TBD: tokenização, dicionários controlados, NER).
- **Anonimização:** rigor extra para violência e saúde mental; política de pseudonimização e remoção de identificadores diretos/indiretos.
- **Validação por especialistas:** GO (ginecologia e obstetrícia) — evidência por checklist assinado ou registro de revisão por lote.
- **Balanceamento:** distribuição entre condições clínicas e faixas etárias documentada antes/depois.
- **Representatividade:** inclusão explícita de perfis socioeconômicos diversos (meta de cobertura a definir no SDD).

## 3. Métricas de avaliação (relatório)

O relatório técnico deve incluir, conforme PDF:

- Metodologia de curadoria específica.
- Técnicas de anonimização para dados sensíveis.
- Métricas de avaliação para o **domínio médico feminino** (ex.: acurácia por tópico, BLEU/ROUGE apenas se justificado, preferência humana com médicos).
- Validação por especialistas GO.
- Análise de **bias e equidade** entre grupos demográficos.
- Avaliação de **segurança** e adequação ética.
- Feedback de profissionais especializados.

**TBD no SDD:** golden set, amostragem, significância estatística, métricas de segurança (toxicidade, violação de política).

## 4. Datasets sugeridos (referência)

Lista derivada do PDF; links são **fontes conceituais** — curadoria própria pode substituir onde indicado.

1. **Women's Health QA** — Perguntas e respostas sobre saúde da mulher. Fonte: curadoria própria baseada em guidelines.
2. **Gynecological Protocols** — Protocolos de atendimento ginecológico. Fonte: **Sociedade Brasileira de Ginecologia** (texto do PDF p. 8).
3. **Obstetric Guidelines** — Diretrizes obstétricas e perinatais. Fonte: FEBRASGO, OMS.
4. **Violence Detection Patterns** — Padrões linguísticos para detecção de violência. Fonte: literatura especializada + dados sintéticos.
5. **Contraceptive Knowledge Base** — Contraceptivos. Fonte: FDA, ANVISA, literatura médica.
6. **Breast Cancer Screening** — Rastreamento câncer de mama. Fonte: INCA, American Cancer Society.
7. **Menstrual Health Data** — Saúde menstrual. Fonte: curadoria de apps especializados (atenção a licença).
8. **Maternal Mental Health** — Saúde mental materna. Fonte: literatura psiquiatria perinatal.

## 5. Entregável de dados no repositório

- Dataset **anonimizado** ou **exemplos sintéticos** específicos, versionados ou documentados com instrução de reprodução.
- Pipeline de fine-tuning como código (ver [07-entregaveis-e-aceite.md](07-entregaveis-e-aceite.md)).

---

## Open questions para SDD

- Licenciamento e **terms of use** de cada fonte externa.
- Tamanho mínimo do corpus por tema para evitar **overfitting** temático.
- Estratégia de **instrução vs completude** (instruction tuning vs continued pretraining).
- Onde hospedar artefatos grandes (Git LFS, release, não versionar binários pesados no Git default).
