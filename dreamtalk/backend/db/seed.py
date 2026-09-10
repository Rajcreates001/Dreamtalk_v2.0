"""Standalone seed script — run with: python seed.py"""

import asyncio
import logging
from database import get_pool, close_pool
from auto_seed import auto_seed

logging.basicConfig(level=logging.INFO)


async def main():
    pool = await get_pool()
    await auto_seed(pool)
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
