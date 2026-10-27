"""Validação independente da interface e do banco (Etapa 2 da N2)."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


class ErroLancamento(ValueError):
    """Dados insuficientes/inconsistentes ou tentativa de duplicidade."""


def somente_digitos(texto: Any) -> str:
    return re.sub(r"\D", "", str(texto or ""))


def limpar_texto(texto: Any) -> str:
    return " ".join(str(texto or "").strip().split())


def normalizar_nome(texto: Any) -> str:
    return limpar_texto(texto).upper()


def converter_data(valor: Any, rotulo: str) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = limpar_texto(valor)
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ErroLancamento(f"{rotulo}: use uma data válida no formato DD/MM/AAAA.")


def converter_valor(valor: Any, rotulo: str) -> Decimal:
    try:
        numero = Decimal(str(valor))
        if not numero.is_finite():
            raise ValueError("não finito")
        numero = numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if numero <= 0 or numero >= Decimal("1000000000000"):
            raise ValueError("fora do intervalo")
        return numero
    except (InvalidOperation, ValueError, TypeError):
        raise ErroLancamento(f"{rotulo}: informe um valor positivo válido.") from None


def validar_lancamento(entrada: dict[str, Any]) -> dict[str, Any]:
    """Transforma formulário em dados seguros e consistentes para persistência."""
    fornecedor = normalizar_nome(entrada.get("fornecedor_nome"))
    fornecedor_fantasia = limpar_texto(entrada.get("fornecedor_fantasia"))
    cnpj = somente_digitos(entrada.get("fornecedor_documento"))
    faturado = normalizar_nome(entrada.get("faturado_nome"))
    doc_faturado = somente_digitos(entrada.get("faturado_documento"))
    numero_nota = limpar_texto(entrada.get("numero_nota"))

    if not fornecedor or len(cnpj) != 14:
        raise ErroLancamento("Fornecedor: informe razão social e CNPJ de 14 dígitos.")
    if not faturado or len(doc_faturado) not in (11, 14):
        raise ErroLancamento("Faturado: informe nome e CPF (11) ou CNPJ (14 dígitos).")
    if not numero_nota:
        raise ErroLancamento("Informe o número da nota fiscal.")

    emissao = converter_data(entrada.get("data_emissao"), "Emissão da nota")
    total = converter_valor(entrada.get("valor_total"), "Valor total")

    categorias = entrada.get("classificacoes") or []
    classificacoes = list(dict.fromkeys(normalizar_nome(c) for c in categorias if limpar_texto(c)))
    if not classificacoes:
        raise ErroLancamento("Selecione pelo menos uma classificação da despesa.")

    parcelas_entrada = entrada.get("parcelas") or []
    if not parcelas_entrada:
        raise ErroLancamento("Informe pelo menos uma parcela com valor e vencimento.")

    parcelas = []
    numeros = set()
    for index, parcela in enumerate(parcelas_entrada, start=1):
        try:
            numero_bruto = parcela.get("numero")
            numero = int(index if numero_bruto is None else numero_bruto)
        except (ValueError, TypeError):
            raise ErroLancamento(f"Parcela {index}: número inválido.") from None
        if numero < 1 or numero in numeros:
            raise ErroLancamento(f"Parcela {index}: número repetido ou inválido.")
        numeros.add(numero)
        parcelas.append({
            "numero": numero,
            "vencimento": converter_data(parcela.get("vencimento"), f"Vencimento da parcela {index}"),
            "valor": converter_valor(parcela.get("valor"), f"Valor da parcela {index}"),
        })

    soma = sum((p["valor"] for p in parcelas), Decimal("0.00"))
    if soma != total:
        raise ErroLancamento(
            f"A soma das parcelas (R$ {soma:.2f}) deve ser igual ao total "
            f"(R$ {total:.2f})."
        )

    chave = hashlib.sha256(
        f"APAGAR|{cnpj}|{numero_nota.upper()}|{emissao.isoformat()}".encode("utf-8")
    ).hexdigest()

    return {
        "fornecedor_nome": fornecedor,
        "fornecedor_fantasia": fornecedor_fantasia or None,
        "fornecedor_documento": cnpj,
        "faturado_nome": faturado,
        "faturado_documento": doc_faturado,
        "numero_nota": numero_nota,
        "data_emissao": emissao,
        "valor_total": total,
        "descricao": limpar_texto(entrada.get("descricao")) or None,
        "classificacoes": classificacoes,
        "parcelas": parcelas,
        "chave_origem": chave,
    }
