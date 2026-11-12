"""0023 push_subscriptions

Revision ID: f65dbe8cffc3
Revises: 6004b696cead
Create Date: 2026-11-12 12:24:41.024047

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f65dbe8cffc3'
down_revision: Union[str, Sequence[str], None] = '6004b696cead'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria `push_subscriptions` (spec 0023 / ADR 0015): inscrições de Web Push por dispositivo."""
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(length=255), nullable=False),
        sa.Column("auth", sa.String(length=255), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )


def downgrade() -> None:
    """Remove `push_subscriptions`."""
    op.drop_table("push_subscriptions")
