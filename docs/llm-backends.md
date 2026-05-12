# LLM Backends - IA Core

Este documento descreve como selecionar e configurar os backends de LLM da
Fase D do fluxo SDD `IA Core e Orquestração Clínica`. A interface `LlmBackend`
fica em `fase3_orquestracao/llm_backend.py` e a configuração canônica em
`config/model_backends.yaml`.

## Princípios

- LangGraph e demais módulos da Fase F dependem apenas da classe
  `LlmBackend`. Nenhum provider específico (OpenAI, Ollama, LoRA local) deve
  ser acoplado ao restante do código.
- Safety e fluxos clínicos não podem depender exclusivamente do LLM
  (`docs/sdd/ia-core/design.md` §8). O backend é uma das peças, nunca a única.
- O backend **default da demo** é `ollama` local (decisão D9 do SDD), e o
  backend `stub_safe` permanece sempre disponível para CI, gates e fallback
  controlado, sem nenhuma chave ou modelo externo.
- Chaves de API ficam em variáveis de ambiente. **Nada de chave em arquivo
  versionado.**

## Backends disponíveis

| Nome              | Tipo                | Quando usar |
|-------------------|---------------------|-------------|
| `ollama`          | `openai_compatible` | **Default da demo.** Servidor Ollama local via API OpenAI-compatible. |
| `stub_safe`       | `stub`              | CI, gates locais e fallback offline determinístico. |
| `openai_compatible` | `openai_compatible` | OpenAI, Azure OpenAI, Together, Anyscale, etc. Opcional. |
| `local_lora`      | `placeholder`       | Slot reservado para o LoRA fine-tuned (Fase H). |

A definição completa fica em `config/model_backends.yaml`. Qualquer alteração
de modelo, base URL ou nome de variável de ambiente é feita nesse arquivo,
sem precisar tocar no código Python.

## Seleção do backend ativo

A prioridade de resolução está implementada em `resolve_backend_name`:

1. Argumento explícito passado para `create_backend(name)` ou `--backend`.
2. Variável de ambiente `IA_LLM_BACKEND`.
3. Chave `default_provider` em `config/model_backends.yaml` (também aceita
   o nome legado `default`).
4. Fallback final de segurança: `stub_safe`.

## Backend `ollama` (default)

Mesma implementação OpenAI-compatible, apontando para o Ollama local na porta
`11434`. Defaults registrados no YAML:

| Variável | Valor padrão |
|----------|--------------|
| `OLLAMA_API_KEY` | `ollama` (token simbólico aceito pelo Ollama). |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434/v1` (também aceita `http://127.0.0.1:11434`; o sufixo `/v1` é anexado automaticamente). |
| `OLLAMA_MODEL` | `llama3.2:3b` |

> A normalização vale para qualquer URL Ollama: passe `http://host:11434` ou `http://host:11434/v1` indistintamente. URLs com path explícito diferente de `/v<n>` permanecem intactas.

Pré-requisitos:

```bash
# instalar e iniciar
ollama serve &
ollama pull llama3.2:3b
```

Teste:

```bash
# o default ja seleciona ollama; --backend e opcional aqui
python -m fase3_orquestracao.llm_backend \
  --prompt "Quais red flags em consulta obstétrica?"
```

`model_version` fica como `ollama:<modelo>` (ex.: `ollama:llama3.2:3b`),
permitindo que a UI valide que a resposta não veio do stub.

Para sobrescrever o modelo sem editar o YAML:

```bash
OLLAMA_MODEL=llama3.1:8b python -m fase3_orquestracao.llm_backend --prompt "..."
```

## Backend `stub_safe`

Sem dependências externas. Útil para gates locais, CI e desenvolvimento
offline. Pode ser forçado via env var, mesmo com Ollama disponível:

```bash
source .venv/bin/activate
IA_LLM_BACKEND=stub_safe python -m fase3_orquestracao.llm_backend \
  --prompt "Como orientar paciente com preventivo atrasado?"
```

A saída contém `model_version=stub-safe-0.1.0` e marcadores `[modo:stub]`,
sem chamar qualquer rede externa.

## Backend `openai_compatible`

Funciona com qualquer provider que siga o protocolo da API OpenAI (OpenAI,
Azure OpenAI, Together, Anyscale, etc.). Permanece como **opção** quando o
Ollama local não atender. As env vars padrão (configuráveis no YAML) são:

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `OPENAI_API_KEY` | Sim | Chave do provedor. Nunca commit. |
| `OPENAI_BASE_URL` | Não | URL base alternativa (Azure, Together, etc.). |
| `OPENAI_MODEL` | Não | Modelo (default `gpt-4o-mini`). |

Exemplo de teste com env vars (substitua pelos valores reais):

```bash
export IA_LLM_BACKEND=openai_compatible
export OPENAI_API_KEY=sk-...redacted...
# opcional: outro provedor compatível
# export OPENAI_BASE_URL=https://api.together.xyz/v1
# export OPENAI_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct

python -m fase3_orquestracao.llm_backend \
  --backend openai_compatible \
  --prompt "Liste sinais de alarme em sangramento na gestação."
```

`model_version` fica no formato `openai_compatible:<modelo>`. A chave nunca
aparece nos logs ou erros.

## Backend `local_lora`

Reserva o slot para o LoRA fine-tuned entregue pela Fase H. Hoje qualquer
chamada falha com mensagem clara apontando para esta seção - **não simulamos
resposta para não confundir avaliação clínica**.

Quando o adaptador estiver disponível (Fase H), o procedimento previsto é:

1. Materializar o adaptador em `outputs/model/` conforme
   `fase2_finetuning/validate_adapters.py`.
2. Atualizar este documento e `config/model_backends.yaml` com o caminho e
   os parâmetros de carregamento (modelo base, dtype, dispositivo).
3. Substituir `LocalLoraBackend` por uma implementação que carregue o
   adaptador via `peft.PeftModel.from_pretrained` ou equivalente, mantendo a
   mesma interface assíncrona `generate`.

Até lá, qualquer integração que precise de fine-tuning deve cair de volta
em `stub_safe` ou `openai_compatible`.

## Integração com o endpoint `/v1/chat/stream` (polish via LLM real)

A partir da Fase G, o endpoint SSE chama o backend ativo para **reescrever**
em português clínico o rascunho determinístico produzido pelos grafos
LangGraph (RAG + guardrails). A integração é controlada por env vars:

| Variável | Default | Efeito |
|----------|---------|--------|
| `IA_LLM_POLISH` | `auto` (ligado para qualquer backend != `stub_safe`) | `0`/`false`/`off`/`no` desativa explicitamente o polish e força uso do rascunho determinístico. |
| `IA_LLM_POLISH_TIMEOUT_S` | `45` | Timeout em segundos para `LlmBackend.generate()`. Atingido => fallback automático para o rascunho, sem quebrar o SSE. |
| `IA_LLM_POLISH_TEMPERATURE` | `0.2` | Temperatura usada na chamada de polish (clamp entre 0 e 1). |

Fluxo de segurança:

1. O grafo executa normalmente (RAG + guardrails da Fase E) e produz o rascunho determinístico autoritativo.
2. Se o backend ativo for real (Ollama, OpenAI-compatible, …), o IA Core monta um prompt com o rascunho como fonte factual + regras (PT-BR, sem prescrição, sem diagnóstico definitivo, sem inventar fontes) e chama `backend.generate(...)`.
3. A saída do LLM passa novamente pelo `ResponseValidator` (Fase E). Se for bloqueada, vazia ou exceder o timeout, o IA Core mantém o rascunho determinístico e emite `log` com o motivo (`timeout`, `llm_error`, `empty_output`, `blocked_by_guardrails`).
4. Quando o polish for bem-sucedido, o `log` inclui `llm_polish ok: resposta reescrita por <modelVersion>` antes do primeiro `token`.

Esse desenho garante que o LLM realmente **gera** a resposta visível ao usuário sem permitir que ele violar guardrails clínicos ou substituir o pipeline determinístico.

## Boas práticas operacionais

- Use `IA_LLM_BACKEND=stub_safe` em CI e nos gates determinísticos das
  fases B e C, para evitar dependência de Ollama no pipeline.
- Para a demo principal, mantenha o Ollama rodando e o modelo já puxado
  (`ollama pull <modelo>`) antes de subir o serviço Python.
- Para usar OpenAI/Azure, exporte env vars na sessão e remova-as ao
  encerrar (`unset OPENAI_API_KEY`).
- Quando trocar de modelo, atualize `config/model_backends.yaml` em vez de
  fixar nomes no código.
- Logs devem usar `backend.model_version`, nunca chaves ou URLs com token.

## Referências

- `fase3_orquestracao/llm_backend.py` - implementação.
- `config/model_backends.yaml` - configuração canônica.
- `docs/sdd/ia-core/design.md` §8 - design.
- `docs/sdd/ia-core/spec.md` IA-SVC-02 - critério de aceite.
- `docs/sdd/ia-core/tasks.md` IA-D1 a IA-D4 - tarefas executadas.
