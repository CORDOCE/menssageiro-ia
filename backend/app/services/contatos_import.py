"""Importação de contatos CSV/XLSX (spec 0002, task 7).

Aplica a matriz de decisão da spec (§ "Matriz de decisão"): normaliza o telefone para E.164
canônico, valida obrigatórios, resolve consentimento (nunca auto-consente, §5.9), faz upsert por
telefone e **nunca ressuscita descadastrado** (§5.4). Persiste por linha (parcial, AC-11) e monta
um relatório com o telefone **mascarado** (AC-16). Não persiste o arquivo (dados mínimos).
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, date, datetime

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.telefone import mascarar_telefone, normalizar_e164
from app.models.contato import Contato
from app.schemas.contato import RelatorioImportacao, ResultadoLinha

# Colunas aceitas no cabeçalho; `nome` e `telefone` são obrigatórias.
_COLUNAS_OBRIGATORIAS = ("nome", "telefone")
_COLUNAS_ACEITAS = (
    "nome",
    "telefone",
    "grupo",
    "tags",
    "consentimento_origem",
    "consentimento_data",
    "observacoes",
)


class ImportacaoError(Exception):
    """Falha do arquivo inteiro (formato, decodificação, cabeçalho) — nada é persistido."""


def importar(
    conteudo: bytes, nome_arquivo: str, db: Session, max_linhas: int | None = None
) -> RelatorioImportacao:
    """Importa contatos do arquivo e devolve o relatório por linha.

    `max_linhas` é checado após o parse e antes de persistir qualquer linha — acima do limite,
    nada é gravado (AC-17).
    """
    linhas = _parse(conteudo, nome_arquivo)
    if max_linhas is not None and len(linhas) > max_linhas:
        raise ImportacaoError(f"arquivo excede o limite de {max_linhas} linhas")
    resultados: list[ResultadoLinha] = [
        _processar_linha(db, linha, numero) for numero, linha in enumerate(linhas, start=2)
    ]
    return RelatorioImportacao(
        total=len(resultados),
        criados=sum(1 for r in resultados if r.status == "criado"),
        atualizados=sum(1 for r in resultados if r.status == "atualizado"),
        ignorados=sum(1 for r in resultados if r.status == "ignorado"),
        erros=sum(1 for r in resultados if r.status == "erro"),
        linhas=resultados,
    )


# --------------------------------------------------------------------------- parsing


def _parse(conteudo: bytes, nome_arquivo: str) -> list[dict[str, str]]:
    nome = nome_arquivo.lower()
    if nome.endswith(".csv"):
        return _parse_csv(conteudo)
    if nome.endswith(".xlsx"):
        return _parse_xlsx(conteudo)
    raise ImportacaoError("formato não suportado; envie um arquivo .csv ou .xlsx")


def _validar_cabecalho(cabecalho: list[str]) -> None:
    faltando = [c for c in _COLUNAS_OBRIGATORIAS if c not in cabecalho]
    if faltando:
        aceitas = ", ".join(_COLUNAS_ACEITAS)
        raise ImportacaoError(
            f"cabeçalho inválido: faltam as colunas {faltando}. Colunas aceitas: {aceitas}"
        )


def _parse_csv(conteudo: bytes) -> list[dict[str, str]]:
    try:
        texto = conteudo.decode("utf-8-sig")  # tolera BOM do Excel
    except UnicodeDecodeError as exc:
        raise ImportacaoError("arquivo não pôde ser lido (codificação inválida); use UTF-8") from exc
    leitor = csv.DictReader(io.StringIO(texto))
    cabecalho = [(c or "").strip().lower() for c in (leitor.fieldnames or [])]
    _validar_cabecalho(cabecalho)
    return [
        {(k or "").strip().lower(): str(v or "").strip() for k, v in bruta.items() if k is not None}
        for bruta in leitor
    ]


def _parse_xlsx(conteudo: bytes) -> list[dict[str, str]]:
    try:
        wb = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl lança vários tipos para arquivo corrompido
        raise ImportacaoError("planilha .xlsx inválida ou corrompida") from exc
    try:
        ws = wb.active
        if ws is None:
            raise ImportacaoError("planilha vazia")
        linhas_iter = ws.iter_rows(values_only=True)
        try:
            cabecalho_bruto = next(linhas_iter)
        except StopIteration as exc:
            raise ImportacaoError("planilha vazia") from exc
        cabecalho = [str(c).strip().lower() if c is not None else "" for c in cabecalho_bruto]
        _validar_cabecalho(cabecalho)

        linhas: list[dict[str, str]] = []
        for valores in linhas_iter:
            if valores is None or all(v is None for v in valores):
                continue
            linha = {
                cabecalho[i]: (str(v).strip() if v is not None else "")
                for i, v in enumerate(valores)
                if i < len(cabecalho) and cabecalho[i]
            }
            linhas.append(linha)
        return linhas
    finally:
        wb.close()


# --------------------------------------------------------------------------- processamento


def _consentimento_da_linha(origem: str, data_raw: str) -> tuple[bool, date | None, str | None]:
    """Resolve o consentimento da linha. Ausente → sem opt-in (sem erro); inválido/futuro →
    sem opt-in **com** motivo informativo no relatório. Nunca auto-consente (§5.9)."""
    if not origem or not data_raw:
        return (False, None, None)
    try:
        data = date.fromisoformat(data_raw)
    except ValueError:
        return (False, None, "data de consentimento inválida; contato ficou sem consentimento")
    if data > datetime.now(UTC).date():
        return (False, None, "data de consentimento no futuro; contato ficou sem consentimento")
    return (True, data, None)


def _como_datetime(d: date | None) -> datetime | None:
    if d is None:
        return None
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _processar_linha(db: Session, linha: dict[str, str], numero: int) -> ResultadoLinha:
    nome = linha.get("nome", "").strip()
    if not nome:
        return ResultadoLinha(linha=numero, status="erro", motivo="nome é obrigatório")
    try:
        telefone = normalizar_e164(linha.get("telefone", "").strip())
    except ValueError:
        return ResultadoLinha(linha=numero, status="erro", motivo="telefone inválido")

    mascarado = mascarar_telefone(telefone)
    origem = linha.get("consentimento_origem", "").strip()
    consent_ok, consent_data, consent_motivo = _consentimento_da_linha(
        origem, linha.get("consentimento_data", "").strip()
    )
    grupo = linha.get("grupo", "").strip() or None
    observacoes = linha.get("observacoes", "").strip() or None
    tags = [t.strip() for t in linha.get("tags", "").split(";") if t.strip()]

    existente = db.execute(
        select(Contato).where(Contato.telefone_e164 == telefone)
    ).scalar_one_or_none()

    # Nunca ressuscita descadastrado (§5.4 / AC-15).
    if existente is not None and existente.descadastrado_em is not None:
        return ResultadoLinha(linha=numero, status="ignorado", telefone=mascarado, motivo="descadastrado")

    if existente is not None:
        existente.nome = nome
        existente.grupo = grupo
        existente.tags = tags
        existente.observacoes = observacoes
        # Opt-in novo só adiciona; ausência NÃO revoga o consentimento existente (matriz, linha 4).
        if consent_ok:
            existente.consentimento = True
            existente.consentimento_origem = origem
            existente.consentimento_data = _como_datetime(consent_data)
        db.commit()
        return ResultadoLinha(linha=numero, status="atualizado", telefone=mascarado, motivo=consent_motivo)

    db.add(
        Contato(
            id=str(uuid.uuid4()),
            nome=nome,
            telefone_e164=telefone,
            grupo=grupo,
            tags=tags,
            observacoes=observacoes,
            consentimento=consent_ok,
            consentimento_origem=origem if consent_ok else None,
            consentimento_data=_como_datetime(consent_data) if consent_ok else None,
        )
    )
    db.commit()
    return ResultadoLinha(linha=numero, status="criado", telefone=mascarado, motivo=consent_motivo)
