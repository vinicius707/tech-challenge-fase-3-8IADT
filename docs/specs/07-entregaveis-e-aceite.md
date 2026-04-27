# Entregáveis e definição de pronto (DoD)

**Fonte:** Tech Challenge Fase 3 — “Entregáveis da Fase 3” e critérios de avaliação.

## 1. Repositório Git (código-fonte)

O repositório deve conter, conforme PDF:

- [ ] Pipeline de **fine-tuning** para dados de saúde da mulher.
- [ ] Integração **LangChain** especializada (orquestração + tools/mocks documentados).
- [ ] **Fluxos LangGraph** para os cenários clínicos obrigatórios (quatro fluxos).
- [ ] **Dataset anonimizado** ou **exemplos sintéticos** específicos + instruções de uso.
- [ ] **Módulos de segurança e validação** (guardrails, validação pré-resposta, logging onde aplicável).

**DoD spec:** README raiz aponta para `docs/specs/`; instruções reproduzem treino mínimo e execução de um fluxo.

## 2. Relatório técnico detalhado

### Fine-tuning

- [ ] Metodologia de curadoria de dados específicos.
- [ ] Técnicas de anonimização para dados sensíveis.
- [ ] Métricas de avaliação para domínio médico feminino.
- [ ] Validação por especialistas em ginecologia e obstetrícia (processo e resultados).

### Assistente especializado

- [ ] Capacidades específicas para saúde da mulher.
- [ ] Limitações e protocolos de segurança.
- [ ] Integração com sistemas hospitalares especializados (real ou simulada, claramente indicado).
- [ ] Casos de uso e cenários de aplicação.

### Diagramas LangChain/LangGraph

- [ ] Fluxograma triagem ginecológica.
- [ ] Protocolo detecção violência doméstica.
- [ ] Fluxo obstétrico e emergências.
- [ ] Sistema prevenção e acompanhamento.

**Nota:** Os diagramas Mermaid em [05-langgraph-fluxos.md](05-langgraph-fluxos.md) podem ser reutilizados ou exportados para o relatório.

### Avaliação do modelo

- [ ] Métricas de precisão por condição (ou tópico).
- [ ] Análise de bias e equidade demográfica.
- [ ] Avaliação de segurança e adequação ética.
- [ ] Feedback de profissionais especializados.

## 3. Vídeo (até 15 minutos)

Demonstrar obrigatoriamente (checklist do PDF):

- [ ] Treinamento e funcionamento da **LLM personalizada**.
- [ ] Execução de **um fluxo automatizado** (LangGraph).
- [ ] Resposta a **perguntas clínicas contextualizadas**.
- [ ] **Logs e validação** das respostas (painel, terminal estruturado ou trace).

## 4. Definição de pronto agregada (Fase 3)

| Área | Pronto quando |
|------|----------------|
| Código | CI básico (lint/test) se adotado no SDD; ao mínimo, `README` com setup e comandos verificados. |
| Dados | Amostra reprodutível sem PII real; licenças citadas. |
| Segurança | Regras NUNCA/SEMPRE demonstráveis em teste manual ou automatizado. |
| Comunicação | Relatório + vídeo + diagramas referenciados no repositório. |

---

## Open questions para SDD

- Formato do relatório (PDF no repo vs link externo privado).
- Onde publicar o vídeo (YouTube não listado, Drive institucional).
- Idioma do vídeo e legendas (pt-BR recomendado pelo contexto acadêmico).
