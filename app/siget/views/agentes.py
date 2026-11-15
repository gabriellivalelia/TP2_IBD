"""Perfil de um agente de transmissão: contratos, empreendimentos, obras e receita."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from siget.data.database import consultar
from siget.ui import charts
from siget.ui import formatting as fmt
from siget.ui.components import Metrica, cabecalho_pagina, grafico, legenda, linha_metricas, secao, tabela
from siget.ui.theme import COR, CORES_SITUACAO


@st.cache_data(show_spinner=False)
def _ranking() -> pd.DataFrame:
    return consultar(
        """
        SELECT a.IdAgente AS id, a.DscRazaoSocial AS agente, a.SigUF AS uf, a.NomMunicipio AS municipio,
               a.NumCNPJ AS cnpj,
               COUNT(DISTINCT c.IdeCcd) AS contratos,
               COUNT(DISTINCT e.IdeEpd) AS empreendimentos,
               COUNT(o.IdeObr) AS obras,
               SUM(COALESCE(o.VlrHisRct, 0)) AS receita
        FROM Agente AS a
        LEFT JOIN Contrato AS c ON c.IdAgente = a.IdAgente
        LEFT JOIN Empreendimento AS e ON e.IdeCcd = c.IdeCcd
        LEFT JOIN Obra AS o ON o.IdeEpd = e.IdeEpd
        GROUP BY a.IdAgente
        ORDER BY receita DESC, obras DESC
        """
    )


def _cnpj(valor: str | None) -> str:
    digitos = "".join(ch for ch in str(valor or "") if ch.isdigit())
    if not digitos or len(digitos) > 14:
        return valor or "—"
    digitos = digitos.zfill(14)  # o CSV perdeu os zeros à esquerda de alguns CNPJs
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def _linha_do_tempo(contratos: pd.DataFrame) -> go.Figure:
    dados = contratos.dropna(subset=["Assinatura", "Término"]).copy()
    dados["inicio"] = pd.to_datetime(dados["Assinatura"], errors="coerce")
    dados["fim"] = pd.to_datetime(dados["Término"], errors="coerce")
    dados = dados.dropna(subset=["inicio", "fim"]).sort_values("inicio", ascending=False)
    rotulos = dados["Contrato"].fillna(dados["ID"])
    fig = go.Figure(
        go.Bar(
            y=rotulos,
            x=(dados["fim"] - dados["inicio"]).dt.total_seconds() * 1000,
            base=dados["inicio"],
            orientation="h",
            marker=dict(
                color=[COR.ambar if n else "#9DB7C7" for n in dados["Empreendimentos"]],
                line=dict(width=0),
            ),
            customdata=dados[["Assinatura", "Término", "Empreendimentos"]].to_numpy(),
            hovertemplate=(
                "<b>Contrato %{y}</b><br>%{customdata[0]} → %{customdata[1]}"
                "<br>%{customdata[2]} empreendimento(s)<extra></extra>"
            ),
        )
    )
    hoje = pd.Timestamp.today().normalize()
    fig.add_vline(x=hoje, line=dict(color=COR.tinta, width=1, dash="dot"))
    fig.add_annotation(
        x=hoje,
        y=0,
        yref="paper",
        text="hoje",
        showarrow=False,
        yanchor="bottom",
        xanchor="left",
        xshift=4,
        bgcolor="rgba(255,255,255,.85)",
        font=dict(size=11, color=COR.ardosia),
    )
    fig.update_layout(
        title="Vigência dos contratos de concessão",
        height=max(240, 70 + 26 * len(dados)),
        xaxis=dict(type="date"),
        yaxis=dict(type="category", showgrid=False, ticksuffix="  "),
    )
    return fig


def render() -> None:
    cabecalho_pagina(
        "Explorar a base",
        "Agentes de transmissão",
        "O perfil de cada concessionária: quantos contratos detém, por quanto tempo, o que está "
        "construindo e em que tipos de instalação. Os agentes estão ordenados pela receita acumulada.",
    )
    ranking = _ranking()
    escolhido = st.selectbox(
        "Agente",
        ranking["id"].tolist(),
        format_func=lambda i: ranking.set_index("id").at[i, "agente"],
        key="agentes-escolhido",
        help="Digite para buscar pela razão social.",
    )
    agente = ranking.set_index("id").loc[escolhido]
    posicao = int(ranking.index[ranking["id"] == escolhido][0]) + 1

    st.html(
        f'<p class="sg-note">CNPJ {_cnpj(agente["cnpj"])} · sede em {agente["municipio"] or "—"}/{agente["uf"] or "—"} · '
        f"{posicao}º de {len(ranking)} em receita acumulada</p>"
    )
    linha_metricas(
        [
            Metrica("Contratos", fmt.inteiro(agente["contratos"])),
            Metrica("Empreendimentos", fmt.inteiro(agente["empreendimentos"])),
            Metrica("Obras", fmt.inteiro(agente["obras"])),
            Metrica(
                "Receita acumulada",
                fmt.moeda_compacta(agente["receita"]),
                f"{fmt.percentual(agente['receita'], ranking['receita'].sum(), 2)} do total da base",
            ),
        ]
    )

    contratos = consultar(
        """
        SELECT c.IdeCcd AS "ID", c.NumCnaCcd AS "Contrato", c.DatAsnCcd AS "Assinatura",
               c.DatFimCcd AS "Término", COUNT(e.IdeEpd) AS "Empreendimentos"
        FROM Contrato AS c
        LEFT JOIN Empreendimento AS e ON e.IdeCcd = c.IdeCcd
        WHERE c.IdAgente = :id
        GROUP BY c.IdeCcd ORDER BY c.DatAsnCcd
        """,
        {"id": escolhido},
    )
    empreendimentos = consultar(
        """
        SELECT e.IdeEpd AS "ID", e.NomEpd AS "Empreendimento",
               COALESCE(e.DscSituacaoEpd, 'Não informada') AS "Situação",
               e.DatOprComEpd AS "Operação prevista", e.DatEfeOprComEpd AS "Operação efetiva",
               COUNT(o.IdeObr) AS "Obras"
        FROM Contrato AS c
        JOIN Empreendimento AS e ON e.IdeCcd = c.IdeCcd
        LEFT JOIN Obra AS o ON o.IdeEpd = e.IdeEpd
        WHERE c.IdAgente = :id
        GROUP BY e.IdeEpd ORDER BY e.DatOprComEpd DESC
        """,
        {"id": escolhido},
    )
    modulos = consultar(
        """
        SELECT m.DscTipMdl AS tipo, o.DscTipObr AS obra, COUNT(*) AS n
        FROM Contrato AS c
        JOIN Empreendimento AS e ON e.IdeCcd = c.IdeCcd
        JOIN Obra AS o ON o.IdeEpd = e.IdeEpd
        JOIN Modulo AS m ON m.IdeMdl = o.IdeMdl
        WHERE c.IdAgente = :id
        GROUP BY 1, 2
        """,
        {"id": escolhido},
    )

    if contratos.empty:
        st.info("Este agente não possui contratos na base normalizada.")
        return

    tempo_col, situacao_col = st.columns([1.5, 1], gap="large")
    with tempo_col:
        grafico(_linha_do_tempo(contratos), chave="agentes-vigencia")
        st.caption("Âmbar: contratos com empreendimentos na base; cinza: sem empreendimentos vinculados.")
    with situacao_col:
        if not empreendimentos.empty:
            situacao = empreendimentos["Situação"].value_counts().rename_axis("situação").reset_index(name="n")
            grafico(
                charts.barras_horizontais(
                    situacao,
                    "situação",
                    "n",
                    titulo="Empreendimentos por situação",
                    cores=[CORES_SITUACAO.get(s, COR.nevoa) for s in situacao["situação"]],
                ),
                chave="agentes-situacao",
            )
        if not modulos.empty:
            por_tipo = (
                modulos.groupby("tipo")["n"]
                .sum()
                .sort_values(ascending=False)
                .rename_axis("tipo")
                .reset_index(name="obras")
            )
            grafico(
                charts.barras_horizontais(
                    por_tipo, "tipo", "obras", titulo="Obras por tipo de módulo", cores=COR.tinta
                ),
                chave="agentes-modulos",
            )

    secao("Empreendimentos do agente", f"{fmt.inteiro(len(empreendimentos))} registros")
    tabela(
        empreendimentos, chave="agentes-empreendimentos", altura=360, nome_arquivo=f"empreendimentos_agente_{escolhido}"
    )

    secao("Comparar com os demais agentes")
    comparacao = ranking[ranking["obras"] > 0].copy()
    comparacao["destaque"] = comparacao["id"] == escolhido
    fig = go.Figure()
    for destaque, cor, tamanho in ((False, "#9DB7C7", 7), (True, COR.ambar, 16)):
        parte = comparacao[comparacao["destaque"] == destaque]
        fig.add_scatter(
            x=parte["obras"],
            y=parte["receita"] / 1e6,
            mode="markers",
            name=agente["agente"] if destaque else "Demais agentes",
            marker=dict(color=cor, size=tamanho, line=dict(width=1, color="#FFFFFF")),
            customdata=parte[["agente", "contratos"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>%{x} obras · %{customdata[1]} contrato(s)<br>R$ %{y:,.1f} mi<extra></extra>",
        )
    fig.update_layout(
        height=400,
        showlegend=False,
        xaxis=dict(type="log", dtick=1, title="Obras"),
        yaxis=dict(type="log", dtick=1, title="Receita acumulada (R$ milhões)"),
    )
    legenda({agente["agente"]: COR.ambar, "Demais agentes": "#9DB7C7"})
    grafico(fig, chave="agentes-comparacao")
