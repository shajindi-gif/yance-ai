"use client";

import { useState } from 'react';
import type { ApplicationArtifact } from '@/lib/api';
import { compareArtifactContent } from '@/lib/artifact-diff';
import styles from './ArtifactComparison.module.css';

export function ArtifactComparison({ artifacts }: { artifacts: ApplicationArtifact[] }) {
  const [selectedId, setSelectedId] = useState('');
  const versions = [...artifacts].sort((a, b) => b.version - a.version);
  const latest = versions[0];
  const previous = versions.filter(item => item.id !== latest?.id && item.artifact_type === latest?.artifact_type);
  const baseline = previous.find(item => item.id === selectedId) || previous[0];
  if (!latest || !baseline) return <p>生成两个同类工作稿版本后，可查看版本差异。</p>;
  const changes = compareArtifactContent(baseline.content, latest.content);
  const sourceChanged = compareArtifactContent(baseline.source_snapshot, latest.source_snapshot).length > 0;
  return <section className={styles.panel} aria-label="工作稿版本比较">
    <h3>版本差异</h3>
    <label>对比基准版本 <select value={baseline.id} onChange={event => setSelectedId(event.target.value)}>
      {previous.map(item => <option key={item.id} value={item.id}>v{item.version} · {item.title}</option>)}
    </select></label>
    <p role="status">v{baseline.version} → v{latest.version}：{changes.length} 项内容变化。来源快照{sourceChanged ? '已变化，请核对证据与画像版本' : '无变化'}。</p>
    <p>只比较保存的版本，不代表新稿已获批准；审批状态和来源检查仍以当前工作稿为准。</p>
    {changes.length === 0 ? <p>正文内容一致；状态、时间和审阅记录不计入正文差异。</p> : changes.map(change => <details key={change.key}>
      <summary>{change.label} · 已修改</summary>
      <div className={styles.columns}><div><h4>原稿 v{baseline.version}</h4><pre>{change.before}</pre></div><div><h4>新稿 v{latest.version}</h4><pre>{change.after}</pre></div></div>
    </details>)}
  </section>;
}
