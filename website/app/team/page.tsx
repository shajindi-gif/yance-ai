"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type TeamMember } from "@/lib/api";

export default function TeamPage() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ email: "", full_name: "", password: "" });

  const load = useCallback(async () => {
    setError("");
    try {
      setMembers(await api.getUsers());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "成员加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!api.isAuthenticated()) {
      window.location.href = "/login";
      return;
    }
    void load();
  }, [load]);

  const addMember = async () => {
    if (form.email.includes("@") === false || form.full_name.trim().length < 2 || form.password.length < 12) {
      setError("请填写有效邮箱、姓名（≥2 字）与初始密码（≥12 位）");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.createUser({
        email: form.email.trim(),
        full_name: form.full_name.trim(),
        password: form.password,
      });
      setForm({ email: "", full_name: "", password: "" });
      setNotice("成员已创建。请把初始密码通过安全渠道转交本人。");
      await load();
    } catch (addError) {
      setError(addError instanceof Error ? addError.message : "创建失败");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <AppShell><LoadingState label="正在加载团队成员" /></AppShell>;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Team"
        title="团队"
        description="同一工作区内的成员共享企业档案、机会与申报数据。角色决定权限：Owner 可管理成员与删除请求。"
      />
      {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
      {notice ? <InlineAlert tone="info">{notice}</InlineAlert> : null}

      <section className={content.card}>
        <div className={content.cardHeader}>
          <strong>成员（{members.length}）</strong>
        </div>
        <div className={content.rows}>
          {members.map((member) => (
            <div key={member.id} className={content.row}>
              <div>
                <strong>{member.full_name}</strong>
                <div className={content.subtle} style={{ fontSize: 12 }}>{member.email || (member.phone ? `${member.phone.slice(0, 6)}****${member.phone.slice(-4)}` : "未设置邮箱")}</div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Badge tone={member.role === "owner" ? "success" : "neutral"}>{member.role}</Badge>
                {member.is_active ? null : <Badge tone="warning">停用</Badge>}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className={content.card} style={{ marginTop: 16 }}>
        <div className={content.cardHeader}>
          <div>
            <strong>添加成员</strong>
            <div className={content.subtle} style={{ fontSize: 12, marginTop: 4 }}>
              新成员以 member 角色创建（当前产品阶段暂不支持自定义角色分配）。
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input
            value={form.full_name}
            onChange={(event) => setForm({ ...form, full_name: event.target.value })}
            placeholder="姓名"
            style={{ flex: 1, minWidth: 140, padding: "10px 12px", border: "1px solid #dde3eb", borderRadius: 8, fontSize: 13 }}
          />
          <input
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            placeholder="工作邮箱"
            type="email"
            style={{ flex: 1, minWidth: 180, padding: "10px 12px", border: "1px solid #dde3eb", borderRadius: 8, fontSize: 13 }}
          />
          <input
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
            placeholder="初始密码（≥12 位）"
            type="password"
            style={{ flex: 1, minWidth: 160, padding: "10px 12px", border: "1px solid #dde3eb", borderRadius: 8, fontSize: 13 }}
          />
          <Button onClick={addMember} disabled={busy}>
            {busy ? "创建中…" : "添加"}
          </Button>
        </div>
      </section>
    </AppShell>
  );
}
