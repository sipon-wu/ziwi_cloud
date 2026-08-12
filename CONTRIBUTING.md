# cloud.ziwi.cn 后端 协同与开发须知

> **版本**: v1.0
> **面向读者**: 在 CVM 上改 cloud 后端的开发者（codebuddy / workbuddy）
> **最后更新**: 2026-08-12
> **基线**: 本文件是 GitHub 协同仓 `ziwi-integration-contracts` 中 `contracts/mfg接入cloud接口契约.md` 的 **CVM 侧镜像**，基于 workbuddy 既有契约续写，不另起山头。

---

## 1. 归属变更（重要）

- **2026-07-27 用户拍板**：cloud（IdP）与 License / heartbeat 线的后续研发、部署由 **codebuddy（Mac 侧，持有 CVM SSH key 与 GitHub 写 key）** 接管，自 workbuddy 移回。
- **2026-08-11~12 codebuddy 完成的基础变更**：
  1. cloud 后端建**独立 GitHub 仓** `sipon-wu/ziwi_cloud`（此前游离态运行于 CVM `/opt/cloud-idp/backend`）；
  2. CVM 上 cloud 后端**接本地 git**（版本保护），GitHub 同步走**方案 A**：CVM 不直连 GitHub，经 Mac 枢纽 rsync + push；
  3. **心跳服务端已实现**：`POST /api/v1/heartbeat`（实例用 license_key 自证）+ `GET /api/v1/instances/heartbeats`（平台角色查看在线），实测 ecms-dna 上报成功。

---

## 2. Git 工作流（方案 A：CVM 不直连 GitHub）

> CVM 上 github key 为只读，误在 CVM `git push` 会报 `read only`（见 runbook G3）。push 只能从 Mac 执行。

**CVM 上改码（本地提交）：**
```bash
cd /opt/cloud-idp/backend
git add <具体文件或目录>   # 严禁 git add -A / git add .，防 keys/ 私钥入历史
git commit -m "feat: ..."
```

**同步到 GitHub（在 Mac 上执行）：**
```bash
rsync -az --delete \
  --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='keys' --exclude='cloud_local.db' --exclude='.pytest_cache' \
  root@193.112.163.147:/opt/cloud-idp/backend/ /Users/sipon/CodeBuddy/ziwi_cloud/
cd /Users/sipon/CodeBuddy/ziwi_cloud
git add <路径> && git commit -m "..." && git push origin main
```

**安全纪律（红线）：**
- 永不 `git add -A`；`.gitignore` 已挡 `keys/`、`*.pem` 私钥、`.venv`、`cloud_local.db`、`.env`。
- 仅 `test_keys/key_v1_public.pem`（公钥，无害）入库。私钥只活 CVM 本地，不经 Mac、不进 GitHub。
- workbuddy 可在 CVM 改码 + 本地 commit，但**不要在 CVM push**（无 key），进 GitHub 由 Mac 枢纽负责。

---

## 3. 心跳服务端实现（2026-08，codebuddy）

| 项 | 值 |
|---|---|
| 上报端点 | `POST /api/v1/heartbeat`（实例用 license_key 自证，cloud 验签确认 tenant） |
| 查询端点 | `GET /api/v1/instances/heartbeats`（平台角色鉴权，返回 online / last_heartbeat_at） |
| 在线判定 | ≤600s 内有心跳为 online（上报频率建议 5 分钟） |
| 数据模型 | `InstanceHeartbeat` 表（tenant_id + instance_domain 唯一约束，upsert） |
| 实测 | ecms-dna 上报成功，返回 online: true |

> 客户端 SDK 基线（D.1~D.3 HeartbeatClient）见 workbuddy 主契约 `contracts/mfg接入cloud接口契约.md`；服务端为互补闭环。

---

## 4. 关联文档（单一沟通机制）

- GitHub 协同仓：`sipon-wu/ziwi-integration-contracts`
  - `contracts/mfg接入cloud接口契约.md`（cloud 主契约，含 §D.4 服务端实现）
  - `runbooks/CVM部署通用规范与坑清单.md`（G3 坑 / 方案 A 工作流）
  - `STATUS.md`（cloud/license 行状态显形）
- CVM 侧镜像：本文件 + `deploy/runbook.md`（部署步骤）
