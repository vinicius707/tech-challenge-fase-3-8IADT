# Requisitos não funcionais

**Documento oficial:** PDF Secretaria — item 4 (p. 6–7), *Considerações éticas específicas* e critérios regulatórios (p. 9–10).

**Convenção:** rastreio **PDF p. X**; **DEVE** / **NÃO DEVE** alinhados ao enunciado; critérios **WHEN / ENTÃO** onde cabível.

---

## RNF-SEG — Segurança e privacidade

| ID | Descrição | Rastreio PDF | Critério de aceite | TBD |
|----|-----------|--------------|-------------------|-----|
| RNF-SEG-01 | Proteção **extrema** de dados de violência doméstica (armazenamento, transporte, logs). | p. 9 “Proteção extrema de dados de violência doméstica” | Threat model resumido + medidas rastreáveis em código/config. | KMS / certificados. |
| RNF-SEG-02 | **Anonimização rigorosa** de dados reprodutivos e sensíveis (treino e exemplos). | p. 9 + p. 3–4 (curadoria) | Procedimento documentado + amostra antes/depois (sintética). | k-anonimato ou método formal. |
| RNF-SEG-03 | **Controle de acesso** baseado em necessidade médica. | p. 9 “Controle de acesso baseado em necessidade médica” | Papéis e permissões; demonstração de negação de acesso. | IAM concreto. |
| RNF-SEG-04 | **Criptografia** (canal + **E2E** para dados de violência conforme item 4). | p. 6–7 protocolos de segurança | Documentar repouso e trânsito; trilha de violência segregada. | Biblioteca e curvas. |

---

## RNF-REG — Conformidade e governança

| ID | Descrição | Rastreio PDF | Critério de aceite | TBD |
|----|-----------|--------------|-------------------|-----|
| RNF-REG-01 | Instrumentos de aderência à **LGPD** (bases legais, minimização, DPIA resumida, direitos do titular em nível conceitual). | p. 9 “Instrumentos de aderência à LGPD” | Seção no relatório técnico com mapeamento artefato → princípio LGPD. | DPO e contratos reais. |
| RNF-REG-02 | Conformidade com **normas de proteção de dados médicos** alinhada ao critério de avaliação “Conformidade regulatória”. | p. 10 item 6 | Lista de normas consideradas + limitações do protótipo acadêmico. | Escopo jurídico formal. |

---

## RNF-ETH — Ética, bias e equidade (PDF p. 9–10)

| ID | Descrição | Rastreio PDF | Critério de aceite | TBD |
|----|-----------|--------------|-------------------|-----|
| RNF-ETH-01 | **Responsabilidade médica:** apoio, nunca substituto; validação obrigatória por especialistas; limitações documentadas. | p. 9 “Responsabilidade Médica” | Disclaimer + pontos de validação humana no fluxo. | UX de confirmação. |
| RNF-ETH-02 | **Bias e equidade:** grupos étnicos e socioeconômicos; validação em populações diversas; disparidades de acesso. | p. 9 “Bias e Equidade” | Relatório com plano ou resultados de análise de bias + limitações. | Métricas por subgroup. |
| RNF-ETH-03 | **Sensibilidade cultural:** linguagem inclusiva; cultura e religião; contextos socioeconômicos. | p. 9 “Sensibilidade Cultural” | Diretrizes de estilo documentadas (prompt/pós-processamento). | Testes com usuários. |

### WHEN / ENTÃO (testáveis)

- WHEN o relatório de avaliação do modelo for entregue ENTÃO ele **DEVE** mencionar **bias e equidade** entre grupos demográficos (PDF p. 7 e p. 9–10).  
- WHEN o assistente for exposto a usuários ENTÃO comunicações **DEVEM** seguir diretrizes de inclusão e respeito (RNF-ETH-03).

---

## RNF-REL — Confiabilidade e qualidade do modelo

| ID | Descrição | Rastreio PDF | Critério de aceite | TBD |
|----|-----------|--------------|-------------------|-----|
| RNF-REL-01 | **Precisão médica** e adequação a **diretrizes de sociedades médicas** (critério de avaliação 1). | p. 7 “Métricas de precisão…”; p. 10 item 1 | Conjunto de teste com referência + métricas reportadas. | Tamanho mínimo do golden set. |
| RNF-REL-02 | **Segurança da paciente** — proteção e detecção de riscos (critério de avaliação 2). | p. 10 item 2 | Casos de teste negativos (prescrição indevida, conduta insegura). | Automação vs manual. |
| RNF-REL-03 | **Estabilidade e previsibilidade** após validação pré-retorno (RF-SEC-02). | p. 6–7 validação antes do retorno | Variância medida ou checklist em lote. | Temperatura, seeds, contratos de saída. |

---

## RNF-OBS — Observabilidade e operação

| ID | Descrição | Rastreio PDF | Critério de aceite | TBD |
|----|-----------|--------------|-------------------|-----|
| RNF-OBS-01 | Rastreamento detalhado de interações. | p. 6–7 “Rastreamento detalhado de todas as interações” | Correlation ID por sessão; exemplos de trilha. | Retenção e anonimização de logs. |
| RNF-OBS-02 | Relatórios de utilização por especialidade médica. | p. 6–7 mesmo bloco | Agregação simulada ou real documentada. | Periodicidade. |

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
