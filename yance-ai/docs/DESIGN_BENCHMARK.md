# AI SaaS / Vertical AI Agent Design Benchmark

**Research date:** 2026-07 (single-session live-site analysis)
**Method:** Programmatic homepage fetch + structural/CSS analysis of each site's rendered markup, font files, color tokens, breakpoints, and animation classes. Motion and mobile behavior are inferred from code evidence (keyframe names, breakpoint lists, mobile asset variants), not from live rendering.
**Purpose:** Extract transferable design patterns for building an enterprise-grade AI product website. Nothing here should be copied from any specific brand — the goal is pattern synthesis.

---

## 0. Coverage Summary

| # | Target | Status | Notes |
|---|--------|--------|-------|
| 1 | Harvey (harvey.ai) | ✅ Analyzed | Legal AI |
| 2 | Sierra (sierra.ai) | ✅ Analyzed | CX agents |
| 3 | Glean (glean.com) | ✅ Analyzed | Work AI / search |
| 4 | Hebbia (hebbia.ai → hebbia.com) | ✅ Analyzed | Finance AI (redirects to .com) |
| 5 | Decagon (decagon.ai) | ✅ Analyzed | CX agents |
| 6 | Hippocratic AI (hippocratic.ai) | ❌ Inaccessible | Fetch failed repeatedly (likely bot protection) |
| 7 | EvenUp (evenuplaw.com) | ✅ Analyzed | Personal-injury legal AI |
| 8 | Abridge (abridge.com) | ✅ Analyzed | Clinical documentation |
| 9 | Ambience Healthcare (ambiencehealthcare.com) | ✅ Analyzed | Clinical documentation/coding |
| 10 | Nabla (nabla.com) | ✅ Analyzed | Clinical AI layer |
| 11 | Legora (legora.ai) | ✅ Analyzed via **legora.com** | legora.ai is an unrelated parked site; real product is at legora.com |
| 12 | Norm AI (norm.ai) | ✅ Analyzed | Agentic law/compliance |
| 13 | Rogo (rogo.ai) | ⚠️ Partial | rogo.ai geo-blocked (CloudFront 403); rogo.com returned mostly CSS (positioning, fonts, palette only) |
| 14 | Brightwave (brightwave.ai) | ❌ Inaccessible | Fetch failed on www and apex |
| 15 | Writer (writer.com) | ✅ Analyzed | Enterprise AI platform |
| 16 | Cognition / Devin (cognition.ai → cognition.com) | ✅ Analyzed | Redirects to cognition.com |
| 17 | Mercor (mercor.com) | ✅ Analyzed | AI talent marketplace |
| 18 | Lindy (lindy.ai) | ✅ Analyzed | AI executive assistant |
| 19 | Dust (dust.tt) | ❌ Inaccessible | Fetch failed repeatedly |
| 20 | Phia (phia.ai) | ❌ Inaccessible | Fetch failed repeatedly |
| 21 | Cursor (cursor.com) | ✅ Analyzed | Coding agent |
| 22 | Perplexity (perplexity.ai) | ❌ Inaccessible | Fetch failed on all variants |
| 23 | Linear (linear.app) | ⚠️ Partial | Heavily JS-rendered; only design-system tokens/CSS retrievable |
| 24 | Vercel (vercel.com) | ✅ Analyzed | Agentic infrastructure |
| 25 | Ramp (ramp.com) | ⚠️ Partial | Served text-only "Machine Version" page (rich content copy, no visuals) |
| 26 | Clay (clay.com) | ✅ Analyzed | GTM data/agents |
| 27 | Attio (attio.com) | ✅ Analyzed | Agentic CRM |
| 28 | Granola (granola.so → granola.ai) | ✅ Analyzed | AI meeting notepad |
| 29 | Lovable (lovable.dev) | ❌ Inaccessible | Cloudflare challenge on both attempts |
| 30 | ElevenLabs (elevenlabs.io) | ✅ Analyzed | Voice AI |

**Substitutes added for inaccessible sites:** Anthropic (anthropic.com) ✅, Synthesia (synthesia.io) ✅, Replit (replit.com) ✅, Bolt.new (bolt.new) ✅. OpenAI (openai.com) and Mistral (mistral.ai) were also attempted as substitutes but were blocked by JS challenges.

**Final sample: 26 sites analyzed (24 substantial, 2 partial), 8 inaccessible.** This exceeds the 20-site minimum.

---

## 1. Site-by-Site Analysis

Each profile covers the 16 benchmark dimensions. Dimensions that could not be determined from the fetch are marked **N/D** (not detectable) rather than guessed.

---

### 1.1 Harvey — harvey.ai (Legal AI)

1. **Hero:** Headline "Practice Made Perfect"; subhead "Today's top law firms and in-house legal teams trust Harvey to elevate their craft and navigate complexity."; CTA "Request a Demo"; full-width video hero (poster asset, not static image). Announcement bar above hero: "Harvey Agents execute legal work end-to-end".
2. **Navigation:** Platform / Solutions / Customers / Security / Resources / Company + Login + Request a Demo. Deep mega-dropdowns (Platform lists Agents, Vault, Knowledge, Shared Spaces, Command Center, Contract Intelligence, Mobile, Ecosystem) with featured promo cards inside menus.
3. **Typography:** Custom branded pairing — **HarveySerif + HarveySans** font files. Large display hero; short high-contrast section labels.
4. **Color:** Dark, premium theme; theme color `#1F1D1A` (warm near-black) with ivory/off-white accents (`gray-50-ivory` token). High contrast, muted, "law-firm grade".
5. **Grid:** Modular section stack: hero → logo marquee → value prop → use-case selector → testimonials → video carousel → stats → security badges → final CTA. Card grids + horizontal carousels.
6. **Spacing:** Generous full-width media blocks; large vertical section padding (typical of dark-premium layouts).
7. **Screenshots:** Deliberately sparse. Relies on video posters, branded imagery, module cards — narrative over dashboard dumps.
8. **Motion:** Logo marquee, video carousels, announcement bar; video-first hero motion.
9. **Social proof:** Elite logos (Vinson & Elkins, Deutsche Telekom, Repsol, Reed Smith, PwC UK, KKR, A&O Shearman, CMS); named GC-level testimonials; big stats (200,000+ professionals, 2,400+ legal teams, 70+ countries, 75+ AmLaw firms).
10. **CTA pattern:** Single repeated primary "Request a Demo" (header, hero, bottom); secondary "Learn more / Explore Platform / arrow links".
11. **Pricing:** None public; links ROI calculators instead.
12. **Dashboard style:** Not shown directly; product framed via use-case labels (Legal Research, Due Diligence, Contract Analysis, Complex Workflows…).
13. **AI interaction:** Agentic framing — agents "execute legal work end-to-end"; answers "grounded in sources you trust".
14. **Mobile:** Mobile product line exists ("Harvey Mobile"); site uses standard responsive sections. **N/D** at pixel level.
15. **Footer:** Columns: Platform / Solutions / Company / Resources / Follow; legal links, help center, social, copyright.
16. **Trust:** Dedicated Security nav item; "Enterprise-grade security and controls" (SAML SSO, audit logs, IP allow-listing, data lifecycle management); badges: **SOC 2 Type II, ISO 27001, ISO 27701, ISO 42001, GDPR, CCPA**.

**Takeaway:** Restraint + prestige. Serif brand fonts, dark ivory-on-charcoal palette, and elite customer names do the selling; product UI is nearly hidden.

---

### 1.2 Sierra — sierra.ai (Customer-experience agents)

1. **Hero:** "Better outcomes. Built on Sierra." CTA "Learn more". Hero shows simulated agent conversations with live widgets (calendar, payment-refund, wifi-troubleshooting) and sample user prompts ("My WiFi keeps dropping"). Announcement bar: "Introducing Voice Personas".
2. **Navigation:** Product / Industries / Customers / Company + Sign in. Product menu organized by lifecycle verbs: **Build** (Ghostwriter, Agent Studio), **Orchestrate** (Horizon, Context Engine), **Optimize** (Explorer, Insights), **Scale** (Channels, Trust & reliability).
3. **Typography:** **GT America Standard + GT America Mono** (Medium/Regular). Bold short H1, mono accents give engineering precision.
4. **Color:** Light default (white), gray section bands (gray-100/200), optional dark "tech" variant; primary button token. Warm neutral photography tones.
5. **Grid:** Vertical marketing flow: announcement → hero → logo strip → benefit messages → testimonials → product modules → trust badges → final CTA. Paired copy + mock-UI cards repeating.
6. **Spacing:** Regular rhythm of paired feature sections; tab/carousel-style module stacks.
7. **Screenshots:** Heavy use of *stylized* product surfaces: Agent Studio dashboards/tables, trace timelines, transfer reports, sNPS cards, reasoning panels, integration maps.
8. **Motion:** Simulated live conversations in hero (chat widgets animate), tabbed module switching implied.
9. **Social proof:** Massive logo wall (30 names incl. Rocket Mortgage, Gap, Singtel, SoftBank, SiriusXM, Wayfair, Vanguard, Uber, GoFundMe, Santander, DIRECTV, Rivian, Nubank, Docusign…); metric graphics ("Great sNPS 32%", "120k conversations").
10. **CTA pattern:** Exploratory, not pushy — "Learn more" primary, "Customer stories" secondary. (Outcome-brand confidence; no "book a demo" hard sell on hero.)
11. **Pricing:** No tiers; explains **outcome-based pricing** ("Pay for a job well done").
12. **Dashboard style:** Agent Studio, Horizon, Insights, Explorer surfaces — observability-forward (traces, monitors, experiments, multivariate tests).
13. **AI interaction:** Multichannel agents (chat, SMS, WhatsApp, email, voice, ChatGPT); bootstrap by uploading SOPs/transcripts/whiteboard photos or plain-English goals; guardrails built in; observability of every tool call.
14. **Mobile:** Standard responsive; locale selector in footer (US English default). **N/D** pixel level.
15. **Footer:** Product / Industries / Customers / Company + Trust Center, Modern Slavery Statement, cookie prefs, language selector.
16. **Trust:** Strongest badge set seen: **SOC 2, ISO 27001, ISO 42001, HIPAA, GDPR, EU AI Act, CSA STAR Level One, FedRAMP, PCI DSS** + dedicated Trust Center.

**Takeaway:** The reference model for "agent platform" IA: organize navigation by what customers *do* (Build/Orchestrate/Optimize/Scale), show agent conversations as the hero, and wall-to-wall compliance.

---

### 1.3 Glean — glean.com (Work AI / enterprise search)

1. **Hero:** Eyebrow "Work AI that understands your company"; H1 "Glean connects knowledge, systems, and context so AI can actually work."; CTAs "Get a Demo" + "See how it works"; visual = large background graphic with integration icons (Slack, Google Drive, Jira, Confluence, SharePoint, GitHub, Salesforce).
2. **Navigation:** In-page anchors observed (Problem Statement, Solution, Security, Statistics, Customers, Platform) — single-scroll narrative with anchor jump-list.
3. **Typography:** Not detectable; one dominant H1, concise benefit headings, **numbered value points ("01", "02", "03")**.
4. **Color:** Blue accent assets ("gradient-blue"); light/dark section mix implied by "light" logo variants.
5. **Grid:** Single-scroll landing: hero → event banner → cost message → compliance block → proof metrics → case studies → testimonials → capability cards → resources → final CTA.
6. **Spacing:** Section-per-argument pacing; repeated case-study card pattern (logo + summary + metric bullets + link).
7. **Screenshots:** Almost none — conceptual illustration of connectors/agents/workflows instead.
8. **Motion:** Not detectable from fetch.
9. **Social proof:** 15+ logos (Rivian, Samsung, Vanta, Wealthsimple, Intercom, SeatGeek, Webflow, Zillow, Intuit, Zapier, Booking.com, Canva, Reddit, Databricks, Pinterest); precise stats: "35+ unique LLMs", "30% reduction in token usage", "110 hours saved per user/year", "20% fewer support tickets", "93% enterprise adoption in <2 years", "<6 months to ROI", even a live token-savings counter (12,442,032,540).
10. **CTA pattern:** "Get a Demo" repeated at top and bottom; exploratory secondaries (Explore the platform, Discover Work AI Institute…).
11. **Pricing:** None.
12. **Dashboard style:** Not shown; capability statements ("Connect knowledge. Take action. Understand context. Work everywhere.").
13. **AI interaction:** "Agents, Assistant & Search"; permission-aware retrieval; no-code agent builders; model-agnostic (35+ LLMs).
14. **Mobile:** **N/D.**
15. **Footer:** Community ("Gleaniverse"), partners, docs, resource cards, final CTA, socials.
16. **Trust:** **ISO 42001, HIPAA, TX-RAMP Level 2, SOC 2 Type II, ISO 27001, GDPR**; copy: "Users only see what they're allowed to see", "secure, explainable, and permission-aware".

**Takeaway:** Quantified-ROI storytelling (specific percentages + time saved) and connector-icon hero instantly communicate "plugs into your stack".

---

### 1.4 Hebbia — hebbia.com (Finance AI)

1. **Hero:** Eyebrow "AI FOR FINANCE"; H1 "Institutional Intelligence"; subhead "Purpose-built AI trusted by leading investors, bankers, advisors, and Fortune 500 companies for high-stakes decisions."; CTA "Request a demo"; dark cinematic video hero (Vimeo-backed).
2. **Navigation:** Max / Product / Solutions / Security / Company / Pricing + Sign in + Request a demo. Solutions dropdown: Investing, Banking, Legal, In-House.
3. **Typography:** Display serif **"Edict Display Variable Roman"** + sans tokens; fluid H1 `clamp(2.19rem → 5rem)`; unusual weight tokens (90, 390); all-caps eyebrows.
4. **Color:** Dark theme (`--color-black` bg), grey-400 eyebrows, muted green-gray play-button accent `rgba(156,170,164,.6)`. Quiet, institutional.
5. **Grid:** Full-bleed hero with overlay container; modules stack: diagram → analysis table → workflow → integrations → metrics → testimonial → compliance → CTA. Logo grid 2-col → 4-col responsive.
6. **Spacing:** Large breathing room; hairline dividers (`--color-divider`).
7. **Screenshots:** Composed mock UI (project cards, document tables, agent lists) labeled with finance artifacts: "ACME VDR Deep Dive", "Airlines Earnings Calls Analysis", "Deal Teaser", "Buyer Universe", "ACME Cash Flow Build".
8. **Motion:** Cinematic hero video; otherwise static precision.
9. **Social proof:** Morgan Stanley, MetLife, Centerview, OHA, New Mountain Capital, Latham & Watkins; scale stats: **$30T AUM of firms using Hebbia**, 200K prompts/day, 1.5B pages processed; CTO testimonial (Apogem Capital).
10. **CTA pattern:** "Request a demo" everywhere; "Sign in" utility.
11. **Pricing:** Nav link exists, not on homepage.
12. **Dashboard style:** Mock toolbar (Export/Automate/Schedule/Share), analysis columns ("Red flags"/"Opportunities"), "Agent running" state, data-source tiles (SEC Filings, FactSet, S&P CapIQ, PitchBook, Preqin, Snowflake).
13. **AI interaction:** Multi-step agentic sequences ("Find fintech AI startups → Analyze expert calls → Create matrix → Draft slides → Send email"); "reason over limitless context"; scheduled automation.
14. **Mobile:** Desktop left-aligned → mobile centered; responsive logo grid observed.
15. **Footer:** Product / Solutions / Company / Follow us / Contact; ToS, Fair Use, DPA, Privacy, Cookie Preferences.
16. **Trust:** **ISO/IEC 42001:2023, SOC 2 Type II, CCPA, GDPR**; "Encrypted end-to-end", "No training on user data"; "AES-256 at rest, TLS 1.2+ in transit".

**Takeaway:** For finance-grade positioning: serif display type, dark cinema hero, $-denominated scale stats ($30T AUM), and explicit encryption specs.

---

### 1.5 Decagon — decagon.ai (Customer-experience agents)

1. **Hero:** Title-level: "The AI concierge for every customer"; meta: "Reimagine your customer experience with AI agents, built for the enterprise."; large background image + **video modal via play button**; announcement: "Decagon Dialogues 2026 is here. Register today".
2. **Navigation:** Dropdown nav + announcement banner + mobile toggle (labels not extractable from truncated fetch).
3. **Typography:** **Open Sans + Inter**, weights 300–800. Clean, neutral, legibility-first.
4. **Color:** Light UI with vivid gradient accents — indigo `#5754FF`, blue `#4D67FF`, cyan `#4EEBF3`/`#30D0EC`, orange `#FF6F22`, violet `#D499FE`/`#D770FF`. Gradients applied to headings, buttons, CTAs.
5. **Grid:** Centered container system; breakpoints at 479/767/991/1200/1280/1450px; modular: announcement → hero → product sections → accordion media blocks → testimonial slider → quote carousel → timeline → logo marquee → mixed CMS grid → footer. Every third card widens in the mixed grid.
6. **Spacing:** Modular container widths; large section padding.
7. **Screenshots:** CMS-driven looping videos, accordion-driven image swapping; scenario visuals over annotated screenshots.
8. **Motion:** Gradient hover shifts, arrow-icon micro-movement, testimonial sliders, logo marquee, video modals — the most motion-forward site in the enterprise CX cohort.
9. **Social proof:** 24 logos incl. Chime, Rippling, Notion, Eventbrite, Oura, Bilt, Affirm, Duolingo, Hertz, Mercado Libre, Figma, Betterment, Windsurf.
10. **CTA pattern:** Button system with **primary/secondary/tertiary/quaternary/alternate/simple/disabled** states; "Register today" for event; HubSpot inline forms.
11. **Pricing:** None visible.
12. **Dashboard style:** Product named per channel: Decagon Voice / Chat / Email; ops modules: Agent Operating Procedures (AOPs), Experiments, Testing & QA, Insights & Reporting, Watchtower, Agent Assist.
13. **AI interaction:** Human-like voice AI, on-brand chat replies, contextual email resolutions; build workflows from natural-language instructions; simulated testing + continuous QA + human handoff.
14. **Mobile:** Explicit 6-breakpoint system — strong responsive engineering evidence.
15. **Footer:** Logo badge, multi-column menu, hover underline animation, dynamic copyright, contact emails (sales@/support@).
16. **Trust:** Product-level safety copy ("Safe, on-brand replies"); certifications not on homepage (likely on /security).

**Takeaway:** Gradient-accented, motion-rich approach works for a younger enterprise audience; formal multi-tier button state system is a good engineering pattern.

---

### 1.6 EvenUp — evenuplaw.com (Personal-injury legal AI)

1. **Hero:** "Leading AI for Personal Injury Lawyers"; meta subhead "EvenUp is the proactive AI platform for personal injury law firms…"; hero slider with decorative SVG background + testimonial carousel (no static product screenshot).
2. **Navigation:** Products / Customers / Resources. Products split into **Pre-Litigation** (Intake, Treatment, Demands, Negotiation) and **Litigation** (Discovery, Trial) + Platform items (PLAAS™, Proactive Workflows, AI Drafting, AI Assistant, Communication Agents, Executive Analytics, Integrations). Featured panel: "Piai™ — the largest dataset in personal injury".
3. **Typography:** **PT Serif headings + Inter body**; H1 responsive 32→42→48px, hero up to 72px; body 16→18px; buttons weight 500–600.
4. **Color:** Dark theme (black bg, light text); brand blue ≈ `rgb(67,107,245)`; green for positive indicators, red for alerts; filled + outline button variants.
5. **Grid:** Bootstrap-style grid/flex utilities; container sections, full-width dark bands, carousels, logo scroll, CTA ticker, off-canvas mobile nav.
6. **Spacing:** Modular, large vertical section padding.
7. **Screenshots:** None on hero; brand imagery, customer photos, SVG illustration, video/testimonial modules.
8. **Motion:** Hero slider, logo scroll, rotating CTA ticker, quote carousels.
9. **Social proof:** PI-firm logos (John K Zaid, William Mattar, Shunnarah, McCready…); **outcome metrics as proof**: "50% reduction in average case lifecycle", "3X higher settlement value", "$1.25M settlement", "10x ROI". Quote: "Case Companion is like having a brain within each file."
10. **CTA pattern:** Pill-shaped high-contrast buttons; "Explore More Products", "Learn More".
11. **Pricing:** None.
12. **Dashboard style:** Not shown; module-based positioning (intake → trial pipeline).
13. **AI interaction:** "Proactive AI" — AI Assistant, AI Drafting, Communication Agents, Proactive Workflows; proprietary dataset branding (Piai™).
14. **Mobile:** Off-canvas mobile navigation; explicit responsive type steps.
15. **Footer:** Footer logo component present; links not extractable (truncation).
16. **Trust:** TrustLogo script reference; no visible badges on homepage.

**Takeaway:** Vertical-niche pattern: name the proprietary data asset (Piai™), structure nav around the customer's case lifecycle, and use settlement-dollar outcomes as proof.

---

### 1.7 Abridge — abridge.com (Clinical documentation)

1. **Hero:** "Enterprise-Grade AI / For every moment of care"; subhead "One intelligence layer connecting health systems, payers, and life sciences organizations. Built by clinicians, for clinicians—trusted by 300+ health systems."; CTAs "Contact Us" + "Customer Stories"; large hero image with dedicated mobile variant (abridge-hero-mobile.avif).
2. **Navigation:** Platform / Resources / About + Log In + Contact Us. Platform grouped PRODUCT / CAPABILITIES / AI Solutions (Clinicians, Revenue Cycle, Nursing, CDS, Care Signals, Contextual Reasoning Engine, Science, Publications…).
3. **Typography:** Clean sans marketing style; oversized hero headline; **uppercase micro-labels** ("PRE-VISIT", "ENCOUNTER", "POST-VISIT"); large stat treatments (`.stat-block-number`).
4. **Color:** Light theme, **warm neutral background `rgb(247,242,237)`** (bone/cream), accent **orange-red `#EA2C00`**; black wordmark; grayscale-with-hover imagery.
5. **Grid:** Webflow-style sections: hero → logo/stats band → impact numbers → 3-step care workflow → whitepaper tabs → awards → news cards → partnership CTA → footer. Breakpoints ~479/767/768/991/992px.
6. **Spacing:** Generous warm-white section bands.
7. **Screenshots:** **Stylized clinical UI panels** with rich alt text: patient summary cards, discussion-topic checklists with audio playback bar, generated clinical notes.
8. **Motion:** Not detectable from fetch; tab and lightbox components.
9. **Social proof:** Elite health systems (Johns Hopkins, Kaiser Permanente, Duke, Mayo Clinic, Emory, Sutter, Yale New Haven, UPMC); deep stats: 100M+ conversations, 95% user retention, 30x adoption growth, 78% lower cognitive load, 83% less note-writing effort, 14% more wRVUs; awards (Best in KLAS 2025/2026, TIME Best Inventions, Forbes).
10. **CTA pattern:** "Contact Us" primary; "Customer Stories", "Learn More", "Watch Video" secondaries. No free trial.
11. **Pricing:** None.
12. **Dashboard style:** Pre-visit/encounter/post-visit documentation panels; login → notes.abridge.com.
13. **AI interaction:** Ambient conversation → documentation ("Transform clinical conversations into documentation, insights, and actions"); timeline framing: prepared before / present during / handled after; real-time capture.
14. **Mobile:** Dedicated mobile hero asset + full breakpoint set.
15. **Footer:** Product / AI / About / Resources columns; legal + social; copyright.
16. **Trust:** Trust via logos, awards, and scale ("trusted by 300+ health systems") rather than badge wall on homepage; science/whitepapers section doubles as credibility.

**Takeaway:** Healthcare-premium recipe: warm bone background + single vivid accent, clinician-endorsement copy, and published science as a nav category.

---

### 1.8 Ambience Healthcare — ambiencehealthcare.com (Clinical documentation + coding)

1. **Hero:** "The AI Platform Clinicians Choose for Documentation and Coding"; subhead "Ambience helps your health system reduce burden, strengthen revenue integrity and ensure compliance"; CTA "Book a Demo"; immediate proof stats under hero: **80% average utilization, 45% less charting time, #1 in competitive bake-offs**.
2. **Navigation:** Products / Use Cases / Care Settings / Careers / Blog + Book a Demo.
3. **Typography:** **N/D**; large H1, short stat callouts, dense specialty tag-wall.
4. **Color:** **N/D.**
5. **Grid:** Stacked sections: hero → comparative metrics → clinician value → specialty coverage → EHR placement → revenue/compliance proof → final CTA → footer.
6. **Spacing:** Standard section rhythm.
7. **Screenshots:** None evident in fetch.
8. **Motion:** **N/D.**
9. **Social proof:** Named executive quotes (CMIO at John Muir Health; research director); metrics "45% less after-hours documentation", "$13K", "27%"; **vendor comparison charts** ("Vendor 1" vs "Vendor 2").
10. **CTA pattern:** "Book a Demo" repeated (hero, closing banner "Get started with Ambience today"); secondary "Explore Our Offering".
11. **Pricing:** None.
12. **Dashboard style:** Not shown; EHR-embedded story ("lives directly inside Epic Toolbox", Hyperdrive, Haiku, native FHIR APIs).
13. **AI interaction:** Live encounter capture → structured specialty-tailored notes → coding (HCC, E/M, ICD-10, CPT); claim-quality and compliance framing.
14. **Mobile:** **N/D.**
15. **Footer:** Company / Resources / Policies / About; products, audiences (Clinicians/Business/Patients/Informatics), care settings, KLAS reports.
16. **Trust:** "Trusted and fully certified" band; "Verified by" AAPC/KLAS; published accuracy tables (E/M coding accuracy, ICD-10 substantiation).

**Takeaway:** Competitive-comparison charts and third-party verification (KLAS, AAPC) plus accuracy tables = aggressive evidence posture for crowded vertical.

---

### 1.9 Nabla — nabla.com (Clinical AI layer)

1. **Hero:** "Smarter clinical workflows. Elevated care."; subhead "The Clinical AI Layer embedded, trusted, and scaled across care delivery—making every patient interaction feel more human."; CTAs **"Learn more" + "Try it for free"** (self-serve + sales hybrid); scrolling logo strip in hero.
2. **Navigation:** Solutions / Case Studies / Customers / Integration / AI / API / About Us + Sign in + "Talk to our team". Dropdowns: Solutions (Ambient AI, Dictation, Coding), Integration (Nabla Connect, All EHRs, Epic, athenahealth), AI (Publications, Whitepapers).
3. **Typography:** **Euclid Circular B** (sans) — premium geometric sans.
4. **Color:** Light clinical theme: white surfaces, dark text, `#E5E5E5` placeholders, **bright yellow hover accent `#FFFB11`** — distinctive micro-accent.
5. **Grid:** Centered modular sections: logo carousels → outcome-stat blocks → 3-part workflow cards → testimonial cards → security band → press cards → CTA panels.
6. **Spacing:** Webflow-style container alignment; utility-driven responsive hiding.
7. **Screenshots:** Phone mockups + framed UI images (not a labeled dashboard tour).
8. **Motion:** Carousels (logos, testimonials).
9. **Social proof:** CVS Health, Accolade, Aultman, CHLA, LCMC, Fairview…; stats: 27% burnout reduction, 55% save ≥1 hr/day, 1.5x more patients; scale: **130+ health orgs, 85,000+ clinicians, 20M+ encounters/year**; press: NEJM, Forbes, MIT Tech Review.
10. **CTA pattern:** Mixed self-serve/sales: "Try it for free", "Get a demo", "Contact Us", "Talk to our team", "Read case studies".
11. **Pricing:** None; conversion = trial/demo/contact.
12. **Dashboard style:** Implied note-gen/coding/EHR panels via framed imagery.
13. **AI interaction:** Ambient capture → structured notes; E/M + ICD-10 suggestions grounded in documentation and AMA guidelines; **human-oversight copy: "every final decision in the clinician's hands"**; distribution via EHR embed + API.
14. **Mobile:** Phone mockups used deliberately; responsive utilities present.
15. **Footer:** Solutions / Resources / Company / Legal; trust center, security, status, help, FAQ; offices (Brooklyn + Paris), language selector, newsletter.
16. **Trust:** **HIPAA, SOC 2 Type II, ISO 27001, GDPR** labels; configurable data retention; AI-governance partnership (CHAI); dedicated trust center.

**Takeaway:** The hybrid funnel (free trial *and* demo) plus one loud micro-accent (yellow hover) on otherwise clinical white = approachable-but-certified.

---

### 1.10 Legora — legora.com (Legal AI, "aOS")

1. **Hero:** "Legal work, without limits."; subhead "Collaborative AI for exceptional lawyers"; CTA "Book a demo"; embedded product/demo panel ("Loading…" suggests live embed), "Legora aOS™" anchors.
2. **Navigation:** Product / Solutions / Security / Customers / Company + Log in + Book a demo; promo bar for ROI report.
3. **Typography:** **N/D**; short H1, large stat values.
4. **Color:** **N/D.**
5. **Grid:** Stacked: promo banner → hero → platform tabs → innovation cards → use-case blocks → metrics → founder message → compliance badges → demo CTA → footer.
6. **Spacing:** Standard section bands.
7. **Screenshots:** Embedded media rather than static imagery.
8. **Motion:** Embedded (likely interactive) demo panel.
9. **Social proof:** "Trusted by" area + metrics ("30%", "0.0hrs", "$2.0m" — animated counter placeholders); no named logos in fetch.
10. **CTA pattern:** "Book a demo" repeated; secondaries "Read more", "Explore the Legora aOS™".
11. **Pricing:** None.
12. **Dashboard style:** Product surfaces named: Agent, Monitors, Lists, Editor, Portal, Tabular Review, Workflows, Legal Research, Word/Outlook add-ins, Mobile app.
13. **AI interaction:** Agent "plans, executes, reviews and delivers"; monitors continuously scan global regulation; tasks generated directly from documents.
14. **Mobile:** Mobile app positioned; site responsive. **N/D** detail.
15. **Footer:** Product / Solutions / Certified / Company + legal (Terms, Privacy, Cookie, Security policies) + socials.
16. **Trust:** **SOC 2 Type II, ISO 27001, ISO 42001, GDPR, HIPAA** + "Zero AI training on your data" + Trust Center; "Certified" footer column is unusual and effective.

**Takeaway:** A footer column literally titled "Certified" turns compliance into brand.

---

### 1.11 Norm AI — norm.ai (Agentic law / regulatory compliance)

1. **Hero:** "Setting the Norms of Agentic Law"; full-bleed bottom-anchored image; funding announcement banner: "Raised $120M Series C at $1.2B valuation, led by Khosla Ventures" (Learn more); CTA "Contact Us" in nav.
2. **Navigation:** Home / Technology / About / Legal AGI Lab / Careers / Resources + Contact Us. Flat, no dropdowns.
3. **Typography:** **Aktiv Grotesk + Suisse Works**; huge display type clamp(2.5rem→4rem), tight leading, negative tracking; footer headers ~24px, links ~14px. Editorial high-contrast sans.
4. **Color:** Dark (black/near-black), white + muted white text; **hairline "rule" borders creating a visible grid aesthetic**.
5. **Grid:** 1440px max width, 12-column desktop grid; generous vertical padding; strong vertical/horizontal hairlines → modular column-aware composition. Sections: hero → logo proof → concept statement → product trio → timeline → demo request → footer.
6. **Spacing:** Hairline-divided, magazine-like; large section breaks.
7. **Screenshots:** None — branded cards, abstract imagery, one video block.
8. **Motion:** Minimal; structural hairlines do the work.
9. **Social proof:** "Trusted by institutions managing over **$35T in combined assets**" + 6 institutional logos; funding/partner timeline (no testimonials).
10. **CTA pattern:** "Contact Us" → demo form ("Request a demo today", Submit); newsletter Subscribe.
11. **Pricing:** None.
12. **Dashboard style:** None; three conceptual pillars: Norm Law, Norm Technology, Supervisory AI.
13. **AI interaction:** "Agentic law is the embedding of law into AI agents"; Supervisory AI = "the verification layer for every AI agent"; Legal AGI Lab for R&D.
14. **Mobile:** 12-col → 2-col collapse. **N/D** detail.
15. **Footer:** Logo + 2 link groups + newsletter form (full name + business email); Trust Center, ToS, Privacy; "© 2026 Nomos Ai, Inc."
16. **Trust:** Trust Center link; governance expressed conceptually (supervisory verification, regulated-environment framing) rather than badge wall.

**Takeaway:** The hairline-grid dark editorial look reads as "institutional infrastructure"; funding milestones as banner content builds momentum.

---

### 1.12 Rogo — rogo.com (Finance AI) — ⚠️ Partial

- **Positioning:** "Rogo | AI for the most ambitious firms in finance."
- **Typography:** Distinctive type stack: **Fragment Mono, ABC Arizona Mix, BR Sonoma, Rooftop Mono, Inter, Martina Plantijn** — editorial serif + multiple monos (finance-terminal feel).
- **Color tokens:** `#fff`, `#151515`, `#f5f2eb` (cream), `#135b45` (deep green), `#0071c1` (blue), `#19a26c` (green), `#d94636` (red) — cream/green "banking" palette with P&L red/green semantics.
- **Layout:** Component-based; desktop containers ~1100–1280px; breakpoints ~1600/1200/810px.
- Homepage content beyond this was not retrievable (rogo.ai returned a CloudFront geo-block).

---

### 1.13 Writer — writer.com (Enterprise AI platform)

1. **Hero:** Title: "WRITER — The enterprise AI platform for agentic work"; meta: "trusted by Fortune 500 companies" for "on-brand, compliant work". Hero visual = composite: centered portrait flanked by **two agent-workflow panels with literal prompts** ("Create derivative assets based on this guide for our Q2 campaign targeting CMOs", "Optimize our website for AEO/GEO…").
2. **Navigation:** Mega-menu structure present but items truncated in fetch; site search capability.
3. **Typography:** **Poppins + Graphik + Canela Deck** (sans + serif display mix); observed scale: ~46px display, ~40px section, ~32px uppercase subheading; presets 13/20/36/42px.
4. **Color:** Light theme; **primary `#5551FF` (indigo) hover `#2E2AE8`**; soft blues (`#BFCBFF`, `#E4E9FF`, `#F3F5FF`); playful pastels (`#83E6AD`, `#FFEBFC`, `#BAEFE2`, `#F9DCD4`, `#FF643C`, `#84CBFF`) for accent surfaces.
5. **Grid:** Block-based flexible columns; hero split with left/right workflow panels around center image; constrained centered widths; cards/sliders/forms.
6. **Spacing:** Centered modules with constrained content widths.
7. **Screenshots:** Stylized **playbook** mocks: "DERIVATIVE CONTENT PLAYBOOK", "AEO/GEO OPTIMIZATION PLAYBOOK" with task cards, status indicators, compliance-rule steps, Semrush data pulls.
8. **Motion:** Sliders and form sections implied.
9. **Social proof:** "Trusted by Fortune 500 companies" (logo slider present but logos not captured).
10. **CTA pattern:** Pill buttons, high contrast, indigo primary with darker hover; CTA copy not captured.
11. **Pricing:** None visible.
12. **Dashboard style:** Agent task sequences with skills/personas/style-guides/compliance rules/web search/report generation.
13. **AI interaction:** Natural-language request → multi-step agent workflow; agents "grounded in their company's data"; enterprise-grade LLMs; supervision ("build, activate, and supervise AI agents").
14. **Mobile:** **N/D.**
15. **Footer:** Nested menus; org metadata with email + phone.
16. **Trust:** "Compliant work" positioning; compliance rules visible inside product mock.

**Takeaway:** Showing the *prompt* and the *playbook steps* side-by-side in the hero is an excellent way to demo agentic work without a live product.

---

### 1.14 Cognition (Devin) — cognition.com (Autonomous software engineer)

1. **Hero:** Text-first statement: "Cognition operates Devin, the first autonomous software engineer." Framing: technology that "expands human capacity"; "Devin plans, writes, tests, and ships production code"; proof line: "deployed at some of the largest and most complex institutions in the world." No hero image, no hero button.
2. **Navigation:** Minimal: Home / Careers / Research / Blog / Contact + external "Devin" product link. "Menu/Close" toggle.
3. **Typography:** **Geist Mono Variable + NB International Pro + STK Bureau Serif** (Book/Medium). Headings 24→36px, leading 1.2, tracking -0.02em; body 15px/1.5; **micro mono labels 10–12px**.
4. **Color:** Semantic tokens (text-primary/secondary, bg-background, border-border, hover:bg-accent); muted logo gray `#626870`; faint dark surface `#202020`. Neutral, minimal, accent only on hover.
5. **Grid:** 12-column grid; content often starts at col 4 (inset composition); **numbered sections "01–04"**; logo grid 6→10 cols, aspect-[2/1] cells.
6. **Spacing:** Editorial restraint; numbered sequence gives museum-label pacing.
7. **Screenshots:** None — blog covers + logo marks only.
8. **Motion:** None detected; stillness as a brand statement.
9. **Social proof:** Institutional logos: Citi, Mercedes-Benz, Goldman Sachs, Lowe's, US Army, AT&T, Fox, Elevance, Rivian; customer stories (Infosys, Anduril, Itaú, Cognizant, Nubank, Athena Health). No numeric stats.
10. **CTA pattern:** Anti-CTA posture — discovery via nav; "Explore roles" recruiting CTA; editorial cards as soft CTAs ("Introducing Devin Desktop", "Devin 2.2").
11. **Pricing:** None.
12. **Dashboard style:** None shown; product described textually.
13. **AI interaction:** Autonomy framed as collaboration: "engineers operate more like architects"; Devin embedded in existing codebases/tools.
14. **Mobile:** Responsive col-span system. **N/D** detail.
15. **Footer:** Legal-heavy: Website ToU, Enterprise ToS, Platform ToS, DPA, SLA, Acceptable Use, Report Vulnerability, Security, Privacy Choices.
16. **Trust:** Security page + vulnerability reporting + DPA + SLA + "AI Productivity Guarantee" editorial; no badge wall.

**Takeaway:** Maximum-prestige minimalism: numbered editorial sections, mono micro-labels, zero screenshots, institutional logos. Works when the product is famous.

---

### 1.15 Mercor — mercor.com (AI talent marketplace)

1. **Hero:** "Shape the frontier of AI"; supporting "Mercor is organizing human intelligence to power the AI economy."; CTAs "Start working" + "Learn more". No hero image.
2. **Navigation:** APEX / Research / Enterprise / Experts / Mission + Log in. APEX sublinks (APEX-Agents, APEX-Accounting, APEX-SWE, Off-the-shelf data); Enterprise sublinks (Enterprise agents, Human data, Data monetization).
3. **Typography:** **N/D**; short display heading, section labels, card titles.
4. **Color:** **N/D.**
5. **Grid:** Sections: hero → stats labels → role cards → story/testimonial cards → footer columns. Role cards: job title + rate + code + hire count + Apply.
6. **Spacing:** Card-grid rhythm.
7. **Screenshots:** None; people/story imagery.
8. **Motion:** **N/D.**
9. **Social proof:** Live marketplace numbers: "154 hired recently", avg contracted rate $/hr, daily payouts $, **336,311 unique roles**; human story cards ("Meet Ruby: Biotech research scientist", "Meet Mateusz: Making AI sound human", "Meet Chandu: Quant trader").
10. **CTA pattern:** Hero "Start working"/"Learn more"; per-card "Apply".
11. **Pricing:** Role rates displayed ($120/hr, $80–120/hr…) — marketplace pricing, not SaaS tiers.
12. **Dashboard style:** None shown.
13. **AI interaction:** "We use AI to understand human ability and match talent"; RLHF data / agent training positioning; APEX benchmarks.
14. **Mobile:** **N/D.**
15. **Footer:** Experts / Research / Enterprise / Contact / Mercor columns; Security link to trust domain; "Your Privacy Choices"; "San Francisco, CA".
16. **Trust:** Dedicated Security link; physical address; no badges on homepage.

**Takeaway:** Live counters + human stories is the proof pattern for marketplaces; per-card action buttons ("Apply") replace the single hero CTA.

---

### 1.16 Lindy — lindy.ai (AI executive assistant)

1. **Hero:** "hey, I'm Lindy" / "I take admin work off your plate." CTA "Try for free". Hero visual = **interactive iPhone mockup styled as iMessage thread** with floating task snippets ("Clear my inbox", "✓ Done").
2. **Navigation:** Pricing / Enterprise / Security / Integrations / Resources / Solutions + Log in / Sign up / Talk to sales / Try for free. Resources: Docs, Case Studies, Blog.
3. **Typography:** **Manrope** (+ -apple-system in phone mock); fluid type and spacing tokens; native iOS type inside mockup.
4. **Color:** Light theme with dark accent sections; iMessage blue `#0A84FF`; bubble gray `#E9E9EB`; dark text `#1C1C1E`; **gold gradient accent `#FFE072`→`#F2A000`**; warm neutrals `#F7F4EC`, `#E7E0CB`, `#1E293B`.
5. **Grid:** **12-column CSS grid** (`--column-count: 12`); full-width sections, centered blocks; hero + animated mockup → logo marquee → stacked feature panels → scrolling process visuals → testimonial cards; desktop/tablet/mobile breakpoints.
6. **Spacing:** Fluid spacing token system.
7. **Screenshots:** Desktop-style visuals for inbox/calendar/meeting flows; primary story told via mobile chat mock; "Watch: See Lindy in action" video module.
8. **Motion:** Animated phone mockup, marquee, scrolling process visuals, typing dots.
9. **Social proof:** "People use me at some pretty cool places": Shopify, Apple, Adobe, McKinsey, NVIDIA, Harvard, Airbnb, Retool, Stanford, Autodesk…; rating 4.9 (171 reviews); playful pull-quotes ("killed the virtual assistant industry", "productivity increased 400%").
10. **CTA pattern:** "Try for free" repeated; "Talk to sales"; interactive "Try this with your own day"; reassurance "Start with 7 days free. Cancel anytime."
11. **Pricing:** Public and playful: comparison vs human assistant "$8,000/mo"; Plus $49.99/mo; Pro $59.99/mo; Save 17% annual; Enterprise custom.
12. **Dashboard style:** Conversation-first UI: status bar, avatar, bubbles, typing dots, suggestion chips, input dock. Sample prompts: "What's on my calendar today?", "Draft replies to my unread emails", "Block 2 hrs of focus time".
13. **AI interaction:** Proactive assistant across inbox/calendar/meetings; chat-based with tappable chips; claims "saves 2 hours a day / 10 hours a week".
14. **Mobile:** Phone-native metaphor; explicit responsive tiers.
15. **Footer:** Not captured in truncated fetch (nav + pricing + testimonials dominated).
16. **Trust:** "Security by design" section; "enterprise-grade security", "privacy-first", "approvals built in", "data never sold or used for training"; logos labeled GDPR/HIPAA/AICPA/PIPEDA; SSO/SCIM/audit logs; HIPAA BAA.

**Takeaway:** Personality-led PLG pattern: first-person copy ("hey, I'm Lindy"), OS-native mockup, public pricing, and a security section that still speaks casually.

---

### 1.17 Cursor — cursor.com (Coding agent)

1. **Hero:** "Cursor is your coding agent for building ambitious software." CTAs: "Download for macOS", "Get started", "Request a demo". Hero visual = **interactive demo showing multiple Cursor interfaces** (Cursor Desktop, Cursor CLI).
2. **Navigation:** Models / Product / Enterprise / Pricing / Resources + Sign in / Contact sales / Download. Product: Agents, Cloud, Mobile, Automations, CLI, Marketplace, Review. Resources: Changelog, Blog, Docs, Community, Help, Workshops, Forum, Careers.
3. **Typography:** Custom icon font (CursorIcons16); hierarchy H1→H2→H3 ("The new way to build software." / "Agents turn ideas into code").
4. **Color:** Light/dark theming; light bg `#F7F7F4` with muted text `rgba(38,37,30,.55)`; dark bg `#14120B` with `#EDECEC`. Neutral charcoal/off-white, low accent usage.
5. **Grid:** Stacked full-width sections: hero → trust strip → feature demos → testimonials → model/agent/enterprise → changelog → research/blog → final CTA → multi-column footer.
6. **Spacing:** Feature copy consistently paired with simulated product panels.
7. **Screenshots:** **Best-in-class simulated product UI** — desktop agent list ("In Progress 2", "Ready for Review 3"), CLI prompt, cloud-agent summary, Slack thread ("@cursor can you take a stab?"), automation builder ("Fix CI failures on main", "Add trigger", "Add Tool or MCP"), repo dashboard.
8. **Motion:** Interactive demo in hero; feature panels simulate live states.
9. **Social proof:** "Trusted every day by teams that build world-class software"; testimonials from **Jensen Huang, Andrej Karpathy, Patrick Collison, Greg Brockman, shadcn, Diana Hu**; stat: "Trusted by over half of the Fortune 500".
10. **CTA pattern:** Install + start + demo triple in hero; "Learn about X →" directional links per feature; closing "Try Cursor now." repeats Download/Get started.
11. **Pricing:** Nav link only; no tiers on homepage.
12. **Dashboard style:** Rich fake-but-realistic surfaces (task boards, cloud summaries, automations) with real example content.
13. **AI interaction:** Chat-to-plan/build ("/ commands · @ files · ! shell"), parallel autonomous agents, scheduled automations, model chooser.
14. **Mobile:** Download-first + standard responsive. **N/D** detail.
15. **Footer:** Product / Resources / Company / Legal / Connect; includes Value Calculator, Status, Brand; "© 2026 Anysphere, Inc."
16. **Trust:** "SOC 2 Certified" badge; Security footer link; "Secure codebase indexing" research highlight; enterprise safety language.

**Takeaway:** Celebrity-developer testimonials + interactive in-hero product demo + off-white/charcoal neutrals = the current gold standard for developer-tool marketing.

---

### 1.18 Vercel — vercel.com (Agentic infrastructure)

1. **Hero:** "Agentic Infrastructure" with layered rotating lines: "For coding agents to ship apps and agents automated by agents", "Sandboxed VMs, durable backends, hundreds of models", "Agents who autonomously investigate errors, plan fixes, and open PRs." CTAs "Deploy now" + "Talk to sales"; dark glowing background + "Drop to deploy" element.
2. **Navigation:** Products / Resources / Enterprise / Pricing / Get a Demo / Log In / Sign Up / **Ask AI** / Dashboard. Products grouped: Agent Stack (AI SDK, AI Gateway, Sandbox, Passport, Connect, eve), Core Platform (Security, Content Delivery, Fluid Compute, Observability), Tools (Workflows, CI/CD, Next.js, Vercel Agent).
3. **Typography:** **Geist Variable + GeistPixel** family (Circle/Grid/Line/Square/Triangle) — geometric sans + pixel display variants.
4. **Color:** System/light/dark theming; dark-glow hero imagery — dark-first style; neutral surfaces, alpha-based borders/shadows.
5. **Grid:** Sticky header; centered constrained container; modular sections: hero → customer scenario panels (Notion, Zapier, Mintlify) → recent product cards → CTA block → large footer. Mobile/desktop + dark/light asset variants.
6. **Spacing:** Consistent container margins; card-per-product rhythm.
7. **Screenshots:** Branded scenario panels + **terminal-style deploy card**: "▲ vercel deploy" with log lines ("✓ Building image from Dockerfile.vercel"…). Product cards for Passport, eve, containers.
8. **Motion:** Rotating hero lines; glowing background; drop-to-deploy interaction.
9. **Social proof:** Scenario stats: "Notion powers millions of agent conversations daily", "Zapier serves 100M+ monthly visits", "Mintlify powers docs for 20,000+ companies".
10. **CTA pattern:** Self-serve "Deploy now" primary; "Talk to sales" secondary; header Get a Demo/Sign Up.
11. **Pricing:** Nav link only.
12. **Dashboard style:** Developer surfaces: API/CLI/MCP/Skills, sandboxed environments, observability; CLI log snippets as UI.
13. **AI interaction:** Agents deploy "in their native language" via API/CLI/MCP/Skills; autonomous error investigation → fix → PR; "Ask AI" in nav.
14. **Mobile:** Dedicated mobile asset variants observed.
15. **Footer:** 12 columns: Agent Stack / Core Platform / Security / Tools / Frameworks / SDKs / Build / Learn / Explore / Company / Legal & Trust / Social.
16. **Trust:** Security, Platform Security, WAF, Bot Management/ID, Trust Center; DPA, Acceptable Use, Status.

**Takeaway:** The terminal/log aesthetic as hero content, "Ask AI" as a nav item, and agent-stack IA = the emerging playbook for agent-era infrastructure.

---

### 1.19 Ramp — ramp.com (AI finance ops) — ⚠️ Partial (text-only "Machine Version" served)

- **Positioning:** "All-in-one spend management platform" / "Machine Version" — Ramp serves an explicit machine-readable homepage variant (interesting SEO/AEO tactic).
- **Social proof:** "Trusted by 70,000+ businesses including Notion, Shopify, Webflow, Eventbrite, Poshmark, Quora"; **time/money stats**: "27M+ hours saved collectively", "close books 75% faster", "intake-to-pay 3x more efficiently"; customer quotes incl. "People ask how we're using AI in finance… We use Ramp."
- **Pricing:** Public — Free $0/mo/user; Plus $15/mo/user + platform fee; Enterprise custom; 20% annual discount; signup bonus ($3,100 AI Research Incentive).
- **AI patterns:** Autonomous-but-supervised: Policy Agent reviews 100% of expenses; OCR 99% accuracy; decisions "transparent and auditable"; **"never takes money-moving actions without human confirmation"**.
- **Trust:** Trust Center, FDIC-insured accounts, fraud prevention, auditability.
- Visual dimensions **N/D** (no images served).

**Takeaway:** Publishing a machine-readable page variant is itself an AI-search-era design pattern; the human-confirmation sentence is the canonical trust line for money-moving agents.

---

### 1.20 Clay — clay.com (GTM data + agents)

1. **Hero:** "Build systems to grow revenue"; subhead "Infrastructure to get any data, run agentic workflows, and launch GTM plays."; CTAs "Start free trial" + "Get a demo"; **developer install module** ("Paste in your coding agent" + Copy); hero visual = playful illustrated contraption (tubes, balls, magnets, funnels on green hills under blue sky).
2. **Navigation:** Product / Use Cases / Solutions / Resources / Company / Pricing. Product grouped: Data infrastructure (Audiences, Data marketplace, Signals & Intent, Waterfall), Agents (Claygents, Agent plugin CLI/API, MCP for rep), Orchestration (Functions, AI formatting), Execution (Ads, Sequencer).
3. **Typography:** Not detectable; bold short headline, small caps section labels ("GTM INFRASTRUCTURE", "GTM engineers build on Clay").
4. **Color:** Saturated, playful, light (illustration-led: green hills, blue sky) — deliberately anti-corporate.
5. **Grid:** Header → hero (message + CTAs + install module + illustration) → logo band → interactive builder → capability sections → testimonials/case studies → resource cards → mega footer. Tabbed use-case modules; alternating text+screenshot blocks.
6. **Spacing:** Dense, content-rich; many sections.
7. **Screenshots:** Workflow-specific screenshots: lead/account tables, filter panels, scoring formulas, routing fields, ad-audience exports, CRM records, agent prompts, Slack-style AI briefs.
8. **Motion:** Interactive builder in-page; tabbed modules.
9. **Social proof:** "Trusted by more than 500,000+ leading GTM teams"; logo wall incl. Stripe, OpenAI, Snapchat, Figma, Cursor, Intercom, UPS, HubSpot, Anthropic, Google, Rippling, Okta, Uber, eBay, Ramp, Klaviyo; outcome stats (+140%, 80%+, 2x, 3x, +50%); quotes ("Clay has become the orchestration layer for everything GTM").
10. **CTA pattern:** "Start free trial" primary, "Get a demo" secondary, "Sign up" in nav; contextual CTAs per section.
11. **Pricing:** Nav link + "14-day Pro trial, no credit card required" in structured data.
12. **Dashboard style:** Labeled module mocks: TAM Sourcing, Automated Inbound, Lead Scoring, Automated Outbound, CRM Enrichment, Launch Ads, Rep Productivity — with realistic table/formula content.
13. **AI interaction:** Claygents as researchers; "Chat to get full account context in natural language"; prompt-style inputs ("Find people data"); MCP for reps; agent-driven call prep/follow-ups/qualification.
14. **Mobile:** **N/D** detail.
15. **Footer:** Giant sitemap: use-case groups, departments, learning/community/partners/company/contact/socials + conference/university/livestream promo cards.
16. **Trust:** No badge wall on homepage (SOC 2 appears only as an example data signal).

**Takeaway:** Playful illustration + hyper-dense information architecture works for community-led GTM tools; the "paste into your coding agent" CTA is a genuinely new pattern.

---

### 1.21 Attio — attio.com (Agentic CRM)

1. **Hero:** "Welcome to agentic revenue."; subhead "Attio is the CRM that builds pipeline, advances deals, and grows accounts around the clock."; CTAs "Talk to sales" / "Start for free" / "Send me a demo"; hero visual = **product demo vignette** (meeting transcript, agent chat output, pipeline modules). Announcement bar: "Orchestrate revenue agents with the new Workflows".
2. **Navigation:** Platform / Resources / Customers / Pricing + Sign in + Start for free. Platform grouped: CRM Platform (Ask Attio, AI, Data model, Universal Context), Agents & automations (Workflows, Sequences), Insights (Call Intelligence, Reporting), Ecosystem (Developer Platform, Apps).
3. **Typography:** **Inter + Inter Display + Tiempos Text (serif accent) + JetBrains Mono**; regular→bold weights; responsive heading classes.
4. **Color:** Light default with dark mode logic; neutral surface-driven tokens (text-primary-foreground, bg-secondary-background, border-subtle-stroke, surface-subtle).
5. **Grid:** Centered container, hairline borders, 12-column grid (visible in 404: `grid-cols-12`, `col-[2/-2]`); homepage = sequence of **product vignettes** rather than static marketing blocks.
6. **Spacing:** Hairline-separated modular sections.
7. **Screenshots:** Active operational vignettes: transcript panel, agent response, record tables, workflow builder, pipeline board, reporting charts, account-risk lists, email composer.
8. **Motion:** Product-vignette animation implied; demo player.
9. **Social proof:** Taskrabbit, Granola, Modal, Railway; "Trusted by 30,000+ customers"; "83% faster lead triage"; platform stats: **2.6M MCP calls/month, 400M API calls/week, 76k active customer agents, 15M emails synced/day**; quote: "When I first opened Attio, I instantly got the feeling this was the next generation of CRM."
10. **CTA pattern:** "Start for free" + "Talk to sales" dual-track; "Send me a demo"; closing "Agentic revenue runs on Attio."
11. **Pricing:** Structured data: Free $0, Plus $35, Pro $79 (annual) with positioning lines ("For individuals / small teams / growing teams").
12. **Dashboard style:** Deep fake-realistic UI: "Ask Attio" query with tool-use readout ("2 tools used", "SQL query executed: 1452 rows in 6.2s"), ICP scores, workflow nodes ("Record created" → "Web agent" → "Enrich lead…"), pipeline stages, account-health chips (Healthy/Watch/At risk), model indicator "auto·Opus 4.8 · 1M context".
13. **AI interaction:** "Ask Attio" natural-language entry; Universal Context™ layer; agents executing tool calls (search-notes-by-metadata, update-record); developer extensibility via MCP/API/SDK.
14. **Mobile:** **N/D** detail (responsive classes present).
15. **Footer:** Platform / Company / Import from / Attio for / Apps / Resources; Services Agreement, Privacy, "LLMs" link (notable).
16. **Trust:** Trust Center + System status; cookie/privacy; badges not on homepage.

**Takeaway:** The most complete "AI-native CRM" pattern: platform-stats-as-proof (MCP calls/month), tool-call transparency in UI mocks, and an "LLMs" footer legal link.

---

### 1.22 Granola — granola.ai (AI meeting notepad)

1. **Hero:** "The AI notepad for back-to-back meetings"; subhead "Notes, actions and memory. Without a meeting bot."; CTA "Download for free"; availability microcopy "macOS, Windows, iOS, Android"; minimal notepad-grid visual with floating graphics.
2. **Navigation:** Features / Enterprise / Pricing / Blog / Careers. Features surfaces: Notepad, Chat, Mobile, Apple Watch.
3. **Typography:** Display font hook "font-quadrant" + body "font-melange"; **very large fluid scale: hero clamp(68px, 6vw, 110px), feature headings clamp(72px, 7.5vw, 120px)**; emphasis via scale + occasional semibold.
4. **Color:** Light, warm-paper theme: ink `#1E1E1E`, **lime accent `#D1E043`**, faint grid texture `#DEDEDE`, borders `#D9D9D9`; oat-toned surfaces.
5. **Grid:** `max-w-7xl` container; hero split `lg:grid-cols-[60%_40%]`; logo wall `grid-cols-3 md:grid-cols-6`; alternating big-type blocks / product media / rule-line feature rows.
6. **Spacing:** Rule-line-separated rows; generous type-led whitespace.
7. **Screenshots:** Contextual mockups with descriptive alt copy: share menu with meeting participants, iPhone home screen dock icon, macOS meeting notification with Granola button.
8. **Motion:** Floating assets implied; typography carries the page.
9. **Social proof:** "Trusted by teams we admire": PostHog, Intercom, Figma, Brex, Ramp, Replit, Lovable, Cursor, Bumble, Asana, Vanta, Linear; named voices (Karri Saarinen, Olivia Moore, Guillermo Rauch, Deedy Das, Nat Friedman); quotes ("It's actually unbelievable how good Granola is."); structured rating 4.9.
10. **CTA pattern:** Download-led: "Download for free" primary, "View pricing" secondary.
11. **Pricing:** Free core: "Unlimited meeting notes for free"; upgrade = access to notes older than 30 days. No amounts on homepage.
12. **Dashboard style:** Note UI states: "Enhancing notes", "Transcribing", "Ask anything", "Your Brief", "List actions", "Write follow-up email", "Draft project plan"; chat example "What did I promise to do in my meetings this week?"
13. **AI interaction:** Pre-meeting prep (attendees, past discussions), in-meeting freeform notes, instant post-meeting outputs; differentiator: **no meeting bot** ("doesn't invite a bot"); notes become context for other AI apps.
14. **Mobile:** Multi-platform is core (macOS/Win/iOS/Android/Watch); site responsive.
15. **Footer:** Features / Product / Company / Resources incl. Security, Transparency, Status, License; "Made with ♥ in Shoreditch".
16. **Trust:** Security + Transparency pages; product-level "Private by default"; no badge wall.

**Takeaway:** Oversized editorial type + one fresh accent (lime) + anti-feature positioning ("without a meeting bot") = the standout B2C-pro pattern.

---

### 1.23 ElevenLabs — elevenlabs.io (Voice AI)

1. **Hero:** "Bringing technology to life"; supporting "Powering the best enterprises, creators, and developers."; CTAs "Sign up" + "Contact sales".
2. **Navigation:** Product families: ElevenCreative / ElevenAgents / ElevenAPI + capability links (AI Voice Generator, TTS, Music, STT, Voice Cloning, Dubbing) + voice-library use cases (Narration, Advertisement, Characters, Conversational, Social Media).
3. **Typography:** **N/D**; H1 display → bold H2 sections → short feature H3s → concise body.
4. **Color:** **N/D** from fetch.
5. **Grid:** Stacked modules: hero → product categories → social proof → platform split → feature deep dives → API section → impact stories → research timeline → safety → updates → final CTA. Repeated pattern: heading + link + short copy + feature cards.
6. **Spacing:** Card-per-capability rhythm; chronological research timeline block.
7. **Screenshots:** App interfaces shown: ElevenCreative editor (voiceover, flow creation, voice cloning options); ElevenAgents dashboard (call statistics, alerts); JS API code snippet with model ID and output format.
8. **Motion:** **N/D** from fetch.
9. **Social proof:** "Trusted by leading developers and enterprises": Twilio, Disney Studios, KPN, Telus, Cisco, Epic Games, NVIDIA, Revolut, Meta, Bertelsmann, Deliveroo, Chess.com, Deutsche Telekom, Meesho, Harvey, Salesforce; case studies (NVIDIA, Clay, Duolingo, Deliveroo, Cars24); stats: 5,000+/10,000+ voices, 70+ languages, **75ms latency**, 98% transcription accuracy; resolution-rate dashboards (83.4%, V1 87.37% vs V2 61.71%).
10. **CTA pattern:** "Sign up" primary, "Contact sales"/"Talk to sales" secondary, "Get started", "Explore docs"; closing pair "Talk to sales" + "Create an AI agent".
11. **Pricing:** Not on homepage ("Free AI Voice Generator" in title).
12. **Dashboard style:** Creative editor UI + agent analytics UI (resolution rate, version comparisons, alerts, guardrails, workflows) + developer code snippet.
13. **AI interaction:** Expressive TTS with controls; conversational refund-dialogue agent with omnichannel actions; transcription, music/SFX generation, dubbing, cloning; SDK/API-first developer path.
14. **Mobile:** **N/D.**
15. **Footer:** Ends with "Latest updates" blog roll + "AI Communication Platform" closing CTA block (full footer not captured).
16. **Trust:** **"Safety, built in"** section with pillars: Moderation, Accountability, Provenance; secure APIs/SDKs.

**Takeaway:** Dual-audience architecture (creators vs enterprises vs developers) under one brand; latency/accuracy numbers as hero-adjacent proof; safety pillars instead of only badges.

---

### 1.24 Linear — linear.app — ⚠️ Partial (JS-rendered; design-system layer only)

- **Title:** "Linear – The system for product development."
- **Typography system:** Title scale `title-1`…`title-9`; body scale `text-micro/mini/small/regular/large`; weights light/normal/medium/semibold; monospace token; `tabular-nums`, letter-spacing controls, `text-wrap: balance`; responsive scaling per breakpoint.
- **Color system:** Fully semantic tokens: `text-primary/secondary/tertiary/quaternary`, `bg-primary`, plus `color-red`/`color-green` semantics.
- **Motion:** Signature **animated dot-grid** (5×5 dot matrices with `upDown` and `pong` opacity keyframes) — decorative grid motif in hero/backgrounds.
- **UI density cues:** `tabular-nums` for aligned numbers, ellipsis truncation, 2-line clamps — dense product-like marketing UI.
- Breakpoints: 640/768/1024/1280px; logged-in state detection in header.

**Takeaway:** Even the *marketing CSS* is a full semantic token system — Linear's brand is the design system itself (dot-grid motion + 9-step type scale + quaternary text hierarchy).

---

### 1.25 Anthropic — anthropic.com (substitute; frontier lab)

1. **Hero:** "AI research and products that put safety at the frontier"; longer mission subhead (public benefit corporation framing); global CTAs "Try Claude" / "Log in to Claude" / "Download app"; hero = script-built **SVG network of question hubs** ("How does AI work?", "Who should govern AI?") with article image tiles.
2. **Navigation:** Research / Policy / Commitments / Learn / News / Try Claude + language selector. Commitments → Initiatives (Claude's Constitution, Claude Corps, Responsible Scaling Policy, Transparency) + Trust center.
3. **Typography:** **"Anthropic Serif"** (Georgia fallback) display; CSS scales for display (up to 5rem), paragraph (up to 1.5rem), detail, monospace.
4. **Color:** Dark warm neutral: `slate-dark`/`#141413` bg, muted `#B0AEA5`, **terracotta accent `#D97757`**, cream detail `rgba(250,249,240,.3)`.
5. **Grid:** 12-column grid with main/full/small containers, clamp-based margins, breakout grids; nav morphs at 56em; cards, sliders, tabs, modals, marquee, terminal-style scroll areas.
6. **Spacing:** Editorial containers with responsive clamp margins.
7. **Screenshots:** None — research thumbnails inside animated hero; hover zoom on cards.
8. **Motion:** Animated question-network hero; logo marquee infrastructure.
9. **Social proof:** None on homepage (no logos/stats) — mission-first.
10. **CTA pattern:** "Try Claude" global; content CTAs ("Model details", "Read announcement", "Learn more").
11. **Pricing:** Linked (product + API), no amounts on homepage.
12. **Dashboard style:** None; product family named in footer (Claude Code, Cowork, @Claude, Design, Science, Security).
13. **AI interaction:** Model family narrative (Opus/Sonnet/Haiku + Mythos/Fable); agentic positioning ("Our most agentic Sonnet yet"); auditable artifacts for science.
14. **Mobile:** 56em nav breakpoint; responsive clamp system.
15. **Footer:** 9 groups: Products / Models / Solutions / Claude Platform / Resources / Programs / Help and security / Company / Terms and policies + cookie settings (Necessary/Analytics/Marketing).
16. **Trust:** Trust center, Responsible Scaling Policy, Transparency, usage/privacy policies, K-12 DPA — governance as content, not badges.

**Takeaway:** Governance-as-navigation (Commitments/Constitution/RSP) is the frontier-lab trust pattern; warm dark neutrals + terracotta + serif = "thoughtful institution" aesthetic.

---

### 1.26 Synthesia — synthesia.io (substitute; AI video)

1. **Hero:** "All-in-one AI Video platform for business"; subhead "Create studio-quality videos with AI avatars and voiceovers in 160+ languages. Save up to 90% of time and cost."; CTAs "Get started for FREE" / "Create free AI video" + "Book demo"; microcopy "No credit card required" + "Rated 4.7/5 on G2"; video-led hero (streaming background). Announcement: "Roleplay Sessions: Practice real conversations with AI avatars".
2. **Navigation:** Platform / Solutions / Resources / Pricing / Enterprise + Log in. Platform grouped by verbs: Create (240+ avatars, 1000+ voices, screen recorder, generator, motion graphics), Localize (dubbing, translator, multilingual player, captions), Manage (brand kit, collaboration), Publish (version control, analytics), Engage (interactivity, roleplay), + "AI Safety & Security". Solutions by team/use-case/industry; language selector (en/fr/de/es/pt-BR).
3. **Typography:** **Basier Square**; fluid rem-based responsive type; restrained medium-weight sans.
4. **Color:** **Indigo/blue primary** (`indigo-500/600/700` tokens) with grey scale; light base with dark nav/hero variants and dark gradient sections; pink labels as micro-accents.
5. **Grid:** Centered hero; mega-dropdown panels with grouped cards; card grids + bento modules; sliders/carousels; fluid spacing variables across breakpoints.
6. **Spacing:** Systematic fluid spacing tokens.
7. **Screenshots:** Video and mixed-media feature cards (`card-visual='avatar'/'assistant'/'multilingual'/'recorder'/'brandkit'`) — short clips/animated UI previews rather than static shots.
8. **Motion:** Hero video streaming, fade masks, play/pause controls, testimonial carousels.
9. **Social proof:** G2-led: "2,000+ five-star reviews", 4.7/5; testimonial Q&A ("How easy it is to use!"); capability numbers (240+ avatars, 1000+ voices, 160+ languages); Heineken case study; code-level ~50,000 customers stat.
10. **CTA pattern:** Free self-serve primary ("Get started for FREE", "No credit card required"), "Book demo" sales path; device-aware CTA targets (desktop→pricing, mobile→anchor).
11. **Pricing:** Free-entry framing; Pricing + Enterprise links; localized pricing pages.
12. **Dashboard style:** Workspace narrative: generator, brand kit, version control, analytics, SSO video pages.
13. **AI interaction:** Avatar/voiceover generation, dubbing/translation, interactive roleplay sessions with avatars, voice cloning.
14. **Mobile:** Device-conditional CTA logic + responsive variables — explicit mobile engineering.
15. **Footer:** Localized footer with language dropdown and branded background (full inventory truncated).
16. **Trust:** Explicit **"SOC 2 Type II compliant, ISO 42001 compliant, GDPR compliant"** + "AI Safety & Security" nav group + Responsible AI + AI Research pages.

**Takeaway:** Verb-organized mega-menus (Create/Localize/Manage/Publish/Engage), G2-rating microcopy under the CTA, and device-aware CTA routing.

---

### 1.27 Replit — replit.com (substitute; app-building agent)

1. **Hero:** "What will you build?"; subhead "Turn ideas into apps in minutes — no coding needed."; reassurance "Your first prompt is free. No credit consumption."; CTA "Start." Hero = **prompt composer with creation modes** (Website, Mobile, Design, Slides, Animation, Data Viz, 3D Game, Document, Spreadsheet) + example prompts ("B2B project management app", "AI sales assistant").
2. **Navigation:** Products (Agent, Design, Database, Publish, Integrations, Mobile) / For Work (Pro, Enterprise + roles: PM, Designers, Operations, Developers, SMB owners, Founders) / Resources (Docs, Community, Expert Network, Customer Stories, Gallery, Blog, News) / Security / Pricing / Careers + Contact sales / Log in / Create account.
3. **Typography:** **Replit Diatype + Diatype Mono + IBM Plex Sans + ReplitHack**; clean variable-weight sans UI.
4. **Color:** Light scheme (`color-scheme: light`): bg `#EBECED`/`#FCFCFC`, ink `#07080A`, **interactive blue `#0F87FF` (dark `#005CB8`)**, brand orange `#EC4E02`, success green `#00A11B`, error red `#FA4B4B`.
5. **Grid:** Centered hero prompt module → product announcement → feature scenes → platform benefits → testimonials → pricing → final CTA → footer. Card panels, logo rows, testimonial carousels.
6. **Spacing:** Modular stacked scenes.
7. **Screenshots:** Stylized vignettes: shopping UI with product cards, agent task graph, team/avatar collaboration view, chat prompt panel — workflow states over literal captures.
8. **Motion:** Carousels; agent task-graph animation implied.
9. **Social proof:** Plaid, Adobe, Atlassian, Boeing, ClickUp, Coinbase, Duolingo, Google, Gusto, Microsoft, PayPal, SoFi, Stripe, Zillow; "Trusted by builders"/"Endorsed by innovators"; named testimonials (Databricks, Zillow, Gusto, Talkdesk).
10. **CTA pattern:** Action-first verbs: "Start", "Sign up", "Join Replit Core/Pro", "Get started free"; low-friction reassurance copy; educational secondaries ("Deep dive into Agent 4").
11. **Pricing:** Full table on homepage: Monthly/Yearly toggle ("Save $60"); Starter free; Core $20/mo; Pro $95–100/mo; Enterprise custom; credit amounts per tier ($25/$100).
12. **Dashboard style:** "Agent chat" ("Describe it." → "Publish it."); platform modules (Authentication, Database, Hosting, Monitoring); enterprise governance surfaces.
13. **AI interaction:** Prompt-to-app generation; **Infinite Canvas, Parallel Agents, Multiple Artifacts**; agent-led execution and visual refinement.
14. **Mobile:** Mobile product line + responsive sections.
15. **Footer:** Handy Links / Legal / Company / Social; DPA, subprocessors, abuse reporting; "Made in sunny California".
16. **Trust:** Dedicated Security nav; enterprise controls: SSO/SAML, SOC 2, admin controls, single-tenant, static outbound IPs, VPC peering.

**Takeaway:** Prompt composer as hero (with example prompts) converts curiosity into action; public credit-based pricing builds PLG trust.

---

### 1.28 Bolt.new — bolt.new (substitute; chat-to-app builder)

1. **Hero:** "What will you build today?"; subhead "Create stunning apps & websites by chatting with AI."; **hero is a working prompt input** ("Let's build a prototype…") with "Plan" / "Build now" actions, quick types (Website, Slides, App, Prototype) and Figma/GitHub import buttons.
2. **Navigation:** Community / Enterprise / Templates / Resources / Careers / Pricing + Sign in / Get started.
3. **Typography:** **N/D**; hero heading + feature/persona subheads.
4. **Color:** System dark/light switching; palette **N/D.**
5. **Grid:** Centered prompt hero → social-proof strip → alternating value props → infrastructure feature grid → persona cards → closing CTA → multi-column footer.
6. **Spacing:** Alternating text+image bands.
7. **Screenshots:** Illustrative graphics for scale/infra/auth/SEO/publishing/personas rather than dashboard captures.
8. **Motion:** **N/D** from fetch.
9. **Social proof:** "Trusted by Google, Microsoft, Salesforce, AWS, Meta, HubSpot, Accenture, TikTok, Shopify"; "98% less errors"; "Join millions and start building today."
10. **CTA pattern:** Prompt-driven conversion (type idea → Plan/Build now); "Get started" nav; closing "Ready to build something amazing?" + "Try it out and start building for free".
11. **Pricing:** Structured data: free tier to $30 USD; "Standard" vs "Max" agent tiers.
12. **Dashboard style:** Builder prompt + mode selection; feature cards (Unlimited databases, Enterprise-grade, Auth, SEO, Hosting with analytics & custom domains).
13. **AI interaction:** Chat-based creation; automatic model routing ("routes to the right model for each task"); auto test/refactor/iterate; "projects 1,000 times larger".
14. **Mobile:** **N/D.**
15. **Footer:** Resources / Company / Social (Discord, LinkedIn, YouTube, X, Instagram, Reddit); "© 2026 StackBlitz".
16. **Trust:** Big-brand logos + "Enterprise-grade" language + auth feature card; no badges on homepage.

**Takeaway:** The interactive prompt-as-hero (Plan vs Build now, import from Figma/GitHub) is the strongest instant-gratification pattern in app builders.

---

## 2. Synthesis

### 2.1 Top 10 Common Design Principles

1. **One headline, one promise.** Every best-in-class hero is a single short declarative sentence ("Practice Made Perfect", "Better outcomes. Built on Sierra.", "Welcome to agentic revenue.", "Agentic Infrastructure"). Subheads carry the "who/why", never a second idea.
2. **Proof before product.** The universal page order: Hero → logo wall/stats → value props → product detail → trust → CTA. Logos and quantified outcomes appear in the first viewport-adjacent section on nearly every site (Sierra's 30-logo wall, Abridge's stat band, Cursor's Fortune-500 line).
3. **Numbers as the primary trust language.** Specific, operational metrics beat adjectives: "110 hours saved per user/year", "75ms latency", "2.6M MCP calls/month", "99% OCR accuracy", "$30T AUM". Every mature site publishes 4–10 of these.
4. **Simulated product UI > static screenshots.** The strongest sites (Cursor, Attio, Clay, Sierra, Writer, Abridge, Hebbia) build *stylized, content-filled UI vignettes* — fake-but-plausible tables, tool-call traces, agent states — instead of raw screenshots or abstract art.
5. **Dual-track conversion.** Self-serve + sales coexist: "Start free trial / Download" paired with "Talk to sales / Request a demo" (Clay, Attio, Nabla, Synthesia, Replit, ElevenLabs, Cursor). Regulated verticals (Harvey, Hebbia, Abridge, Norm Ai) collapse to demo-only.
6. **IA organized by customer job, not org chart.** Nav groups follow verbs and workflows: Sierra's Build/Orchestrate/Optimize/Scale; Synthesia's Create/Localize/Manage/Publish/Engage; EvenUp's Pre-Litigation/Litigation lifecycle; Glean's Connect/Act/Understand.
7. **Compliance as first-class content.** Trust Centers, security pages, and certification badges (SOC 2 Type II, ISO 27001, ISO 42001, HIPAA, GDPR) appear on homepages or in footers of every enterprise player; ISO 42001 (AI management) is the emerging AI-specific signal (Sierra, Harvey, Hebbia, Legora, Synthesia).
8. **Restraint in color; identity in type.** Most sites use neutral surfaces (white/bone/charcoal) with one restrained accent (Harvey ivory, Abridge `#EA2C00`, Writer `#5551FF`, Anthropic `#D97757`, Granola `#D1E043`). Differentiation comes from custom/branded fonts: HarveySerif, Edict Display, Geist, Diatype, Euclid Circular, Basier Square, Anthropic Serif, Aktiv Grotesk/Suisse Works.
9. **Human oversight is a stated design value.** Trust copy for agents consistently promises supervision: "never takes money-moving actions without human confirmation" (Ramp), "every final decision in the clinician's hands" (Nabla), "approvals are built in" (Lindy), "auditable artifacts" (Anthropic), observability/traces (Sierra, Decagon).
10. **The prompt box is becoming the hero.** AI-native products increasingly put the interaction itself above the fold: Bolt's working prompt input, Replit's mode composer, Sierra's simulated agent chat, Hebbia's workflow sequence, Writer's prompt panels, Clay's "paste into your coding agent" install module.

### 2.2 Common Patterns Across Best-in-Class AI SaaS

**Page anatomy (modal structure):**
1. Announcement bar (launch/event/funding) — Harvey, Sierra, Decagon, Attio, Norm Ai
2. Hero: short headline + who-it's-for subhead + 1–2 CTAs + demo/video/prompt visual
3. Logo wall immediately below (grayscale, uniform height)
4. Problem/positioning section (often numbered 01/02/03 — Glean, Cognition)
5. Capability modules as paired copy + simulated UI (tabs or alternating rows)
6. Metrics band (3–6 large stat blocks)
7. Testimonials: named, titled, and increasingly from named executives or celebrity practitioners
8. Security/trust band with badges + Trust Center link
9. Final repeated CTA
10. Mega-footer (4–12 columns) with legal cluster (ToS, DPA, Privacy, Cookie prefs, Subprocessors, Status)

**Navigation patterns:**
- 4–7 top-level items; mega-menus with grouped cards and featured promos (Harvey, Synthesia, Vercel)
- "Security"/"Trust Center" promoted to nav, not just footer (Harvey, Replit, Legora)
- "Ask AI" as nav item (Vercel); developer install CTAs (Clay, Cursor CLI)
- Language/locale selectors on global enterprise sites (Sierra, Nabla, Synthesia)

**Typography:**
- Custom branded fonts are the norm at scale; pairings are usually *sans for UI + serif for editorial authority* (Harvey, Hebbia, Rogo, Anthropic, Writer's Canela, Attio's Tiempos) or *sans + mono for engineering precision* (Sierra GT America Mono, Cognition Geist Mono, Linear monospace tokens, Replit Diatype Mono)
- Fluid clamp() hero sizing is standard (Hebbia 2.2–5rem; Granola 68–110px; Norm Ai 2.5–4rem)
- Uppercase micro-labels/eyebrows for taxonomy ("AI FOR FINANCE", "PRE-VISIT", "GTM INFRASTRUCTURE")
- 9-step or token-based type scales (Linear title-1…9; Writer presets)

**Color:**
- Split between dark-premium (Harvey `#1F1D1A`, Hebbia black, Norm Ai black, Vercel dark-glow, Anthropic `#141413`) and light-clinical (Sierra white, Abridge bone `rgb(247,242,237)`, Nabla white, Writer light, Cursor `#F7F7F4`)
- Single-accent discipline: one saturated hue per brand, everything else neutral; semantic tokens for text hierarchy (primary/secondary/tertiary/quaternary — Linear, Attio)
- Finance vertical leans cream + deep green + P&L red/green semantics (Rogo, Hebbia)
- Healthcare leans warm bone + one warm accent + clinical white (Abridge, Nabla, Ambience)

**Social-proof hierarchy (strongest → weakest in use):**
1. Named enterprise logos (wall, grayscale/marquee)
2. Quantified outcome stats with units (hours saved, %, $, latency)
3. Named executive/practitioner testimonials with titles
4. Awards (Best in KLAS, TIME, G2 ratings)
5. Platform scale counters (MCP calls, conversations processed, pages analyzed)
6. Funding announcements as banners (Norm Ai)

**Pricing behavior:**
- Enterprise/regulated: no pricing (Harvey, Sierra, Hebbia, Abridge, EvenUp, Legora, Writer) — demo-gated
- PLG: public tiers on homepage or one click (Attio Free/$35/$79; Replit free/$20/$95; Lindy $49.99/$59.99; Ramp Free/$15/Enterprise; Synthesia free entry)
- Outcome-based pricing narratives appear where pricing is hidden (Sierra "pay for a job well done")

**Footer:**
- 4–12 columns mirroring nav + Resources + Company + Legal
- Near-universal: Privacy, Terms, Cookie Preferences, Status, Trust/Security center
- Emerging: DPA/Subprocessors links (Anthropic, Replit, Cognition), "LLMs" page (Attio), Modern Slavery Statement (Sierra)

### 2.3 What Makes Them Look "Enterprise-Grade" vs "Startup"

| Signal | Enterprise-grade | Startup / PLG |
|---|---|---|
| Palette | Dark neutrals or warm bone; near-zero saturation outside one accent (Harvey, Hebbia, Norm Ai, Cognition) | Bright accents, gradients, playful illustration (Decagon gradients, Clay illustration, Lindy gold) |
| Typography | Branded serif display or refined grotesk; tight tracking; small-caps eyebrows | Rounded sans (Manrope), first-person casual copy ("hey, I'm Lindy") |
| Proof | Institutional logos + $-scale stats + named GC/CMIO/CTO testimonials + awards | Ratings (G2 4.7), review counts, community quotes, hiring counters |
| Conversion | Single "Request a demo" / "Contact us"; no free trial | "Start free trial" / "Download" + pricing table on homepage |
| Trust | Badge wall (SOC 2 II, ISO 27001/42001, HIPAA, GDPR, FedRAMP) + Trust Center + DPA/SLA in footer | "Security by design" copy, privacy promises, trust pages without certifications |
| Content | Whitepapers, science/publications, research, ROI calculators (Abridge, Nabla, Harvey, Hebbia) | Blogs, templates, community, university, livestreams (Clay, Replit, Bolt) |
| Imagery | Cinematic video, photography of institutions/clinicians, hairline editorial grids | OS-native mockups (iMessage), illustrated worlds, meme-adjacent quotes |
| Voice | Third-person, outcome nouns ("Institutional Intelligence") | First-person, verbs ("What will you build?") |
| Motion | Slow hero video, marquees, restrained fades | Interactive demos, prompt inputs, typing dots, animated task graphs |

**Gradient of the cohort:** Cognition/Norm Ai/Harvey (pure institutional) → Sierra/Abridge/Hebbia (enterprise with product polish) → Cursor/Vercel/Attio/Clay (developer-credible hybrid) → Lindy/Granola/Bolt/Replit (personality-led PLG).

### 2.4 Key Visual Patterns That Convey Trust, Precision, and AI-Native Feel

**Trust:**
- Certification badge rows placed adjacent to security copy, not buried: SOC 2 Type II is table stakes; **ISO 42001** is the AI-era differentiator; HIPAA/FedRAMP/PCI for regulated verticals
- Dedicated Trust Center link in nav *and* footer
- Explicit data promises: "No training on your data" (Hebbia, Legora), "Zero AI training on your data", "your data is never sold" (Lindy), encryption specs (AES-256/TLS 1.2+)
- Human-oversight language near every autonomy claim (see Principle 9)
- Legal maturity artifacts: DPA, SLA, subprocessors, vulnerability reporting, status page
- Safety-as-product: moderation/accountability/provenance (ElevenLabs), Responsible AI pages (Synthesia), AI governance partnerships (Nabla)

**Precision:**
- Monospace micro-labels and data accents (Sierra GT America Mono, Cognition Geist Mono 10–12px labels, Linear mono tokens)
- `tabular-nums` for all statistics; oversized stat blocks with unit labels
- Numbered section indices ("01/02/03") and hairline grid rules (Norm Ai, Glean, Cognition)
- Tool-call transparency in UI mocks: traces, "2 tools used", "SQL query executed: 1452 rows in 6.2s" (Attio), reasoning panels (Sierra), version-comparison metrics (ElevenLabs)
- Specificity everywhere: latency (75ms), accuracy (99%, 98%), counts (12,442,032,540 tokens saved)

**AI-native feel:**
- The interaction is the hero: prompt boxes, simulated chats, agent task lists — not abstract gradient orbs
- Streaming/live states: typing dots, "Agent running", "In Progress 2 / Ready for Review 3", transcribing indicators, rotating hero lines
- Agent vocabulary made visible: workflows, monitors, guardrails, experiments, observability, MCP/API/CLI surfaces shown as product (Vercel, Clay, Attio, Cursor)
- Multi-surface storytelling: same agent across chat/voice/email/Slack/mobile/EHR (Sierra, Decagon, Lindy, Nabla)
- Model/context indicators in UI mocks ("auto · Opus 4.8 · 1M context" — Attio); model choosers (Cursor)
- Developer-native entry points: CLI install snippets, "paste into your coding agent", MCP servers
- Dark-glow/terminal aesthetics for infra (Vercel), warm-paper/light for knowledge work (Granola, Abridge)

---

## 3. Actionable Blueprint (distilled checklist)

If building an enterprise-grade AI product site from these patterns:

1. **Hero:** ≤8-word declarative headline + one-sentence who/why + dual CTA (primary verb + "Watch/Talk") + a *working-looking* product moment (prompt, chat, or 10s video) — never a static illustration alone.
2. **Announcement bar** for launches/events/funding with "Learn more".
3. **Logo wall** within one scroll; grayscale, marquee or static grid; 8–30 logos.
4. **Stats band:** 3–6 metrics with units and `tabular-nums`; prefer time-saved, money, latency, accuracy, or scale counters.
5. **Capability sections** organized as customer jobs (verb groups), each pairing copy with a simulated UI vignette containing realistic content.
6. **Testimonials:** named person + title + company; executive-level for enterprise, practitioner-level for PLG.
7. **Trust band:** badge row (SOC 2 II, ISO 27001, ISO 42001, + vertical certs), 3 security bullets (SSO, audit logs, no-training), Trust Center link.
8. **Typography:** custom or distinctive pairing — display serif or grotesk + mono for data; fluid clamp() hero; uppercase eyebrows; 8–9-step token scale.
9. **Color:** neutral surface system (light-bone or dark-charcoal) + 1 accent ≤ 10% of pixels; semantic text hierarchy tokens (primary→quaternary).
10. **Grid:** 12-column, max-width 1280–1440px, hairline dividers optional; 4–6 responsive breakpoints; mobile hero variants for image-heavy heroes.
11. **Footer:** sitemap mega-footer + legal cluster (Privacy, Terms, DPA, Cookies, Status, Security/Trust).
12. **Pricing:** hide it if sales-led regulated; publish it (with free tier + credits) if PLG; consider outcome-based framing if usage-based.
13. **Motion budget:** one signature motion (hero video, dot-grid, marquee, or interactive demo) + subtle scroll/hover states; avoid decorative excess in enterprise positioning.
14. **AI-native signals:** show traces/guardrails/observability in mocks; expose CLI/API/MCP surfaces; state human-oversight guarantees near every autonomy claim.

---

## 4. Inaccessible Sites Log

| Site | Attempts | Failure mode |
|---|---|---|
| hippocratic.ai | 2 (www + apex) | fetch failed (likely bot protection) |
| brightwave.ai | 2 (www + apex) | fetch failed |
| dust.tt | 3 | fetch failed |
| phia.ai | 2 | fetch failed |
| perplexity.ai | 4 (apex, www, /enterprise) | fetch failed |
| lovable.dev | 2 | Cloudflare JS challenge |
| openai.com | 1 (substitute attempt) | JS challenge |
| mistral.ai | 2 (substitute attempts) | fetch failed |
| rogo.ai | 1 | CloudFront geo-block (403); rogo.com partially analyzed instead |

*Document compiled from live fetches; page content reflects each site at the time of retrieval. Font names, hex values, and copy quoted above were extracted from page assets/markup during analysis.*
