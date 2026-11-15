"""Leitura do relatório (tp2.ipynb) como fonte única dos textos de análise.

As interpretações de cada consulta são escritas pelo grupo no notebook. Em vez
de copiá-las para a aplicação (e deixá-las desatualizadas), o app extrai do
notebook o bloco "Análise dos resultados" que segue cada "### Consulta N".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import streamlit as st

from siget import settings

_TITULO_CONSULTA = re.compile(r"^###\s*Consulta\s+(\d+)\s*:\s*(.+)$", re.MULTILINE)
_MARCADOR_ANALISE = re.compile(r"^\s*\*\*An[aá]lise dos resultados\*\*\s*", re.IGNORECASE)
_SQL_NO_CODIGO = re.compile(r'sql\s*=\s*"""(.*?)"""', re.DOTALL)
_CIFRAO = re.compile(r"\\*\$")


@dataclass(frozen=True, slots=True)
class TrechoRelatorio:
    numero: int
    pergunta: str
    sql: str | None
    analise: str | None


@st.cache_data(show_spinner=False)
def trechos_consultas() -> dict[int, TrechoRelatorio]:
    """Mapeia o número da consulta para pergunta, SQL original e análise do notebook."""
    try:
        celulas = json.loads(settings.NOTEBOOK.read_text(encoding="utf-8"))["cells"]
    except (OSError, ValueError, KeyError):
        return {}

    trechos: dict[int, TrechoRelatorio] = {}
    atual: dict | None = None

    def fechar() -> None:
        if atual:
            trechos[atual["numero"]] = TrechoRelatorio(**atual)

    for celula in celulas:
        fonte = "".join(celula.get("source", []))
        tipo = celula.get("cell_type")

        if tipo == "markdown" and (titulo := _TITULO_CONSULTA.search(fonte)):
            fechar()
            atual = {
                "numero": int(titulo.group(1)),
                "pergunta": titulo.group(2).strip(),
                "sql": None,
                "analise": None,
            }
        elif atual is None:
            continue
        elif tipo == "code" and atual["sql"] is None and (sql := _SQL_NO_CODIGO.search(fonte)):
            atual["sql"] = sql.group(1).strip()
        elif tipo == "markdown" and _MARCADOR_ANALISE.match(fonte):
            atual["analise"] = _normalizar_markdown(_MARCADOR_ANALISE.sub("", fonte, count=1))
        elif tipo == "markdown" and fonte.lstrip().startswith("#"):
            fechar()
            atual = None
    fechar()
    return trechos


def _normalizar_markdown(texto: str) -> str:
    # O Jupyter exige "R\$" para não abrir LaTeX; o Streamlit também, mas com
    # uma única barra. Normaliza qualquer quantidade de barras antes do cifrão.
    return _CIFRAO.sub(r"\\$", texto).strip()
