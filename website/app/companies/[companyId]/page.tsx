"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
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
  district: null,
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

const STEPS = [
  { id: "basic", label: "基本信息", hint: "行业、地域与规模" },
  { id: "certs", label: "认定资质", hint: "高企 / 专精特新等" },
  { id: "rd", label: "研发与产品", hint: "研发、知识产权、产品" },
  { id: "needs", label: "需求", hint: "当前项目与诉求" },
] as const;

type StepId = (typeof STEPS)[number]["id"];

const PROVINCE_CITY: Record<string, string[]> = {
  上海市: ["上海市"],
  北京市: ["北京市"],
  广东省: ["广州市", "深圳市", "东莞市", "佛山市", "珠海市", "中山市"],
  浙江省: ["杭州市", "宁波市", "嘉兴市", "温州市", "绍兴市"],
  江苏省: ["南京市", "苏州市", "无锡市", "常州市", "南通市"],
  山东省: ["济南市", "青岛市", "烟台市", "潍坊市"],
  四川省: ["成都市", "绵阳市"],
  湖北省: ["武汉市", "襄阳市"],
  福建省: ["福州市", "厦门市", "泉州市"],
};

const lines = (value: string) =>
  value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

function missingForScan(draft: CompanyProfileData): string[] {
  const gaps: string[] = [];
  if (!draft.industry) gaps.push("所属行业");
  if (!draft.province) gaps.push("省份");
  if (!draft.city) gaps.push("城市");
  if (!draft.company_scale) gaps.push("企业规模");
  if (!draft.high_tech_status && !draft.specialized_sme_status) gaps.push("至少一项认定状态");
  return gaps;
}

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
  const [supportsDistrict, setSupportsDistrict] = useState(false);
  const [step, setStep] = useState<StepId>("basic");

  const load = async () => {
    const [companyResult, profileResult, versionResult, capabilities] = await Promise.all([
      api.getCompany(companyId),
      api.getCompanyProfile(companyId),
      api.getCompanyProfileVersions(companyId),
      api.getAuthConfig(),
    ]);
    setCompany(companyResult);
    setProfile(profileResult);
    const nextDraft = { ...EMPTY_PROFILE, ...profileResult.draft_json };
    if (!nextDraft.province && companyResult.province) nextDraft.province = companyResult.province;
    if (!nextDraft.city && companyResult.city) nextDraft.city = companyResult.city;
    if (!nextDraft.industry && companyResult.industry) nextDraft.industry = companyResult.industry;
    setDraft(nextDraft);
    setVersions(versionResult);
    setSupportsDistrict(capabilities.district_profile_enabled === true);
  };

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
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

  const profilePayload = (): CompanyProfileData => {
    if (supportsDistrict) return draft;
    if (draft.district) throw new Error("暂未确认服务端支持区县字段，为保留已有资料，请刷新后重试。");
    const legacy = { ...draft };
    delete legacy.district;
    return legacy;
  };

  const save = async () => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const result = await api.updateCompanyProfile(companyId, profilePayload());
      setProfile(result);
      setMessage(`本步草稿已保存，完整度 ${result.completeness_score}%`);
      return result;
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "画像保存失败");
      return null;
    } finally {
      setSaving(false);
    }
  };

  const saveAndNext = async () => {
    const result = await save();
    if (!result) return;
    const index = STEPS.findIndex((item) => item.id === step);
    if (index < STEPS.length - 1) setStep(STEPS[index + 1].id);
  };

  const publish = async () => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await api.updateCompanyProfile(companyId, profilePayload());
      const version = await api.publishCompanyProfile(companyId);
      await load();
      setMessage(`企业画像 V${version.version} 已发布。可前往问衍策或开始政策扫描。`);
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : "画像发布失败");
    } finally {
      setSaving(false);
    }
  };

  const gaps = useMemo(() => missingForScan(draft), [draft]);
  const cityOptions = draft.province ? PROVINCE_CITY[draft.province] || [] : [];

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
        title={company.name}
        description="分步填写可验证画像；每步可保存草稿，发布后形成不可变版本。"
        actions={
          <div className={flow.toolbarActions}>
            <ButtonLink href="/companies" variant="secondary">返回列表</ButtonLink>
            <Button type="button" variant="secondary" onClick={save} disabled={saving}>
              保存本步
            </Button>
            <Button type="button" onClick={publish} disabled={saving}>
              {saving ? "处理中…" : "一键发布"}
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
              : gaps.length
                ? `发布前建议补齐：${gaps.join("、")}`
                : "字段已齐，可发布后扫描 / 问答"}
          </span>
        </div>
        <div className={flow.progress} aria-label={`画像完整度 ${profile.completeness_score}%`}>
          <span style={{ width: `${profile.completeness_score}%` }} />
        </div>
      </div>

      <div className={flow.toolbar} role="tablist" aria-label="画像步骤">
        {STEPS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={step === item.id ? flow.secondaryAction : undefined}
            aria-selected={step === item.id}
            onClick={() => setStep(item.id)}
            style={{
              border: "1px solid var(--line)",
              borderRadius: 8,
              background: step === item.id ? "var(--surface)" : "transparent",
              padding: "8px 12px",
              cursor: "pointer",
              textAlign: "left",
            }}
          >
            <strong style={{ display: "block", fontSize: 13 }}>{item.label}</strong>
            <span style={{ color: "var(--muted)", fontSize: 12 }}>{item.hint}</span>
          </button>
        ))}
      </div>

      <section className={content.card}>
        <div className={flow.formGrid}>
          {step === "basic" && (
            <>
              <div className={flow.field}>
                <label htmlFor="profile-industry">所属行业</label>
                <input id="profile-industry" value={draft.industry || ""} onChange={(event) => setValue("industry", event.target.value || null)} placeholder="如：人工智能 / 先进制造" />
              </div>
              <div className={flow.field}>
                <label htmlFor="profile-founded">成立日期</label>
                <input id="profile-founded" type="date" value={draft.founded_date || ""} onChange={(event) => setValue("founded_date", event.target.value || null)} />
              </div>
              <div className={flow.field}>
                <label htmlFor="profile-province">省份</label>
                <select
                  id="profile-province"
                  value={draft.province || ""}
                  onChange={(event) => {
                    const province = event.target.value || null;
                    const cities = province ? PROVINCE_CITY[province] || [] : [];
                    setDraft((current) => ({
                      ...current,
                      province,
                      city: cities.includes(current.city || "") ? current.city : cities[0] || null,
                    }));
                    setMessage("");
                  }}
                >
                  <option value="">请选择</option>
                  {draft.province && !PROVINCE_CITY[draft.province] ? (
                    <option value={draft.province}>{draft.province}</option>
                  ) : null}
                  {Object.keys(PROVINCE_CITY).map((province) => (
                    <option key={province} value={province}>{province}</option>
                  ))}
                </select>
                <input
                  aria-label="省份手填"
                  placeholder="列表外省份可手填"
                  value={PROVINCE_CITY[draft.province || ""] ? "" : draft.province || ""}
                  onChange={(event) => {
                    const province = event.target.value || null;
                    setDraft((current) => ({ ...current, province, city: current.city }));
                    setMessage("");
                  }}
                  style={{ marginTop: 6 }}
                />
              </div>
              <div className={flow.field}>
                <label htmlFor="profile-city">城市</label>
                {cityOptions.length ? (
                  <select id="profile-city" value={draft.city || ""} onChange={(event) => setValue("city", event.target.value || null)}>
                    <option value="">请选择</option>
                    {cityOptions.map((city) => <option key={city} value={city}>{city}</option>)}
                  </select>
                ) : (
                  <input id="profile-city" value={draft.city || ""} onChange={(event) => setValue("city", event.target.value || null)} placeholder="手填城市" />
                )}
              </div>
              {supportsDistrict ? (
                <div className={flow.field}>
                  <label htmlFor="profile-district">区县</label>
                  <input id="profile-district" value={draft.district || ""} onChange={(event) => setValue("district", event.target.value || null)} />
                </div>
              ) : null}
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
                <input id="profile-funding" value={draft.funding_stage || ""} onChange={(event) => setValue("funding_stage", event.target.value || null)} placeholder="如：A 轮 / 未融资" />
              </div>
            </>
          )}

          {step === "certs" && (
            <>
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
            </>
          )}

          {step === "rd" && (
            <>
              <div className={flow.field}>
                <label htmlFor="profile-rd-ratio">研发费用占比（%）</label>
                <input id="profile-rd-ratio" type="number" min="0" max="100" step="0.1" value={draft.rd_expense_ratio ?? ""} onChange={(event) => setValue("rd_expense_ratio", event.target.value === "" ? null : Number(event.target.value))} />
              </div>
              <div className={flow.fieldWide}>
                <label htmlFor="profile-ip">知识产权（每行一项）</label>
                <textarea id="profile-ip" value={draft.intellectual_property.join("\n")} onChange={(event) => setValue("intellectual_property", lines(event.target.value))} />
              </div>
              <div className={flow.fieldWide}>
                <label htmlFor="profile-products">核心产品（每行一项）</label>
                <textarea id="profile-products" value={draft.core_products.join("\n")} onChange={(event) => setValue("core_products", lines(event.target.value))} />
              </div>
              <div className={flow.fieldWide}>
                <label htmlFor="profile-rd">研发情况</label>
                <textarea id="profile-rd" value={draft.rd_summary || ""} onChange={(event) => setValue("rd_summary", event.target.value || null)} />
              </div>
              <div className={flow.fieldWide}>
                <label htmlFor="profile-talent">人才情况</label>
                <textarea id="profile-talent" value={draft.talent_summary || ""} onChange={(event) => setValue("talent_summary", event.target.value || null)} />
              </div>
            </>
          )}

          {step === "needs" && (
            <>
              <div className={flow.fieldWide}>
                <label htmlFor="profile-projects">当前项目（每行一项）</label>
                <textarea id="profile-projects" value={draft.projects.join("\n")} onChange={(event) => setValue("projects", lines(event.target.value))} />
              </div>
              <div className={flow.fieldWide}>
                <label htmlFor="profile-needs">当前需求（每行一项）</label>
                <textarea id="profile-needs" value={draft.current_needs.join("\n")} onChange={(event) => setValue("current_needs", lines(event.target.value))} placeholder="如：专精特新申报、研发加计材料梳理" />
              </div>
            </>
          )}
        </div>

        <div className={flow.toolbarActions} style={{ marginTop: 16 }}>
          {step !== "basic" && (
            <Button
              type="button"
              variant="secondary"
              disabled={saving}
              onClick={() => setStep(STEPS[Math.max(0, STEPS.findIndex((item) => item.id === step) - 1)].id)}
            >
              上一步
            </Button>
          )}
          {step !== "needs" ? (
            <Button type="button" onClick={saveAndNext} disabled={saving}>
              {saving ? "保存中…" : "保存并下一步"}
            </Button>
          ) : (
            <Button type="button" onClick={publish} disabled={saving}>
              {saving ? "处理中…" : "保存并发布"}
            </Button>
          )}
          <ButtonLink href="/dashboard" variant="secondary">回工作台提问</ButtonLink>
          <ButtonLink href="/opportunities" variant="secondary">去看机会</ButtonLink>
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
