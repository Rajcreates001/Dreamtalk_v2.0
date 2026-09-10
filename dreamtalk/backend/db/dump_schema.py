"""Dump complete database schema to schema.db file."""
import asyncio
import asyncpg
import os
from datetime import datetime

OUTPUT = r"D:\Black folder\DreamTalk_Startup\Dreamtalk-Integrated\dreamtalk\backend\db\schema.db"


async def dump_schema():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "dream_talk_db"),
    )

    lines = []
    version = await conn.fetchval("SELECT version()")
    lines.append("-- Dreamtalk Database Schema Dump")
    lines.append(f"-- Generated: {datetime.now()}")
    lines.append(f"-- {version}")
    lines.append("")

    tables = await conn.fetch(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE' "
        "ORDER BY table_name"
    )

    for t in tables:
        tn = t["table_name"]
        lines.append(f"-- ============================================")
        lines.append(f"-- Table: {tn}")
        lines.append(f"-- ============================================")
        lines.append(f"CREATE TABLE {tn} (")

        cols = await conn.fetch(
            "SELECT column_name, data_type, is_nullable, "
            "column_default, character_maximum_length "
            "FROM information_schema.columns "
            "WHERE table_name=$1 AND table_schema='public' "
            "ORDER BY ordinal_position",
            tn,
        )

        col_defs = []
        for c in cols:
            nullable = "NOT NULL" if c["is_nullable"] == "NO" else "NULL"
            default = f" DEFAULT {c['column_default']}" if c["column_default"] else ""
            col_type = c["data_type"]
            if c["character_maximum_length"]:
                col_type += f"({c['character_maximum_length']})"
            col_defs.append(f"    {c['column_name']} {col_type} {nullable}{default}")

        lines.append(",\n".join(col_defs))
        lines.append(");\n")

        indexes = await conn.fetch(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename=$1 AND schemaname='public' "
            "ORDER BY indexname",
            tn,
        )
        for idx in indexes:
            lines.append(f"-- {idx['indexdef']}")
        lines.append("")

    # Seed data
    lines.append("-- ============================================")
    lines.append("-- Seed Data: digital_humans")
    lines.append("-- ============================================")
    rows = await conn.fetch(
        "SELECT name, description, category, popularity "
        "FROM digital_humans ORDER BY popularity DESC"
    )
    for r in rows:
        lines.append(f"--   {r['name']:25s} | {r['category']:15s} | pop={r['popularity']}")

    lines.append("")
    lines.append(f"-- Total tables: {len(tables)}")
    lines.append(f"-- Total seed rows: {len(rows)}")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Schema dumped to {OUTPUT}")
    print(f"  Tables: {len(tables)}")
    print(f"  Seed digital humans: {len(rows)}")
    await conn.close()


asyncio.run(dump_schema())
