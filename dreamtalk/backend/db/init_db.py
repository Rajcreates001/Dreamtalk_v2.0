"""
Initialize the Dreamtalk database.
Usage: python -m dreamtalk.backend.db.init_db
"""
import asyncio
import asyncpg
import os
from pathlib import Path


async def init_database():
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "dream_talk_db")

    # Connect to postgres default db first to create our database if needed
    try:
        sys_conn = await asyncpg.connect(
            host=host, port=port, user=user, password=password, database="postgres"
        )
        exists = await sys_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", database
        )
        if not exists:
            await sys_conn.execute(f'CREATE DATABASE "{database}"')
            print(f"Created database: {database}")
        else:
            print(f"Database {database} already exists")
        await sys_conn.close()
    except Exception as e:
        print(f"Warning: Could not create database: {e}")

    # Connect to our database and run schema
    conn = await asyncpg.connect(
        host=host, port=port, user=user, password=password, database=database
    )

    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        print(f"Schema file not found: {schema_path}")
        return False

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    try:
        await conn.execute(schema_sql)
        print("Schema applied successfully")
    except Exception as e:
        print(f"Error applying schema: {e}")
        return False
    finally:
        await conn.close()

    return True


def main():
    success = asyncio.run(init_database())
    if success:
        print("Database initialization complete!")
    else:
        print("Database initialization failed!")
        exit(1)


if __name__ == "__main__":
    main()
