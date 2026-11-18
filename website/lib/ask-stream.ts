export interface Citation {
  index: number; policy_id: string; version_id: string; title: string;
  source_url?: string | null; policy_quote: string; char_start: number;
}
export type AskEvent =
  | { event: 'retrieval'; data: { sources: Citation[] } }
  | { event: 'token'; data: { text: string } }
  | { event: 'citations'; data: { citations: Citation[] } }
  | { event: 'done'; data: { conversation_id: string; status: string } }
  | { event: 'error'; data: { message: string; code: string; conversation_id: string } };

/** POST SSE supports Authorization and cancellation; EventSource cannot do either body/header. */
export async function consumeAskStream(body: ReadableStream<Uint8Array>, receive: (event: AskEvent) => void) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let pending = ''; let terminal = false;
  function drain() {
    pending = pending.replace(/\r\n/g, '\n');
    let boundary: number;
    while ((boundary = pending.indexOf('\n\n')) >= 0) {
      const block = pending.slice(0, boundary); pending = pending.slice(boundary + 2);
      const name = block.split('\n').find(line => line.startsWith('event:'))?.slice(6).trim();
      const raw = block.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
      if (!name || !raw) continue;
      if (!['retrieval', 'token', 'citations', 'done', 'error'].includes(name)) throw new Error('回答协议无效');
      if (terminal) throw new Error('回答结束后收到额外内容');
      const data = JSON.parse(raw);
      receive({event: name, data} as AskEvent);
      if (name === 'done' || name === 'error') terminal = true;
    }
  }
  try {
    while (true) {
      const {value, done} = await reader.read();
      pending += decoder.decode(value, {stream: !done});
      if (pending.length > 1_000_000) throw new Error('回答超出长度限制');
      drain();
      if (done) break;
    }
    if (!terminal) throw new Error('连接已中断，回答尚未完成；可从最近对话查看已保存状态');
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}

/** Locate normalized quotations while retaining exact UTF-16 render positions. */
export function findQuoteSpan(content: string, quote: string, charStart = 0): {start: number; end: number} | null {
  if (!quote.trim()) return null;
  const offset = Array.from(content).slice(0, charStart).join('').length;
  const exact = content.indexOf(quote, offset);
  if (exact >= 0) return {start: exact, end: exact + quote.length};
  const positions = Array.from(content.slice(offset).matchAll(/\S/g));
  const normalized = positions.map(match => match[0]).join('');
  const target = quote.replace(/\s/g, '');
  const found = normalized.indexOf(target);
  if (found < 0) return null;
  return {start: offset + positions[found].index, end: offset + positions[found + target.length - 1].index + 1};
}
