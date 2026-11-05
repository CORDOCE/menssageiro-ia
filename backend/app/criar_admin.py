"""Cria (ou reaproveita) o único usuário admin a partir de ADMIN_EMAIL/ADMIN_PASSWORD.

Rodar uma vez após as migrações: `python -m app.criar_admin`. Remova as variáveis depois (ver .env.example).
Idempotente: se o e-mail já existir, não faz nada.
"""

import sys
import uuid

import pyotp
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import cifrar_segredo, hash_password
from app.db.database import SessionLocal
from app.models.usuario import Usuario


def main() -> int:
    s = get_settings()
    if not s.admin_email or not s.admin_password:
        print("Defina ADMIN_EMAIL e ADMIN_PASSWORD no ambiente.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        existe = db.execute(select(Usuario).where(Usuario.email == s.admin_email)).scalar_one_or_none()
        if existe is not None:
            print(f"Admin já existe: {s.admin_email}")
            return 0
        # 2FA obrigatório (ADR 0001): provisiona um segredo TOTP no cadastro.
        totp_secret = pyotp.random_base32()
        db.add(
            Usuario(
                id=str(uuid.uuid4()),
                nome="Admin",
                email=s.admin_email,
                senha_hash=hash_password(s.admin_password),
                totp_secret=cifrar_segredo(totp_secret),  # cifrado em repouso (ADR 0011)
            )
        )
        db.commit()
        uri = pyotp.TOTP(totp_secret).provisioning_uri(name=s.admin_email, issuer_name="Mensageiro")
        print(f"Admin criado: {s.admin_email}")
        print("2FA (TOTP) — cadastre no seu app autenticador (Google Authenticator, etc.):")
        print(f"  segredo: {totp_secret}")
        print(f"  otpauth: {uri}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
