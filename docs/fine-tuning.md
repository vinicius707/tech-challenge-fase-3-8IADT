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

## 3. Hiperparâmetros canônicos

Sincronizados entre `train_lora.py` e o notebook:

| Parâmetro | Valor | Justificativa |
|---|---|---|
| `base_model` | `meta-llama/Llama-3.2-3B-Instruct` | Bom balanço qualidade/VRAM em T4. Alternativa documentada: `Qwen/Qwen2.5-1.5B-Instruct`. |
| `lora.r` | `16` | Faixa intermediária para domínios pequenos. |
| `lora.lora_alpha` | `32` | `alpha = 2 × r`, regra estável para SFT. |
| `lora.lora_dropout` | `0.05` | Reduz overfitting do dataset enxuto. |
| `target_modules` | `q_proj,k_proj,v_proj,o_proj` | Cobre atenção (suficiente para ajuste de estilo). |
| `epochs` | `2` | Evita memorização no corpus pequeno. |
| `batch_size × grad_accum` | `1 × 8` | Compatível com 16 GB de VRAM. |
| `learning_rate` | `2e-4` | Padrão SFT/LoRA. |
| `optim` | `paged_adamw_8bit` | Necessário para QLoRA 4-bit. |
| `max_seq_length` | `1024` | Trade-off com `messages` mais longos. |

Override por env vars: `FT_BASE_MODEL`, `FT_EPOCHS`, `FT_LR`, `FT_OUTPUT_DIR`.

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

### 4.2 GitHub Release (fallback)

Quando não há HF Hub disponível:

```bash
cd outputs/model
zip -r ../../adapter.zip .
gh release create v0.1.0-lora ../../adapter.zip --notes 'LoRA adapter Fase H'
```

Download via `gh release download v0.1.0-lora -p adapter.zip && unzip adapter.zip -d outputs/model`.

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

## 6. Carregamento no IA Core

Depois de baixar o adapter para `outputs/model/`, ative o backend:

```yaml
# config/model_backends.yaml já tem o slot `local_lora`.
```

```bash
IA_LLM_BACKEND=local_lora python -m fase3_orquestracao.llm_backend --prompt 'teste'
```

> Atenção: o backend `local_lora` em `fase3_orquestracao/llm_backend.py` é um placeholder até o pipeline de carregamento ser concluído. Os guardrails (`fase4_seguranca`) continuam autoritativos.

## 7. Limitações e éticas

- Dataset enxuto (≤ 200 exemplos curados + complementos sintéticos): adequado para ajuste de estilo, não para conhecimento clínico inédito.
- Conteúdo sensível (violência doméstica, autoagressão) **nunca** entra em prompts de treino sem redação prévia (`fase4_seguranca/audit.py`).
- O modelo treinado pode incorporar viéses do MedQuAD (inglês, traduzido). RAG continua sendo a fonte autoritativa de evidência clínica versionada (`data/rag_documents.jsonl`).
- Para uso clínico real, é necessário processo de homologação institucional, fora do escopo deste TCC.
