"""
Run once to create all tables and seed the first Network Engineer login.
Usage: python -m app.bootstrap_db  [--username admin --password ChangeMe123!]
"""
import argparse
import sys

from sqlalchemy import text

from app.core.security import hash_password
from app.database.base import Base
from app.database.connection import engine, SessionLocal
from app import models  # noqa: F401  (imports all models so Base.metadata knows them)
from app.models.system_user import SystemUser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default=None)
    parser.add_argument("--full-name", default="Network Engineer")
    args = parser.parse_args()

    print("Creating schema + tables (network.*) ...")
    # All models live in the "network" Postgres schema. On a brand-new database
    # only "public" exists by default, so create_all() below fails with
    # "no schema has been selected" unless we create it first.
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS network"))
    Base.metadata.create_all(bind=engine)

    # create_all() only creates missing TABLES, not missing COLUMNS on an
    # already-existing table. Adding a column to a model (e.g. new profile/
    # preference fields on SystemUser) needs an explicit, idempotent ALTER
    # for anyone re-running this against a database that predates the change.
    _NEW_SYSTEM_USER_COLUMNS = [
        ("email", "VARCHAR(255)"),
        ("department", "VARCHAR(150)"),
        ("organization", "VARCHAR(150)"),
        ("last_login_at", "TIMESTAMPTZ"),
        ("notify_anomaly_alerts", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("notify_system", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("timezone", "VARCHAR(64) NOT NULL DEFAULT 'Africa/Dar_es_Salaam'"),
        ("dashboard_default_range_days", "INTEGER NOT NULL DEFAULT 14"),
        ("dashboard_refresh_interval_seconds", "INTEGER NOT NULL DEFAULT 0"),
    ]
    with engine.begin() as conn:
        for col_name, col_def in _NEW_SYSTEM_USER_COLUMNS:
            conn.execute(text(
                f"ALTER TABLE network.system_users ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
            ))
    print("Tables ready.")

    if args.password is None:
        print("No --password given: skipping user seed. Re-run with --password to create a login.")
        return

    db = SessionLocal()
    try:
        existing = db.query(SystemUser).filter_by(username=args.username).one_or_none()
        if existing:
            print(f"User '{args.username}' already exists — leaving it as is.")
            return
        user = SystemUser(
            username=args.username,
            password_hash=hash_password(args.password),
            full_name=args.full_name,
            role="network_engineer",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created user '{args.username}'.")
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
