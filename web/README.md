# Web — Next.js (BFF + UI)

Interface do assistente clínico descrita em [.specs/features/web-ui/spec.md](../.specs/features/web-ui/spec.md).

## Requisitos

- Node.js 20+

## Variáveis de ambiente

Copie `.env.example` para `.env.local` na pasta `web/`.

| Variável | Descrição |
|----------|-----------|
| `ORCHESTRATION_API_URL` | Base URL do Python. Se vazio, o BFF usa **stub** SSE (demo local). |
| `ORCHESTRATION_API_KEY` | Opcional: Bearer para o serviço Python. |

Contrato HTTP: [docs/api.md](../docs/api.md).

## Comandos

```bash
cd web
npm install
npm run dev
```

Abra `http://localhost:3000`.

## Roteiro rápido para vídeo (Fase 3)

1. Mostrar avisos legais e seletor de fluxo.  
2. Opcional: preencher JSON de contexto (dados fictícios).  
3. Enviar mensagem e mostrar streaming + painel **Explainability**.  
4. Mostrar painel de **logs** e `x-request-id`.  
5. Fluxo **violência doméstica**: demonstrar **gate** de confirmação profissional antes do envio.

## Gates de qualidade

```bash
npm run lint
npm run build
```
