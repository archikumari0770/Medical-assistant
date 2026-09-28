"""
Creates all Postgres tables from the SQLAlchemy models.

Run from backend/:  python -m scripts.init_postgres
"""
import asyncio

from app.database.postgres import init_postgres
# Import models so they register on Base.metadata before create_all runs.
from app.models import id_counter, lab, patient, user  # noqa: F401


async def main():
    print("Creating Postgres tables...")
    await init_postgres()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())