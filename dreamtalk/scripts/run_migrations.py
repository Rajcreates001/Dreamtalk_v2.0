"""
DreamTalk — Database Migration Runner
Applies schema changes in order.
Usage: python scripts/run_migrations.py
"""
import os
import sys
import glob
import psycopg2
from datetime import datetime


def get_connection():
    """Connect to PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "changeme"),
        dbname=os.getenv("DB_NAME", "dream_talk_db"),
    )


def ensure_migrations_table(conn):
    """Create the migrations tracking table."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()


def get_applied_migrations(conn):
    """Get list of already applied migrations."""
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM _migrations ORDER BY id")
        return {row[0] for row in cur.fetchall()}


def apply_migration(conn, filepath, applied):
    """Apply a single migration file."""
    name = os.path.basename(filepath)
    if name in applied:
        print(f"  ⏭️  {name} (already applied)")
        return False

    print(f"  🔄 Applying {name}...")
    with conn.cursor() as cur:
        with open(filepath, "r") as f:
            sql = f.read()
        cur.execute(sql)
        cur.execute("INSERT INTO _migrations (name) VALUES (%s)", (name,))
        conn.commit()

    print(f"  ✅ {name} applied")
    return True


def main():
    print("=" * 50)
    print("  DreamTalk — Database Migration Runner")
    print("=" * 50)

    # Find migration files
    migration_dirs = [
        "dreamtalk/backend/db/migrations",
        "dreamtalk/backend/db",
    ]
    
    migration_files = []
    for d in migration_dirs:
        pattern = os.path.join(d, "*.sql")
        migration_files.extend(glob.glob(pattern))
    
    # Sort by name (timestamp-based naming)
    migration_files.sort()
    
    if not migration_files:
        print("\n⚠️  No migration files found.")
        print("Looking for .sql files in:")
        for d in migration_dirs:
            print(f"  - {d}")
        return

    print(f"\nFound {len(migration_files)} migration files:")
    for f in migration_files:
        print(f"  - {os.path.basename(f)}")

    try:
        conn = get_connection()
        print(f"\nConnected to database at {conn.info.host}:{conn.info.port}/{conn.info.dbname}")
    except Exception as e:
        print(f"\n❌ Failed to connect to database: {e}")
        print("Make sure PostgreSQL is running and DB_PASSWORD is set correctly.")
        sys.exit(1)

    try:
        ensure_migrations_table(conn)
        applied = get_applied_migrations(conn)
        print(f"Already applied: {len(applied)} migrations\n")

        applied_count = 0
        for filepath in migration_files:
            if apply_migration(conn, filepath, applied):
                applied_count += 1

        print(f"\n{'=' * 50}")
        if applied_count > 0:
            print(f"  ✅ {applied_count} migration(s) applied successfully")
        else:
            print("  ✅ All migrations already applied")
        print("=" * 50)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
