"""Leitura do relatório (tp2.ipynb) como fonte única de textos e diagramas.

As interpretações de cada consulta e os diagramas são mantidos pelo grupo no
notebook. Em vez de copiá-los para a aplicação (e deixá-los desatualizados), o
app extrai do notebook:

* o bloco "Análise dos resultados" que segue cada "### Consulta N";
* a imagem e o texto das seções "## Diagrama ER" e "## Diagrama relacional".

A leitura é refeita sempre que o arquivo do notebook muda.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from siget import settings

_TITULO_CONSULTA = re.compile(r"^###\s*Consulta\s+(\d+)\s*:\s*(.+)$", re.MULTILINE)
_MARCADOR_ANALISE = re.compile(r"^\s*\*\*An[aá]lise dos resultados\*\*\s*", re.IGNORECASE)
_SQL_NO_CODIGO = re.compile(r'sql\s*=\s*"""(.*?)"""', re.DOTALL)
_CIFRAO = re.compile(r"\\*\$")
_TITULO_DIAGRAMA = re.compile(r"^##\s*Diagrama\s+(ER|relacional)\b.*$", re.IGNORECASE | re.MULTILINE)
_IMAGEM_MARKDOWN = re.compile(r"!\[[^\]]*\]\(\s*<?([^)>\s]+)>?\s*\)")


@dataclass(frozen=True, slots=True)
class TrechoRelatorio:
    numero: int
    pergunta: str
    sql: str | None
    analise: str | None


@dataclass(frozen=True, slots=True)
class Diagrama:
    imagem: Path | None  # caminho absoluto da imagem referenciada no notebook
    texto: str | None  # parágrafos que acompanham a imagem


# ── Leitura do notebook ─────────────────────────────────────────────────────
def _celulas() -> list[dict]:
    try:
        marca = settings.NOTEBOOK.stat().st_mtime_ns
    except OSError:
        return []
    return _ler_celulas(marca)


@st.cache_data(show_spinner=False, max_entries=2)
def _ler_celulas(marca: int) -> list[dict]:
    """Células do notebook. ``marca`` (data de modificação) invalida o cache quando o arquivo muda."""
    try:
        return json.loads(settings.NOTEBOOK.read_text(encoding="utf-8"))["cells"]
    except (OSError, ValueError, KeyError):
        return []


# ── Diagramas ───────────────────────────────────────────────────────────────
def diagramas() -> dict[str, Diagrama]:
    """Diagramas como o notebook os apresenta, nas chaves ``"er"`` e ``"relacional"``."""
    encontrados: dict[str, Diagrama] = {}
    for celula in _celulas():
        if celula.get("cell_type") != "markdown":
            continue
        fonte = "".join(celula.get("source", []))
        if not (titulo := _TITULO_DIAGRAMA.search(fonte)):
            continue
        corpo = fonte[titulo.end() :]
        imagem = _IMAGEM_MARKDOWN.search(corpo)
        texto = _IMAGEM_MARKDOWN.sub("", corpo).strip()
        encontrados[titulo.group(1).lower()] = Diagrama(
            imagem=(settings.ROOT_DIR / imagem.group(1)).resolve() if imagem else None,
            texto=_normalizar_markdown(texto) if texto else None,
        )
    return encontrados


# ── Consultas ───────────────────────────────────────────────────────────────
def trechos_consultas() -> dict[int, TrechoRelatorio]:
    """Mapeia o número da consulta para pergunta, SQL original e análise do notebook."""
    celulas = _celulas()
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
