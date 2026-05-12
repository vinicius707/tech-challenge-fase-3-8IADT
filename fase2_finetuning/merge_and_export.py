"""Merge do adapter LoRA + export HF e instrucoes para GGUF/Ollama.

Cobre o caminho `treino local -> servir no Ollama` documentado em
`docs/fine-tuning.md` (secao Apple Silicon). E o passo entre
`train_lora.py` (gera adapter) e o `ollama create -f Modelfile`
(serve o modelo customizado).

Uso tipico:

    python fase2_finetuning/merge_and_export.py \\
      --base-model meta-llama/Llama-3.2-3B-Instruct \\
      --adapter-dir outputs/model \\
      --output-dir outputs/model_merged

O script:

1. Carrega o modelo base em bf16 (MPS, CUDA ou CPU).
2. Aplica o adapter PEFT salvo em `--adapter-dir`.
3. Chama `merge_and_unload()` para gerar um modelo HF auto-suficiente.
4. Salva `tokenizer` + `model` em `--output-dir`.
5. Imprime instrucoes para converter o resultado em GGUF e criar um
   `Modelfile` que o Ollama possa importar.

Restricoes:

- Modelos completos NAO sao versionados no Git deste repositorio. Use
  HF Hub privado, GitHub Release ou pasta externa.
- Treino e merge mudam o conteudo gerado; safety guard, RAG e router
  da Fase F/E continuam autoritativos.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase2_finetuning.train_lora import detect_device


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADAPTER_DIR = PROJECT_ROOT / "outputs" / "model"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "model_merged"


def _ollama_instructions(merged_dir: Path, ollama_tag: str) -> str:
    relative = merged_dir.resolve()
    return f"""
Proximos passos para servir o adapter mergeado pelo Ollama:

1. (Uma vez) clonar/compilar llama.cpp para gerar GGUF:

    git clone https://github.com/ggerganov/llama.cpp ~/llama.cpp
    cd ~/llama.cpp && pip install -r requirements.txt
    make -j  # ou: cmake -B build && cmake --build build --config Release

2. Converter o modelo HF para GGUF (bf16):

    python ~/llama.cpp/convert_hf_to_gguf.py {relative} \\
      --outfile {relative}/femcare.f16.gguf

3. Quantizar (recomendado em Apple Silicon 24-32GB):

    ~/llama.cpp/build/bin/llama-quantize \\
      {relative}/femcare.f16.gguf \\
      {relative}/femcare-q4_k_m.gguf q4_k_m

4. Criar o Modelfile (ja inclui SYSTEM prompt clinico conservador):

    cat > {relative}/Modelfile <<'EOF'
    FROM {relative}/femcare-q4_k_m.gguf
    SYSTEM \"\"\"Voce e um assistente de apoio clinico em saude da mulher.
    Nao prescreva medicamentos, nao de diagnostico definitivo e sempre
    recomende avaliacao por profissional habilitado.\"\"\"
    PARAMETER temperature 0.2
    PARAMETER stop \"<|eot_id|>\"
    PARAMETER stop \"<|end_of_text|>\"
    EOF

5. Importar no Ollama:

    ollama create {ollama_tag} -f {relative}/Modelfile
    ollama run {ollama_tag} \"Ola, qual e o seu papel?\"

6. Apontar o IA Core para o modelo customizado:

    OLLAMA_MODEL={ollama_tag} \\
    OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 \\
    uvicorn fase3_orquestracao.app:app --port 8000

Os guardrails de Fase E e o router de Fase F continuam autoritativos -
o modelo treinado e ajuste de formato/linguagem, nao fonte clinica.
"""


def merge_adapter(
    *,
    base_model: str,
    adapter_dir: Path,
    output_dir: Path,
    device: str | None = None,
) -> Path:
    """Aplica o adapter PEFT no modelo base e salva o resultado em HF format."""

    try:
        import torch  # type: ignore[import-not-found]
        from peft import PeftModel  # type: ignore[import-not-found]
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "Dependencias de fine-tuning ausentes. Instale `requirements-finetuning.txt` "
            "(em Apple Silicon, sem bitsandbytes) antes de rodar o merge."
        ) from exc

    if not adapter_dir.exists():
        raise SystemExit(
            f"Diretorio do adapter nao encontrado: {adapter_dir}. Rode `train_lora.py` antes."
        )

    active_device = device or detect_device()
    dtype = torch.bfloat16 if active_device in {"cuda", "mps"} else torch.float32

    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    base = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=dtype)
    if active_device != "cuda":
        base.to(active_device)

    model = PeftModel.from_pretrained(base, str(adapter_dir))
    merged = model.merge_and_unload()

    output_dir.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    return output_dir


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge LoRA adapter + export HF + receita Ollama (Fase H)."
    )
    parser.add_argument(
        "--base-model",
        default="meta-llama/Llama-3.2-3B-Instruct",
        help="Modelo base no Hugging Face Hub.",
    )
    parser.add_argument(
        "--adapter-dir",
        type=Path,
        default=DEFAULT_ADAPTER_DIR,
        help="Diretorio com o adapter LoRA salvo pelo train_lora.py.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Onde salvar o modelo mergeado (formato HF).",
    )
    parser.add_argument(
        "--device",
        choices=("cuda", "mps", "cpu"),
        default=None,
        help="Forca o device. Sem o flag, detecta automaticamente.",
    )
    parser.add_argument(
        "--ollama-tag",
        default="femcare:v0.1",
        help="Tag que sera usada em `ollama create <tag> -f Modelfile`.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Apenas imprime as instrucoes Ollama; nao chama torch/peft.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.print_only:
        print(_ollama_instructions(args.output_dir, args.ollama_tag))
        return 0

    out = merge_adapter(
        base_model=args.base_model,
        adapter_dir=args.adapter_dir,
        output_dir=args.output_dir,
        device=args.device,
    )
    print(f"Modelo mergeado salvo em {out}")
    print(_ollama_instructions(out, args.ollama_tag))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["merge_adapter", "main"]
