"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type Company } from "@/lib/api";

export default function CompaniesPage() {
  const router = useRouter();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [province, setProvince] = useState("");
  const [city, setCity] = useState("");

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let active = true;
    api
      .getCompanies()
      .then((result) => {
        if (active) setCompanies(result);
      })
      .catch((loadError) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "企业列表加载失败");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  const createCompany = async (event: React.FormEvent) => {
    event.preventDefault();
    setCreating(true);
    setError("");
    try {
      const company = await api.createCompany({ name, industry, province, city });
      setCompanies((current) => [company, ...current]);
      setShowForm(false);
      setName("");
      setIndustry("");
      setProvince("");
      setCity("");
      router.push(`/companies/${company.id}`);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "企业创建失败");
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载企业" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Companies"
        title="企业"
        description="每家企业拥有独立画像、资料、扫描和申报历史。"
        actions={
          <Button type="button" onClick={() => setShowForm((visible) => !visible)}>
            {showForm ? "关闭表单" : "创建企业"}
          </Button>
        }
      />
      {error && <InlineAlert>{error}</InlineAlert>}

      {showForm && (
        <form className={content.card} onSubmit={createCompany}>
          <div className={flow.formGrid}>
            <div className={flow.fieldWide}>
              <label htmlFor="company-name">企业名称</label>
              <input
                id="company-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                minLength={1}
                maxLength={240}
                required
              />
            </div>
            <div className={flow.field}>
              <label htmlFor="company-industry">所属行业</label>
              <input
                id="company-industry"
                value={industry}
                onChange={(event) => setIndustry(event.target.value)}
                maxLength={160}
              />
            </div>
            <div className={flow.field}>
              <label htmlFor="company-province">省份</label>
              <input
                id="company-province"
                value={province}
                onChange={(event) => setProvince(event.target.value)}
                maxLength={80}
              />
            </div>
            <div className={flow.field}>
              <label htmlFor="company-city">城市</label>
              <input
                id="company-city"
                value={city}
                onChange={(event) => setCity(event.target.value)}
                maxLength={80}
              />
            </div>
          </div>
          <div className={content.actionRow}>
            <Button type="submit" disabled={creating || !name.trim()}>
              {creating ? "创建中…" : "创建并完善画像"}
            </Button>
          </div>
        </form>
      )}

      {!showForm && companies.length === 0 ? (
        <EmptyState
          icon="▦"
          title="暂无企业"
          description="创建第一家企业后，系统会建立独立的画像草稿。"
          action={
            <Button type="button" onClick={() => setShowForm(true)}>
              创建企业
            </Button>
          }
        />
      ) : (
        <div className={content.stack}>
          {companies.map((company) => (
            <Link key={company.id} href={`/companies/${company.id}`} className={content.listCard}>
              <div className={content.listCardHeader}>
                <span className={content.itemTitle}>{company.name}</span>
                <span className={content.subtle}>查看画像 →</span>
              </div>
              <div className={content.meta}>
                {[company.industry, company.province, company.city].filter(Boolean).join(" · ") ||
                  "基础信息待完善"}
              </div>
            </Link>
          ))}
        </div>
      )}
    </AppShell>
  );
}
