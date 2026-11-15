"""Teste de fumaça da interface: cada página e cada consulta renderizam sem exceções.

As páginas são funções registradas com ``st.navigation``; por isso cada uma é
executada isoladamente com ``AppTest.from_function``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = str(Path(__file__).resolve().parents[1] / "app")
VIEWS = ["inicio", "dados", "modelagem", "consultas", "rede", "agentes", "empreendimentos", "laboratorio"]


def _executar_view(app_dir: str, view: str) -> None:
    import importlib
    import sys

    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    from siget.ui.theme import aplicar_tema

    aplicar_tema()
    importlib.import_module(f"siget.views.{view}").render()


def _rodar(view: str, estado: dict | None = None) -> AppTest:
    app = AppTest.from_function(_executar_view, args=(APP_DIR, view), default_timeout=90)
    for chave, valor in (estado or {}).items():
        app.session_state[chave] = valor
    return app.run()


def _erros(app: AppTest) -> list[str]:
    return [e.value for e in app.exception]


@pytest.mark.parametrize("view", VIEWS)
def test_pagina_renderiza(view: str) -> None:
    assert not _erros(app := _rodar(view)), _erros(app)


@pytest.mark.parametrize("numero", range(1, 11))
def test_consulta_renderiza(numero: int) -> None:
    app = _rodar("consultas", {"consulta_atual": numero})
    assert not _erros(app), _erros(app)
    assert any(f"Consulta {numero:02d}" in h.proto.body for h in app.get("html"))


def test_parametro_alterado_reexecuta() -> None:
    app = _rodar("consultas", {"consulta_atual": 1, "param-c1-tensao_minima": 230.0})
    assert not _erros(app), _erros(app)
    codigo = " ".join(c.value for c in app.code)
    assert ">= 230" in codigo


def test_laboratorio_executa_consulta() -> None:
    app = _rodar("laboratorio")
    app.text_area(key="lab-sql").set_value("SELECT SigUF, COUNT(*) AS n FROM Agente GROUP BY 1")
    app = app.button[0].click().run()
    assert not _erros(app), _erros(app)
    assert len(app.dataframe) >= 1 and "SigUF" in app.dataframe[-1].value.columns


def test_laboratorio_bloqueia_escrita() -> None:
    app = _rodar("laboratorio")
    app.text_area(key="lab-sql").set_value("DELETE FROM Obra")
    app = app.button[0].click().run()
    assert app.error and "somente leitura" in app.error[0].value
