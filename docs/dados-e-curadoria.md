# Dados e Curadoria - IA Core

Este documento registra as fontes e decisões de curadoria da Fase B do fluxo SDD
`IA Core e Orquestração Clínica`.

## Fonte Base

| Campo | Valor |
|---|---|
| Dataset | MedQuAD - Medical Question Answering Dataset |
| Slug Kaggle | `pythonafroz/medquad-medical-question-answer-for-ai-research` |
| URL | <https://www.kaggle.com/datasets/pythonafroz/medquad-medical-question-answer-for-ai-research> |
| Método de download | `kagglehub.dataset_download("pythonafroz/medquad-medical-question-answer-for-ai-research")` |
| Data de download | Registrada em `outputs/reports/medquad_manifest.json` no momento da execução |
| Licença/termos | Devem ser conferidos pela equipe no Kaggle antes de redistribuição ou uso público dos artefatos |

O pipeline não versiona o dataset bruto. Por padrão, `fase1_dados/download_medquad.py`
apenas localiza/baixa o dataset no cache do `kagglehub` e registra um manifesto
local em `outputs/reports/medquad_manifest.json`. A pasta `data/raw/medquad/`
é ignorada pelo Git para evitar commit acidental de arquivos grandes.

## Comandos Reprodutíveis

```bash
python fase1_dados/download_medquad.py
python fase1_dados/explore_dataset.py
python fase1_dados/build_dataset.py
python fase1_dados/validate_data.py
```

Quando o Kaggle não estiver disponível no ambiente local, é possível executar
um smoke test apenas com dados sintéticos/curados:

```bash
python fase1_dados/build_dataset.py --synthetic-only
python fase1_dados/validate_data.py
```

Esse modo não substitui a execução completa com MedQuAD; ele existe apenas para
validar o contrato de arquivos, schemas e cobertura mínima dos quatro fluxos.

## Artefatos Gerados

| Artefato | Origem | Versionamento |
|---|---|---|
| `outputs/reports/medquad_manifest.json` | Download/localização do Kaggle | Não versionado |
| `outputs/reports/data_profile.md` | Exploração redigida do corpus | Não versionado |
| `data/processed/medquad_normalized.jsonl` | Normalização do MedQuAD | Não versionado |
| `data/synthetic/womens_health_curated.jsonl` | Complementos sintéticos/curados | Versionado |
| `data/rag_documents.jsonl` | Documentos para RAG | Não versionado |
| `data/train.jsonl` | Corpus de treino | Não versionado |
| `data/val.jsonl` | Corpus de validação | Não versionado |
| `outputs/reports/data_validation.md` | Relatório de validação | Não versionado |

## Domínios Clínicos

Os registros normalizados recebem um dos domínios abaixo:

- `triagemGinecologica`
- `violenciaDomestica`
- `obstetrico`
- `prevencao`
- `medicinaGeral`
- `excluir`

Registros `medicinaGeral` podem apoiar o RAG como conhecimento auxiliar, mas
não devem ser usados como evidência principal para demonstrar os quatro fluxos
clínicos obrigatórios. Registros `excluir` não entram em RAG nem treino.

## Complementos Sintéticos/Curados

O MedQuAD é um corpus médico geral e não cobre suficientemente:

- violência doméstica com minimização de logs;
- obstetrícia contextual com sinais de alarme;
- prevenção alinhada ao cenário brasileiro;
- triagem ginecológica com respostas sem prescrição.

Por isso, `data/synthetic/womens_health_curated.jsonl` inclui exemplos
sintéticos e não identificáveis para os quatro domínios obrigatórios. Esses
registros são marcados com:

- `source`: `synthetic_protocol_v1`;
- `citation`: referência legível para UI/relatório;
- `sensitivity`: `low`, `medium` ou `high`;
- `include_for_training` e `include_for_rag`.

## Segurança e Privacidade

- O pipeline não baixa nem cria dados reais identificáveis.
- Amostras de exploração são truncadas e passam por redação simples de emails e
  telefones.
- Conteúdos de `violenciaDomestica` são marcados como `sensitivity = high`.
- O dataset bruto fica no cache local do `kagglehub` ou em `data/raw/medquad/`,
  ambos fora do versionamento.
- A curadoria não autoriza prescrição, diagnóstico definitivo ou substituição
  de avaliação profissional.

## Limitações

- A classificação de domínio usa regras e palavras-chave, adequada para MVP
  acadêmico, mas não substitui revisão clínica.
- O MedQuAD está majoritariamente em inglês e é generalista; respostas em
  português dependem dos complementos sintéticos/curados e das fases seguintes.
- Termos de licença/uso do Kaggle devem ser conferidos no momento do download,
  pois podem mudar fora do controle do repositório.
- Os artefatos gerados localmente devem ser revisados antes de qualquer uso em
  demonstração pública.
