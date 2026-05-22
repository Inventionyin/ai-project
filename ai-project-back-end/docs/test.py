import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect(
            user='postgres',
            password='123456',
            database='ai_test_platform',
            host='localhost',
            port=5432
        )
        print("✅ 连接成功")
        await conn.close()
    except Exception as e:
        print(f"❌ 连接失败: {e}")

asyncio.run(main())