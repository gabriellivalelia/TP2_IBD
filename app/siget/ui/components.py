"""Componentes de interface reutilizáveis.

Os componentes escrevem HTML apenas para elementos puramente visuais (títulos,
chips, faixas de etapas). Tudo o que é interativo usa widgets nativos do
Streamlit, preservando acessibilidade e navegação por teclado.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from siget.ui.theme import CLASSES_TENSAO, CORES_SITUACAO, PLOTLY_CONFIG


# ── Cabeçalhos ──────────────────────────────────────────────────────────────
def cabecalho_pagina(eyebrow: str, titulo: str, lede: str | None = None) -> None:
    html = f'<div class="sg-eyebrow">{escape(eyebrow)}</div><h1 class="sg-page-title">{escape(titulo)}</h1>'
    if lede:
        html += f'<p class="sg-lede">{escape(lede)}</p>'
    st.html(html)


def secao(titulo: str, apoio: str | None = None) -> None:
    aside = f"<span>{escape(apoio)}</span>" if apoio else ""
    st.html(f'<div class="sg-section"><h3>{escape(titulo)}</h3>{aside}</div>')


def nota(texto: str) -> None:
    st.html(f'<p class="sg-note">{escape(texto)}</p>')


# ── Chips ───────────────────────────────────────────────────────────────────
def chips(itens: Iterable[str], *, juncao: bool = False, destaque: bool = False) -> None:
    """Lista de rótulos. Com ``juncao=True`` desenha ⋈ entre as relações."""
    classe = "sg-chip is-accent" if destaque else "sg-chip"
    partes = [f'<span class="{classe}">{escape(i)}</span>' for i in itens]
    separador = '<span class="sg-join">⋈</span>' if juncao else ""
    st.html(f"<div>{separador.join(partes)}</div>")


def legenda(itens: Mapping[str, str], rotulo: str = "Legenda") -> None:
    """Legenda horizontal em HTML: {rótulo: cor}."""
    html = "".join(f'<span><i style="background:{cor}"></i>{escape(nome)}</span>' for nome, cor in itens.items())
    st.html(f'<div class="sg-legend" aria-label="{escape(rotulo)}">{html}</div>')


def legenda_tensao() -> None:
    legenda({c.rotulo: c.cor for c in CLASSES_TENSAO}, "Classes de tensão")


def legenda_situacao(presentes: Iterable[str]) -> None:
    presentes = set(presentes)
    legenda({s: c for s, c in CORES_SITUACAO.items() if s in presentes}, "Situação")


# ── Blocos de texto ─────────────────────────────────────────────────────────
def destaque_markdown(titulo: str, markdown: str, *, chave: str) -> None:
    """Caixa com borda âmbar para textos interpretativos (aceita Markdown)."""
    with st.container(key=f"sg-callout-{_slug(chave)}"):
        st.html(f'<div class="sg-callout-title">{escape(titulo)}</div>')
        st.markdown(markdown)


# ── Faixa de etapas ─────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Etapa:
    rotulo: str
    valor: str
    detalhe: str
    tipo: str = ""  # "", "loss" ou "final"


def faixa_etapas(etapas: Sequence[Etapa]) -> None:
    blocos = "".join(
        f'<div class="sg-step{" is-" + e.tipo if e.tipo else ""}">'
        f'<div class="sg-step-label">{escape(e.rotulo)}</div>'
        f'<div class="sg-step-value">{escape(e.valor)}</div>'
        f'<div class="sg-step-detail">{escape(e.detalhe)}</div></div>'
        for e in etapas
    )
    st.html(f'<div class="sg-pipeline" style="--n:{len(etapas)}" role="list">{blocos}</div>')


# ── Métricas ────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Metrica:
    rotulo: str
    valor: str
    ajuda: str | None = None
    delta: str | None = None


def linha_metricas(metricas: Sequence[Metrica]) -> None:
    """Grade de métricas que se reorganiza sozinha conforme a largura disponível.

    O texto de ajuda fica visível sob o valor (tooltips não funcionam em telas de toque).
    """
    cartoes = "".join(
        '<div class="sg-metric" role="group">'
        f'<span class="sg-metric-label">{escape(m.rotulo)}</span>'
        f'<b class="sg-metric-value">{escape(m.valor)}</b>'
        + (f'<span class="sg-metric-help">{escape(m.ajuda)}</span>' if m.ajuda else "")
        + "</div>"
        for m in metricas
    )
    st.html(f'<div class="sg-metrics">{cartoes}</div>')


# ── Gráficos e tabelas ──────────────────────────────────────────────────────
def grafico(
    fig: go.Figure,
    *,
    chave: str | None = None,
    selecionavel: bool = False,
    rolagem: bool = False,
):
    """Renderiza uma figura Plotly com o template da aplicação.

    O título sai do Plotly e vira HTML: assim ele quebra linha em telas estreitas e
    não fica sob a barra de ferramentas do gráfico. Com ``rolagem=True`` o gráfico
    mantém largura mínima e rola na horizontal (útil para matrizes densas).
    """
    titulo = fig.layout.title.text
    if titulo:
        st.html(f'<div class="sg-chart-title">{escape(titulo)}</div>')
        topo = fig.layout.margin.t if fig.layout.margin.t is not None else 36
        fig.update_layout(title=None, margin=dict(t=max(topo - 28, 8)))
    destino = st.container(key=f"sg-rolagem-{chave}") if rolagem and chave else st.container()
    with destino:
        return st.plotly_chart(
            fig,
            theme=None,
            config=PLOTLY_CONFIG,
            key=chave,
            on_select="rerun" if selecionavel else "ignore",
            selection_mode="points",
        )


def tabela(
    dados: pd.DataFrame,
    *,
    chave: str,
    altura: int | str = "auto",
    nome_arquivo: str | None = None,
    colunas: dict | None = None,
) -> None:
    """Tabela com busca textual e exportação para CSV."""
    filtrados = dados
    topo = st.columns([3, 1], vertical_alignment="bottom")
    termo = topo[0].text_input(
        "Filtrar linhas",
        key=f"{chave}-busca",
        placeholder="Digite parte de um nome, código ou UF…",
        label_visibility="collapsed",
        icon=":material/search:",
    )
    if termo:
        mascara = dados.astype("string").apply(
            lambda coluna: coluna.str.contains(termo, case=False, regex=False, na=False)
        )
        filtrados = dados[mascara.any(axis=1)]
    topo[1].download_button(
        "Baixar CSV",
        filtrados.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{nome_arquivo or chave}.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
        key=f"{chave}-csv",
    )
    st.dataframe(
        filtrados,
        hide_index=True,
        width="stretch",
        height=altura,
        column_config=colunas,
        key=f"{chave}-df",
    )
    st.caption(
        f"{len(filtrados):,} de {len(dados):,} linhas".replace(",", ".") + (f" · filtro: “{termo}”" if termo else "")
    )


# ── Utilidades ──────────────────────────────────────────────────────────────
def _slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")
