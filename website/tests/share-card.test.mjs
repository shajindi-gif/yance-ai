import assert from 'node:assert/strict';
import test from 'node:test';
import { buildShareModel, shareCopy, wrapText, SHARE_ANONYMOUS_LABEL, SHARE_DISCLAIMER } from '../lib/share-card.ts';

const NOW = new Date(2026, 10, 24);

function opp(overrides = {}) {
  const { rank, region, ...rest } = overrides;
  return {
    title: rest.title ?? '默认政策',
    score: rest.score ?? 0.6,
    eligibility_status: rest.eligibility_status ?? 'NEED_MORE_INFORMATION',
    policy_snapshot_json: {
      title: rest.title ?? '默认政策',
      issuing_authority: '上海市科委',
      jurisdiction: '上海市',
      city: '上海市',
      deadline: '2026-12-31T00:00:00Z',
      ...(rest.policy_snapshot_json ?? {}),
    },
    evidence_json: {
      rank_features: {
        final_score: rank ?? 50,
        region_fit: region ?? 0,
        ranking_note: rest.ranking_note ?? null,
      },
    },
  };
}

test('top items are ordered by effectiveness score and capped at three', () => {
  const list = [
    opp({ title: 'A', rank: 40 }),
    opp({ title: 'B', rank: 90 }),
    opp({ title: 'C', rank: 70 }),
    opp({ title: 'D', rank: 60 }),
  ];
  const model = buildShareModel(list, { now: NOW });
  assert.deepEqual(model.items.map(i => i.title), ['B', 'C', 'D']);
  assert.equal(model.reviewable, 4);
});

test('company name is hidden by default and only shown on explicit opt-in', () => {
  const list = [opp({ rank: 80 })];
  const hidden = buildShareModel(list, { companyName: '某某科技有限公司', now: NOW });
  assert.equal(hidden.companyLabel, SHARE_ANONYMOUS_LABEL);
  assert.ok(!hidden.subhead.includes('某某科技'));
  assert.ok(!shareCopy(hidden).includes('某某科技'));

  const shown = buildShareModel(list, { companyName: '某某科技有限公司', showCompany: true, now: NOW });
  assert.equal(shown.companyLabel, '某某科技有限公司');
});

test('wording never claims eligibility and keeps the disclaimer', () => {
  const list = [
    opp({ title: '专精特新', rank: 80, eligibility_status: 'ELIGIBLE' }),
    opp({ title: '高企', rank: 70, eligibility_status: 'POTENTIALLY_ELIGIBLE' }),
  ];
  const model = buildShareModel(list, { now: NOW });
  const copy = shareCopy(model);
  for (const banned of ['符合', '可以申请', '可获得', '万元', '已通过']) {
    assert.ok(!copy.includes(banned), `copy must not contain ${banned}`);
    assert.ok(!model.headline.includes(banned), `headline must not contain ${banned}`);
  }
  assert.ok(copy.includes(SHARE_DISCLAIMER));
});

test('not-eligible and weak matches are counted out of highlights', () => {
  const list = [
    opp({ title: '拒绝项', rank: 99, eligibility_status: 'NOT_ELIGIBLE' }),
    opp({ title: '弱项', rank: 98, ranking_note: '弱匹配：尚无已审核硬门槛规则，已降权并仅作信息参考' }),
    opp({ title: '有效项', rank: 10 }),
  ];
  const model = buildShareModel(list, { now: NOW });
  assert.deepEqual(model.items.map(i => i.title), ['有效项']);
  assert.equal(model.total, 3);
  assert.equal(model.reviewable, 1);
});

test('same-region and deadline counts come from the rank features and snapshot', () => {
  const list = [
    opp({ rank: 80, region: 20 }),
    opp({ rank: 70, region: 4, policy_snapshot_json: { deadline: null } }),
  ];
  const model = buildShareModel(list, { now: NOW });
  assert.equal(model.cityMatched, 1);
  assert.equal(model.withDeadline, 1);
  assert.equal(model.items[0].sameRegion, true);
  assert.equal(model.items[0].deadline, '2026-12-31');
  assert.equal(model.items[1].deadline, null);
});

test('empty result yields a neutral headline and no items', () => {
  const model = buildShareModel([], { now: NOW });
  assert.equal(model.headline, '本次扫描暂无可优先核对的政策机会');
  assert.deepEqual(model.items, []);
  assert.equal(model.generatedOn, '2026年11月24日');
});

test('share copy truncates long titles and stays within a readable length', () => {
  const longTitle = '关于进一步支持人工智能与集成电路产业高质量发展若干政策措施的通知（试行）补充说明文件';
  const model = buildShareModel([opp({ title: longTitle, rank: 50 })], { now: NOW });
  const copy = shareCopy(model);
  assert.ok(copy.includes('…'));
  assert.ok(copy.length < 400);
});

test('wrapText is CJK-aware, respects maxLines and adds an ellipsis when truncated', () => {
  const measure = text => Array.from(text).length * 10;
  assert.deepEqual(wrapText(measure, '短句', 100, 2), ['短句']);
  assert.deepEqual(wrapText(measure, '一二三四五六七八九十甲乙丙丁戊己庚辛', 100, 2).join(''), '一二三四五六七八九十甲乙丙丁戊己庚辛');
  const lines = wrapText(measure, '一二三四五六七八九十甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午', 100, 2);
  assert.equal(lines.length, 2);
  assert.ok(lines[1].endsWith('…'));
  for (const line of lines) assert.ok(measure(line) <= 100);
});
