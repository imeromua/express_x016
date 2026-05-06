"""Add is_working to schedules, first_name/last_name to users, xlsx settings

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-06

Що змінюється:
1. schedules  — додається колонка is_working (Boolean, DEFAULT true)
2. users      — додаються first_name, last_name (nullable)
3. settings   — додаються ключі xlsx_path, xlsx_sheet, xlsx_cell_range
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. schedules: додаємо is_working
    #    DEFAULT true — усі існуючі рядки вважаються робочими
    op.add_column(
        "schedules",
        sa.Column(
            "is_working",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # 2. users: first_name, last_name
    op.add_column(
        "users",
        sa.Column("first_name", sa.String(64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_name", sa.String(64), nullable=True),
    )

    # 3. settings: xlsx налаштування (порожні записи, поповнюються адміном)
    op.execute(
        "INSERT INTO settings (key, value) VALUES "
        "('xlsx_path', ''), "
        "('xlsx_sheet', ''), "
        "('xlsx_cell_range', '') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    # settings: видаляємо xlsx-ключі
    op.execute(
        "DELETE FROM settings "
        "WHERE key IN ('xlsx_path', 'xlsx_sheet', 'xlsx_cell_range')"
    )

    # users: видаляємо колонки
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")

    # schedules: видаляємо is_working
    op.drop_column("schedules", "is_working")
