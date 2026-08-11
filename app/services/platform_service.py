"""Platform operations service: users, licenses, tickets."""

import uuid
import secrets
import string
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import PlatformUser, BusinessLine, LicenseTicket, InstanceHeartbeat
from app.models.user import User
from app.models.token import RefreshTokenRecord
from app.core.security import hash_password, verify_password

# 北京时间偏移（中国全年 UTC+8，无夏令时），用于运营看板按本地时分桶
CN_OFFSET = timedelta(hours=8)


def _cn_date(dt: Optional[datetime]):
    if not dt:
        return None
    return (dt + CN_OFFSET).date()


def _cn_hour(dt: Optional[datetime]):
    if not dt:
        return None
    return (dt + CN_OFFSET).hour


async def get_platform_stats(db: AsyncSession) -> dict:
    """聚合超管看板全部运营数据（单次多查询，前端一次取用，避免 N+1）。"""
    now = datetime.now(timezone.utc)
    today = (now + CN_OFFSET).date()
    d30_ago = today - timedelta(days=29)

    # ---- 基础计数 ----
    tenant_total = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    tenant_active = (
        await db.execute(select(func.count()).select_from(User).where(User.is_active == True))
    ).scalar() or 0
    platform_total = (await db.execute(select(func.count()).select_from(PlatformUser))).scalar() or 0
    bl_total = (
        await db.execute(select(func.count()).select_from(BusinessLine).where(BusinessLine.is_active == True))
    ).scalar() or 0
    active_sessions = (
        await db.execute(select(func.count()).select_from(RefreshTokenRecord).where(RefreshTokenRecord.status == "active"))
    ).scalar() or 0
    open_tickets = (
        await db.execute(
            select(func.count()).select_from(LicenseTicket).where(LicenseTicket.status.in_(["pending", "paid"]))
        )
    ).scalar() or 0

    # ---- 行级数据（用于趋势分桶）----
    user_rows = (
        await db.execute(select(User.created_at, User.is_active, User.products))
    ).all()
    pu_rows = (
        await db.execute(select(PlatformUser.role, PlatformUser.is_active))
    ).all()
    tk_rows = (
        await db.execute(
            select(
                LicenseTicket.id,
                LicenseTicket.tenant_name,
                LicenseTicket.product,
                LicenseTicket.ticket_type,
                LicenseTicket.status,
                LicenseTicket.created_at,
                LicenseTicket.approved_at,
                LicenseTicket.requested_expires_at,
            )
        )
    ).all()

    # ---- 用户增长（近 30 天按日）----
    user_growth = defaultdict(int)
    for r in user_rows:
        d = _cn_date(r.created_at)
        if d and d30_ago <= d <= today:
            user_growth[d] += 1

    # ---- 平台账号按角色 ----
    platform_by_role = defaultdict(int)
    platform_active = 0
    for r in pu_rows:
        platform_by_role[r.role] += 1
        if r.is_active:
            platform_active += 1

    # ---- 业务线用户分布（products 为 JSON 数组）----
    by_product = defaultdict(int)
    for r in user_rows:
        prods = r.products or []
        for p in prods:
            by_product[p] += 1

    # ---- 全量工单统计 ----
    ticket_total = len(tk_rows)
    ticket_by_status = defaultdict(int)
    ticket_by_type = defaultdict(int)
    ticket_by_product = defaultdict(int)
    ticket_trend = defaultdict(int)
    for r in tk_rows:
        ticket_by_status[r.status] += 1
        ticket_by_type[r.ticket_type] += 1
        ticket_by_product[r.product] += 1
        d = _cn_date(r.created_at)
        if d and d30_ago <= d <= today:
            ticket_trend[d] += 1

    # ---- Token 购销：实时 + 分时 ----
    buy_today = 0
    sell_today = 0
    pending = 0
    active_licenses = 0
    trade_by_hour = {h: {"buy": 0, "sell": 0} for h in range(24)}
    trade_by_day = defaultdict(lambda: {"buy": 0, "sell": 0})
    expiring = []
    for r in tk_rows:
        # 购 = created_at
        cd = _cn_date(r.created_at)
        ch = _cn_hour(r.created_at)
        if cd == today:
            buy_today += 1
            if ch is not None:
                trade_by_hour[ch]["buy"] += 1
        if cd and d30_ago <= cd <= today:
            trade_by_day[cd]["buy"] += 1
        # 销 = approved_at
        if r.approved_at:
            ad = _cn_date(r.approved_at)
            ah = _cn_hour(r.approved_at)
            if ad == today:
                sell_today += 1
                if ah is not None:
                    trade_by_hour[ah]["sell"] += 1
            if ad and d30_ago <= ad <= today:
                trade_by_day[ad]["sell"] += 1
        # 待处理
        if r.status in ("pending", "paid"):
            pending += 1
        # 有效授权（已通过/已完成 且未过期）
        if r.status in ("approved", "completed") and r.requested_expires_at and r.requested_expires_at > now:
            active_licenses += 1
        # 临期提醒（未来 90 天内）
        if r.requested_expires_at and now < r.requested_expires_at <= now + timedelta(days=90):
            days_left = (r.requested_expires_at - now).days
            expiring.append({
                "id": str(r.id),
                "tenant_name": r.tenant_name,
                "product": r.product,
                "expires_at": r.requested_expires_at.isoformat(),
                "days_left": days_left,
            })
    expiring.sort(key=lambda x: x["days_left"])

    # ---- 组装 ----
    def fill_range(bucket: dict):
        out = []
        for i in range(30):
            d = d30_ago + timedelta(days=i)
            out.append({"date": d.isoformat(), "count": bucket.get(d, 0)})
        return out

    return {
        "kpi": {
            "tenant_users": tenant_total,
            "tenant_active": tenant_active,
            "platform_users": platform_total,
            "platform_active": platform_active,
            "business_lines": bl_total,
            "active_sessions": active_sessions,
            "open_tickets": open_tickets,
        },
        "user_growth": {
            "7d": fill_range(user_growth)[23:],
            "30d": fill_range(user_growth),
        },
        "by_product": [{"product": k, "count": v} for k, v in sorted(by_product.items(), key=lambda x: -x[1])],
        "activity": {
            "active": tenant_active,
            "inactive": tenant_total - tenant_active,
        },
        "platform_by_role": dict(platform_by_role),
        "tickets": {
            "total": ticket_total,
            "by_status": dict(ticket_by_status),
            "by_type": dict(ticket_by_type),
            "by_product": [{"product": k, "count": v} for k, v in sorted(ticket_by_product.items(), key=lambda x: -x[1])],
            "trend": {
                "7d": fill_range(ticket_trend)[23:],
                "30d": fill_range(ticket_trend),
            },
        },
        "token_trade": {
            "realtime": {
                "buy_today": buy_today,
                "sell_today": sell_today,
                "pending": pending,
                "active_licenses": active_licenses,
            },
            "by_hour": [{"hour": f"{h:02d}", **trade_by_hour[h]} for h in range(24)],
            "by_day": [
                {"date": (d30_ago + timedelta(days=i)).isoformat(),
                 **trade_by_day.get(d30_ago + timedelta(days=i), {"buy": 0, "sell": 0})}
                for i in range(30)
            ],
        },
        "expiring": expiring[:20],
        "login_trend": {"7d": [], "30d": []},  # P2：需 auth_events 表，本期占位
        "security": {"replay_7d": 0, "revoked_7d": 0},  # P2：精确审计，本期占位
        "generated_at": now.isoformat(),
    }


# ============================================================
# Platform User
# ============================================================

async def create_platform_user(db: AsyncSession, data: dict) -> PlatformUser:
    user = PlatformUser(
        email=data["email"],
        password_hash=hash_password(data["password"]),
        display_name=data["display_name"],
        role=data["role"],
        phone=data.get("phone"),
        business_lines=data.get("business_lines", []),
        region=data.get("region"),
        region_province=data.get("region_province"),
        region_city=data.get("region_city"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_platform_user(db: AsyncSession, user_id: str) -> Optional[PlatformUser]:
    result = await db.execute(
        select(PlatformUser).where(PlatformUser.id == uuid.UUID(user_id))
    )
    return result.scalar_one_or_none()


async def get_platform_user_by_email(db: AsyncSession, email: str) -> Optional[PlatformUser]:
    result = await db.execute(
        select(PlatformUser).where(PlatformUser.email == email)
    )
    return result.scalar_one_or_none()


async def list_platform_users(
    db: AsyncSession, role: Optional[str] = None, active_only: bool = True
) -> list[PlatformUser]:
    query = select(PlatformUser)
    if role:
        query = query.where(PlatformUser.role == role)
    if active_only:
        query = query.where(PlatformUser.is_active == True)
    query = query.order_by(PlatformUser.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_platform_user(
    db: AsyncSession, user_id: str, data: dict
) -> Optional[PlatformUser]:
    user = await get_platform_user(db, user_id)
    if not user:
        return None
    for key, value in data.items():
        if value is not None and hasattr(user, key):
            setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_platform_user(
    db: AsyncSession, email: str, password: str
) -> Optional[PlatformUser]:
    user = await get_platform_user_by_email(db, email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def generate_platform_token(user: PlatformUser) -> str:
    """签发平台用户的 JWT（复用 cloud RS256，含 account_type / roles / env 供前端路由与多环境鉴权）"""
    from app.main import jwt_service  # 延迟导入避免循环依赖
    from app.config import settings
    return jwt_service.create_access_token(
        sub=str(user.id),
        email=user.email,
        tenant_id=None,
        products=[f"platform:{user.role}"],
        account_type="platform",
        roles=[user.role],
        env=settings.env,
    )


# ============================================================
# Business Line
# ============================================================

async def create_business_line(db: AsyncSession, data: dict) -> BusinessLine:
    bl = BusinessLine(
        id=data["id"],
        name=data["name"],
        description=data.get("description"),
        sort_order=data.get("sort_order", 0),
    )
    db.add(bl)
    await db.commit()
    await db.refresh(bl)
    return bl


async def list_business_lines(db: AsyncSession) -> list[BusinessLine]:
    result = await db.execute(
        select(BusinessLine).where(BusinessLine.is_active == True)
        .order_by(BusinessLine.sort_order)
    )
    return list(result.scalars().all())


# ============================================================
# License Ticket
# ============================================================

def _generate_ticket_no() -> str:
    """生成工单号: LIC-YYYYMM-XXXX"""
    now = datetime.now()
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"LIC-{now.strftime('%Y%m')}-{suffix}"


def _ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite 存回的 datetime 为 naive，统一补 UTC tz 以便安全比较。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def create_license_ticket(db: AsyncSession, data: dict) -> LicenseTicket:
    ticket = LicenseTicket(
        ticket_no=_generate_ticket_no(),
        tenant_id=data["tenant_id"],
        tenant_name=data["tenant_name"],
        product=data.get("product", "school"),
        ticket_type=data["ticket_type"],
        current_expires_at=data.get("current_expires_at"),
        requested_issued_at=data.get("requested_issued_at"),
        requested_expires_at=data["requested_expires_at"],
        requested_status=data.get("requested_status", "active"),
        tier=data.get("tier"),
        seats=data.get("seats"),
        deploy_mode=data.get("deploy_mode", "saas"),
        remarks=data.get("remarks"),
        applicant_id=(
            uuid.UUID(data["applicant_id"]) if data.get("applicant_id") else None
        ),
        assignee_id=(
            uuid.UUID(data["assignee_id"]) if data.get("assignee_id") else None
        ),
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def list_license_tickets(
    db: AsyncSession,
    status: Optional[str] = None,
    tenant_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
) -> list[LicenseTicket]:
    query = select(LicenseTicket)
    if status:
        query = query.where(LicenseTicket.status == status)
    if tenant_id:
        query = query.where(LicenseTicket.tenant_id == tenant_id)
    if assignee_id:
        query = query.where(LicenseTicket.assignee_id == uuid.UUID(assignee_id))
    query = query.order_by(LicenseTicket.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def approve_license_ticket(
    db: AsyncSession, ticket_id: str, approver_id: str, remarks: Optional[str] = None
) -> Optional[LicenseTicket]:
    result = await db.execute(
        select(LicenseTicket).where(LicenseTicket.id == uuid.UUID(ticket_id))
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        return None
    now = datetime.now(timezone.utc)
    ticket.status = "approved"
    ticket.approver_id = uuid.UUID(approver_id)
    ticket.approved_at = now
    if remarks:
        ticket.remarks = (ticket.remarks or "") + f"\n[审批] {remarks}"
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_license_ticket(db: AsyncSession, ticket_id: str) -> Optional[LicenseTicket]:
    result = await db.execute(
        select(LicenseTicket).where(LicenseTicket.id == uuid.UUID(ticket_id))
    )
    return result.scalar_one_or_none()


async def renew_license(
    db: AsyncSession,
    tenant_id: str,
    product: str,
    new_expires_at: datetime,
    operator_id: str,
    remarks: Optional[str] = None,
) -> Optional[LicenseTicket]:
    """License 续期（技术方案 v1.2 §0.5.2：订阅续期制，私有化/SaaS 客户通用）。

    以该租户+产品最近一张 approved/completed license 为基线，
    新建一张 ticket_type=renewal、status=approved 的工单并延长 expires_at。
    返回 None = 无可续期基线；ValueError = 参数不合法。
    """
    now = datetime.now(timezone.utc)
    new_exp = _ensure_aware(new_expires_at)
    if new_exp <= now:
        raise ValueError("续期到期时间必须晚于当前时间")

    result = await db.execute(
        select(LicenseTicket)
        .where(
            LicenseTicket.tenant_id == tenant_id,
            LicenseTicket.product == product,
            LicenseTicket.status.in_(["approved", "completed"]),
        )
        .order_by(LicenseTicket.requested_expires_at.desc())
    )
    base = result.scalars().first()
    if not base:
        return None

    base_exp = _ensure_aware(base.requested_expires_at)
    if base_exp > now and new_exp <= base_exp:
        raise ValueError("续期到期时间必须晚于现有 license 到期时间")

    op_uuid = uuid.UUID(operator_id)
    ticket = LicenseTicket(
        ticket_no=_generate_ticket_no(),
        tenant_id=base.tenant_id,
        tenant_name=base.tenant_name,
        product=base.product,
        ticket_type="renewal",
        current_expires_at=base.requested_expires_at,
        requested_issued_at=now,
        requested_expires_at=new_expires_at,
        requested_status="active",
        tier=base.tier,
        seats=base.seats,
        deploy_mode=base.deploy_mode,
        status="approved",
        applicant_id=op_uuid,
        approver_id=op_uuid,
        approved_at=now,
        remarks=(f"[续期] 基线工单 {base.ticket_no}" + (f"；{remarks}" if remarks else "")),
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def issue_license_key(db: AsyncSession, ticket_id: str) -> Optional[LicenseTicket]:
    """为已审批工单签发离线验签 license key（私有化实例本地用 cloud 公钥验签）。

    返回 None = 工单不存在；ValueError = 状态/有效期不满足签发条件。
    """
    ticket = await get_license_ticket(db, ticket_id)
    if not ticket:
        return None
    if ticket.status not in ("approved", "completed"):
        raise ValueError("仅已审批/已完成的工单可签发 license key")
    now = datetime.now(timezone.utc)
    exp = _ensure_aware(ticket.requested_expires_at)
    if exp <= now:
        raise ValueError("license 已过期，请先续期再签发")

    from app.main import jwt_service  # 延迟导入避免循环依赖
    claims = {
        "license_id": str(ticket.id),
        "ticket_no": ticket.ticket_no,
        "tenant_id": ticket.tenant_id,
        "tenant_name": ticket.tenant_name,
        "products": [ticket.product],
        "tier": ticket.tier,
        "seats": ticket.seats,
        "deploy_mode": ticket.deploy_mode,
    }
    ticket.license_key = jwt_service.create_license_key(claims, expires_at=exp)
    ticket.license_key_issued_at = now
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def finance_confirm_ticket(
    db: AsyncSession, ticket_id: str, confirm_by_id: str, remarks: Optional[str] = None
) -> Optional[LicenseTicket]:
    """财务确认收款：工单 pending→paid，记录确认人与时间（幂等）。"""
    ticket = await get_license_ticket(db, ticket_id)
    if not ticket:
        return None
    if ticket.status == "paid":
        return ticket  # 已确认，幂等返回
    now = datetime.now(timezone.utc)
    ticket.status = "paid"
    ticket.finance_confirm_by = uuid.UUID(confirm_by_id)
    ticket.paid_at = now
    if remarks:
        ticket.remarks = (ticket.remarks or "") + f"\n[财务确认收款] {remarks}"
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def list_private_instances(db: AsyncSession) -> list[dict]:
    """运维私有化实例清单（凭证视角）：deploy_mode='private' 且已签发 license key 的工单，
    逐一对 key 做验签自检，返回有效期/合法性/临近到期预警，并合并心跳在线状态。
    心跳由实例主动上报（POST /api/v1/platform/heartbeat），超过 HEARTBEAT_ONLINE_WINDOW 未上报视为离线。"""
    result = await db.execute(
        select(LicenseTicket).where(
            LicenseTicket.deploy_mode == "private",
            LicenseTicket.license_key.isnot(None),
        ).order_by(LicenseTicket.updated_at.desc())
    )
    tickets = list(result.scalars().all())
    from app.main import jwt_service  # 延迟导入避免循环依赖
    from app.models.platform import InstanceHeartbeat
    now = datetime.now(timezone.utc)
    hb_map = await get_heartbeat_map(db)
    online_window = HEARTBEAT_ONLINE_WINDOW
    instances: list[dict] = []
    for t in tickets:
        exp = _ensure_aware(t.requested_expires_at)
        days_left = (exp - now).days if exp else None
        valid = True
        error = None
        try:
            jwt_service.verify_license_key(t.license_key)
        except ValueError as e:
            valid = False
            error = str(e)
        # 心跳在线状态
        seen = hb_map.get(t.tenant_id, {})
        last_heartbeat_at = max(seen.values()) if seen else None
        online = False
        if last_heartbeat_at is not None:
            delta = (now - _ensure_aware(last_heartbeat_at)).total_seconds()
            online = delta <= online_window
        instances.append({
            "ticket_id": str(t.id),
            "ticket_no": t.ticket_no,
            "tenant_id": t.tenant_id,
            "tenant_name": t.tenant_name,
            "product": t.product,
            "tier": t.tier,
            "seats": t.seats,
            "license_key_hint": (t.license_key[:8] + "…") if t.license_key else None,
            "issued_at": t.license_key_issued_at.isoformat() if t.license_key_issued_at else None,
            "expires_at": exp.isoformat() if exp else None,
            "days_left": days_left,
            "valid": valid,
            "error": error,
            "warning": days_left is not None and days_left <= 30,
            "status": t.status,
            "last_heartbeat_at": last_heartbeat_at.isoformat() if last_heartbeat_at else None,
            "online": online,
            "heartbeat_domains": list(seen.keys()),
        })
    return instances


# 心跳在线判定阈值（实例超过该时长未上报视为离线）
HEARTBEAT_ONLINE_WINDOW = 600  # 秒，10 分钟


async def record_heartbeat(
    db: AsyncSession,
    *,
    license_key: str,
    instance_domain: str,
    version: Optional[str] = None,
) -> dict:
    """接收私有化实例心跳上报（通用，无需预注册）。

    实例用自身持有的 cloud 签发 license_key 自证身份，cloud RS256 验签通过后
    upsert instance_heartbeats（按 tenant_id + instance_domain）。返回结果 dict。
    """
    from app.main import jwt_service  # 延迟导入避免循环依赖
    from app.models.platform import InstanceHeartbeat  # 延迟导入避免循环依赖
    try:
        claims = jwt_service.verify_license_key(license_key)
    except ValueError as e:
        raise ValueError(f"license 验签失败: {e}")

    tenant_id = claims.get("tenant_id")
    product = claims.get("products")[0] if isinstance(claims.get("products"), list) and claims.get("products") else None
    ticket_no = claims.get("ticket_no")

    now = datetime.now(timezone.utc)
    # upsert：同 (tenant_id, instance_domain) 更新 last_seen_at，否则插入
    existing = await db.execute(
        select(InstanceHeartbeat).where(
            InstanceHeartbeat.tenant_id == tenant_id,
            InstanceHeartbeat.instance_domain == instance_domain,
        )
    )
    row = existing.scalar_one_or_none()
    if row is None:
        row = InstanceHeartbeat(
            tenant_id=tenant_id,
            instance_domain=instance_domain,
            product=product,
            version=version,
            license_ticket_no=ticket_no,
            last_seen_at=now,
        )
        db.add(row)
    else:
        row.product = product
        row.version = version
        row.license_ticket_no = ticket_no
        row.last_seen_at = now
    await db.commit()
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "instance_domain": instance_domain,
        "last_seen_at": now.isoformat(),
    }


async def get_heartbeat_map(db: AsyncSession) -> dict:
    """返回 {tenant_id: {domain: last_seen_at}} 便于实例清单合并在线状态。"""
    result = await db.execute(select(InstanceHeartbeat))
    rows = list(result.scalars().all())
    m: dict = {}
    for r in rows:
        m.setdefault(r.tenant_id, {})[r.instance_domain] = r.last_seen_at
    return m
