"""Fábricas de gráficos Plotly no padrão visual da aplicação.

Cada função recebe um DataFrame já agregado e devolve uma ``go.Figure``; nenhuma
consulta ao banco acontece aqui.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

from siget.ui.theme import COR, ESCALA_SEQUENCIAL, FONTE_TITULO

_HOVER_PADRAO = "<b>%{y}</b><br>%{x:,.0f}<extra></extra>"


# Rótulos maiores que isto vão para cima da barra: no eixo Y eles roubariam a
# largura do gráfico (ou seriam cortados) em telas estreitas.
LIMITE_ROTULO_EIXO = 16
LIMITE_ROTULO_TEXTO = 48
ALTURA_BARRA_ROTULADA = 46


def _altura_barras(n: int, minimo: int = 220, por_barra: int = 30) -> int:
    return max(minimo, 70 + n * por_barra)


def _rotulos_longos(categorias: Sequence[str]) -> bool:
    return max((len(str(c)) for c in categorias), default=0) > LIMITE_ROTULO_EIXO


def rotulos_sobre_barras(fig: go.Figure, categorias: Sequence[str]) -> None:
    """Escreve cada rótulo acima da sua barra, alinhado à esquerda, e oculta o eixo Y."""
    fig.update_yaxes(showticklabels=False, ticksuffix="")
    fig.update_layout(bargap=0.5, margin=dict(l=4))
    for categoria in categorias:
        texto = str(categoria)
        if len(texto) > LIMITE_ROTULO_TEXTO:
            texto = texto[: LIMITE_ROTULO_TEXTO - 1].rstrip() + "…"
        fig.add_annotation(
            x=0,
            y=str(categoria),
            xref="x",
            yref="y",
            text=texto,
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
            yshift=12,
            font=dict(size=11.5, color=COR.ardosia),
        )


def barras_horizontais(
    dados: pd.DataFrame,
    rotulo: str,
    valor: str,
    *,
    titulo: str | None = None,
    cores: str | Sequence[str] = COR.petroleo,
    formato: str = ",.0f",
    sufixo: str = "",
    hover: str | None = None,
    destaque: str | None = None,
) -> go.Figure:
    """Ranking horizontal ordenado do maior (topo) para o menor, com rótulos de valor."""
    ordenado = dados.iloc[::-1]
    if destaque is not None and isinstance(cores, str):
        cores = [COR.ambar if r == destaque else cores for r in ordenado[rotulo]]
    elif not isinstance(cores, str):
        cores = list(cores)[::-1]
    fig = go.Figure(
        go.Bar(
            x=ordenado[valor],
            y=ordenado[rotulo].astype(str),
            orientation="h",
            marker=dict(color=cores, line=dict(width=0)),
            text=ordenado[valor],
            texttemplate=f"%{{text:{formato}}}{sufixo}",
            textposition="outside",
            cliponaxis=False,
            textfont=dict(color=COR.tinta, size=12),
            hovertemplate=hover or _HOVER_PADRAO,
        )
    )
    categorias = ordenado[rotulo].astype(str).tolist()
    longos = _rotulos_longos(categorias)
    fig.update_layout(
        title=titulo,
        height=_altura_barras(len(dados), por_barra=ALTURA_BARRA_ROTULADA if longos else 30),
        xaxis=dict(showgrid=False, showticklabels=False, rangemode="tozero"),
        yaxis=dict(showgrid=False, ticksuffix="  "),
        margin=dict(r=56),
    )
    if longos:
        rotulos_sobre_barras(fig, categorias)
    return fig


def barras_empilhadas(
    dados: pd.DataFrame,
    categoria: str,
    serie: str,
    valor: str,
    *,
    cores: Mapping[str, str],
    ordem_series: Sequence[str] | None = None,
    titulo: str | None = None,
    normalizar: bool = False,
    horizontal: bool = True,
) -> go.Figure:
    """Barras empilhadas (absolutas ou em 100%) com uma cor fixa por série."""
    tabela = dados.pivot_table(index=categoria, columns=serie, values=valor, aggfunc="sum", fill_value=0)
    if horizontal:  # ranking: maior total no topo
        tabela = tabela.loc[tabela.sum(axis=1).sort_values(ascending=True).index]
    else:  # série ordenada (ex.: anos): mantém a ordem natural das categorias
        tabela = tabela.sort_index()
    if normalizar:
        tabela = tabela.div(tabela.sum(axis=1), axis=0) * 100
    series = [s for s in (ordem_series or tabela.columns) if s in tabela.columns]

    fig = go.Figure()
    for s in series:
        valores = tabela[s]
        eixo_cat = tabela.index.astype(str)
        fig.add_bar(
            name=str(s),
            x=valores if horizontal else eixo_cat,
            y=eixo_cat if horizontal else valores,
            orientation="h" if horizontal else "v",
            marker=dict(color=cores.get(s, COR.nevoa), line=dict(width=0)),
            hovertemplate=(
                f"<b>%{{{'y' if horizontal else 'x'}}}</b><br>{s}: "
                f"%{{{'x' if horizontal else 'y'}:,.{1 if normalizar else 0}f}}"
                f"{'%' if normalizar else ''}<extra></extra>"
            ),
        )
    categorias = tabela.index.astype(str).tolist()
    longos = horizontal and _rotulos_longos(categorias)
    por_barra = ALTURA_BARRA_ROTULADA if longos else 30
    fig.update_layout(
        barmode="stack",
        title=dict(text=titulo, y=0.99, yanchor="top"),
        height=max(260, _altura_barras(len(tabela), por_barra=por_barra) + 20) if horizontal else 400,
        margin=dict(t=44 if titulo else 12),
        showlegend=False,  # legenda em HTML (components.legenda), igual à das classes de tensão
    )
    eixo_valor = dict(ticksuffix="%" if normalizar else "", range=[0, 100] if normalizar else None)
    if horizontal:
        fig.update_layout(xaxis=eixo_valor, yaxis=dict(showgrid=False, ticksuffix="  "))
        if longos:
            rotulos_sobre_barras(fig, categorias)
    else:
        fig.update_layout(yaxis=eixo_valor, xaxis=dict(showgrid=False))
    return fig


def pareto(
    dados: pd.DataFrame,
    rotulo: str,
    valor: str,
    *,
    titulo: str | None = None,
    nome_valor: str = "Valor",
    sufixo_valor: str = "",
) -> go.Figure:
    """Barras ordenadas + curva de participação acumulada (concentração)."""
    acumulado = 100 * dados[valor].cumsum() / dados[valor].sum()
    fig = go.Figure()
    fig.add_bar(
        x=dados[rotulo],
        y=dados[valor],
        name=nome_valor,
        marker=dict(color=COR.petroleo, line=dict(width=0)),
        hovertemplate=f"<b>%{{x}}</b><br>{nome_valor}: %{{y:,.1f}}{sufixo_valor}<extra></extra>",
    )
    fig.add_scatter(
        x=dados[rotulo],
        y=acumulado,
        name="Participação acumulada",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color=COR.ambar, width=2.5),
        marker=dict(size=6, color=COR.ambar),
        hovertemplate="<b>%{x}</b><br>Acumulado: %{y:.1f}%<extra></extra>",
    )
    fig.update_layout(
        title=titulo,
        height=430,
        xaxis=dict(showgrid=False, tickangle=-60, tickfont=dict(size=10.5)),
        yaxis=dict(title=nome_valor),
        showlegend=False,  # legenda em HTML na página
        yaxis2=dict(
            overlaying="y",
            side="right",
            range=[0, 105],
            tickvals=[0, 25, 50, 75, 100],
            ticksuffix="%",
            showgrid=False,
            tickfont=dict(color=COR.ambar),
        ),
    )
    return fig


def mapa_calor(
    matriz: pd.DataFrame,
    *,
    titulo: str | None = None,
    rotulo_x: str = "",
    rotulo_y: str = "",
    nome_valor: str = "Valor",
    log: bool = False,
) -> go.Figure:
    valores = matriz.to_numpy(dtype=float)
    cor = np.log10(np.where(valores > 0, valores, np.nan)) if log else np.where(valores > 0, valores, np.nan)
    texto = np.where(valores > 0, valores.astype(int).astype(str), "")
    fig = go.Figure(
        go.Heatmap(
            z=cor,
            x=matriz.columns.astype(str),
            y=matriz.index.astype(str),
            customdata=valores,
            text=texto,
            texttemplate="%{text}",
            textfont=dict(size=10),
            colorscale=ESCALA_SEQUENCIAL,
            showscale=False,
            xgap=2,
            ygap=2,
            hovertemplate=(
                f"{rotulo_y}: <b>%{{y}}</b><br>{rotulo_x}: <b>%{{x}}</b><br>"
                f"{nome_valor}: %{{customdata:,.0f}}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=dict(text=titulo, y=0.995, yanchor="top"),
        height=max(380, 24 * len(matriz) + 150),
        margin=dict(t=96, l=8, r=8, b=8),
        xaxis=dict(title=dict(text=rotulo_x, standoff=6), showgrid=False, side="top", tickfont=dict(size=11)),
        yaxis=dict(title=dict(text=rotulo_y, standoff=6), showgrid=False, autorange="reversed", tickfont=dict(size=11)),
    )
    return fig


# ── Mapa em grade do Brasil ─────────────────────────────────────────────────
# Cartograma em ladrilhos: cada UF ocupa uma célula (coluna, linha) que preserva
# a vizinhança aproximada. Evita depender de GeoJSON externo e dá a todas as
# UFs o mesmo peso visual, o que favorece a comparação de valores.
GRADE_UF: dict[str, tuple[int, int]] = {
    "RR": (1, 0),
    "AP": (3, 0),
    "AM": (1, 1),
    "PA": (2, 1),
    "MA": (3, 1),
    "CE": (4, 1),
    "RN": (5, 1),
    "AC": (0, 2),
    "RO": (1, 2),
    "TO": (2, 2),
    "PI": (3, 2),
    "PE": (4, 2),
    "PB": (5, 2),
    "MT": (1, 3),
    "GO": (2, 3),
    "BA": (3, 3),
    "SE": (4, 3),
    "AL": (5, 3),
    "MS": (1, 4),
    "DF": (2, 4),
    "MG": (3, 4),
    "ES": (4, 4),
    "SP": (2, 5),
    "RJ": (3, 5),
    "PR": (2, 6),
    "SC": (2, 7),
    "RS": (2, 8),
}


def mapa_ufs(
    dados: pd.DataFrame,
    uf: str,
    valor: str,
    *,
    nome_valor: str,
    selecionadas: Sequence[str] = (),
    formato: str = ",.0f",
    altura: int = 520,
) -> go.Figure:
    """Cartograma em ladrilhos das 27 UFs, colorido pelo valor informado."""
    base = pd.DataFrame([(sigla, col, lin) for sigla, (col, lin) in GRADE_UF.items()], columns=["uf", "col", "lin"])
    base = base.merge(dados[[uf, valor]].rename(columns={uf: "uf"}), on="uf", how="left")
    base[valor] = base[valor].fillna(0)
    maximo = base[valor].max() or 1
    selecionadas = set(selecionadas)

    proporcao = (base[valor] / maximo).clip(0, 1)
    preenchimento = sample_colorscale(ESCALA_SEQUENCIAL, proporcao.tolist())
    texto_cor = ["#FFFFFF" if p > 0.45 else COR.tinta for p in proporcao]

    # Ladrilhos como formas em coordenadas de dados: escalam com a largura do
    # contêiner (marcadores Plotly têm tamanho fixo em pixels e se sobrepõem).
    meio = 0.45
    ladrilhos = [
        dict(
            type="rect",
            x0=c - meio,
            x1=c + meio,
            y0=r - meio,
            y1=r + meio,
            fillcolor=cor,
            line=dict(color=COR.ambar if sigla in selecionadas else "rgba(0,0,0,0)", width=3.5),
            layer="below",
        )
        for sigla, c, r, cor in zip(base["uf"], base["col"], base["lin"], preenchimento, strict=True)
    ]

    # Rótulos como anotações: não são esmaecidos quando o Plotly marca uma seleção.
    rotulos = [
        dict(
            x=c,
            y=r,
            text=f"<b>{sigla}</b>",
            showarrow=False,
            font=dict(family=FONTE_TITULO, size=12, color=cor_texto),
        )
        for sigla, c, r, cor_texto in zip(base["uf"], base["col"], base["lin"], texto_cor, strict=True)
    ]

    fig = go.Figure(
        go.Scatter(
            x=base["col"],
            y=base["lin"],
            mode="markers",
            # Marcador invisível: área de clique e de hover sobre cada ladrilho.
            marker=dict(symbol="square", size=34, color="rgba(0,0,0,0)"),
            customdata=np.stack([base["uf"], base[valor]], axis=-1),
            hovertemplate=f"<b>%{{customdata[0]}}</b><br>{nome_valor}: %{{customdata[1]:{formato}}}<extra></extra>",
            selected=dict(marker=dict(opacity=1)),
            unselected=dict(marker=dict(opacity=1)),
        )
    )
    fig.update_layout(
        shapes=ladrilhos,
        annotations=rotulos,
        height=altura,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(visible=False, range=[-0.6, 5.6], fixedrange=True),
        yaxis=dict(visible=False, range=[8.6, -0.6], fixedrange=True, scaleanchor="x"),
        dragmode=False,
        clickmode="event+select",
        showlegend=False,
    )
    return fig
