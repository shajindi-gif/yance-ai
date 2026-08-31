#!/usr/bin/env python3
"""
yance.ai 示范数据 Seeder — 幂等脚本
保留原第1个示范企业并补充完整 + 新增4家不同类型示范企业
重复执行不会重复创建
"""
import os, sys, secrets, uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/opt/yance/yance-ai")
os.environ.setdefault("ENV_FILE", "/opt/yance/yance-ai/.env.prod")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# 从环境变量读取数据库连接（Docker容器中由 compose env_file 注入）
DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    # fallback: 尝试从文件读取（本地执行时）
    for path in ["/opt/yance/yance-ai/.env.prod", ".env.prod"]:
        try:
            with open(path) as f:
                for line in f:
                    if line.startswith("DATABASE_URL="):
                        DB_URL = line.split("=", 1)[1].strip()
                        break
            if DB_URL:
                break
        except FileNotFoundError:
            continue
if not DB_URL:
    print("ERROR: DATABASE_URL not found in env or file")
    sys.exit(1)

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

NOW = datetime.now(timezone.utc)

def days_ago(n):
    return NOW - timedelta(days=n)

def days_ago_ts(n, hour=10, minute=30):
    d = days_ago(n)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)

# ─────────────────────────────────────────────────
# STEP 1: 清理测试数据（保留真实用户）
# ─────────────────────────────────────────────────
print("\n=== STEP 1: 清理测试数据 ===")
TEST_EMAIL_PATTERNS = ["@test.ai", "@yance.ai"]  # 测试邮箱后缀
# 排除 admin@yance.ai（管理员）
KEEP_EMAILS = {"admin@yance.ai"}

deleted = db.execute(text("""
    DELETE FROM tenants WHERE id IN (
        SELECT t.id FROM tenants t 
        JOIN users u ON u.tenant_id = t.id 
        WHERE (u.email LIKE '%%@test.ai' OR (u.email LIKE '%%@yance.ai' AND u.email != 'admin@yance.ai')
               OR u.email = 'test@qq.com' OR u.email = 'fere@qq.com')
        AND u.email NOT IN ('admin@yance.ai')
    )
"""))
db.commit()
print(f"  清理测试租户: {deleted.rowcount} 条")

# 同时清理孤立的 analytics_events
db.execute(text("DELETE FROM analytics_events WHERE tenant_id NOT IN (SELECT id FROM tenants)"))
db.execute(text("DELETE FROM opportunities WHERE tenant_id NOT IN (SELECT id FROM tenants)"))
db.execute(text("DELETE FROM orders WHERE tenant_id NOT IN (SELECT id FROM tenants)"))
db.execute(text("DELETE FROM entitlements WHERE tenant_id NOT IN (SELECT id FROM tenants)"))
db.execute(text("DELETE FROM invoices WHERE tenant_id NOT IN (SELECT id FROM tenants)"))
db.execute(text("DELETE FROM payments WHERE tenant_id NOT IN (SELECT id FROM tenants)"))
db.execute(text("DELETE FROM companies WHERE tenant_id NOT IN (SELECT id FROM tenants)"))
db.execute(text("DELETE FROM users WHERE tenant_id NOT IN (SELECT id FROM tenants)"))
db.commit()
print("  清理孤立数据完成")

# 验证剩余
remaining = db.execute(text("""
    SELECT t.name, u.email FROM tenants t JOIN users u ON u.tenant_id=t.id ORDER BY t.created_at
""")).fetchall()
print(f"  剩余租户: {len(remaining)}")
for r in remaining:
    print(f"    {r[0]} ({r[1]})")


# ─────────────────────────────────────────────────
# STEP 2: 补充第1个示范企业（上海衍策引擎）
# ─────────────────────────────────────────────────
print("\n=== STEP 2: 补充示范企业1 ===")

master_tenant = db.execute(text("SELECT id FROM tenants WHERE slug='yance-ai'")).fetchone()
if not master_tenant:
    print("ERROR: master tenant not found")
    sys.exit(1)
master_tid = master_tenant[0]

# 更新公司画像
db.execute(text("""
    UPDATE companies SET 
        unified_credit_code = '91310000MA1FL8XXXX',
        metadata_json = CAST(:meta AS jsonb)
    WHERE tenant_id = :tid
"""), {
    "tid": master_tid,
    "meta": '{"district":"徐汇区","scale":"小型（20-100人）","founded_year":"2024年","registered_capital":"500万元","headcount":"35人","rd_ratio":"45%","rd_expense_ratio":"18","annual_revenue":"800-1500万","core_tech":"AI政策匹配引擎、企业画像系统、RAG知识库","qualifications":["科技型中小企业"],"ip_count":"6（软著6项）","funding_stage":"种子轮","funding_needs":"Pre-A轮 500-1000万","policy_needs":["高新技术企业认定","科技型中小企业评价","研发费用加计扣除","人才政策","算力券"],"ai_needs":"自身为AI公司，持续优化匹配算法","demo":true,"profile_completeness":100}'
})
db.commit()
print("  ✓ 示范企业1（上海衍策引擎）画像已补充完整")

# 获取该公司 company_id
master_cid = db.execute(text("SELECT id FROM companies WHERE tenant_id=:tid"), {"tid": master_tid}).fetchone()[0]

# 为示范企业1创建2个新的订单（补充现有订单，总共3份报告的感觉）
existing_orders = db.execute(text("SELECT count(*) FROM orders WHERE tenant_id=:tid"), {"tid": master_tid}).fetchone()[0]
print(f"  现有订单数: {existing_orders}")

if existing_orders < 2:
    # 创建 POLICY_DIAGNOSIS 订单
    db.execute(text("""
        INSERT INTO orders (id, tenant_id, order_no, product_code, amount, currency, status, created_at, updated_at)
        VALUES (gen_random_uuid(), :tid, :ono, 'POLICY_DIAGNOSIS', 299.00, 'CNY', 'paid', :created, now())
        ON CONFLICT (order_no) DO NOTHING
    """), {"tid": master_tid, "ono": f"Y{secrets.token_hex(8).upper()}", "created": days_ago_ts(5)})
    
    # 创建 APPLICATION_PLAN 订单
    db.execute(text("""
        INSERT INTO orders (id, tenant_id, order_no, product_code, amount, currency, status, created_at, updated_at)
        VALUES (gen_random_uuid(), :tid, :ono, 'APPLICATION_PLAN', 699.00, 'CNY', 'paid', :created, now())
        ON CONFLICT (order_no) DO NOTHING
    """), {"tid": master_tid, "ono": f"Y{secrets.token_hex(8).upper()}", "created": days_ago_ts(3)})
    db.commit()
    print("  ✓ 补充订单: POLICY_DIAGNOSIS ¥299 + APPLICATION_PLAN ¥699")


# ─────────────────────────────────────────────────
# STEP 3: 新增4家示范企业
# ─────────────────────────────────────────────────
print("\n=== STEP 3: 新增4家示范企业 ===")

DEMO_COMPANIES = [
    {
        "name": "上海云启智能科技有限公司",
        "email": "demo2@yance-demo.ai",
        "owner": "李明远",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHRzYWx0c2FsdA$RdescudvJPjn8Qn9Y2sVwGOWjbMmMYn8mTQnk3WnEKo",  # placeholder
        "industry": "人工智能",
        "unified_credit_code": "91310000MA1K9XXXX",
        "province": "上海市",
        "city": "上海市",
        "reg_days_ago": 12,
        "metadata": {
            "district": "杨浦区", "scale": "微型（<20人）", "founded_year": "1-3年",
            "registered_capital": "100万元", "headcount": "12人", "rd_ratio": "60%",
            "rd_expense_ratio": "25", "annual_revenue": "100-300万",
            "core_tech": "NLP大模型应用、智能客服SaaS、企业知识库",
            "qualifications": [],
            "ip_count": "3（软著3项）",
            "funding_stage": "天使轮",
            "funding_needs": "Pre-A轮 300-500万",
            "policy_needs": ["科技型中小企业评价", "算力券", "模型券", "创业补贴", "高新技术企业认定"],
            "ai_needs": "需要GPU算力支持大模型推理",
            "demo": True, "profile_completeness": 100
        },
        "orders": [
            {"code": "POLICY_REPORT", "amount": 99.00, "days_ago": 8},
            {"code": "POLICY_DIAGNOSIS", "amount": 299.00, "days_ago": 5},
        ],
        "renewed": False,
    },
    {
        "name": "上海精衡智能装备有限公司",
        "email": "demo3@yance-demo.ai",
        "owner": "王振华",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHRzYWx0c2FsdA$RdescudvJPjn8Qn9Y2sVwGOWjbMmMYn8mTQnk3WnEKo",
        "industry": "高端装备制造",
        "unified_credit_code": "91310000MA1T3XXXX",
        "province": "上海市",
        "city": "上海市",
        "reg_days_ago": 20,
        "metadata": {
            "district": "闵行区", "scale": "小型（20-100人）", "founded_year": "5-10年",
            "registered_capital": "2000万元", "headcount": "68人", "rd_ratio": "22%",
            "rd_expense_ratio": "6.5", "annual_revenue": "3000-5000万",
            "core_tech": "工业机器人精密装配、智能检测系统、数控加工",
            "qualifications": ["高新技术企业"],
            "ip_count": "18（发明专利5项，实用新型8项，软著5项）",
            "funding_stage": "未融资",
            "funding_needs": "技术改造专项贷款 500万",
            "policy_needs": ["专精特新认定", "技术改造补贴", "研发费用加计扣除", "首台套政策"],
            "ai_needs": "产线视觉检测AI化改造",
            "demo": True, "profile_completeness": 95
        },
        "orders": [
            {"code": "POLICY_REPORT", "amount": 99.00, "days_ago": 15},
            {"code": "POLICY_DIAGNOSIS", "amount": 299.00, "days_ago": 10},
            {"code": "APPLICATION_PLAN", "amount": 699.00, "days_ago": 7},
        ],
        "renewed": False,
    },
    {
        "name": "上海泽康生物科技有限公司",
        "email": "demo4@yance-demo.ai",
        "owner": "陈雨薇",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHRzYWx0c2FsdA$RdescudvJPjn8Qn9Y2sVwGOWjbMmMYn8mTQnk3WnEKo",
        "industry": "生物医药",
        "unified_credit_code": "91310000MA1P7XXXX",
        "province": "上海市",
        "city": "上海市",
        "reg_days_ago": 35,
        "metadata": {
            "district": "浦东新区", "scale": "小型（20-100人）", "founded_year": "3-5年",
            "registered_capital": "1000万元", "headcount": "45人", "rd_ratio": "50%",
            "rd_expense_ratio": "35", "annual_revenue": "500-1000万",
            "core_tech": "体外诊断试剂、微流控芯片、AI辅助诊断算法",
            "qualifications": ["科技型中小企业"],
            "ip_count": "9（发明专利3项，软著6项）",
            "funding_stage": "A轮",
            "funding_needs": "B轮 2000-3000万",
            "policy_needs": ["研发项目补贴", "人才政策", "产业专项", "高新技术企业认定", "创新医疗器械"],
            "ai_needs": "AI辅助诊断算法训练算力需求",
            "demo": True, "profile_completeness": 88
        },
        "orders": [
            {"code": "POLICY_REPORT", "amount": 99.00, "days_ago": 25},
        ],
        "renewed": False,
    },
    {
        "name": "上海慧联数科有限公司",
        "email": "demo5@yance-demo.ai",
        "owner": "赵启明",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHRzYWx0c2FsdA$RdescudvJPjn8Qn9Y2sVwGOWjbMmMYn8mTQnk3WnEKo",
        "industry": "软件与信息技术",
        "unified_credit_code": "91310000MA1FL8XXXY",
        "province": "上海市",
        "city": "上海市",
        "reg_days_ago": 50,
        "metadata": {
            "district": "静安区", "scale": "中型（100-500人）", "founded_year": "5-10年",
            "registered_capital": "5000万元", "headcount": "180人", "rd_ratio": "18%",
            "rd_expense_ratio": "5", "annual_revenue": "5000万-1亿",
            "core_tech": "企业数字化转型咨询、低代码平台、数据中台",
            "qualifications": ["高新技术企业", "ISO27001"],
            "ip_count": "22（软著22项）",
            "funding_stage": "未融资",
            "funding_needs": "数字化改造专项补贴",
            "policy_needs": ["数字化转型专项", "创新创业政策", "人才政策", "办公空间补贴"],
            "ai_needs": "大模型在企业服务场景的落地应用",
            "demo": True, "profile_completeness": 82
        },
        "orders": [
            {"code": "POLICY_REPORT", "amount": 99.00, "days_ago": 40},
        ],
        "renewed": False,
    },
]

# 获取产品 ID 映射
products = db.execute(text("SELECT id, code FROM products")).fetchall()
product_map = {code: pid for pid, code in products}
print(f"  产品目录: {list(product_map.keys())}")

# 获取全局政策 ID（用于创建 opportunities）
policy_ids = [row[0] for row in db.execute(text("SELECT id FROM policies WHERE tenant_id IS NULL AND status='published'")).fetchall()]
print(f"  全局政策数: {len(policy_ids)}")

created_count = 0
for comp in DEMO_COMPANIES:
    # 幂等检查
    existing = db.execute(text(
        "SELECT t.id FROM tenants t JOIN users u ON u.tenant_id=t.id WHERE u.email=:email"
    ), {"email": comp["email"]}).fetchone()
    
    if existing:
        print(f"  ⏭ {comp['name']} 已存在，跳过")
        continue
    
    reg_time = days_ago_ts(comp["reg_days_ago"])
    
    # 1. 创建租户
    tid = uuid.uuid4()
    slug = f"demo-{secrets.token_hex(4)}"
    db.execute(text("""
        INSERT INTO tenants (id, name, slug, is_active, created_at, updated_at)
        VALUES (:id, :name, :slug, true, :created, now())
    """), {"id": tid, "name": comp["name"], "slug": slug, "created": reg_time})
    
    # 2. 创建用户
    uid = uuid.uuid4()
    db.execute(text("""
        INSERT INTO users (id, tenant_id, email, full_name, password_hash, role, is_active, created_at, updated_at)
        VALUES (:id, :tid, :email, :name, :ph, 'owner', true, :created, now())
    """), {"id": uid, "tid": tid, "email": comp["email"], "name": comp["owner"], 
           "ph": comp["password_hash"], "created": reg_time})
    
    # 3. 创建公司
    cid = uuid.uuid4()
    import json
    meta_str = json.dumps(comp["metadata"], ensure_ascii=False)
    db.execute(text("""
        INSERT INTO companies (id, tenant_id, name, unified_credit_code, province, city, industry, metadata_json, created_at, updated_at)
        VALUES (:id, :tid, :name, :ucc, :prov, :city, :ind, CAST(:meta AS jsonb), :created, now())
    """), {"id": cid, "tid": tid, "name": comp["name"], "ucc": comp["unified_credit_code"],
           "prov": comp["province"], "city": comp["city"], "ind": comp["industry"],
           "meta": meta_str, "created": reg_time})
    
    # 4. 创建订单 + Entitlement + Invoice
    for order_def in comp["orders"]:
        oid = uuid.uuid4()
        order_no = f"Y{secrets.token_hex(8).upper()}"
        order_time = days_ago_ts(order_def["days_ago"])
        
        db.execute(text("""
            INSERT INTO orders (id, tenant_id, order_no, product_code, amount, currency, status, created_at, updated_at)
            VALUES (:id, :tid, :ono, :code, :amt, 'CNY', 'paid', :created, now())
        """), {"id": oid, "tid": tid, "ono": order_no, "code": order_def["code"], 
               "amt": order_def["amount"], "created": order_time})
        
        # Payment
        db.execute(text("""
            INSERT INTO payments (id, tenant_id, order_id, provider, provider_trade_no, amount, currency, status, raw_response, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, :oid, 'demo', :tno, :amt, 'CNY', 'completed', CAST('{}' AS jsonb), :created, now())
        """), {"tid": tid, "oid": oid, "tno": f"DEMO_{order_no}", "amt": order_def["amount"], "created": order_time})
        
        # Entitlement
        pid = product_map.get(order_def["code"])
        if pid:
            resource_type = {"POLICY_REPORT": "report", "POLICY_DIAGNOSIS": "diagnosis", "APPLICATION_PLAN": "plan"}.get(order_def["code"], "report")
            db.execute(text("""
                INSERT INTO entitlements (id, tenant_id, user_id, product_id, order_id, resource_type, resource_id, status, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, :uid, :pid, :oid, :rtype, :cid, 'active', :created, now())
            """), {"tid": tid, "uid": uid, "pid": pid, "oid": oid, "rtype": resource_type, "cid": cid, "created": order_time})
        
        # Invoice
        db.execute(text("""
            INSERT INTO invoices (id, tenant_id, order_id, invoice_no, title, tax_number, invoice_type, amount, tax_amount, total_amount, status, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, :oid, :ino, :name, :taxno, 'vat_normal', :amt, 0, :amt, 'generated', :created, now())
        """), {"tid": tid, "oid": oid, "ino": f"INV_{order_no}", "name": comp["name"], 
               "taxno": comp["unified_credit_code"], "amt": order_def["amount"], "created": order_time})
    
    # 5. 创建 Opportunities（政策匹配记录）
    num_opps = min(len(policy_ids), 8)
    scores = [0.85, 0.78, 0.72, 0.68, 0.62, 0.55, 0.48, 0.42]
    for i in range(num_opps):
        opp_time = reg_time + timedelta(days=1, hours=i)
        db.execute(text("""
            INSERT INTO opportunities (id, tenant_id, company_id, policy_id, title, score, status, evidence_json, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, :cid, :pid, :title, :score, 'identified', CAST(:ev AS jsonb), :created, now())
        """), {"tid": tid, "cid": cid, "pid": policy_ids[i], 
               "title": f"{comp['name']} × 政策匹配 #{i+1}", 
               "score": scores[i % len(scores)],
               "ev": '{"score_breakdown":{"region":15,"industry":12,"scale":8,"qualification":10,"tech":12,"finance":8,"semantic":8},"total_score":73}',
               "created": opp_time})
    
    # 6. 创建 AnalyticsEvents（模拟用户行为）
    events = [
        ("report_generated", reg_time + timedelta(days=1)),
        ("payment_completed", reg_time + timedelta(days=2)),
        ("report_downloaded", reg_time + timedelta(days=2, hours=2)),
    ]
    if comp["renewed"]:
        events.append(("payment_completed", reg_time + timedelta(days=30)))
    
    for ev_name, ev_time in events:
        db.execute(text("""
            INSERT INTO analytics_events (id, tenant_id, user_id, name, occurred_at, properties)
            VALUES (gen_random_uuid(), :tid, :uid, :name, :time, CAST('{}' AS jsonb))
        """), {"tid": tid, "uid": uid, "name": ev_name, "time": ev_time})
    
    created_count += 1
    print(f"  ✓ {comp['name']} ({comp['industry']}) | 注册:{comp['reg_days_ago']}天前 | 订单:{len(comp['orders'])} | 匹配:{num_opps}")

db.commit()
print(f"\n✅ 新增 {created_count} 家示范企业")


# ─────────────────────────────────────────────────
# STEP 4: 验证统计
# ─────────────────────────────────────────────────
print("\n=== STEP 4: 最终统计验证 ===")
stats = db.execute(text("""
    SELECT 
        (SELECT count(DISTINCT t.id) FROM tenants t) as total_tenants,
        (SELECT count(*) FROM users u WHERE u.is_active) as active_users,
        (SELECT count(*) FROM companies) as companies,
        (SELECT count(*) FROM opportunities) as opportunities,
        (SELECT count(*) FROM orders WHERE status='paid') as paid_orders,
        (SELECT sum(amount) FROM orders WHERE status='paid') as total_revenue,
        (SELECT count(*) FROM entitlements WHERE status='active') as entitlements,
        (SELECT count(*) FROM invoices) as invoices
""")).fetchone()

print(f"  租户总数: {stats[0]}")
print(f"  活跃用户: {stats[1]}")
print(f"  企业档案: {stats[2]}")
print(f"  政策匹配: {stats[3]}")
print(f"  已付订单: {stats[4]}")
print(f"  总收入: ¥{stats[5] or 0:.0f}")
print(f"  有效授权: {stats[6]}")
print(f"  发票: {stats[7]}")

# 分租户明细
print("\n  分企业明细:")
detail = db.execute(text("""
    SELECT t.name, 
           (SELECT metadata_json->>'profile_completeness' FROM companies c WHERE c.tenant_id=t.id LIMIT 1) as completeness,
           (SELECT count(*) FROM orders o WHERE o.tenant_id=t.id AND o.status='paid') as orders,
           (SELECT count(*) FROM opportunities opp WHERE opp.tenant_id=t.id) as opps,
           (SELECT count(*) FROM entitlements e WHERE e.tenant_id=t.id AND e.status='active') as ents
    FROM tenants t ORDER BY t.created_at
""")).fetchall()

for r in detail:
    completeness = r[1] if r[1] else "N/A"
    print(f"    {r[0][:20]:20s} | 画像:{completeness:>3s}% | 订单:{r[2]} | 匹配:{r[3]} | 授权:{r[4]}")

db.close()
print("\n✅ Seeder 执行完成")
