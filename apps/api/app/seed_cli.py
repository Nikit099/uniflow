import asyncio

from app.db import SessionFactory
from app.seed import seed_demo


async def main() -> None:
    async with SessionFactory() as db:
        await seed_demo(db)


if __name__ == "__main__":
    asyncio.run(main())
