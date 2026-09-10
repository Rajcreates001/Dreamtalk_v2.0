"""Check DB-backend connection by running a full end-to-end test."""
import asyncio
import asyncpg
import os


async def check_connection():
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "dream_talk_db")

    print(f"Connecting to PostgreSQL at {host}:{port}/{database} as {user}...")

    try:
        conn = await asyncpg.connect(
            host=host, port=port, user=user, password=password, database=database
        )

        # Test basic connectivity
        version = await conn.fetchval("SELECT version()")
        print(f"  Connected OK. PostgreSQL version: {version[:50]}...")

        # Count all tables
        tables = await conn.fetch(
            "SELECT table_name, (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name AND table_schema = 'public') as cols "
            "FROM information_schema.tables t "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        )
        print(f"\n  Tables ({len(tables)}):")
        for t in tables:
            row_count = await conn.fetchval(f'SELECT COUNT(*) FROM "{t["table_name"]}"')
            print(f"    {t['table_name']:30s} {t['cols']:2d} cols, {row_count} rows")

        # Test auth flow: create a test user
        test_email = "test@dreamtalk.ai"
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", test_email)
        if not existing:
            import uuid, hashlib, os as os2
            uid = str(uuid.uuid4())
            salt = os2.urandom(32)
            pw = "test1234"
            key = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100000)
            pw_hash = salt.hex() + ":" + key.hex()
            await conn.execute(
                "INSERT INTO users (id, email, password_hash, full_name, role) VALUES ($1,$2,$3,$4,$5)",
                uid, test_email, pw_hash, "Test User", "personal",
            )
            await conn.execute(
                "INSERT INTO subscriptions (id, user_id, tier, status, current_period_start, current_period_end) "
                "VALUES ($1,$2,'free','active',NOW(),NOW()+ INTERVAL '100 years')",
                str(uuid.uuid4()), uid,
            )
            await conn.execute(
                "INSERT INTO user_settings (id, user_id) VALUES ($1,$2)",
                str(uuid.uuid4()), uid,
            )
            print(f"\n  Created test user: {test_email}")
        else:
            print(f"\n  Test user already exists: {test_email}")

        # Run a quick health query
        await conn.execute("SELECT 1")
        print("  Health check: OK")

        await conn.close()
        print("\nDatabase connection test: PASSED")
        return True
    except Exception as e:
        print(f"\nDatabase connection test: FAILED - {e}")
        return False


asyncio.run(check_connection())
