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

## 四、workbuddy 团队须知

- 你们可以**在 CVM 上直接改码并 `git commit`（本地）**，但**不要试图在 CVM 上 `git push`**（无 key，会失败）。
- 需要进 GitHub 时，把改动留在 CVM 本地 commit，由 **Mac/codebuddy 负责 rsync + push**（唯一有 GitHub key 的枢纽）。
- 任何涉及 `keys/`、`cloud_local.db`、`.env` 的操作都不要 commit。
- 部署生效步骤（在 CVM）：`cd /opt/cloud-idp && docker compose up -d --build backend`（需 Mac 侧协助或你方已在 CVM 有权限时）。

---

## 五、仓库结构

```
app/
  api/        # FastAPI 路由：auth / user / platform / public_key / deps
  core/       # jwt_service / rsa_key_manager / security / database
  models/     # SQLAlchemy 模型（含 InstanceHeartbeat 心跳）
  schemas/    # Pydantic 模型
  services/   # 业务逻辑（auth_service / user_service / platform_service）
  main.py     # 应用入口
  config.py
  seed_platform.py
tests/        # pytest
test_keys/    # 仅公钥 key_v1_public.pem（测试夹具）
Dockerfile
requirements.txt
.gitignore
```

## 六、私有化实例心跳（监控）

cloud 端已实现 `POST /api/v1/heartbeat`（实例用 license_key 自证身份上报）与 `GET /api/v1/instances/heartbeats`（平台角色查看在线状态）。详见对话历史：私有化实例（如 ecms-dna）上报心跳 → cloud 验签 → 标记 online（≤600s 内有心跳）。
