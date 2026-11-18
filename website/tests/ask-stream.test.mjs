import assert from 'node:assert/strict';
import test from 'node:test';
import { consumeAskStream, findQuoteSpan } from '../lib/ask-stream.ts';
import { WORKSPACE_NAVIGATION, WORKSPACE_ROUTES, WORKSPACE_SECONDARY } from '../lib/navigation.ts';
function body(parts) { return new ReadableStream({start(controller) { for (const part of parts) controller.enqueue(new TextEncoder().encode(part)); controller.close(); }}); }
test('SSE handles fragmented JSON, Chinese, CRLF and terminal status', async () => {
  const events = [];
  await consumeAskStream(body(['event: token\r\ndata: {"text":"研', '发"}\r\n\r\nevent: done\ndata: {"status":"completed"}\n\n']), event => events.push(event));
  assert.equal(events[0].data.text, '研发'); assert.equal(events[1].event, 'done');
});
test('interrupted or malformed stream never pretends completion', async () => {
  await assert.rejects(consumeAskStream(body(['event: token\ndata: {"text":"partial"}\n\n']), () => {}), /连接已中断/);
  await assert.rejects(consumeAskStream(body(['event: token\ndata: broken\n\n']), () => {}));
});
test('five main destinations preserve legacy routes and contextual entry points', () => {
  assert.equal(WORKSPACE_NAVIGATION.length, 5);
  assert.ok(WORKSPACE_ROUTES.includes('/tasks')); assert.ok(WORKSPACE_ROUTES.includes('/agents'));
  for (const route of WORKSPACE_ROUTES.filter(path => path !== '/admin')) assert.equal(WORKSPACE_NAVIGATION.filter(item => item.match(route)).length, 1, route);
  assert.ok(WORKSPACE_SECONDARY['/applications'].some(item => item.href === '/agents'));
});

test('normalized quote highlights actual whitespace and Unicode source positions', () => {
  const content = '📄条款：研发\n 费用比例';
  const span = findQuoteSpan(content, '研发费用', 4);
  assert.deepEqual(span, {start: 5, end: 11});
  assert.equal(findQuoteSpan(content, '虚构引用'), null);
});
