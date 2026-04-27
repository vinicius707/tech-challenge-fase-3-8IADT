# Requisitos não funcionais

**Fonte:** Tech Challenge Fase 3 — segurança, ética, conformidade, avaliação.

---

## RNF-SEG — Segurança e privacidade

| ID | Descrição | Critério de aceite | TBD |
|----|-----------|-------------------|-----|
| RNF-SEG-01 | Proteção **extrema** de dados relacionados a violência doméstica (armazenamento, transporte, logs). | Threat model resumido + medidas listadas e rastreáveis no código/config. | Provedor de KMS / certificados. |
| RNF-SEG-02 | **Anonimização rigorosa** de dados reprodutivos e sensíveis em datasets de treino e exemplos. | Procedimento documentado + amostra antes/depois (sintética). | Nível de k-anonimato ou método formal. |
| RNF-SEG-03 | **Controle de acesso** baseado em necessidade médica (princípio do menor privilégio). | Papéis e permissões descritos; demonstração de negação de acesso. | IAM concreto. |
| RNF-SEG-04 | **Criptografia** para canal e, onde exigido pelo PDF, E2E em trilha de violência. | Documentar o que está cifrado em repouso e em trânsito. | Biblioteca e curva algorítmica. |

---

## RNF-REG — Conformidade e governança

| ID | Descrição | Critério de aceite | TBD |
|----|-----------|-------------------|-----|
| RNF-REG-01 | Instrumentos de aderência à **LGPD** (bases legais, minimização, DPIA resumida, direitos do titular em nível conceitual). | Seção no relatório técnico com mapeamento artefato → princípio LGPD. | DPO e contratos reais. |
| RNF-REG-02 | Conformidade com **normas de proteção de dados médicos** aplicáveis ao contexto acadêmico/simulado. | Lista explícita de normas consideradas (ex.: LGPD + boas práticas CFM quando relevante) e limitações do protótipo. | Escopo jurídico formal. |

---

## RNF-ETH — Ética, bias e equidade

| ID | Descrição | Critério de aceite | TBD |
|----|-----------|-------------------|-----|
| RNF-ETH-01 | **Responsabilidade médica:** assistente como apoio; validação obrigatória por especialistas em produção; limitações documentadas. | Texto de disclaimer e fluxos que exigem confirmação humana. | UX de confirmação. |
| RNF-ETH-02 | **Bias e equidade:** representatividade étnica e socioeconômica; validação em populações diversas; atenção a disparidades de acesso. | Relatório com análise de bias planejada ou resultados preliminares + limitações. | Métricas de equidade (ex.: paridade por subgroup). |
| RNF-ETH-03 | **Sensibilidade cultural:** linguagem inclusiva; aspectos culturais e religiosos; adaptação socioeconômica. | Diretrizes de estilo no prompt/pós-processamento documentadas. | Avaliação com usuários reais (fora do escopo mínimo). |

---

## RNF-REL — Confiabilidade e qualidade do modelo

| ID | Descrição | Critério de aceite | TBD |
|----|-----------|-------------------|-----|
| RNF-REL-01 | **Precisão médica** alinhada a diretrizes de sociedades médicas (avaliação no relatório). | Conjunto de teste com referência + métricas reportadas. | Tamanho mínimo do golden set. |
| RNF-REL-02 | **Segurança da paciente** em cenários de risco (detecção, escalação, abstinência de conduta insegura). | Casos de teste negativos (jailbreak clínico, prescrição indevida). | Automatização vs manual. |
| RNF-REL-03 | **Estabilidade e previsibilidade** das respostas após validação pré-retorno (ligado a RF-SEC-02). | Variância medida ou checklist de validação em lote. | Temperatura, seeds, contratos de saída. |

---

## RNF-OBS — Observabilidade e operação

| ID | Descrição | Critério de aceite | TBD |
|----|-----------|-------------------|-----|
| RNF-OBS-01 | Rastreamento detalhado de interações compatível com RF-SEC-03. | Correlation ID por sessão; exemplos de trilha. | Retenção e anonimização de logs. |
| RNF-OBS-02 | Relatórios de utilização por especialidade médica. | Agregação simulada ou real documentada. | Periodicidade. |

---

## RNF-PER — Performance (aberto no SDD)

| ID | Descrição | Critério de aceite | TBD |
|----|-----------|-------------------|-----|
| RNF-PER-01 | Latência aceitável para uso interativo em demo (não numerada no PDF). | Definir no SDD (ex.: P95 alvo em ambiente de demo). | Hardware e batch. |

---

## Open questions para SDD

- LGPD: tratamento de **titulares** em ambiente acadêmico (dados 100% sintéticos simplifica).
- E2E: escopo realista para **protótipo** vs “E2E conceitual” documentado apenas.
- Relação entre **RNF-REL** e métricas obrigatórias do relatório (precisão por condição, segurança, ética).
