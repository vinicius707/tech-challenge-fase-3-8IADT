/** Consumidor SSE genérico (sem React) para testes e reutilização. */
export async function consumeSse(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: string, data: string) => void,
): Promise<void> {
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    for (;;) {
      const idx = buffer.indexOf("\n\n");
      if (idx === -1) break;
      const block = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);

      let eventName = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) onEvent(eventName, data);
    }
  }
}
