"""Initial schema: users, schedules, settings

Revision ID: 0001
Revises:
Create Date: 2026-05-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("user_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("phone", sa.String(20), nullable=True, unique=True),
        sa.Column("pib", sa.String(255), nullable=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("role", sa.String(10), server_default="staff", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_pib", "users", ["pib"])

    # ── schedules ────────────────────────────────────────────────────────────
    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pib", sa.String(255), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("day_name", sa.String(20), nullable=False),
    )
    op.create_unique_constraint("uq_schedule_pib_date", "schedules", ["pib", "work_date"])
    op.create_index("ix_schedule_pib", "schedules", ["pib"])
    op.create_index("ix_schedule_work_date", "schedules", ["work_date"])

    # ── settings ─────────────────────────────────────────────────────────────
    op.create_table(
        "settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
    )

    # Початкові значення налаштувань
    op.execute(
        "INSERT INTO settings (key, value) VALUES "
        "('forbidden_words', '[]'), "
        "('url_whitelist', '[\"t.me\", \"telegram.org\", \"youtube.com\", \"youtu.be\"')"
        " ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_index("ix_schedule_work_date", table_name="schedules")
    op.drop_index("ix_schedule_pib", table_name="schedules")
    op.drop_constraint("uq_schedule_pib_date", "schedules", type_="unique")
    op.drop_table("schedules")
    op.drop_index("ix_users_pib", table_name="users")
    op.drop_table("users")
