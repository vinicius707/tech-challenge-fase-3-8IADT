# Visão e escopo — Assistente virtual em saúde da mulher

**Documento oficial:** [8IADT - Fase 3 - Tech challenge Secretaria.pdf](../../8IADT%20-%20Fase%203%20-%20Tech%20challenge%20Secretaria.pdf) (11 páginas)  
**Propósito:** contrato de alto nível entre o enunciado da Fase 3 e o SDD (arquitetura, APIs, dados operacionais).

## 1. Contexto acadêmico (PDF p. 2)

- O **Tech Challenge** integra as disciplinas da fase; desenvolvimento **em grupo** (princípio do enunciado).
- Atividade **obrigatória**; atenção ao **prazo de entrega** definido pela instituição.
- Peso: **90%** da nota de **todas** as disciplinas da fase (reforça criticidade da entrega completa).

## 2. Problem statement (PDF p. 2–3)

Após automação de análises de exames e modelos para saúde da mulher, a rede hospitalar quer um **assistente virtual médico** que:

- seja treinado com **dados próprios** da instituição (direção de produto: especialização + governança de dados);
- **auxilie condutas** clínicas em saúde feminina, **responda dúvidas** de profissionais especializados e **sugira procedimentos** segundo **protocolos internos**;
- organize **fluxos de decisão automatizados e seguros**: exames ginecológicos pendentes, questões reprodutivas, **alertas** para suspeita de **violência doméstica**, **coordenação multidisciplinar** (ginecologista, psicóloga, assistente social), com **LangChain** e sensibilidade ao atendimento feminino.

## 3. Objetivo do produto (PDF p. 2–3)

Desenvolver assistente virtual de atendimento médico em **saúde e segurança da mulher** que combine:

1. **Fine-tuning** de LLM com dados específicos da área (exemplos no PDF: LLaMA, Falcon ou outro).
2. **Fluxos automatizados** de decisão clínica via **LangChain** (e **LangGraph** nos fluxos descritos; ver [01-requisitos-funcionais.md](01-requisitos-funcionais.md)).
3. **Protocolos de segurança, privacidade** e **sensibilidade cultural** do atendimento feminino.

## 4. Metas mensuráveis (alinhadas ao PDF)

- [ ] Existe **pipeline reprodutível** de fine-tuning com dados curados e anonimizados da saúde da mulher (p. 3–4, 7).
- [ ] Existe **assistente** com pipeline **LangChain** integrando LLM customizada a conhecimento e bases conceituais (p. 4–5, 7).
- [ ] Existem **quatro fluxos** implementados com **LangGraph**, cada um usando **dados relevantes** ao cenário (p. 5–6).
- [ ] Existem **módulos** de segurança, validação, logging/auditoria e explainability conforme item 4 do PDF (p. 6–7).
- [ ] Há **dataset anonimizado** ou **dados sintéticos** representativos no repositório (p. 7).
- [ ] Há **relatório técnico**, **diagramas** dos fluxos e **vídeo** ≤ 15 min com os itens obrigatórios (p. 7–8).

## 5. Stakeholders implícitos

- **Paciente / usuária** (se houver canal direto): privacidade, dignidade, encaminhamento seguro.
- **Profissionais** (GO, psicologia, assistência social, segurança): validação, auditoria, limites do sistema.
- **Instituição / TI / compliance**: LGPD, controles de acesso, rastreabilidade.
- **Avaliadores Fase 3**: código, relatório, diagramas, vídeo e aderência aos **seis critérios de avaliação** (p. 10).

## 6. Glossário mínimo

| Termo | Significado neste projeto |
|-------|---------------------------|
| Assistente | LLM + orquestração (LangChain/LangGraph) + políticas; **apoio à decisão**, não substituto legal/clínico do profissional. |
| Protocolo | Diretriz institucional ou de sociedade médica citável na resposta (explainability). |
| Fluxo (LangGraph) | Grafo de estados para um cenário clínico; deve consumir **dados relevantes** àquele fluxo (PDF p. 5). |
| Dado sensível | Violência doméstica, saúde mental, reprodução; exige anonimização e controles reforçados. |

## 7. Dentro do escopo (spec)

- Itens 1–4 das **Entregas técnicas** obrigatórias (PDF p. 3–7): fine-tuning, LangChain, LangGraph, segurança e validação.
- **Entregáveis da Fase 3** (PDF p. 7–8): repositório, relatório, diagramas, avaliação do modelo, vídeo.
- Considerações **éticas** e instrumentos de **LGPD** (PDF p. 9).

## 8. Fora do escopo explícito (nesta spec)

| Exclusão | Motivo |
|----------|--------|
| Stack de hospedagem, framework web, SGBD específico | Não prescritos no PDF; SDD escolhe. |
| Prescrição ou diagnóstico definitivo autônomo | **Proibido** pelos limites do PDF (p. 6). |
| Certificação de produto como software médico regulado | Não exigida no texto; aderência a boas práticas e LGPD como meta de desenho. |

## 9. Restrições tecnológicas e de conformidade

- **LangChain** para pipeline e integração (PDF p. 3–5).
- **LangGraph** para cada fluxo de atendimento descrito (PDF p. 5–6).
- **LGPD** e normas de proteção de dados médicos como referência de conformidade (PDF p. 9–10).
- Fine-tuning: modelo tipo **LLaMA**, **Falcon** ou **outro** explicitamente permitido no enunciado (PDF p. 3).

## 10. Critérios de sucesso da avaliação (PDF p. 10)

O trabalho será julgado, entre outros ângulos, por:

1. Precisão médica especializada (diretrizes de sociedades médicas).  
2. Segurança da paciente (proteção e detecção de riscos).  
3. Sensibilidade ética (questões sensíveis).  
4. Aplicabilidade prática em ambiente clínico.  
5. Impacto social no atendimento à mulher.  
6. Conformidade regulatória em proteção de dados médicos.

Mensagem de encerramento do PDF (p. 10): priorizar **segurança, privacidade e bem-estar feminino**, com **validação contínua** por profissionais especializados.

---

## Open questions para SDD

- LLM base, licença e ambiente de treino reprodutível.
- Público-alvo primário: **somente profissionais** vs interface também para paciente.
- Integração hospitalar: **mock**, **API genérica** ou acoplamento real.
- Métricas quantitativas mínimas e limiares de aceite para o modelo.
- Política de retenção e segregação de logs em trilhas de violência doméstica.
