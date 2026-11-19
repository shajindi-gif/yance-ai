# workspace-ask-activate-20261119

在 `opportunity-20261119-rank01` 之上启用问衍策（配置级），并可叠加 Ask reading 检索补丁。

## 前置验收（必须全绿）

1. `QWEN_API_KEY` / `DEEPSEEK_API_KEY` 已配置（不打印）。
2. 合成租户：有企业画像 → 提问 → SSE 含 citations；无来源 → 拒答。
3. 不自动发布画像、不改资格、不绕过购买门禁。
4. `WORKSPACE_ASK_ENABLED=false` 时仍返回 503。

## 激活（服务器）

```bash
R=/opt/yance/releases/opportunity-20261119-rank01
# 1) 备份
sudo cp "$R/production.env" "$R/production.env.bak-ask-$(date +%Y%m%d%H%M)"
sudo cp "$R/release.override.json" "$R/release.override.json.bak-ask-$(date +%Y%m%d%H%M)"
# 2) 仅改开关（勿整文件回写以免泄密）
sudo sed -i 's/^WORKSPACE_ASK_ENABLED=.*/WORKSPACE_ASK_ENABLED=true/' "$R/production.env"
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/opt/yance/releases/opportunity-20261119-rank01/release.override.json")
data = json.loads(p.read_text())
for svc in ("api", "agent-worker"):
    env = data.setdefault("services", {}).setdefault(svc, {}).setdefault("environment", {})
    env["WORKSPACE_ASK_ENABLED"] = "true"
p.write_text(json.dumps(data, indent=2) + "\n")
print("override ask=true")
PY
# 3) 热补丁 recreate（沿用 rank01 activate 的 compose 链）
bash "$R/activate.sh"   # 或等价 up -d --no-deps --force-recreate api
```

若需同时上线 Ask `reading` 证据补丁：先部署含 `workspace.py` 变更的镜像/文件补丁，再开开关。

## 回滚

```bash
R=/opt/yance/releases/opportunity-20261119-rank01
sudo sed -i 's/^WORKSPACE_ASK_ENABLED=.*/WORKSPACE_ASK_ENABLED=false/' "$R/production.env"
# 同步把 release.override.json 中 WORKSPACE_ASK_ENABLED 改回 false 后 recreate api
```

## 验收命令（合成账号）

```bash
# home.ask_enabled 应为 true
# POST /api/v1/ask 应 SSE retrieval → citations|done 或证据不足拒答
```
