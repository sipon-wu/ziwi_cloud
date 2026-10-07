# ziwi_cloud — cloud.ziwi.cn 统一身份后端

知微云统一身份与租户管理平台（IdP）后端。生产运行于腾讯云 CVM `193.112.163.147` 的 `/opt/cloud-idp/backend`，对外服务 `cloud.ziwi.cn`。

---

## 一、四节点关系（协同必读）

| 节点 | 角色 | 说明 |
|------|------|------|
| **本地 Mac** (`/Users/sipon/CodeBuddy/ziwi_cloud/`) | 操作枢纽 | 写代码、rsync 到 CVM、持有 GitHub SSH key（唯一能 push GitHub 的机器） |
| **GitHub** (`sipon-wu/ziwi_cloud`) | 代码真相源/备份 | 只存代码，不运行；**不含任何私钥** |
| **腾讯云 CVM** (`193.112.163.147`) | 运行现场 | docker 容器实际运行处，含数据库、JWT 签名密钥卷、RSA 私钥 `keys/` |
| workbuddy（Win 机） | 协同开发 | 共用同一 CVM 与同一 GitHub 账号，**但无 CVM SSH key、无 GitHub push 能力**（见纪律） |

**流转模型**：Mac 写 → GitHub 存 → CVM 跑。GitHub 不是生产环境，代码必须落到 CVM 并 `docker compose up --build` 才生效。

---

## 二、Git 工作流（重要：方案 A）

> **CVM 不直接连 GitHub。** CVM 只建了**本地 git**（版本保护用），所有 GitHub 同步经由 Mac 枢纽。

### CVM 上改码（本地提交）
```bash
cd /opt/cloud-idp/backend
# 改码后 —— 严禁 git add -A，只加具体路径
git add <具体文件或目录>
git commit -m "feat: ..."
```

### 同步到 GitHub（在 Mac 上执行）
```bash
# 1. 从 CVM 拉回最新源码（已排除 venv/私钥/本地库）
rsync -az --delete \
  --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='keys' --exclude='cloud_local.db' --exclude='.pytest_cache' \
  root@193.112.163.147:/opt/cloud-idp/backend/ /Users/sipon/CodeBuddy/ziwi_cloud/

# 2. Mac 上提交并推送
cd /Users/sipon/CodeBuddy/ziwi_cloud
git add <具体路径>
git commit -m "..."
git push origin main
```

---

## 三、安全纪律（红线）

1. **永不 `git add -A` / `git add .`** —— 必须列具体路径，否则可能把 `keys/` 私钥塞进历史。
2. **`.gitignore` 已挡**：`keys/`、`test_keys/*_private.pem`、`.venv/`、`cloud_local.db`、`*.db`、`.env`。
   - 入库的只有 `test_keys/key_v1_public.pem`（**公钥，无害**）。
3. **私钥只活在 CVM 本地**（`/opt/cloud-idp/backend/keys/key_v1_private.pem`），绝不经过 Mac、绝不进 GitHub。
4. **CVM 无 GitHub SSH key**（PB denied），所以 CVM 自己 push 不了——这是刻意的安全设计，不要给 CVM 配 GitHub key（会让 workbuddy 借同一 CVM 拿到 push 你所有仓库的能力）。
5. JWT 签名密钥在 `cloud_keys` docker 卷；DB 口令在 `/opt/cloud-secrets/.env`（均在 CVM，不在本仓）。

---

## 四、改码与部署纪律（2026-10-07 用户拍板：cloud / heartbeat / mfg 三线全归 codebuddy）

- **唯一改码入口是本仓**：cloud / heartbeat 的任何改动只在本仓（Mac 侧）改 → 提交 → rsync 到 CVM → CVM 上 `docker compose` 重建。CVM SSH key 仅 Mac 持有。
- **⛔ 禁止在 CVM 上直接改码**：2026-10-07 取证发现 `/opt/cloud-idp` 上有 **5 个前端文件 + 3 个组件是直接在服务器写的、从未入库**——包含运营端 License 工单流（`/platform/tickets`、审批、财务确认、续期、实例列表）的完整功能。这些改动会被下一次 rsync 覆盖或删除，只能靠人工取证捞回。**这就是本仓必须存在的根本原因。**
- CVM 上的 `~/.ssh/config` 虽有 `github-mfg` 别名，但**只服务 mfg 仓**，不要用于 cloud/heartbeat；cloud/heartbeat 走 Mac 枢纽 rsync（方案 A）。
- 任何涉及 `keys/`、`cloud-idp_cloud_keys` 卷、`cloud_local.db`、`.env` 的操作都不要 commit。
- 部署生效步骤（CVM）：`cd /opt/cloud-idp && docker compose up -d --build backend`；**部署前必须先跑 `deploy/runbook.md` 的 dry-run 校验**。

---

## 五、仓库结构

> 📌 布局与线上 `/opt/cloud-idp` **完全一致**（`backend/` 为构建上下文，compose `build: ./backend`），因此 rsync 是**纯覆盖**、无需改服务器任何配置。这是 2026-10-07 布局对齐的目的。

```
backend/            # ← 构建上下文（compose: build ./backend）
  app/              # FastAPI 路由：auth / user / platform / public_key / deps
    core/           # jwt_service / rsa_key_manager / security / database
    models/         # SQLAlchemy 模型（含 InstanceHeartbeat 心跳、LicenseTicket 工单流）
    schemas/        # Pydantic 模型
    services/       # 业务逻辑（auth / user / platform service）
    main.py         # 应用入口
    config.py
    seed_platform.py
  tests/            # pytest（从 backend/ 目录跑：`pytest tests/`）
  test_keys/        # 仅公钥 key_v1_public.pem（测试夹具；私钥永不入库）
  Dockerfile
  requirements.txt
frontend/          # Vue3 运营控制台（登录页、租户、工单、财务、私有实例）
  src/views/       # Dashboard / TenantView / AdminConsole 等
  src/components/  # AuthLayout / SparkLine / tickets/ / ops/
heartbeat/         # A 心跳服务端（私有部署在线监控，SQLite + admin/RBAC/审计）
deploy/            # deploy.sh、nginx conf、runbook.md（部署 SOP 在此）
qa/                # Playwright 验证脚本（verify_cloud_console / stage2）
docker-compose.yml
产品规划/           # 运营平台 Stage2 规划
质量保障纪律.md
reset_super_admin_password.py   # 灾备：直改 platform_users 密码哈希（默认不执行）
.gitignore
```

## 六、私有化实例心跳（监控）⚠️ 两套并存，尚未归一

| 服务端 | 端点 | 存储 | 状态 |
|---|---|---|---|
| **B（cloud 侧）** | `POST /api/v1/platform/heartbeat`（实例用 `license_key` RS256 JWT 自证） | PG `instance_heartbeats` | 在用（`ecms-dna`） |
| **A（独立服务）** | `POST https://heartbeat.ziwi.cn/api/v1/heartbeat`（`X-Api-Key`） | SQLite + admin 后台 | 在用（mfg SDK、school 客户端） |

- 运营端查看私有实例在线：`GET /api/v1/platform/instances/heartbeats`。
- **A 的源码在本仓 `heartbeat/`**；其部署与 cloud 分离（`/opt/heartbeat`，端口 8091）。
- 两套并存成因与归一方案见 `ziwi-integration-contracts/contracts/mfg接入cloud接口契约.md` §D.4 与 §0.1.1（**注意：文档中若写 `POST /api/v1/heartbeat` 指 cloud 侧，实际路径带 `/platform` 前缀**）。

---

## 七、站点基础信息（合规 · 全局真相源）

> 以下为**单一真相源**：所有前端页脚、设计稿、部署文案中的同类标识，**必须引用此处值，禁止凭记忆手写**（曾因手敲把"渝"误作"蜀"、号码尾段漏位，已修正）。

| 项 | 值 |
|----|----|
| 品牌 | 知微 / 知微云（ziwi） |
| 主域名 | `cloud.ziwi.cn`（统一身份与租户管理 IdP） |
| ICP 备案号 | **渝ICP备2026009247号** |
| 备案主体属地 | 重庆（渝） |

**关联说明**：知微 AI 教学助手（`school.ziwi.cn`）与本站共用同一 ICP 备案主体，备案号同为 `渝ICP备2026009247号`。前端 `TeacherDashboard` 等页脚若展示备案号，须与该值一致。
