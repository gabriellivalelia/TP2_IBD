"""Catálogo das 10 consultas do relatório, na ordem em que aparecem no notebook."""

from __future__ import annotations

from siget.queries.agregacao import CONSULTA_9, CONSULTA_10
from siget.queries.base import TODOS, Categoria, Consulta, Parametro
from siget.queries.juncao_duas import CONSULTA_3, CONSULTA_4, CONSULTA_5
from siget.queries.juncao_multipla import CONSULTA_6, CONSULTA_7, CONSULTA_8
from siget.queries.selecao import CONSULTA_1, CONSULTA_2

CONSULTAS: tuple[Consulta, ...] = (
    CONSULTA_1,
    CONSULTA_2,
    CONSULTA_3,
    CONSULTA_4,
    CONSULTA_5,
    CONSULTA_6,
    CONSULTA_7,
    CONSULTA_8,
    CONSULTA_9,
    CONSULTA_10,
)

POR_NUMERO: dict[int, Consulta] = {c.numero: c for c in CONSULTAS}

__all__ = ["CONSULTAS", "POR_NUMERO", "TODOS", "Categoria", "Consulta", "Parametro"]
