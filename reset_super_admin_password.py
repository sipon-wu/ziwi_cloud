#!/usr/bin/env python3
# /opt/cloud-idp/reset_super_admin_password.py
#
# 用途：cloud 平台超级管理员忘记密码时的运维直改手段。
# 背景：cloud 后端当前无 forgot-password / SMTP 邮件重置能力，
#       唯一自助外找回方式 = 直改 platform_users.password_hash。
# 注意：本脚本默认【不执行】，仅作灾备。需运维修改密码时再调用。
#
# 用法（容器内）：
#   docker exec -i cloud-backend python - < /opt/cloud-idp/reset_super_admin_password.py <新密码> [email]
# 例：
#   docker exec -i cloud-backend python - < /opt/cloud-idp/reset_super_admin_password.py 'MyNewPwd123' fengliang@ziwi.cn
#
import asyncio
import sys

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.platform import PlatformUser
from sqlalchemy import select


async def main():
    if len(sys.argv) < 2:
        print("用法: python reset_super_admin_password.py <新密码> [email]")
        print("默认 email=fengliang@ziwi.cn")
        sys.exit(1)

    new_pwd = sys.argv[1]
    email = sys.argv[2] if len(sys.argv) > 2 else "fengliang@ziwi.cn"

    async with async_session_factory() as db:
        u = (
            await db.execute(select(PlatformUser).where(PlatformUser.email == email))
        ).scalars().first()
        if not u:
            print("NO SUCH USER:", email)
            sys.exit(1)
        u.password_hash = hash_password(new_pwd)
        await db.commit()
        print(f"PASSWORD RESET FOR {email} (role={u.role})")


if __name__ == "__main__":
    asyncio.run(main())
