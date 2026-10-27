import assert from 'node:assert/strict';
import test from 'node:test';
import { apiErrorMessage } from '../lib/api-errors.ts';
import { safeReturnPath } from '../lib/return-path.ts';

test('post-auth destinations preserve the task and reject external or privileged API destinations', () => {
  for (const path of ['/feedback', '/checkout?product=POLICY_REPORT&company=synthetic', '/applications/synthetic?tab=review#draft']) assert.equal(safeReturnPath(path), path);
  for (const path of ['https://evil.invalid', '//evil.invalid', '/\\evil.invalid', '/%5cevil.invalid', '/%2f%2fevil.invalid', '/login?next=/login', '/api/v1/admin', '/companies/../api/v1/users', '/feedback%0a', '/%zz']) assert.equal(safeReturnPath(path), '/dashboard');
});

test('structured API errors provide next steps without disclosing validation inputs', () => {
  assert.equal(apiErrorMessage({ message: '该产品暂未开通', code: 'blocked' }, '失败'), '该产品暂未开通');
  assert.match(apiErrorMessage({ code: 'quota_exceeded', meter: 'generated_documents' }, '失败'), /生成工作稿额度不足/);
  assert.equal(apiErrorMessage([{ msg: '至少两个字符', input: 'private-synthetic-input', loc: ['body','message'] }], '失败'), '至少两个字符');
  assert.equal(apiErrorMessage({ input: 'private-synthetic-input' }, '请求失败'), '请求失败');
  assert.equal(apiErrorMessage(null, '请求失败'), '请求失败');
});
