"""
Ekodi – Create/promote admin or superadmin user.

Usage (inside Docker):
  python -m scripts.create_admin create --email admin@ekodi.ai --name Admin --password yourpass --role superadmin
  python -m scripts.create_admin promote --email user@example.com --role admin

Usage (local dev):
  python scripts/create_admin.py create --email admin@ekodi.ai --name Admin --password yourpass
"""

import argparse
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session, init_db
from app.models.user import User
from app.middleware.auth import hash_password, STAFF_ROLES
from sqlalchemy import select


async def create_admin(email: str, name: str, password: str, role: str = "superadmin"):
    """Create a new staff user or promote existing user."""
    if role not in STAFF_ROLES:
        print(f"Error: Invalid role '{role}'. Must be one of: {', '.join(STAFF_ROLES)}")
        sys.exit(1)

    await init_db()

    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            existing.role = role
            existing.is_staff = True
            existing.tier = "pro"
            existing.email_verified = True
            await db.commit()
            print(f"Updated existing user {email} to role={role}, is_staff=True")
        else:
            user = User(
                email=email,
                name=name,
                password_hash=hash_password(password),
                role=role,
                tier="pro",
                is_staff=True,
                email_verified=True,
                consent_given=True,
            )
            db.add(user)
            await db.commit()
            print(f"Created new staff user: {email} (role={role})")


async def promote_user(email: str, role: str = "admin"):
    """Promote an existing user to a staff role."""
    if role not in STAFF_ROLES:
        print(f"Error: Invalid role '{role}'. Must be one of: {', '.join(STAFF_ROLES)}")
        sys.exit(1)

    await init_db()

    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"Error: User {email} not found.")
            sys.exit(1)

        user.role = role
        user.is_staff = True
        user.tier = "pro"
        await db.commit()
        print(f"Promoted {email} to role={role}, is_staff=True")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ekodi admin management")
    sub = parser.add_subparsers(dest="command", help="Command")

    # create command
    create_cmd = sub.add_parser("create", help="Create a new staff user")
    create_cmd.add_argument("--email", required=True)
    create_cmd.add_argument("--name", required=True)
    create_cmd.add_argument("--password", required=True)
    create_cmd.add_argument("--role", default="superadmin", help="Role: superadmin, admin, support, marketing, finance, moderator, developer")

    # promote command
    promote_cmd = sub.add_parser("promote", help="Promote existing user to staff role")
    promote_cmd.add_argument("--email", required=True)
    promote_cmd.add_argument("--role", default="admin", help="Target role")

    # Default: create (for backward compat with --email --name --password at top level)
    parser.add_argument("--email", default=None)
    parser.add_argument("--name", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--role", default="superadmin")

    args = parser.parse_args()

    if args.command == "create":
        asyncio.run(create_admin(args.email, args.name, args.password, args.role))
    elif args.command == "promote":
        asyncio.run(promote_user(args.email, args.role))
    elif args.email and args.name and args.password:
        asyncio.run(create_admin(args.email, args.name, args.password, args.role))
    else:
        parser.print_help()
