"""
Creates one demo account per role, including the first admin.

This is the ONLY way an admin account gets created without already
having an admin token — it writes directly to the database, bypassing
the API entirely, which is intentional: POST /api/auth/register now
requires an authenticated admin, so something has to plant the first
one. Run this once per fresh database.

Run from backend/ (after init_postgres has created the tables):
    python -m scripts.seed_users

CHANGE THESE PASSWORDS before this ever touches anything but a local demo.
"""
import asyncio

from sqlalchemy import select

from app.auth.security import hash_password
from app.database.postgres import AsyncSessionLocal, init_postgres
from app.models.user import ROLE_ID_PREFIX, User, UserRole
from app.utils.id_generator import next_sequential_id

DEMO_USERS = [
    {"email": "admin@medgraph.demo", "password": "admin12345", "full_name": "System Admin", "role": UserRole.admin},
    {"email": "doctor@medgraph.demo", "password": "doctor12345", "full_name": "Dr. Alex Chen", "role": UserRole.doctor},
    {"email": "reception@medgraph.demo", "password": "reception12345", "full_name": "Sam Reyes", "role": UserRole.receptionist},
    {"email": "lab@medgraph.demo", "password": "lab12345", "full_name": "Priya Nair", "role": UserRole.lab},
]


async def seed():
    await init_postgres()

    async with AsyncSessionLocal() as db:
        for u in DEMO_USERS:
            existing = await db.scalar(select(User).where(User.email == u["email"]))
            if existing:
                print(f"Skipping {u['email']} — already exists.")
                continue
            staff_id = await next_sequential_id(
                db, counter_name=f"staff_{u['role'].value}", prefix=ROLE_ID_PREFIX[u["role"]]
            )
            db.add(
                User(
                    staff_id=staff_id,
                    email=u["email"],
                    hashed_password=hash_password(u["password"]),
                    full_name=u["full_name"],
                    role=u["role"],
                )
            )
            print(f"Created {u['role'].value} ({staff_id}): {u['email']} / {u['password']}")
        await db.commit()

    print("Done. Log in with any of the accounts above.")


if __name__ == "__main__":
    asyncio.run(seed())