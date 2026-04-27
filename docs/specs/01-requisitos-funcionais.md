# Requisitos funcionais

**Documento oficial:** PDF Secretaria — seções *Requisitos obrigatórios* (p. 3–7) e *Entregáveis* (p. 7–8).  
**Convenção:** **DEVE** = obrigatório no enunciado; critérios **WHEN / ENTÃO** = testáveis (TLC Specify); **TBD** = decisão no SDD.

## Rastreio por bloco do PDF

| Bloco no PDF | Páginas | IDs neste doc |
|--------------|---------|----------------|
| 1. Fine-tuning LLM saúde da mulher | 3–4 | RF-FT-01 … RF-FT-04 |
| 2. Assistente com LangChain | 4–5 | RF-LC-01 … RF-LC-06 |
| 3. Fluxos LangGraph | 5–6 | RF-LG-00 … RF-LG-04 |
| 4. Segurança e validação | 6–7 | RF-SEC-01 … RF-SEC-04 |

---

## RF-FT — Fine-tuning e corpus (PDF p. 3–4)

| ID | Descrição | Rastreio PDF | Critério de aceite | TBD |
|----|-----------|--------------|---------------------|-----|
| RF-FT-01 | O sistema **DEVE** permitir fine-tuning de um LLM (ex.: LLaMA, Falcon ou outro) com protocolos de: atendimento ginecológico e **obstétrico** do hospital; violência doméstica; triagem câncer de **mama** e **colo do útero**; emergências obstétricas; saúde mental da mulher; planejamento familiar e saúde reprodutiva. | Lista “Protocolos médicos especializados” | Corpus versionado + rastre de fontes por versão do modelo. | Formato e licença de cada protocolo. |
| RF-FT-02 | O corpus **DEVE** incluir FAQs sobre: contraceptivos; ciclos menstruais e distúrbios hormonais; sinais de alerta gravidez/pós-parto; violência doméstica; amamentação e neonatal; menopausa e climatério. | “Exemplos de perguntas frequentes específicas” | Exemplos por tema (Q/A ou instrução) catalogados. | Esquema de rotulagem e revisão por especialista. |
| RF-FT-03 | O corpus **DEVE** contemplar documentos: laudos mamografia/USG ginecológico; receitas terapias hormonais; colposcopia/biópsias; relatórios atendimento a vítimas de violência; pré-natal e puerpério. | “Modelos especializados de documentos” | Amostra anonimizada ou sintética **por tipo**. | Nível de desidentificação por tipo. |
| RF-FT-04 | A preparação **DEVE** incluir: preprocessing para terminologia médica feminina; anonimização rigorosa (violência, saúde mental); curadoria com validação por especialistas em **ginecologia e obstetrícia**; balanceamento entre condições e faixas etárias; dados representativos de perfis socioeconômicos. | “Preparação e curadoria de dados” | Documentação do pipeline + checklist de curadoria por lote. | Ferramentas e métricas de balanceamento. |

---

## RF-LC — LangChain (PDF p. 4–5)

| ID | Descrição | Rastreio PDF | Critério de aceite | TBD |
|----|-----------|--------------|---------------------|-----|
| RF-LC-01 | **DEVE** existir pipeline integrando a **LLM customizada** com conhecimento específico. | “Pipeline de integração especializada” | Diagrama + ponto de entrada único para inferência assistida. | Composição FT vs RAG. |
| RF-LC-02 | **DEVE** prever integração com bases: registros ginecológicos e histórico obstétrico; exames preventivos (papanicolau, mamografias etc.); violência doméstica com protocolos de segurança; medicamentos para saúde da mulher. | “Integração com bases…” e lista estruturada | Contratos documentados + **adaptador mock** demonstrável. | Modelo de dados real vs sintético. |
| RF-LC-03 | **DEVE** contextualizar respostas com informações **atualizadas** da paciente quando disponíveis. | “Contextualizar respostas…” | Cenários com/sem contexto; ausência de fatos inventados. | Identidade e autorização de acesso. |
| RF-LC-04 | **DEVE** integrar **calendário menstrual** e **histórico reprodutivo** quando fornecidos. | Mesmo parágrafo | Pelo menos um fluxo ou consulta usando esses dados. | Origem dos dados (manual vs sistema). |
| RF-LC-05 | **DEVE** expor funcionalidades: triagem por sintomas; alertas de preventivos em atraso; padrões suspeitos de violência; encaminhamento multidisciplinar; orientações pós-consulta personalizadas. | “Funcionalidades especializadas” | Cada item mapeado a caso de uso ou nó documentado. | Priorização MoSCoW para MVP/vídeo. |
| RF-LC-06 | **DEVE** permitir acesso a **protocolos atualizados** de **sociedades médicas especializadas**. | Terceiro bullet do pipeline LangChain | Fonte de protocolo versionada ou conector documentado (mock aceito). | Catálogo de sociedades e cadência de atualização. |

---

## RF-LG — LangGraph (PDF p. 5–6)

| ID | Descrição | Rastreio PDF | Critério de aceite | TBD |
|----|-----------|--------------|---------------------|-----|
| RF-LG-00 | Cada fluxo **DEVE** ser implementado com **LangGraph** usando **dados relevantes** para aquele fluxo (não apenas texto genérico sem ligação ao cenário). | “utilizando LangGraph e os dados relevantes para cada um” | Matriz fluxo → fontes de dados / mocks declarados. | Quais dados são obrigatórios por fluxo no MVP. |
| RF-LG-01 | **Fluxo triagem ginecológica:** sintomas → análise de risco → classificação de urgência → sugestão de exames → orientações iniciais → agendamento apropriado. | Texto linear p. 5 | Grafo executável + exemplo; ver [05-langgraph-fluxos.md](05-langgraph-fluxos.md). | Regras de urgência. |
| RF-LG-02 | **Fluxo violência doméstica:** sinais de alerta → avaliação de risco → protocolo de segurança → equipe especializada → documentação segura → seguimento. | Texto linear p. 5 | Grafo + trilha de auditoria descrita. | Acionamento real vs simulado. |
| RF-LG-03 | **Fluxo obstétrico:** dados da gestante → avaliação de risco gestacional → orientações → agendamento de exames → alertas de urgência → acompanhamento contínuo. | Texto linear p. 5–6 | Grafo demonstrado no vídeo (trecho obrigatório). | Definição operacional de acompanhamento contínuo. |
| RF-LG-04 | **Fluxo prevenção:** histórico → exames devidos → orientações preventivas → agendamento automático → lembretes personalizados. | Texto linear p. 5–6 | Grafo com saída de exames/lembretes. | Guidelines de rastreamento por idade/risco. |

---

## RF-SEC — Segurança, validação, explainability (PDF p. 6–7)

| ID | Descrição | Rastreio PDF | Critério de aceite | TBD |
|----|-----------|--------------|---------------------|-----|
| RF-SEC-01 | Limites: **NUNCA** prescrever sem validação de especialista; **NUNCA** diagnosticar definitivamente condições sensíveis; **SEMPRE** encaminhar violência a profissionais qualificados; **SEMPRE** sugerir presencial para sintomas alarmantes; **MANTER** confidencialidade absoluta em violência. | “Limites específicos de atuação” | Guardrails + testes de regressão documentados. | Definições operacionais de “sensível” e “alarmante”. |
| RF-SEC-02 | Protocolos: verificação de identidade (sensível); **criptografia E2E** para dados de violência; alertas à equipe de segurança; emergências críticas; **validação da resposta pelo LLM** antes do retorno para estabilidade e previsibilidade. | “Protocolos de segurança específicos” (o PDF usa “de forma [a] manter…”) | Middleware ou segunda passagem documentada. | Stack criptográfica. |
| RF-SEC-03 | Logging: rastreamento de interações; logs específicos violência; auditoria de acesso; relatórios por especialidade. | “Logging e auditoria especializados” | Esquema de eventos + exemplo de relatório. | Armazenamento e PII. |
| RF-SEC-04 | Explainability: fonte (protocolo, guideline, literatura); raciocínio compreensível; nível de confiança; informação adicional necessária. | “Explainability contextualizada” | Saída estruturada com `fonte`, `confiança`, `lacunas` (ou equivalente). | Formato de serialização. |

---

## Histórias de usuário e prioridades (TLC Specify)

### P1 — MVP (DEVE entregar o desafio)

| ID | História | Por que P1 |
|----|----------|------------|
| US-P1-01 | Como **avaliador**, quero ver **fine-tuning** documentado e reprodutível com dados da mulher, para validar o item 1 do PDF. | Obrigatório p. 3–4 e repositório p. 7. |
| US-P1-02 | Como **avaliador**, quero ver **LangChain** integrando a LLM customizada a conhecimento/bases, para validar o item 2. | Obrigatório p. 4–5 e repositório p. 7. |
| US-P1-03 | Como **avaliador**, quero ver **pelo menos um fluxo LangGraph** completo em execução no vídeo, para validar o item 3 e o roteiro do vídeo p. 8. | Vídeo exige “execução de um fluxo automatizado”. |
| US-P1-04 | Como **avaliador**, quero ver **segurança e validação** (guardrails/logs/explainability) evidenciados, para validar o item 4 e o trecho de vídeo sobre logs. | Obrigatório p. 6–7 e vídeo p. 8. |

### P2 — Forte aderência ao enunciado

| ID | História | Por que P2 |
|----|----------|------------|
| US-P2-01 | Como **profissional**, quero os **quatro** fluxos LangGraph implementados e diagramados, para cobrir integralmente o p. 5–6 e diagramas p. 7. | Enunciado lista quatro fluxos; vídeo pode focar em um, mas entrega integral exige os quatro no código/diagramas. |
| US-P2-02 | Como **instituição**, quero rastreio de **fonte e confiança** nas respostas, para auditabilidade (RF-SEC-04). | Avaliação cita precisão e conformidade. |

### P3 — Elevação de qualidade

| US-P3-01 | Como **equipe multidisciplinar**, quero encaminhamentos sugeridos de forma **culturalmente sensível** e inclusiva (p. 9–10). | Impacto social e sensibilidade ética. |

---

## Critérios testáveis (WHEN / ENTÃO / DEVE)

1. WHEN o repositório for clonado e o pipeline de dados for executado ENTÃO o conjunto de treino **DEVE** estar documentado com anonimização e curadoria (RF-FT-04).  
2. WHEN uma consulta for feita à assistente com contexto de paciente ENTÃO a resposta **NÃO DEVE** afirmar dados clínicos não presentes no contexto (RF-LC-03).  
3. WHEN um sintoma de **alarme** obstétrico for informado no fluxo obstétrico ENTÃO o fluxo **DEVE** priorizar orientação de urgência/presencial (RF-LG-03, RF-SEC-01).  
4. WHEN sinais de **risco** de violência forem detectados ENTÃO o fluxo **DEVE** acionar trilha de segurança e encaminhamento humano sem expor detalhes em canais inseguros (RF-LG-02, RF-SEC-01).  
5. WHEN uma resposta for retornada ao usuário ENTÃO ela **DEVE** incluir indicação de **fonte** e **lacunas** quando aplicável (RF-SEC-04).  
6. WHEN o vídeo de até 15 min for exibido ENTÃO ele **DEVE** cobrir treino/LLM, um fluxo, perguntas contextualizadas e logs/validação (PDF p. 8).

---

## Casos extremos (edge cases)

- WHEN o contexto da paciente estiver **vazio** ENTÃO o sistema **DEVE** degradar com segurança (perguntas esclarecedoras ou abstinência), sem inventar prontuário.  
- WHEN o usuário solicitar **prescrição** ou **diagnóstico definitivo** de condição sensível ENTÃO o sistema **DEVE** recusar e orientar validação humana/presencial (RF-SEC-01).  
- WHEN dados de violência forem tratados ENTÃO logs **NÃO DEVEM** duplicar conteúdo sensível em canais genéricos (RF-SEC-03).

---

## Rastreabilidade de requisitos (status para SDD)

| Requirement ID | Story / área | Fase SDD sugerida | Status |
|------------------|--------------|-------------------|--------|
| RF-FT-01 … 04 | US-P1-01 | Design dados + tasks treino | Pending |
| RF-LC-01 … 06 | US-P1-02 | Design pipeline | Pending |
| RF-LG-00 … 04 | US-P1-03 / US-P2-01 | Design grafos | Pending |
| RF-SEC-01 … 04 | US-P1-04 | Design segurança | Pending |

**Cobertura:** 18 requisitos funcionais listados; mapear cada um a tasks na fase de implementação.

---

## Open questions para SDD

- Unificar RF-LC e RF-LG em um **mapa de capacidades** com dependências de dados?
- Definir **perfil de usuário** (médico vs paciente) por fluxo e impacto em RF-SEC-02.
- Matriz **MoSCoW** para RF-LC-05 vs duração do vídeo (15 min).
