"""Prazos de implantação: data prevista no ato legal × data efetiva de operação comercial."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from siget.data.database import consultar
from siget.ui import charts
from siget.ui import formatting as fmt
from siget.ui.components import (
    Metrica,
    cabecalho_pagina,
    destaque_markdown,
    grafico,
    legenda_situacao,
    linha_metricas,
    secao,
    tabela,
)
from siget.ui.theme import COR, CORES_SITUACAO

TOLERANCIA_DIAS = 0  # diferença acima disto conta como atraso


@st.cache_data(show_spinner=False)
def _empreendimentos() -> pd.DataFrame:
    dados = consultar(
        """
        SELECT e.IdeEpd AS id, e.NomEpd AS nome,
               COALESCE(e.DscSituacaoEpd, 'Não informada') AS situacao,
               e.DatOprComEpd AS prevista, e.DatEfeOprComEpd AS efetiva,
               a.DscRazaoSocial AS agente,
               julianday(e.DatEfeOprComEpd) - julianday(e.DatOprComEpd) AS desvio_dias
        FROM Empreendimento AS e
        JOIN Contrato AS c ON c.IdeCcd = e.IdeCcd
        JOIN Agente AS a ON a.IdAgente = c.IdAgente
        """
    )
    dados["ano_previsto"] = pd.to_datetime(dados["prevista"], errors="coerce").dt.year
    return dados


def render() -> None:
    cabecalho_pagina(
        "Explorar a base",
        "Prazos de implantação",
        "Cada empreendimento tem uma data de operação comercial fixada no ato legal e, quando entra em "
        "operação, uma data efetiva. Comparar as duas mostra o ritmo da expansão e onde ela atrasa.",
    )
    dados = _empreendimentos()
    concluidos = dados.dropna(subset=["desvio_dias"])
    atrasados = concluidos[concluidos["desvio_dias"] > TOLERANCIA_DIAS]
    adiantados = concluidos[concluidos["desvio_dias"] < 0]

    linha_metricas(
        [
            Metrica("Com as duas datas", fmt.inteiro(len(concluidos)), f"de {fmt.inteiro(len(dados))} empreendimentos"),
            Metrica(
                "Entraram após o prazo",
                fmt.percentual(len(atrasados), len(concluidos)),
                f"{fmt.inteiro(len(atrasados))} empreendimentos",
            ),
            Metrica(
                "Atraso mediano", f"{fmt.inteiro(atrasados['desvio_dias'].median())} dias", "Entre os que atrasaram"
            ),
            Metrica(
                "Antes do prazo",
                fmt.percentual(len(adiantados), len(concluidos)),
                f"{fmt.inteiro(len(adiantados))} empreendimentos",
            ),
        ]
    )

    secao("Ritmo da expansão", "Empreendimentos por ano de operação prevista no ato legal")
    por_ano = dados.dropna(subset=["ano_previsto"]).groupby(["ano_previsto", "situacao"]).size().reset_index(name="n")
    por_ano["ano_previsto"] = por_ano["ano_previsto"].astype(int)
    fig = charts.barras_empilhadas(
        por_ano,
        "ano_previsto",
        "situacao",
        "n",
        cores=CORES_SITUACAO,
        ordem_series=list(CORES_SITUACAO),
        horizontal=False,
    )
    # Eixo numérico: o Plotly reduz a quantidade de anos rotulados conforme a largura.
    fig.update_layout(xaxis=dict(type="linear", tickformat="d", showgrid=False), height=400, bargap=0.18)
    legenda_situacao(por_ano["situacao"])
    grafico(fig, chave="prazos-anos")
    st.caption(
        "A partir do ano corrente, as barras são majoritariamente “Em andamento”: é a carteira de obras "
        "que ainda vai entrar em operação."
    )

    secao("Quanto os prazos se desviam", "Data efetiva − data do ato legal, em meses")
    histograma_col, texto_col = st.columns([1.6, 1], gap="large")
    with histograma_col:
        meses = (concluidos["desvio_dias"] / 30.44).clip(-36, 60)
        bordas = np.arange(-36, 61, 3)
        contagem, _ = np.histogram(meses, bins=bordas)
        centros = (bordas[:-1] + bordas[1:]) / 2
        fig = go.Figure(
            go.Bar(
                x=centros,
                y=contagem,
                width=2.7,
                marker=dict(color=[COR.ambar if c > 0 else COR.petroleo for c in centros], line=dict(width=0)),
                hovertemplate="%{x:+.0f} meses: %{y} empreendimentos<extra></extra>",
            )
        )
        fig.add_vline(x=0, line=dict(color=COR.tinta, width=1.5))
        fig.update_layout(
            height=360,
            bargap=0.05,
            xaxis=dict(title="Meses de desvio (− antes, + depois do prazo)", zeroline=False),
            yaxis=dict(title="Empreendimentos"),
        )
        grafico(fig, chave="prazos-histograma")
    with texto_col:
        destaque_markdown(
            "Como ler",
            f"Cada barra agrupa três meses. À esquerda da linha, em petróleo, os empreendimentos que entraram "
            f"em operação **antes** da data do ato legal; à direita, em âmbar, os que **atrasaram**.\n\n"
            f"Dos {fmt.inteiro(len(concluidos))} empreendimentos com as duas datas, "
            f"{fmt.percentual(len(atrasados), len(concluidos))} atrasaram e "
            f"{fmt.percentual(len(adiantados), len(concluidos))} anteciparam. "
            "A antecipação é comum porque o ato legal fixa um prazo máximo.",
            chave="prazos-leitura",
        )

    secao("Agentes com mais atrasos", "Mínimo de 10 empreendimentos com as duas datas")
    por_agente = (
        concluidos.assign(atrasou=concluidos["desvio_dias"] > TOLERANCIA_DIAS)
        .groupby("agente")
        .agg(total=("id", "count"), atrasados=("atrasou", "sum"), mediana=("desvio_dias", "median"))
        .query("total >= 10")
        .assign(taxa=lambda d: 100 * d["atrasados"] / d["total"])
        .sort_values("taxa", ascending=False)
        .head(12)
        .reset_index()
    )
    por_agente["rotulo"] = por_agente["agente"].map(lambda t: t if len(t) <= 30 else t[:29] + "…")
    grafico(
        charts.barras_horizontais(
            por_agente,
            "rotulo",
            "taxa",
            formato=".0f",
            sufixo="%",
            cores=COR.ambar,
            hover="<b>%{y}</b><br>%{x:.1f}% dos empreendimentos atrasaram<extra></extra>",
        ),
        chave="prazos-agentes",
    )

    secao("Maiores atrasos registrados")
    maiores = (
        atrasados.sort_values("desvio_dias", ascending=False)
        .head(200)
        .assign(**{"Atraso (dias)": lambda d: d["desvio_dias"].round().astype(int)})
        .rename(columns={"nome": "Empreendimento", "agente": "Agente", "prevista": "Prevista", "efetiva": "Efetiva"})[
            ["Empreendimento", "Agente", "Prevista", "Efetiva", "Atraso (dias)"]
        ]
    )
    tabela(maiores, chave="prazos-maiores", altura=360, nome_arquivo="maiores_atrasos")
