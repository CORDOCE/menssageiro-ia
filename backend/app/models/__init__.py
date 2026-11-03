"""Modelos SQLAlchemy. Importados aqui para registrar as tabelas em `Base.metadata`
(o autogenerate do Alembic depende disso)."""

from app.models.auditoria import Auditoria
from app.models.contato import Contato
from app.models.envio import Envio
from app.models.modelo import Modelo
from app.models.saude import Saude
from app.models.usuario import SessaoUsuario, Usuario

__all__ = ["Auditoria", "Contato", "Envio", "Modelo", "Saude", "SessaoUsuario", "Usuario"]
