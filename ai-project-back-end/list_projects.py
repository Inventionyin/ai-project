import asyncio
import uuid
from sqlalchemy import select
from app.core.database import get_sessionmaker
from app.models.project import Project

async def main():
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        res = await db.execute(select(Project))
        projects = res.scalars().all()
        for p in projects:
            print(f"Project ID: {p.id}, Name: {p.name}")

if __name__ == "__main__":
    asyncio.run(main())
