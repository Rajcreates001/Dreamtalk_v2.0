"""Verify the database setup."""
import asyncio
import asyncpg
import os


async def verify():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "dream_talk_db"),
    )

    rows = await conn.fetch(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    )
    print("=== Database Tables ===")
    for r in rows:
        cnt = await conn.fetchval(f'SELECT COUNT(*) FROM "{r["table_name"]}"')
        print(f"  {r['table_name']}: {cnt} rows")

    seed = await conn.fetchval("SELECT COUNT(*) FROM digital_humans")
    print(f"\nPre-built digital humans seeded: {seed}")

    await conn.close()


asyncio.run(verify())
