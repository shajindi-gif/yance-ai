import { test } from 'node:test';
import assert from 'node:assert/strict';
import { compareArtifactContent } from '../lib/artifact-diff.ts';

test('object key order does not invent evidence changes', () => {
  assert.deepEqual(compareArtifactContent({ evidence: { quote: '原文', id: 1 } }, { evidence: { id: 1, quote: '原文' } }), []);
});
test('missing and null remain distinct, deletion is visible', () => {
  assert.equal(compareArtifactContent({ title: '旧稿' }, { title: null })[0].after, 'null');
  assert.equal(compareArtifactContent({ title: '旧稿' }, {})[0].after, '（字段不存在）');
});
test('changed nested citations and ordered arrays are visible', () => {
  assert.equal(compareArtifactContent({ evidence: [{ quote: '原文' }] }, { evidence: [{ quote: '另一条款' }] })[0].label, '政策证据');
  assert.equal(compareArtifactContent({ criteria: [1, 2] }, { criteria: [2, 1] }).length, 1);
});
test('source comparison covers unknown metadata without dropping fields', () => {
  assert.equal(compareArtifactContent({ profile: 'v1' }, { profile: 'v2' })[0].key, 'profile');
});
