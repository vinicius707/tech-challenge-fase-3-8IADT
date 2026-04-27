# Visão e escopo — Assistente virtual em saúde da mulher

**Fonte:** `8IADT - Fase 3 - Tech challenge Secretaria.pdf` (Tech Challenge, Fase 3)  
**Propósito deste documento:** delimitar problema, objetivos e escopo para refinamento em SDD (arquitetura, APIs, dados operacionais).

## 1. Problema

Uma rede hospitalar especializada deseja evoluir de automação de análises de exames para um **assistente virtual médico** focado em **saúde e segurança da mulher**, capaz de:

- apoiar condutas clínicas alinhadas a protocolos institucionais;
- responder dúvidas de profissionais especializados;
- sugerir procedimentos com base em protocolos internos;
- orquestrar **fluxos de decisão automatizados e seguros** (exames pendentes, tratamentos reprodutivos, alertas de violência doméstica, coordenação multidisciplinar), com sensibilidade ao contexto de atendimento feminino.

## 2. Objetivo do produto (nível spec)

Desenvolver um assistente de **apoio à decisão** (não substituto do profissional) que combine:

1. **LLM ajustada ao domínio** (fine-tuning com dados curados e anonimizados da área).
2. **Orquestração LangChain** (pipeline, contexto, integrações conceituais com bases e protocolos).
3. **Fluxos LangGraph** para cenários clínicos definidos no desafio.
4. **Camadas de segurança, privacidade, auditoria e explicabilidade** compatíveis com dados sensíveis e LGPD.

## 3. Stakeholders implícitos

- **Paciente / usuária final** (quando houver interface direta): privacidade, linguagem respeitosa, encaminhamentos seguros.
- **Profissionais de saúde** (ginecologia, obstetrícia, psicologia, assistência social, equipe de segurança): validação clínica, auditoria, limites do sistema.
- **Instituição / TI / compliance**: logs, controle de acesso, conformidade regulatória.
- **Avaliadores acadêmicos** (Fase 3): repositório, relatório, diagramas, vídeo demonstrativo.

## 4. Glossário mínimo

| Termo | Significado neste projeto |
|-------|---------------------------|
| Assistente | Agente de software que combina LLM + ferramentas + fluxos; **ferramenta de apoio**, não prescrição autônoma definitiva. |
| Protocolo | Diretriz institucional ou de sociedade médica usada como fonte de conduta ou evidência citável. |
| Fluxo (LangGraph) | Grafo de estados/decisões com entradas, transições e saídas padronizadas para um cenário clínico. |
| Dado sensível | Inclui violência doméstica, saúde mental, reprodução; exige anonimização e controles reforçados. |

## 5. Dentro do escopo (spec)

- Fine-tuning de LLM com corpus médico da mulher (conforme lista do PDF).
- Pipeline LangChain integrando modelo customizado e **interfaces** para bases estruturadas e protocolos.
- Quatro fluxos LangGraph: triagem ginecológica, violência doméstica, obstétrico, prevenção.
- Módulos de segurança, validação de respostas, logging/auditoria e explainability.
- Dataset anonimizado ou **exemplos sintéticos** representativos + documentação do processo.

## 6. Fora do escopo explícito (nesta spec)

- Definir stack de hospedagem, framework web ou banco específico (fica para SDD).
- Substituir julgamento clínico humano ou prescrever medicação **sem** validação de especialista (proibido pelo próprio desafio).
- Garantir certificação regulatória de software médico (não exigida no texto; aderência a boas práticas e LGPD como **objetivo de desenho**).

## 7. Premissas e restrições

- Uso de **LangChain** e **LangGraph** como tecnologias de orquestração/fluxo obrigatórias no enunciado.
- **LGPD** e sensibilidade cultural como restrições de produto e engenharia.
- Idioma e tom: inclusivos e adaptáveis a contextos socioeconômicos diversos (meta-qualidade).

---

## Open questions para SDD

- Qual **LLM base** e licença (ex.: família LLaMA, Falcon, outro) e ambiente de treino?
- O assistente atende **só profissionais** ou também pacientes? Isso altera UX, consentimento e logs.
- Integração com **sistemas hospitalares reais** é mock, API genérica ou protótipo desacoplado?
- Critérios quantitativos mínimos de **qualidade do modelo** (métricas, limiares, conjunto de teste) além do relatório qualitativo.
- Política de **retenção** de logs e segregação de logs de violência doméstica.
