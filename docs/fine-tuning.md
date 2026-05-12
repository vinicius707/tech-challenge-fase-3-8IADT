# Fine-tuning LoRA/QLoRA — distribuição de artefatos (Fase H)

Documenta como o adapter LoRA gerado em `fase2_finetuning/` é treinado, validado e distribuído. Cobre **IA-H5** do SDD (`docs/sdd/ia-core/tasks.md`) e atende ao gate **IA-FT-02** (`docs/sdd/ia-core/spec.md`).

> O fine-tuning deste projeto é um **ajuste de formato e linguagem** dos quatro fluxos clínicos. Ele não substitui RAG, guardrails ou o roteador clínico. Pesos pesados nunca vão para o Git deste repositório.

## 1. O que entra no Git

Versionamos apenas:

- `fase2_finetuning/train_lora.py` — pipeline (LoRA + QLoRA via TRL).
- `fase2_finetuning/validate_adapters.py` — gate IA-FT-02.
- `fase2_finetuning/FemCare_FineTuning_Colab.ipynb` — receita Colab.
- `outputs/model/metadata.json` — sha256 dos splits, hiperparâmetros, canal externo do adapter.
- `outputs/reports/finetuning_validation.md` — saída do gate (não versionado: regenerável).
- `docs/fine-tuning.md` — este documento.

O `.gitignore` bloqueia `outputs/model/*` com exceção explícita para `metadata.json` e `.gitkeep`. Não tente forçar commit de `adapter_model.safetensors` ou similar.

## 2. Pipeline reproduzível

### 2.1 Modo dry-run (sem GPU, local ou CI)

```bash
python -m pip install -r requirements.txt
python fase1_dados/build_dataset.py          # gera data/train.jsonl e data/val.jsonl
python fase2_finetuning/train_lora.py --dry-run
python fase2_finetuning/validate_adapters.py
```

O dry-run não baixa modelos nem usa GPU. Ele:

1. Valida que `data/train.jsonl` e `data/val.jsonl` existem, têm exemplos e respeitam o schema `{domain, messages[…]}`.
2. Calcula `sha256` de cada split.
3. Gera `outputs/model/metadata.json` com `mode=dry_run`, hiperparâmetros canônicos e instruções de publicação.
4. Permite que o avaliador rode o gate IA-FT-02 sem GPU.

### 2.2 Treino real (Colab T4/A100 ou workstation com GPU)

1. Abra `fase2_finetuning/FemCare_FineTuning_Colab.ipynb` no Google Colab e selecione runtime **GPU**.
2. Execute as células em ordem; ao final, `outputs/model/metadata.json` virá com `mode=trained`, `training.results` populado e `artifacts.local.files` listando arquivos do adapter.
3. Alternativa CLI em workstation:

   ```bash
   python -m pip install -r requirements-finetuning.txt
   python fase2_finetuning/train_lora.py \
     --base-model meta-llama/Llama-3.2-3B-Instruct \
     --output-dir outputs/model
   ```

### 2.3 Treino local em Apple Silicon (M-series, recomendado para a demo Ollama)

Receita testada para Macs M3/M4 com 24–32 GB de memória unificada. Em Apple Silicon **não usamos `bitsandbytes`** — o script detecta `mps` e troca o otimizador para `adamw_torch` + bf16 puro automaticamente.

```bash
# 1. ambiente isolado (uv ou venv)
python -m venv .venv-ft && source .venv-ft/bin/activate

# 2. instalar somente o que funciona em MPS (sem bitsandbytes)
pip install --upgrade pip
pip install \
  'torch>=2.4' 'transformers>=4.42,<5' 'datasets>=2.20,<3' \
  'peft>=0.11,<0.14' 'trl>=0.9,<0.13' 'accelerate>=0.31,<2'

# 3. confirmar device disponível
python -c "from fase2_finetuning.train_lora import detect_device; print(detect_device())"
# saída esperada em M-series: mps

# 4. login no Hugging Face (Llama exige aceitar os termos do modelo)
huggingface-cli login

# 5. treinar (≈ 8–15 min por epoch no dataset curado)
python fase2_finetuning/train_lora.py \
  --base-model meta-llama/Llama-3.2-3B-Instruct \
  --output-dir outputs/model

# 6. validar
python fase2_finetuning/validate_adapters.py
```

> Importante: `requirements-finetuning.txt` inclui `bitsandbytes`, que **não compila** em macOS arm64. Em Apple Silicon, instale somente as dependências da seção 2.3 acima — o `train_lora.py` só importa `bitsandbytes` quando detecta `device=cuda`.

## 3. Hiperparâmetros canônicos

Sincronizados entre `train_lora.py` e o notebook:

| Parâmetro | Valor canônico | Valor desta entrega | Justificativa |
|---|---|---|---|
| `base_model` | `meta-llama/Llama-3.2-3B-Instruct` | `meta-llama/Llama-3.2-1B-Instruct` | Versão 1B foi escolhida para a execução real em Apple Silicon (M4); 3B é o canônico em GPU dedicada. Alternativa aberta: `Qwen/Qwen2.5-1.5B-Instruct`. |
| `lora.r` | `16` | `16` | Faixa intermediária para domínios pequenos. |
| `lora.lora_alpha` | `32` | `32` | `alpha = 2 × r`, regra estável para SFT. |
| `lora.lora_dropout` | `0.05` | `0.05` | Reduz overfitting do dataset enxuto. |
| `target_modules` | `q_proj,k_proj,v_proj,o_proj` | idem | Cobre atenção (suficiente para ajuste de estilo). |
| `epochs` | `2` | `2` | Evita memorização no corpus pequeno. |
| `batch_size × grad_accum` | `1 × 8` | `1 × 2` (MPS) | Reduzido em MPS por throughput; em CUDA T4 manter `1 × 8`. |
| `learning_rate` | `2e-4` | `2e-4` | Padrão SFT/LoRA. |
| `optim` | resolvido por device | `adamw_torch` (MPS) | `paged_adamw_8bit` em CUDA / `adamw_torch` em MPS e CPU. |
| `bf16` | resolvido por device | `True` (MPS) | `True` em CUDA/MPS; `False` (fp32) em CPU. |
| `max_seq_length` | `1024` | `512` (MPS) | Reduzido em MPS para acelerar; em CUDA voltar a 1024 quando possível. |

Override por env vars: `FT_BASE_MODEL`, `FT_EPOCHS`, `FT_LR`, `FT_OUTPUT_DIR`. Flag `--device cuda|mps|cpu` força a escolha quando necessário. Os flags `--max-seq-length`, `--gradient-accumulation-steps`, `--per-device-batch-size`, `--max-train-samples` e `--max-val-samples` permitem ajustar throughput sem editar código (úteis em MPS).

Os valores efetivamente usados nesta entrega ficam registrados em `outputs/model/metadata.json` (`training.results`):

- `train_loss = 1.2287`
- `eval_loss = 1.1917` (menor que `train_loss` → sem overfit)
- `eval_runtime_s = 233.2231` (≈ 4 min sobre 557 exemplos de validação)
- `device_target = mps`

## 4. Distribuição do adapter (canal externo)

A ordem de preferência segue o que está em `outputs/model/metadata.json` (`artifacts.external`).

### 4.1 Hugging Face Hub (recomendado)

```bash
huggingface-cli login              # token write
huggingface-cli repo create femcare-llama32-lora --type model
cd outputs/model
huggingface-cli upload <org>/femcare-llama32-lora . --repo-type model
```

Download em qualquer máquina:

```bash
huggingface-cli download <org>/femcare-llama32-lora --local-dir outputs/model
```

### 4.2 GitHub Release (canal atual deste projeto)

O adapter real desta entrega está publicado como asset do GitHub Release [`ia-core-phase-h-v0.1`](https://github.com/vinicius707/tech-challenge-fase-3-8IADT/releases/tag/ia-core-phase-h-v0.1) (tarball `femcare-lora-v0.1.tar.gz`, ~15 MB).

| | |
|---|---|
| Tag | `ia-core-phase-h-v0.1` |
| Asset | `femcare-lora-v0.1.tar.gz` |
| SHA256 do tarball | `e29c490837f9c1fbd4d4e63e4962459d99ce36c4aad23ac6d3aaa7cad3d0a46f` |
| Conteúdo | adapter PEFT + tokenizer (`adapter_model.safetensors`, `adapter_config.json`, `tokenizer*`, `special_tokens_map.json`, `training_args.bin`, `README.md`) |

Para baixar e instalar localmente (corresponde a `artifacts.external.download_command` em `outputs/model/metadata.json`):

```bash
mkdir -p outputs/model
curl -L https://github.com/vinicius707/tech-challenge-fase-3-8IADT/releases/download/ia-core-phase-h-v0.1/femcare-lora-v0.1.tar.gz \
  | tar -xzf - -C outputs/model
python fase2_finetuning/validate_adapters.py
```

Para republicar uma nova versão:

```bash
mkdir -p outputs/dist
tar -czvf outputs/dist/femcare-lora-vX.Y.tar.gz -C outputs/model \
  adapter_config.json adapter_model.safetensors special_tokens_map.json \
  tokenizer.json tokenizer_config.json training_args.bin README.md
gh release create ia-core-phase-h-vX.Y outputs/dist/femcare-lora-vX.Y.tar.gz \
  --title "IA Core - Fine-tuning Phase H - vX.Y" \
  --notes "..."
```

Atualize `artifacts.external.{release_tag,release_url,asset_url,sha256}` em `outputs/model/metadata.json` após o upload.

### 4.3 Git LFS (último recurso)

Se você precisar versionar binários grandes (ex.: avaliação interna fechada), habilite Git LFS **em um fork interno** e nunca no repositório público:

```bash
git lfs install
git lfs track 'outputs/model/*.safetensors'
echo 'outputs/model/*.safetensors' >> .gitattributes
git add .gitattributes outputs/model/*.safetensors
```

Para o repositório principal, mantenha apenas `metadata.json`.

## 5. Validação (gate IA-FT-02)

```bash
python fase2_finetuning/validate_adapters.py
cat outputs/reports/finetuning_validation.md
```

Critérios de sucesso (exit code `0`):

- `outputs/model/metadata.json` existe e tem todos os campos obrigatórios (`schema_version`, `mode`, `purpose`, `base_model`, `lora_config`, `training`, `dataset`, `artifacts`).
- `dataset.train.path` e `dataset.val.path` apontam para arquivos válidos no checkout (ou levantam `warning` informativo quando regerados localmente após Fase B).
- Em `mode=trained`: todos os arquivos de `artifacts.local.files[]` existem e os `sha256` batem.
- `artifacts.external` declara o canal preferido (HF Hub > GitHub Release > Git LFS).

## 6. Servir o modelo treinado pelo Ollama (caminho preferencial)

Quando o objetivo é demonstrar o modelo customizado **dentro da própria stack** (BFF → IA Core → Ollama), use o caminho merge → GGUF → `ollama create`. Ele evita o backend `local_lora` (que carrega PyTorch em runtime) e mantém a inferência rápida em Apple Silicon.

### 6.1 Mergear o adapter no modelo base

```bash
python fase2_finetuning/merge_and_export.py \
  --base-model meta-llama/Llama-3.2-3B-Instruct \
  --adapter-dir outputs/model \
  --output-dir outputs/model_merged \
  --ollama-tag femcare:v0.1
```

O script aplica `merge_and_unload()` do PEFT e salva o modelo completo em formato HF. Imprime, ao final, todos os comandos das próximas etapas (Modelfile incluído) — útil para colar direto no terminal.

### 6.2 Converter para GGUF via `llama.cpp`

```bash
git clone https://github.com/ggerganov/llama.cpp ~/llama.cpp
cd ~/llama.cpp && pip install -r requirements.txt && make -j

python ~/llama.cpp/convert_hf_to_gguf.py outputs/model_merged \
  --outfile outputs/model_merged/femcare.f16.gguf

~/llama.cpp/build/bin/llama-quantize \
  outputs/model_merged/femcare.f16.gguf \
  outputs/model_merged/femcare-q4_k_m.gguf q4_k_m
```

### 6.3 Criar o `Modelfile` e importar no Ollama

```bash
cat > outputs/model_merged/Modelfile <<'EOF'
FROM outputs/model_merged/femcare-q4_k_m.gguf
SYSTEM """Voce e um assistente de apoio clinico em saude da mulher.
Nao prescreva medicamentos, nao de diagnostico definitivo e sempre
recomende avaliacao por profissional habilitado."""
PARAMETER temperature 0.2
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"
EOF

ollama create femcare:v0.1 -f outputs/model_merged/Modelfile
ollama run femcare:v0.1 "Ola, qual seu papel?"
```

### 6.4 Apontar o IA Core para o modelo customizado

```bash
OLLAMA_MODEL=femcare:v0.1 \
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 \
uvicorn fase3_orquestracao.app:app --port 8000
```

A UI continuará vendo `modelVersion: ollama:femcare:v0.1` no evento `meta` do stream SSE (Fase G), evidenciando que a demo passou a usar o modelo treinado.

### 6.5 Alternativa: backend `local_lora` direto (sem GGUF)

Quando você precisa rodar o adapter sem conversão (ex.: avaliação rápida em Python), use o backend `local_lora` registrado em `config/model_backends.yaml`. Ele continua sendo um placeholder explícito do design (`docs/sdd/ia-core/design.md` §8) e exige carregar PyTorch+PEFT em runtime; preferir o caminho Ollama acima quando possível.

```bash
IA_LLM_BACKEND=local_lora python -m fase3_orquestracao.llm_backend --prompt 'teste'
```

> Os guardrails da Fase E (`fase4_seguranca/safety_guard.py`) e o router clínico da Fase F (`fase3_orquestracao/clinical_router.py`) **continuam autoritativos** — o modelo treinado nunca decide diagnóstico ou prescrição sozinho.

### 6.6 Evidência do deploy desta entrega

O fluxo da seção 6 foi executado de ponta a ponta para esta entrega, com os artefatos efetivamente registrados no Ollama e o `modelVersion` propagado pelo SSE:

| Etapa | Saída |
|---|---|
| `convert_hf_to_gguf.py` | `outputs/model_merged/femcare.f16.gguf` (~2.47 GB, 147 tensors) |
| `llama-quantize q4_k_m` | `outputs/model_merged/femcare-q4_k_m.gguf` (~762 MB, 5.18 BPW) |
| `ollama create femcare:v0.1` | `5cb61a7cc9a6` (807 MB no Ollama, 100% GPU em M4) |
| `ollama show femcare:v0.1` | arch `llama`, 1.2B params, `Q4_K_M`, SYSTEM prompt aplicado |

Comando de validação no IA Core:

```bash
IA_LLM_BACKEND=ollama OLLAMA_MODEL=femcare:v0.1 \
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 OLLAMA_API_KEY=ollama \
.venv/bin/uvicorn fase3_orquestracao.app:app --port 8000
```

Resposta capturada em `POST /v1/chat/stream` para um caso do fluxo `prevencao` (primeiro evento do SSE):

```
event: meta
data: {"requestId":"862e2ea3-...","flowId":"prevencao","modelVersion":"ollama:femcare:v0.1","urgencia":"nenhuma"}
```

O `modelVersion` real (`ollama:femcare:v0.1`) **substitui o `stub-0.1.0`** quando o IA Core está configurado para o modelo treinado, encerrando os requisitos **IA-D2** e **IA-G2** com evidência reproduzível. Sequência completa observada: `meta → log* → token* → explain → trace → done`.

## 7. Limitações e éticas

- Dataset enxuto (≤ 200 exemplos curados + complementos sintéticos): adequado para ajuste de estilo, não para conhecimento clínico inédito.
- Conteúdo sensível (violência doméstica, autoagressão) **nunca** entra em prompts de treino sem redação prévia (`fase4_seguranca/audit.py`).
- O modelo treinado pode incorporar viéses do MedQuAD (inglês, traduzido). RAG continua sendo a fonte autoritativa de evidência clínica versionada (`data/rag_documents.jsonl`).
- Para uso clínico real, é necessário processo de homologação institucional, fora do escopo deste TCC.
