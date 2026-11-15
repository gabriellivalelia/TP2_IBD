"""Formatação numérica no padrão brasileiro (1.234,5)."""

from __future__ import annotations

import math


def _trocar_separadores(texto: str) -> str:
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def inteiro(valor: float | int | None) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    return _trocar_separadores(f"{round(valor):,}")


def decimal(valor: float | None, casas: int = 1) -> str:
    if valor is None or math.isnan(valor):
        return "—"
    return _trocar_separadores(f"{valor:,.{casas}f}")


def percentual(parte: float, total: float, casas: int = 1) -> str:
    if not total:
        return "—"
    return f"{decimal(100 * parte / total, casas)}%"


def moeda_compacta(valor_reais: float | None) -> str:
    """R$ 1,98 tri · R$ 31,7 bi · R$ 813,8 mi."""
    if valor_reais is None or math.isnan(valor_reais):
        return "—"
    for limite, sufixo, casas in ((1e12, "tri", 2), (1e9, "bi", 1), (1e6, "mi", 1), (1e3, "mil", 1)):
        if abs(valor_reais) >= limite:
            return f"R$ {decimal(valor_reais / limite, casas)} {sufixo}"
    return f"R$ {decimal(valor_reais, 2)}"
