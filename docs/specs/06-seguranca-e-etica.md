# Segurança, ética e conformidade cultural

**Fonte:** Tech Challenge Fase 3 — item 4 (segurança e validação), “Considerações éticas específicas”, critérios de avaliação.

## 1. Regras normativas (do PDF)

| Tipo | Regra |
|------|--------|
| NUNCA | Prescrever medicações sem **validação de especialista**. |
| NUNCA | Diagnosticar **definitivamente** condições sensíveis. |
| SEMPRE | Encaminhar casos suspeitos de **violência** a profissionais qualificados. |
| SEMPRE | Sugerir consulta **presencial** para sintomas alarmantes. |
| MANTER | **Confidencialidade absoluta** em casos de violência doméstica. |

Implementação: políticas como **guardrails** de saída, listas de verificação no LangGraph e validação pré-retorno (RF-SEC-02).

## 2. Protocolos de segurança específicos

- **Verificação de identidade** em casos sensíveis (quem pergunta é o profissional autorizado? — TBD implementação).
- **Criptografia end-to-end** para dados de violência doméstica (alvo de desenho; nível acadêmico pode ser documental + protótipo parcial).
- **Alertas automáticos** para equipe de segurança em risco crítico.
- **Protocolos de emergência** para situações críticas (encaminhamento a urgência, mensagens padronizadas).
- **Validação da resposta pelo LLM** antes do retorno: segunda passagem, verificador, ou modelo crítico (TBD).

## 3. Logging e auditoria

Conforme PDF e RF-SEC-03:

- Rastreamento detalhado das interações (correlation ID, timestamp, versão do modelo).
- Logs **específicos** para trilha de violência (conteúdo mínimo, segregação).
- Auditoria de acesso a dados sensíveis (quem leu o quê).
- Relatórios de utilização por especialidade médica.

## 4. Explainability contextualizada

- Indicar **fonte** (protocolo interno, guideline nomeado, literatura).
- Expor **raciocínio clínico** em linguagem compreensível ao público-alvo definido no SDD.
- Exibir **nível de confiança** (calibrado ou heurístico — TBD).
- Destacar **necessidade de informação adicional** antes de conclusões fortes.

## 5. Considerações éticas (resumo acionável)

### Privacidade e confidencialidade

- Proteção extrema de dados de violência doméstica.
- Anonimização rigorosa de dados reprodutivos.
- Controle de acesso por necessidade médica.
- Instrumentos de aderência à **LGPD**.

### Bias e equidade

- Representatividade étnica e socioeconômica no treino e avaliação.
- Validação em populações diversas.
- Atenção explícita a disparidades de acesso à saúde no relatório.

### Responsabilidade médica

- Assistente como **ferramenta de apoio**, nunca substituto.
- Validação obrigatória por especialistas em cenários de produção.
- Documentação clara de **limitações** do sistema.

### Sensibilidade cultural

- Linguagem inclusiva e respeitosa.
- Consideração a aspectos culturais e religiosos (sem substituir autonomia da paciente).
- Adaptação a diferentes contextos socioeconômicos (tom e exemplos).

## 6. Critérios de avaliação (alinhamento do produto)

1. Precisão médica especializada.  
2. Segurança da paciente.  
3. Sensibilidade ética.  
4. Aplicabilidade prática em ambiente clínico.  
5. Impacto social.  
6. Conformidade regulatória (dados médicos).

Estes itens devem aparecer como **seção explícita** no relatório técnico e, quando possível, evidências no vídeo.

---

## Open questions para SDD

- Definição operacional de “**validação de especialista**” no protótipo (mock, fila humana, duplo controle offline).
- Política de **retenção** e **direito ao esquecimento** em logs de violência.
- Como evitar **re-identificação** em relatórios agregados.
- Tratamento de crenças culturais que conflitem com evidência clínica (escalação humana).
