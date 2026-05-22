from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_sessionmaker
from app.models.tenant import Tenant
from app.models.user import User
from app.models.enums import UserStatus
import bcrypt


async def seed_user(
    *,
    email: str,
    name: str,
    password: str,
    username: str | None = None,
    tenant_name: str = "Default Tenant",
    roles: list[str] | None = None,
) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:  # type: AsyncSession
        try:
            tenant = (await db.execute(select(Tenant).where(Tenant.name == tenant_name))).scalar_one_or_none()
            if tenant is None:
                tenant = Tenant(name=tenant_name)
                db.add(tenant)
                await db.flush()

            existing = (
                await db.execute(
                    select(User).where(User.tenant_id == tenant.id, User.email == email)
                )
            ).scalar_one_or_none()
            if existing:
                print(f"User already exists: {email}")
                return

            user = User(
                tenant_id=tenant.id,
                email=email,
                username=username,
                name=name,
                status=UserStatus.ACTIVE,
                hashed_password=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                roles_json=roles or ["Editor"],
            )
            db.add(user)
            await db.flush()
            await db.commit()
            print(f"Seeded user: {email}, id={user.id}, tenant_id={tenant.id}")
        except Exception:
            await db.rollback()
            raise


def main() -> None:
    asyncio.run(
        seed_user(
            email="qa@example.com",
            name="QA",
            username="qa",
            password="123456",
            tenant_name="t1",
            roles=["Editor"],
        )
    )


if __name__ == "__main__":
    main()
