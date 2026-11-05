"""cifrar totp_secret em repouso (ADR 0011)

Revision ID: c4c7ff4e9646
Revises: 4ff11dacdb87
Create Date: 2026-11-05 11:26:46.977654

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4c7ff4e9646'
down_revision: Union[str, Sequence[str], None] = '4ff11dacdb87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _linhas_com_segredo(bind: sa.engine.Connection) -> list[tuple[str, str]]:
    res = bind.execute(
        sa.text("SELECT id, totp_secret FROM usuarios WHERE totp_secret IS NOT NULL")
    ).fetchall()
    return [(r[0], r[1]) for r in res]


def upgrade() -> None:
    """Alarga a coluna e cifra os segredos existentes (ADR 0011).

    A chave `TOTP_ENC_KEY` só é exigida quando há linhas a cifrar — tabela vazia (ex.: ciclo de
    CI em banco limpo) é no-op e não precisa da chave.
    """
    op.alter_column(
        "usuarios", "totp_secret",
        existing_type=sa.String(64), type_=sa.String(255), existing_nullable=True,
    )
    bind = op.get_bind()
    linhas = _linhas_com_segredo(bind)
    if linhas:
        from app.core.security import cifrar_segredo  # import tardio: só quando há o que cifrar

        for uid, claro in linhas:
            bind.execute(
                sa.text("UPDATE usuarios SET totp_secret = :v WHERE id = :id"),
                {"v": cifrar_segredo(claro), "id": uid},
            )


def downgrade() -> None:
    """Decifra os segredos de volta ao claro e estreita a coluna. Chave exigida só se houver linhas."""
    bind = op.get_bind()
    linhas = _linhas_com_segredo(bind)
    if linhas:
        from app.core.security import decifrar_segredo

        for uid, cifra in linhas:
            bind.execute(
                sa.text("UPDATE usuarios SET totp_secret = :v WHERE id = :id"),
                {"v": decifrar_segredo(cifra), "id": uid},
            )
    op.alter_column(
        "usuarios", "totp_secret",
        existing_type=sa.String(255), type_=sa.String(64), existing_nullable=True,
    )
