# Requisitos funcionais

**Fonte:** Tech Challenge Fase 3 — PDF Secretaria (requisitos obrigatórios e entregáveis).  
**Convenção:** cada requisito possui ID, descrição, critério de aceite (quando aplicável), **TBD** para refinamento no SDD.

---

## RF-FT — Fine-tuning e corpus

| ID | Descrição | Critério de aceite | TBD |
|----|-----------|-------------------|-----|
| RF-FT-01 | O sistema deve suportar fine-tuning de um LLM com **protocolos** de: atendimento ginecológico e obstétrico; identificação e manejo de violência doméstica; triagem câncer de mama e colo; emergências obstétricas; saúde mental da mulher (ex.: depressão pós-parto, ansiedade); planejamento familiar e saúde reprodutiva. | Corpus versionado + traço de quais protocolos foram ingeridos por versão do modelo. | Formato dos protocolos; fonte única vs múltiplas. |
| RF-FT-02 | O corpus deve incluir **FAQs** alinhadas a: contraceptivos; ciclos menstruais e distúrbios hormonais; sinais de alerta gravidez/pós-parto; sinais de violência doméstica; amamentação e neonatal; menopausa e climatério. | Conjunto de exemplos (Q/A ou instrução) mapeado por tema. | Esquema de rotulagem e validação por especialista. |
| RF-FT-03 | O corpus deve contemplar **documentos-modelo** (estrutura ou texto sintético): laudos mamografia/USG ginecológico; receitas terapias hormonais; colposcopia/biópsias; relatórios atendimento violência; protocolos pré-natal e puerpério. | Amostras anonimizadas ou sintéticas por tipo de documento. | Grau de desidentificação exigido por tipo. |
| RF-FT-04 | Pipeline de dados deve aplicar **preprocessamento** para terminologia médica feminina; **anonimização rigorosa** (violência, saúde mental); **curadoria** com validação por especialistas em GO; **balanceamento** entre condições e faixas etárias; **representatividade** socioeconômica. | Documentação do pipeline + checklist de curadoria por lote. | Ferramentas e métricas de balanceamento. |

---

## RF-LC — LangChain (pipeline e funcionalidades)

| ID | Descrição | Critério de aceite | TBD |
|----|-----------|-------------------|-----|
| RF-LC-01 | Deve existir **pipeline** integrando LLM customizada (fine-tuned) com conhecimento específico (RAG adicional é opcional no SDD, mas integração “com conhecimento” deve estar explícita). | Diagrama de componentes + ponto único de entrada da aplicação para inferência assistida. | Estratégia híbrida FT vs RAG. |
| RF-LC-02 | O pipeline deve prever **integração conceitual** com bases: prontuários ginecológicos/obstétricos; histórico de exames preventivos; registros de violência (com protocolo de segurança); medicamentos específicos saúde da mulher. | Interfaces (contratos) documentadas; pelo menos um **adaptador mock** demonstrável. | Modelo de dados real vs sintético. |
| RF-LC-03 | Deve contextualizar respostas com **informações atualizadas da paciente** quando disponíveis. | Testes com cenários: com/sem contexto de paciente; resposta referencia dados fornecidos sem inventar fatos. | Identificador de paciente e autorização. |
| RF-LC-04 | Deve integrar **calendário menstrual** e **histórico reprodutivo** quando fornecidos. | Fluxo demonstra uso desses dados em pelo menos uma consulta contextualizada. | Fonte do calendário (manual vs integração). |
| RF-LC-05 | Funcionalidades: **triagem** automática por sintomas específicos; **alertas** exames preventivos atrasados; **padrões suspeitos** violência doméstica; **encaminhamento** multidisciplinar; **orientações pós-consulta** personalizadas. | Cada funcionalidade mapeada a um caso de uso ou nó LangGraph/LangChain documentado. | Prioridade entre funcionalidades para MVP. |

---

## RF-LG — LangGraph (fluxos automatizados)

| ID | Descrição | Critério de aceite | TBD |
|----|-----------|-------------------|-----|
| RF-LG-01 | **Fluxo triagem ginecológica:** sintomas → análise de risco → classificação urgência → sugestão exames → orientações iniciais → agendamento apropriado. | Grafo executável ou especificação equivalente + exemplo de execução. | Regras de urgência e SLAs. |
| RF-LG-02 | **Fluxo violência doméstica:** sinais alerta → avaliação risco → protocolo segurança → equipe especializada → documentação segura → seguimento. | Grafo com ramos de alto risco e trilha de auditoria descrita. | Contatos reais vs simulados. |
| RF-LG-03 | **Fluxo obstétrico:** dados gestante → avaliação risco gestacional → orientações → agendamento exames → alertas urgência → acompanhamento contínuo. | Grafo cobrindo ciclo mínimo demonstrado no vídeo. | Definição de “acompanhamento contínuo” (frequência, canais). |
| RF-LG-04 | **Fluxo prevenção:** histórico → exames devidos → orientações preventivas → agendamento automático → lembretes personalizados. | Grafo com entrada de histórico e saída de lista de exames/lembretes. | Calendário de preventivos por guideline. |

Detalhamento de estados e diagramas: [05-langgraph-fluxos.md](05-langgraph-fluxos.md).

---

## RF-SEC — Segurança, validação e explainability

| ID | Descrição | Critério de aceite | TBD |
|----|-----------|-------------------|-----|
| RF-SEC-01 | **Limites:** nunca prescrever sem validação especialista; nunca diagnosticar definitivamente condições sensíveis; sempre encaminhar violência a qualificados; sempre sugerir presencial para sintomas alarmantes; confidencialidade absoluta em violência. | Políticas implementadas como guardrails + testes de regressão linguísticos (lista negativa/positiva). | Formalização de “condição sensível” e “alarmante”. |
| RF-SEC-02 | **Protocolos segurança:** verificação identidade casos sensíveis; criptografia E2E para dados violência; alertas automáticos equipe segurança; protocolos emergência crítica; **validação da resposta pelo LLM** antes do retorno (estabilidade/previsibilidade). | Documentação + evidência no código ou middleware de validação. | Implementação criptográfica concreta. |
| RF-SEC-03 | **Logging/auditoria:** rastreamento interações; logs específicos violência; auditoria acesso dados sensíveis; relatórios utilização por especialidade. | Esquema de eventos de log e exemplo de relatório agregado. | Onde armazenar logs e PII. |
| RF-SEC-04 | **Explainability:** indicar fonte (protocolo, guideline, literatura); explicar raciocínio de forma compreensível; nível de confiança; destacar necessidade de informação adicional. | Respostas estruturadas com campos `fonte`, `confiança`, `lacunas` (ou equivalente). | Formato JSON vs markdown clínico. |

---

## Open questions para SDD

- Unificar RF-LC e RF-LG em um único **mapa de capacidades** com dependências?
- Definir **perfil de usuário** (médico vs paciente) por fluxo e impacto em RF-SEC-02 (identidade).
- Matriz de **prioridade MoSCoW** para RF-LC-05 vs tempo do vídeo (15 min).
