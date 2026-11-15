"""Garante que a aplicação reproduz exatamente as consultas do relatório.

Para cada consulta, executa o SQL original extraído do notebook (tp2.ipynb) e a
versão parametrizada da aplicação com os valores padrão, e compara os
resultados linha a linha.

    uv run pytest
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from siget.data.database import ErroConsulta, consultar, executar_livre  # noqa: E402
from siget.data.report import trechos_consultas  # noqa: E402
from siget.queries import CONSULTAS  # noqa: E402

TRECHOS = trechos_consultas()


def test_notebook_tem_as_dez_consultas() -> None:
    assert sorted(TRECHOS) == list(range(1, 11))
    assert all(t.sql for t in TRECHOS.values())
    assert all(t.analise for t in TRECHOS.values())


@pytest.mark.parametrize("consulta", CONSULTAS, ids=lambda c: c.codigo)
def test_padrao_reproduz_o_notebook(consulta) -> None:
    original = consultar(TRECHOS[consulta.numero].sql)
    da_aplicacao = consulta.executar()
    pd.testing.assert_frame_equal(
        da_aplicacao.reset_index(drop=True),
        original.reset_index(drop=True),
        check_dtype=False,
    )


@pytest.mark.parametrize("consulta", CONSULTAS, ids=lambda c: c.codigo)
def test_sql_exibido_e_executavel(consulta) -> None:
    sql = consulta.sql_com_valores(consulta.valores_padrao())
    assert not re.search(r":[a-z_]+\b", sql), "parâmetro não substituído no SQL exibido"
    resultado = executar_livre(sql, limite=1_000_000)
    assert len(resultado.dados) == len(consulta.executar())


@pytest.mark.parametrize(
    "sql",
    ["DELETE FROM Obra", "DROP TABLE Agente", "SELECT 1; SELECT 2", "   "],
)
def test_laboratorio_e_somente_leitura(sql: str) -> None:
    with pytest.raises(ErroConsulta):
        executar_livre(sql)
