"""Consultas 9 e 10 — funções de agregação sobre junções."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from siget.queries.base import Categoria, Consulta, Parametro
from siget.queries.juncao_duas import UFS_SUBESTACAO_SQL
from siget.ui import charts
from siget.ui import formatting as fmt
from siget.ui.components import Metrica, grafico, legenda, linha_metricas
from siget.ui.theme import COR, cor_tensao

LIMIAR_HUB = 5


# ── Consulta 9 ──────────────────────────────────────────────────────────────
def _visualizar_c9(dados: pd.DataFrame, valores: dict[str, Any]) -> None:
    if dados.empty:
        st.info("Nenhuma subestação conectada a linhas para o filtro escolhido.")
        return
    hubs = int((dados["Total de linhas"] >= LIMIAR_HUB).sum())
    lider = dados.iloc[0]
    linha_metricas(
        [
            Metrica("Subestações conectadas", fmt.inteiro(len(dados))),
            Metrica(
                f"Hubs ({LIMIAR_HUB}+ linhas)",
                fmt.inteiro(hubs),
                f"{fmt.percentual(hubs, len(dados))} das subestações conectadas",
            ),
            Metrica(
                "Mais conectada",
                f"{lider['Subestação'].title()}",
                f"{lider['UF']} · {int(lider['Total de linhas'])} linhas",
            ),
            Metrica("Média de linhas por SE", fmt.decimal(dados["Total de linhas"].mean(), 2)),
        ]
    )

    esquerda, direita = st.columns([1.5, 1], gap="large")
    with esquerda:
        topo = dados.head(15).iloc[::-1]
        rotulos = topo["Subestação"].str.title() + " · " + topo["UF"].fillna("?")
        fig = go.Figure()
        fig.add_bar(
            y=rotulos,
            x=topo["Como origem"],
            orientation="h",
            name="Como origem",
            marker=dict(color=COR.petroleo, line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Origem: %{x}<extra></extra>",
        )
        fig.add_bar(
            y=rotulos,
            x=topo["Como destino"],
            orientation="h",
            name="Como destino",
            marker=dict(color="#8DBBC1", line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>Destino: %{x}<extra></extra>",
        )
        fig.add_scatter(
            y=rotulos,
            x=topo["Total de linhas"] + 0.35,
            mode="markers+text",
            name="Maior tensão",
            marker=dict(symbol="square", size=10, color=[cor_tensao(v) for v in topo["Maior tensão (kV)"]]),
            text=[f"{v:g} kV" for v in topo["Maior tensão (kV)"]],
            textposition="middle right",
            textfont=dict(size=11, color=COR.ardosia),
            hovertemplate="<b>%{y}</b><br>Maior tensão: %{text}<extra></extra>",
        )
        fig.update_layout(
            barmode="stack",
            title="Quinze subestações mais conectadas",
            height=520,
            showlegend=False,
            xaxis=dict(title="Linhas conectadas", range=[0, dados["Total de linhas"].max() + 3.5]),
            yaxis=dict(showgrid=False, ticksuffix="  "),
        )
        if rotulos.str.len().max() > charts.LIMITE_ROTULO_EIXO:
            fig.update_layout(height=60 + len(topo) * charts.ALTURA_BARRA_ROTULADA)
            charts.rotulos_sobre_barras(fig, rotulos.tolist())
        legenda({"Como origem": COR.petroleo, "Como destino": "#8DBBC1"})
        grafico(fig, chave="c9-ranking")
        st.caption("O quadrado ao fim de cada barra indica a maior tensão conectada, na cor da sua classe.")
    with direita:
        por_uf = (
            dados.groupby("UF")
            .agg(participacoes=("Total de linhas", "sum"), subestacoes=("ID da subestação", "count"))
            .reset_index()
        )
        st.html('<div class="sg-chart-title">Participações em linhas, por UF</div>')
        grafico(
            charts.mapa_ufs(
                por_uf,
                "UF",
                "participacoes",
                nome_valor="Participações",
                selecionadas=[valores.get("uf")] if valores.get("uf") else [],
                altura=440,
            ),
            chave="c9-mapa",
        )
        st.caption("Cada ladrilho é uma UF, posicionado como no mapa. Cor mais escura = mais terminais de linha.")


CONSULTA_9 = Consulta(
    numero=9,
    titulo="Subestações mais conectadas",
    pergunta="Quais subestações estão conectadas ao maior número de linhas?",
    descricao=(
        "Junta Subestacao, LinhaSubestacao e LinhaTransmissao e agrega com COUNT, SUM e MAX para medir "
        "o grau de conectividade de cada subestação: total de linhas, divisão entre origem e destino "
        "e a maior tensão operada."
    ),
    categoria=Categoria.AGREGACAO,
    relacoes=("Subestacao", "LinhaSubestacao", "LinhaTransmissao"),
    sql="""
SELECT s.IdeSbe AS "ID da subestação",
       s.NomSubestacao AS "Subestação",
       s.SigUFSubestacao AS "UF",
       COUNT(ls.IdeLinTms) AS "Total de linhas",
       SUM(CASE WHEN ls.Papel = 'Origem' THEN 1 ELSE 0 END) AS "Como origem",
       SUM(CASE WHEN ls.Papel = 'Destino' THEN 1 ELSE 0 END) AS "Como destino",
       MAX(lt.NumTensaoBaseLinhaTransm) AS "Maior tensão (kV)"
FROM Subestacao AS s
JOIN LinhaSubestacao AS ls ON ls.IdeSbe = s.IdeSbe
JOIN LinhaTransmissao AS lt ON lt.IdeLinTms = ls.IdeLinTms
WHERE :uf IS NULL OR s.SigUFSubestacao = :uf
GROUP BY s.IdeSbe, s.NomSubestacao, s.SigUFSubestacao
ORDER BY "Total de linhas" DESC, s.NomSubestacao, s.IdeSbe;
""".strip(),
    parametros=(Parametro("uf", "UF da subestação", "escolha", padrao=None, opcoes_sql=UFS_SUBESTACAO_SQL),),
    visualizar=_visualizar_c9,
)


# ── Consulta 10 ─────────────────────────────────────────────────────────────
COLUNA_RECEITA = "Receita histórica total (R$ milhões)"


def _visualizar_c10(dados: pd.DataFrame, valores: dict[str, Any]) -> None:
    if dados.empty:
        st.info("Nenhum agente com obras vinculadas.")
        return
    total = dados[COLUNA_RECEITA].sum()
    top5 = dados.head(5)[COLUNA_RECEITA].sum()
    top10 = dados.head(10)[COLUNA_RECEITA].sum()
    linha_metricas(
        [
            Metrica(
                "Receita acumulada", fmt.moeda_compacta(total * 1e6), "Soma de VlrHisRct por obra, valores nominais"
            ),
            Metrica("Agentes com obras", fmt.inteiro(len(dados))),
            Metrica("Cinco maiores", fmt.percentual(top5, total), "Participação na receita acumulada"),
            Metrica("Dez maiores", fmt.percentual(top10, total), "Participação na receita acumulada"),
        ]
    )

    n = st.slider("Agentes no gráfico de concentração", 5, 40, 15, step=5, key="c10-n")
    legenda({"Receita acumulada (R$ milhões)": COR.petroleo, "Participação acumulada (%)": COR.ambar})
    topo = dados.head(n).copy()
    topo["Agente"] = topo["Agente"].map(lambda t: t if len(t) <= 16 else t[:15].rstrip() + "…")
    grafico(
        charts.pareto(
            topo,
            "Agente",
            COLUNA_RECEITA,
            titulo=f"Concentração da receita — {n} maiores agentes (barras em R$ milhões)",
            nome_valor="R$ milhões",
        ),
        chave="c10-pareto",
    )

    validos = dados[(dados[COLUNA_RECEITA] > 0) & (dados["Total de obras"] > 0)]
    fig = go.Figure(
        go.Scatter(
            x=validos["Total de obras"],
            y=validos[COLUNA_RECEITA],
            mode="markers",
            marker=dict(
                size=np.clip(np.sqrt(validos["Contratos"]) * 7, 6, 34),
                color=validos["Receita média por obra (R$ milhões)"],
                colorscale=[[0, "#C9DDE0"], [0.5, COR.petroleo], [1, COR.ambar]],
                showscale=True,
                colorbar=dict(title=dict(text="R$ mi/obra", font=dict(size=11)), thickness=10),
                line=dict(width=0.6, color="#FFFFFF"),
                opacity=0.85,
            ),
            customdata=np.stack(
                [validos["Agente"], validos["Contratos"], validos["Receita média por obra (R$ milhões)"]], axis=-1
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{x} obras · %{customdata[1]} contrato(s)"
                "<br>Receita: R$ %{y:,.1f} mi<br>Média por obra: R$ %{customdata[2]:,.1f} mi<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Porte dos agentes: obras × receita acumulada (tamanho = contratos)",
        height=440,
        xaxis=dict(type="log", dtick=1, title="Total de obras"),
        yaxis=dict(type="log", dtick=1, title="Receita acumulada (R$ milhões)"),
    )
    grafico(fig, chave="c10-dispersao")
    st.caption(
        "No SIGET o valor de receita se repete em cada obra do mesmo empreendimento; a soma por obra "
        "mede o porte financeiro ponderado pelo número de obras, não um faturamento."
    )


CONSULTA_10 = Consulta(
    numero=10,
    titulo="Receita por agente",
    pergunta="Quais agentes concentram os maiores valores históricos de receita associados às obras?",
    descricao=(
        "Junta Agente, Contrato, Empreendimento e Obra e agrega com SUM, AVG e COUNT para consolidar "
        "o valor histórico de receita (VlrHisRct) associado às obras de cada concessionária."
    ),
    categoria=Categoria.AGREGACAO,
    relacoes=("Agente", "Contrato", "Empreendimento", "Obra"),
    sql="""
SELECT a.IdAgente AS "ID do agente",
       a.DscRazaoSocial AS "Agente",
       a.SigUF AS "UF",
       COUNT(DISTINCT c.IdeCcd) AS "Contratos",
       COUNT(DISTINCT e.IdeEpd) AS "Empreendimentos",
       COUNT(o.IdeObr) AS "Total de obras",
       ROUND(SUM(COALESCE(o.VlrHisRct, 0)) / 1e6, 2) AS "Receita histórica total (R$ milhões)",
       ROUND(AVG(o.VlrHisRct) / 1e6, 2) AS "Receita média por obra (R$ milhões)"
FROM Agente AS a
JOIN Contrato AS c ON c.IdAgente = a.IdAgente
JOIN Empreendimento AS e ON e.IdeCcd = c.IdeCcd
JOIN Obra AS o ON o.IdeEpd = e.IdeEpd
GROUP BY a.IdAgente, a.DscRazaoSocial, a.SigUF
ORDER BY "Receita histórica total (R$ milhões)" DESC, "Total de obras" DESC;
""".strip(),
    visualizar=_visualizar_c10,
)
