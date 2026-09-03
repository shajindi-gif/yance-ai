"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, {
  type Company,
  type CompanyProfile,
  type CompanyProfileData,
  type CompanyProfileVersion,
} from "@/lib/api";

const EMPTY_PROFILE: CompanyProfileData = {
  industry: null,
  province: null,
  city: null,
  registered_address: null,
  founded_date: null,
  company_scale: null,
  employee_count: null,
  revenue_stage: null,
  annual_revenue: null,
  funding_stage: null,
  high_tech_status: null,
  tech_sme_status: null,
  specialized_sme_status: null,
  intellectual_property: [],
  core_products: [],
  rd_summary: null,
  rd_expense_ratio: null,
  talent_summary: null,
  projects: [],
  current_needs: [],
};

const lines = (value: string) =>
  value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

export default function CompanyProfilePage() {
  const params = useParams<{ companyId: string }>();
  const router = useRouter();
  const companyId = params.companyId;
  const [company, setCompany] = useState<Company | null>(null);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [versions, setVersions] = useState<CompanyProfileVersion[]>([]);
  const [draft, setDraft] = useState<CompanyProfileData>(EMPTY_PROFILE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    const [companyResult, profileResult, versionResult] = await Promise.all([
      api.getCompany(companyId),
      api.getCompanyProfile(companyId),
      api.getCompanyProfileVersions(companyId),
    ]);
    setCompany(companyResult);
    setProfile(profileResult);
    setDraft({ ...EMPTY_PROFILE, ...profileResult.draft_json });
    setVersions(versionResult);
  };

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let active = true;
    load()
      .catch((loadError) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "企业画像加载失败");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [companyId, router]);

  const setValue = <K extends keyof CompanyProfileData>(key: K, value: CompanyProfileData[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setMessage("");
  };

  const save = async () => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const result = await api.updateCompanyProfile(companyId, draft);
      setProfile(result);
      setMessage(`画像草稿已保存，完整度 ${result.completeness_score}%`);
      return result;
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "画像保存失败");
      return null;
    } finally {
      setSaving(false);
    }
  };

  const publish = async () => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await api.updateCompanyProfile(companyId, draft);
      const version = await api.publishCompanyProfile(companyId);
      await load();
      setMessage(`企业画像 V${version.version} 已发布，后续扫描会固定使用该版本。`);
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : "画像发布失败");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载企业画像" />
      </AppShell>
    );
  }

  if (!company || !profile) {
    return (
      <AppShell>
        <PageHeader title="企业不可用" description="企业不存在、无权访问或暂时无法加载。" />
        {error && <InlineAlert>{error}</InlineAlert>}
        <ButtonLink href="/companies" variant="secondary">返回企业列表</ButtonLink>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Company profile"
        title={company.name}
        description="编辑可验证的结构化画像；发布后形成不可变版本，扫描不会被后续修改静默影响。"
        actions={
          <div className={flow.toolbarActions}>
            <ButtonLink href="/companies" variant="secondary">返回列表</ButtonLink>
            <Button type="button" variant="secondary" onClick={save} disabled={saving}>
              保存草稿
            </Button>
            <Button type="button" onClick={publish} disabled={saving}>
              {saving ? "处理中…" : "发布新版本"}
            </Button>
          </div>
        }
      />
      {error && <InlineAlert>{error}</InlineAlert>}
      {message && <InlineAlert tone="info">{message}</InlineAlert>}

      <div className={flow.summaryBar}>
        <div>
          <strong>画像完整度 {profile.completeness_score}%</strong>
          <span>
            {profile.published_version
              ? `当前已发布 V${profile.published_version}`
              : "尚未发布；发布后才能创建政策扫描。"}
          </span>
        </div>
        <div className={flow.progress} aria-label={`画像完整度 ${profile.completeness_score}%`}>
          <span style={{ width: `${profile.completeness_score}%` }} />
        </div>
      </div>

      <section className={content.card}>
        <div className={flow.formGrid}>
          <div className={flow.field}>
            <label htmlFor="profile-industry">所属行业</label>
            <input id="profile-industry" value={draft.industry || ""} onChange={(event) => setValue("industry", event.target.value || null)} />
          </div>
          <div className={flow.field}>
            <label htmlFor="profile-founded">成立日期</label>
            <input id="profile-founded" type="date" value={draft.founded_date || ""} onChange={(event) => setValue("founded_date", event.target.value || null)} />
          </div>
          <div className={flow.field}>
            <label htmlFor="profile-province">省份</label>
            <input id="profile-province" value={draft.province || ""} onChange={(event) => setValue("province", event.target.value || null)} />
          </div>
          <div className={flow.field}>
            <label htmlFor="profile-city">城市</label>
            <input id="profile-city" value={draft.city || ""} onChange={(event) => setValue("city", event.target.value || null)} />
          </div>
          <div className={flow.fieldWide}>
            <label htmlFor="profile-address">注册地址</label>
            <input id="profile-address" value={draft.registered_address || ""} onChange={(event) => setValue("registered_address", event.target.value || null)} />
          </div>
          <div className={flow.field}>
            <label htmlFor="profile-scale">企业规模</label>
            <select id="profile-scale" value={draft.company_scale || ""} onChange={(event) => setValue("company_scale", event.target.value || null)}>
              <option value="">请选择</option><option>微型</option><option>小型</option><option>中型</option><option>大型</option>
            </select>
          </div>
          <div className={flow.field}>
            <label htmlFor="profile-employees">员工人数</label>
            <input id="profile-employees" type="number" min="0" value={draft.employee_count ?? ""} onChange={(event) => setValue("employee_count", event.target.value === "" ? null : Number(event.target.value))} />
          </div>
          <div className={flow.field}>
            <label htmlFor="profile-revenue-stage">营收阶段</label>
            <input id="profile-revenue-stage" value={draft.revenue_stage || ""} onChange={(event) => setValue("revenue_stage", event.target.value || null)} />
          </div>
          <div className={flow.field}>
            <label htmlFor="profile-revenue">年营收（元）</label>
            <input id="profile-revenue" type="number" min="0" value={draft.annual_revenue ?? ""} onChange={(event) => setValue("annual_revenue", event.target.value === "" ? null : Number(event.target.value))} />
          </div>
          <div className={flow.field}>
            <label htmlFor="profile-funding">融资阶段</label>
            <input id="profile-funding" value={draft.funding_stage || ""} onChange={(event) => setValue("funding_stage", event.target.value || null)} />
          </div>
          <div className={flow.field}>
            <label htmlFor="profile-rd-ratio">研发费用占比（%）</label>
            <input id="profile-rd-ratio" type="number" min="0" max="100" step="0.1" value={draft.rd_expense_ratio ?? ""} onChange={(event) => setValue("rd_expense_ratio", event.target.value === "" ? null : Number(event.target.value))} />
          </div>
          {([
            ["high_tech_status", "高新技术企业情况"],
            ["tech_sme_status", "科技型中小企业情况"],
            ["specialized_sme_status", "专精特新情况"],
          ] as const).map(([key, label]) => (
            <div className={flow.field} key={key}>
              <label htmlFor={`profile-${key}`}>{label}</label>
              <select id={`profile-${key}`} value={draft[key] || ""} onChange={(event) => setValue(key, event.target.value || null)}>
                <option value="">请选择</option><option>未认定</option><option>准备申报</option><option>申报中</option><option>已认定</option><option>已过期</option>
              </select>
            </div>
          ))}
          {([
            ["intellectual_property", "知识产权（每行一项）"],
            ["core_products", "核心产品（每行一项）"],
            ["projects", "当前项目（每行一项）"],
            ["current_needs", "当前需求（每行一项）"],
          ] as const).map(([key, label]) => (
            <div className={flow.fieldWide} key={key}>
              <label htmlFor={`profile-${key}`}>{label}</label>
              <textarea id={`profile-${key}`} value={draft[key].join("\n")} onChange={(event) => setValue(key, lines(event.target.value))} />
            </div>
          ))}
          <div className={flow.fieldWide}>
            <label htmlFor="profile-rd">研发情况</label>
            <textarea id="profile-rd" value={draft.rd_summary || ""} onChange={(event) => setValue("rd_summary", event.target.value || null)} />
          </div>
          <div className={flow.fieldWide}>
            <label htmlFor="profile-talent">人才情况</label>
            <textarea id="profile-talent" value={draft.talent_summary || ""} onChange={(event) => setValue("talent_summary", event.target.value || null)} />
          </div>
        </div>
      </section>

      <section className={content.section}>
        <div className={content.sectionHeading}>
          <h2>已发布版本</h2>
          <p>历史扫描可固定引用这些快照；发布不会覆盖旧版本。</p>
        </div>
        {versions.length === 0 ? (
          <InlineAlert tone="info">暂无已发布画像版本。</InlineAlert>
        ) : (
          <div className={content.stack}>
            {versions.map((version) => (
              <div className={content.listCard} key={version.id}>
                <div className={content.listCardHeader}>
                  <span className={content.itemTitle}>画像 V{version.version}</span>
                  <Badge tone="success">已发布</Badge>
                </div>
                <div className={content.meta}>
                  完整度 {version.completeness_score}% · {new Date(version.published_at).toLocaleString("zh-CN")}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}
