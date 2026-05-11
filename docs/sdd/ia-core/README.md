# SDD - IA Core

Este pacote de especificacoes transforma as lacunas identificadas em `LACUNAS_IMPLEMENTACAO_TECH_CHALLENGE_FASE3.md` em um fluxo SDD implementavel para o projeto da Fase 3.

Arquivos:

- `context.md` - contexto, decisoes, escopo e restricoes.
- `spec.md` - requisitos funcionais, historias, criterios testaveis e rastreabilidade.
- `design.md` - arquitetura tecnica, contratos, schemas, fluxos e integracao com o BFF existente.
- `tasks.md` - backlog por fases, dependencias e gates de validacao.

Escopo principal:

- Pipeline de dados de saude da mulher.
- Fine-tuning LoRA/QLoRA.
- Servico Python de orquestracao.
- LangChain/RAG com fontes reais.
- Quatro fluxos LangGraph reais.
- Guardrails, auditoria e explainability no backend de IA.
- Avaliacao e relatorio final.

Uso recomendado:

1. Ler `context.md` para alinhar as premissas.
2. Validar `spec.md` como contrato funcional.
3. Implementar seguindo `design.md`.
4. Executar `tasks.md` fase a fase, sem pular gates.
