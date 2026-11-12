"""0024 anexos

Revision ID: 0cc4c21580b1
Revises: f65dbe8cffc3
Create Date: 2026-11-12 14:13:56.144608

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cc4c21580b1'
down_revision: Union[str, Sequence[str], None] = 'f65dbe8cffc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FK = "fk_agendamentos_anexo_id"


def upgrade() -> None:
    """Cria `anexos` (bytea) e `agendamentos.anexo_id` (spec 0024 / ADR 0016)."""
    op.create_table(
        "anexos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("nome_arquivo", sa.String(length=255), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("tamanho", sa.Integer(), nullable=False),
        sa.Column("conteudo", sa.LargeBinary(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("agendamentos", sa.Column("anexo_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(_FK, "agendamentos", "anexos", ["anexo_id"], ["id"])


def downgrade() -> None:
    """Remove `agendamentos.anexo_id` e `anexos`."""
    op.drop_constraint(_FK, "agendamentos", type_="foreignkey")
    op.drop_column("agendamentos", "anexo_id")
    op.drop_table("anexos")
