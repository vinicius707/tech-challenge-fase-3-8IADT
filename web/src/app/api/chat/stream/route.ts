import type {
  ChatStreamRequest,
  ClinicalFlowId,
  ExplainBlock,
} from "@/types/assistant";

const FLOW_IDS: ClinicalFlowId[] = [
  "triagemGinecologica",
  "violenciaDomestica",
  "obstetrico",
  "prevencao",
];

function isClinicalFlowId(v: unknown): v is ClinicalFlowId {
  return typeof v === "string" && (FLOW_IDS as string[]).includes(v);
}

function encodeSse(event: string, data: unknown): Uint8Array {
  const encoder = new TextEncoder();
  return encoder.encode(
    `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`,
  );
}

function lastUserMessage(req: ChatStreamRequest): string {
  const users = req.messages.filter((m) => m.role === "user");
  const last = users[users.length - 1];
  return last?.content?.trim() || "";
}

function buildStubPlan(flowId: ClinicalFlowId, userText: string): {
  fullText: string;
  explain: ExplainBlock;
  urgencia: "nenhuma" | "moderada" | "alta" | "emergencia";
} {
  const baseCtx = userText
    ? `Considerando o relato: “${userText.slice(0, 280)}${userText.length > 280 ? "…" : ""}”. `
    : "";

  switch (flowId) {
    case "triagemGinecologica":
      return {
        fullText:
          `${baseCtx}Esta resposta é de **apoio à triagem** e **não** substitui avaliação presencial. ` +
          "Sugiro classificar urgência com protocolo institucional e registrar sinais de alarme. " +
          "Para sintomas graves (dor intensa, sangramento abundante, febre alta), **busque urgência presencial** imediatamente.",
        explain: {
          fonte: "Protocolo institucional de triagem ginecológica (exemplo)",
          confianca: 0.55,
          lacunas: [
            "Sem exame físico ou exames complementares nesta sessão.",
            "Dados de sinais vitais não informados.",
          ],
          raciocinioClinico:
            "Priorizar segurança: quando há dúvida, escalar para avaliação presencial.",
        },
        urgencia: "moderada",
      };
    case "violenciaDomestica":
      return {
        fullText:
          `${baseCtx}Se houver risco imediato à segurança, **ligue aos serviços de emergência locais**. ` +
          "Este assistente **não** substitui acionamento da equipe especializada nem plano de segurança individual. " +
          "Encaminhe a situação a profissionais qualificados (saúde, assistência social, rede de proteção) conforme protocolo.",
        explain: {
          fonte: "Diretriz institucional de violência / literatura especializada (exemplo)",
          confianca: 0.42,
          lacunas: [
            "Conteúdo sensível não deve ser registrado em canais inseguros.",
            "É necessária avaliação humana para decisões de proteção.",
          ],
          raciocinioClinico:
            "Priorizar proteção e confidencialidade; evitar instruções que exponham a pessoa em risco.",
        },
        urgencia: "alta",
      };
    case "obstetrico":
      return {
        fullText:
          `${baseCtx}Em gestação, sinais de alarme (dor abdominal intensa, sangramento, cefaleia intensa, alterações visuais, diminuição de movimentação fetal) exigem **avaliação urgente presencial**. ` +
          "Use exames e retornos conforme pré-natal e risco obstétrico.",
        explain: {
          fonte: "FEBRASGO / pré-natal institucional (exemplo)",
          confianca: 0.58,
          lacunas: ["IG exata e exames recentes não validados nesta demo."],
          raciocinioClinico:
            "Estratificar risco obstétrico e reforçar retorno quando houver sintomas de alerta.",
        },
        urgencia: "moderada",
      };
    case "prevencao":
      return {
        fullText:
          `${baseCtx}Para rastreamento, alinhe mamografia, citopatológico e outros exames à idade, fatores de risco e diretrizes vigentes (ex.: INCA, sociedades médicas). ` +
          "Agende lembretes e registre barreiras de acesso quando identificadas.",
        explain: {
          fonte: "INCA / diretrizes de rastreamento (exemplo)",
          confianca: 0.6,
          lacunas: ["Histórico familiar detalhado não informado."],
          raciocinioClinico:
            "Comparar últimos exames com janelas recomendadas e propor próximos passos não invasivos.",
        },
        urgencia: "nenhuma",
      };
  }
}

async function* stubEvents(
  requestId: string,
  body: ChatStreamRequest,
): AsyncGenerator<Uint8Array> {
  const plan = buildStubPlan(body.flowId, lastUserMessage(body));
  yield encodeSse("meta", {
    requestId,
    flowId: body.flowId,
    modelVersion: "stub-0.1.0",
    urgencia: plan.urgencia,
  });
  yield encodeSse("log", {
    level: "info",
    message: "Validação stub: políticas de segurança aplicadas (demo).",
    ts: new Date().toISOString(),
  });

  const words = plan.fullText.split(/(\s+)/).filter((w) => w.length > 0);
  for (const w of words) {
    yield encodeSse("token", { delta: w });
    await new Promise((r) => setTimeout(r, 8));
  }

  yield encodeSse("explain", plan.explain);
  yield encodeSse("log", {
    level: "info",
    message: "Resposta finalizada (stub).",
    ts: new Date().toISOString(),
  });
  yield encodeSse("done", {});
}

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  if (!body || typeof body !== "object") {
    return new Response("Invalid body", { status: 400 });
  }

  const b = body as Partial<ChatStreamRequest>;
  if (!isClinicalFlowId(b.flowId)) {
    return new Response("Invalid flowId", { status: 400 });
  }
  if (!Array.isArray(b.messages) || b.messages.length === 0) {
    return new Response("messages required", { status: 400 });
  }
  for (const m of b.messages) {
    if (!m || typeof m !== "object") return new Response("invalid message", { status: 400 });
    if (m.role !== "user" && m.role !== "assistant" && m.role !== "system") {
      return new Response("invalid message.role", { status: 400 });
    }
    if (typeof m.content !== "string") {
      return new Response("invalid message.content", { status: 400 });
    }
  }

  const chatBody: ChatStreamRequest = {
    flowId: b.flowId,
    threadId: typeof b.threadId === "string" ? b.threadId : undefined,
    messages: b.messages as ChatStreamRequest["messages"],
    patientContext:
      b.patientContext && typeof b.patientContext === "object"
        ? (b.patientContext as ChatStreamRequest["patientContext"])
        : undefined,
  };

  const requestId =
    req.headers.get("x-request-id")?.trim() || crypto.randomUUID();

  const baseUrl = process.env.ORCHESTRATION_API_URL?.trim();
  if (baseUrl) {
    const target = `${baseUrl.replace(/\/$/, "")}/v1/chat/stream`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "x-request-id": requestId,
    };
    const key = process.env.ORCHESTRATION_API_KEY?.trim();
    if (key) headers.Authorization = `Bearer ${key}`;

    const upstream = await fetch(target, {
      method: "POST",
      headers,
      body: JSON.stringify(chatBody),
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => "");
      return new Response(
        JSON.stringify({
          code: "upstream_error",
          message: `Falha ao contatar orquestração (${upstream.status}): ${text.slice(0, 500)}`,
        }),
        { status: 502, headers: { "content-type": "application/json" } },
      );
    }

    return new Response(upstream.body, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "x-request-id": requestId,
      },
    });
  }

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        for await (const chunk of stubEvents(requestId, chatBody)) {
          controller.enqueue(chunk);
        }
      } catch (e) {
        controller.enqueue(
          encodeSse("error", {
            code: "stub_failed",
            message: e instanceof Error ? e.message : "unknown",
          }),
        );
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "x-request-id": requestId,
    },
  });
}
