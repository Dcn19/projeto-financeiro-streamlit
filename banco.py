"""Repositório PostgreSQL para contas a pagar e cadastros (N2 Etapa 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from financeiro import ErroLancamento, validar_lancamento


SCHEMA_PATH = Path(__file__).resolve().parent / "sql" / "001_schema.sql"


def conectar(url: str):
    if not url or not url.strip():
        raise ErroLancamento("Configure DATABASE_URL nos Secrets ou no .env.")
    # A URL é lida exclusivamente de configuração privada, nunca exibida na interface.
    return psycopg.connect(
        url, connect_timeout=10, row_factory=dict_row, prepare_threshold=None,
    )


def inicializar_banco(url: str) -> None:
    """Inicialização idempotente de um banco novo, sem apagar dados existentes."""
    comandos = [s.strip() for s in SCHEMA_PATH.read_text(encoding="utf-8").split(";") if s.strip()]
    with conectar(url) as conexao:
        with conexao.cursor() as cursor:
            for comando in comandos:
                cursor.execute(comando)


def _consultar_pessoa(cursor, tipo: str, documento: str) -> dict[str, Any] | None:
    cursor.execute(
        "SELECT id, tipo, razao_social, documento, status FROM pessoas "
        "WHERE tipo = %s AND documento = %s",
        (tipo, documento),
    )
    return cursor.fetchone()


def _consultar_classificacao(cursor, descricao: str) -> dict[str, Any] | None:
    cursor.execute(
        "SELECT id, tipo, descricao, status FROM classificacao "
        "WHERE tipo = 'DESPESA' AND descricao = %s",
        (descricao,),
    )
    return cursor.fetchone()


def consultar_cadastros(url: str, entrada: dict[str, Any]) -> dict[str, Any]:
    dados = validar_lancamento(entrada)
    with conectar(url) as conexao:
        with conexao.cursor() as cursor:
            fornecedor = _consultar_pessoa(cursor, "CLIENTE-FORNECEDOR", dados["fornecedor_documento"])
            faturado = _consultar_pessoa(cursor, "FATURADO", dados["faturado_documento"])
            classes = [
                {"descricao": descricao, "registro": _consultar_classificacao(cursor, descricao)}
                for descricao in dados["classificacoes"]
            ]
            cursor.execute(
                "SELECT id FROM movimentocontas WHERE chave_origem = %s",
                (dados["chave_origem"],),
            )
            existente = cursor.fetchone()
    return {
        "fornecedor": fornecedor,
        "faturado": faturado,
        "classificacoes": classes,
        "movimento_existente": existente,
    }


def _salvar_pessoa(cursor, tipo: str, nome: str, documento: str, fantasia: str | None = None) -> int:
    cursor.execute(
        """
        INSERT INTO pessoas(tipo, razao_social, nome_fantasia, documento)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (tipo, documento) DO UPDATE
           SET status = 'ATIVO', atualizado_em = CURRENT_TIMESTAMP
        RETURNING id
        """,
        (tipo, nome, fantasia, documento),
    )
    return int(cursor.fetchone()["id"])


def _salvar_classificacao(cursor, descricao: str) -> int:
    cursor.execute(
        """
        INSERT INTO classificacao(tipo, descricao) VALUES ('DESPESA', %s)
        ON CONFLICT (tipo, descricao) DO UPDATE
           SET status = 'ATIVO', atualizado_em = CURRENT_TIMESTAMP
        RETURNING id
        """,
        (descricao,),
    )
    return int(cursor.fetchone()["id"])


def registrar_lancamento(url: str, entrada: dict[str, Any]) -> dict[str, Any]:
    """Tudo em uma transação: pessoas, categorias, movimento e parcelas."""
    dados = validar_lancamento(entrada)
    with conectar(url) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM movimentocontas WHERE chave_origem = %s",
                (dados["chave_origem"],),
            )
            existente = cursor.fetchone()
            if existente:
                raise ErroLancamento(
                    f"Esta nota fiscal já foi lançada (movimento ID {existente['id']})."
                )

            fornecedor_id = _salvar_pessoa(
                cursor, "CLIENTE-FORNECEDOR", dados["fornecedor_nome"],
                dados["fornecedor_documento"], dados["fornecedor_fantasia"],
            )
            faturado_id = _salvar_pessoa(
                cursor, "FATURADO", dados["faturado_nome"],
                dados["faturado_documento"],
            )
            ids_classificacao = [
                _salvar_classificacao(cursor, categoria) for categoria in dados["classificacoes"]
            ]

            cursor.execute(
                """
                INSERT INTO movimentocontas
                (tipo, fornecedor_id, faturado_id, numero_nota_fiscal,
                 data_emissao, descricao, valor_total, chave_origem)
                VALUES ('APAGAR', %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chave_origem) DO NOTHING
                RETURNING id
                """,
                (fornecedor_id, faturado_id, dados["numero_nota"],
                 dados["data_emissao"], dados["descricao"], dados["valor_total"],
                 dados["chave_origem"]),
            )
            novo_movimento = cursor.fetchone()
            if not novo_movimento:
                raise ErroLancamento("A nota já foi registrada por outra sessão. Nenhum dado foi duplicado.")
            movimento_id = int(novo_movimento["id"])

            for classificacao_id in ids_classificacao:
                cursor.execute(
                    "INSERT INTO movimentocontas_classificacao(movimento_id, classificacao_id) VALUES (%s, %s)",
                    (movimento_id, classificacao_id),
                )

            for parcela in dados["parcelas"]:
                identificacao = f"MOV{movimento_id:010d}-P{parcela['numero']:03d}"
                cursor.execute(
                    """
                    INSERT INTO parcelacontas
                    (movimento_id, identificacao, numero, data_vencimento, valor)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (movimento_id, identificacao, parcela["numero"],
                     parcela["vencimento"], parcela["valor"]),
                )

    return {
        "movimento_id": movimento_id,
        "fornecedor_id": fornecedor_id,
        "faturado_id": faturado_id,
        "classificacoes_ids": ids_classificacao,
        "parcelas": len(dados["parcelas"]),
    }


def listar_cadastros(url: str, entidade: str, termo: str = "", incluir_inativos: bool = False):
    """Busca por nome, documento ou ID; limitada para não sobrecarregar a UI."""
    if entidade not in ("pessoas", "classificacao"):
        raise ValueError("Entidade inválida")
    consulta = (
        "SELECT id, tipo, razao_social AS descricao, documento, status FROM pessoas"
        if entidade == "pessoas" else
        "SELECT id, tipo, descricao, '' AS documento, status FROM classificacao"
    )
    campo_nome = "razao_social" if entidade == "pessoas" else "descricao"
    campo_documento = "documento" if entidade == "pessoas" else "''"
    clausulas = []
    parametros = []
    if not incluir_inativos:
        clausulas.append("status = 'ATIVO'")
    if termo.strip():
        clausulas.append(
            f"(CAST(id AS TEXT) = %s OR {campo_nome} ILIKE %s OR {campo_documento} ILIKE %s)"
        )
        parametros.extend((termo.strip(), f"%{termo.strip()}%", f"%{termo.strip()}%"))
    if clausulas:
        consulta += " WHERE " + " AND ".join(clausulas)
    consulta += " ORDER BY id DESC LIMIT 100"
    with conectar(url) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(consulta, parametros)
            return cursor.fetchall()


def atualizar_status_cadastro(url: str, entidade: str, identificador: int, status: str) -> None:
    if entidade not in ("pessoas", "classificacao") or status not in ("ATIVO", "INATIVO"):
        raise ValueError("Entidade/status inválidos")
    # Identificador SQL é selecionado exclusivamente entre duas constantes.
    with conectar(url) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                f"UPDATE {entidade} SET status = %s, atualizado_em = CURRENT_TIMESTAMP WHERE id = %s RETURNING id",
                (status, identificador),
            )
            if cursor.fetchone() is None:
                raise ErroLancamento("Cadastro não encontrado.")


def listar_movimentos(url: str, limite: int = 30):
    with conectar(url) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT m.id, m.numero_nota_fiscal AS nota, m.data_emissao,
                       p.razao_social AS fornecedor, m.valor_total, m.criado_em,
                       COUNT(pa.id) AS parcelas
                FROM movimentocontas m
                INNER JOIN pessoas p ON p.id = m.fornecedor_id
                LEFT JOIN parcelacontas pa ON pa.movimento_id = m.id
                GROUP BY m.id, p.razao_social
                ORDER BY m.id DESC LIMIT %s
                """,
                (max(1, min(100, limite)),),
            )
            return cursor.fetchall()
