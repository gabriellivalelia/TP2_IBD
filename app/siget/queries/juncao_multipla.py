"""Consultas 6, 7 e 8 — junção de três ou mais relações."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from siget.data.database import escalar
from siget.queries.base import Categoria, Consulta, Parametro
from siget.queries.selecao import NIVEIS_TENSAO_SQL
from siget.ui import charts
from siget.ui import formatting as fmt
from siget.ui.components import Metrica, grafico, legenda_situacao, legenda_tensao, linha_metricas
from siget.ui.theme import COR, CORES_CLASSES, CORES_SITUACAO, ORDEM_CLASSES, classe_tensao

SEM_SITUACAO = "Não informada"


def _rotulo_curto(texto: str, limite: int = 30) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


# ── Consulta 6 ──────────────────────────────────────────────────────────────
def _visualizar_c6(dados: pd.DataFrame, valores: dict[str, Any]) -> None:
    if dados.empty:
        st.info("Nenhum empreendimento para a situação escolhida.")
        return
    dados = dados.assign(Situação=dados["Situação"].fillna(SEM_SITUACAO))
    por_agente = dados.groupby("Agente")["ID do empreendimento"].count().sort_values(ascending=False)
    cinco = por_agente.head(5).sum()
    total_agentes = int(escalar("SELECT COUNT(*) FROM Agente"))
    total_contratos = int(escalar("SELECT COUNT(*) FROM Contrato"))

    linha_metricas(
        [
            Metrica("Empreendimentos", fmt.inteiro(len(dados))),
            Metrica(
                "Contratos envolvidos",
                fmt.inteiro(dados["ID do contrato"].nunique()),
                f"de {fmt.inteiro(total_contratos)} cadastrados",
            ),
            Metrica("Agentes envolvidos", fmt.inteiro(len(por_agente)), f"de {fmt.inteiro(total_agentes)} cadastrados"),
            Metrica(
                "Cinco maiores agentes", fmt.percentual(cinco, len(dados)), f"{fmt.inteiro(cinco)} empreendimentos"
            ),
        ]
    )

    esquerda, direita = st.columns([1.6, 1], gap="large")
    with esquerda:
        topo = por_agente.head(12).index
        recorte = dados[dados["Agente"].isin(topo)].groupby(["Agente", "Situação"]).size().reset_index(name="n")
        recorte["Agente"] = recorte["Agente"].map(_rotulo_curto)
        fig = charts.barras_empilhadas(
            recorte,
            "Agente",
            "Situação",
            "n",
            cores=CORES_SITUACAO,
            ordem_series=list(CORES_SITUACAO),
            titulo="Doze agentes com mais empreendimentos, por situação",
        )
        legenda_situacao(recorte["Situação"])
        grafico(fig, chave="c6-agentes")
    with direita:
        situacao = dados["Situação"].value_counts().rename_axis("situação").reset_index(name="n")
        cores = [CORES_SITUACAO.get(s, COR.nevoa) for s in situacao["situação"]]
        grafico(
            charts.barras_horizontais(situacao, "situação", "n", titulo="Empreendimentos por situação", cores=cores),
            chave="c6-situacao",
        )


CONSULTA_6 = Consulta(
    numero=6,
    titulo="Agente → contrato → empreendimento",
    pergunta="Quais empreendimentos estão vinculados a cada agente e contrato?",
    descricao=(
        "Junta Agente, Contrato e Empreendimento pelos identificadores IdAgente e IdeCcd para "
        "relacionar cada empreendimento ao seu contrato de concessão e ao agente responsável."
    ),
    categoria=Categoria.JUNCAO_MULTIPLA,
    relacoes=("Agente", "Contrato", "Empreendimento"),
    sql="""
SELECT a.IdAgente AS "ID do agente",
       a.DscRazaoSocial AS "Agente",
       c.IdeCcd AS "ID do contrato",
       c.NumCnaCcd AS "Nº do contrato",
       e.IdeEpd AS "ID do empreendimento",
       e.NomEpd AS "Empreendimento",
       e.DscSituacaoEpd AS "Situação"
FROM Agente AS a
JOIN Contrato AS c ON c.IdAgente = a.IdAgente
JOIN Empreendimento AS e ON e.IdeCcd = c.IdeCcd
WHERE :situacao IS NULL OR e.DscSituacaoEpd = :situacao
ORDER BY a.DscRazaoSocial, c.IdeCcd, e.IdeEpd;
""".strip(),
    parametros=(
        Parametro(
            "situacao",
            "Situação do empreendimento",
            "escolha",
            padrao=None,
            opcoes_sql=(
                "SELECT DscSituacaoEpd FROM Empreendimento WHERE DscSituacaoEpd IS NOT NULL "
                "GROUP BY 1 ORDER BY COUNT(*) DESC"
            ),
        ),
    ),
    visualizar=_visualizar_c6,
)


# ── Consulta 7 ──────────────────────────────────────────────────────────────
def _visualizar_c7(dados: pd.DataFrame, valores: dict[str, Any]) -> None:
    if dados.empty:
        st.info("Nenhuma obra para o tipo de módulo escolhido.")
        return
    obras_por_modulo = dados.groupby("ID do módulo").size()
    recorrentes = int((obras_por_modulo > 1).sum())
    linha_metricas(
        [
            Metrica("Obras", fmt.inteiro(len(dados))),
            Metrica("Empreendimentos", fmt.inteiro(dados["ID do empreendimento"].nunique())),
            Metrica("Módulos distintos", fmt.inteiro(len(obras_por_modulo))),
            Metrica(
                "Módulos com 2+ obras",
                fmt.inteiro(recorrentes),
                f"{fmt.percentual(recorrentes, len(obras_por_modulo))} — evidência da cardinalidade 1:N",
            ),
        ]
    )

    dados = dados.assign(**{"Situação da obra": dados["Situação da obra"].fillna(SEM_SITUACAO)})
    esquerda, direita = st.columns([1.4, 1], gap="large")
    with esquerda:
        cruzamento = dados.groupby(["Tipo de módulo", "Situação da obra"]).size().reset_index(name="n")
        fig = charts.barras_empilhadas(
            cruzamento,
            "Tipo de módulo",
            "Situação da obra",
            "n",
            cores=CORES_SITUACAO,
            ordem_series=list(CORES_SITUACAO),
            normalizar=True,
            titulo="Situação das obras dentro de cada tipo de módulo",
        )
        legenda_situacao(cruzamento["Situação da obra"])
        grafico(fig, chave="c7-cruzamento")
        totais = dados["Tipo de módulo"].value_counts()
        st.caption(
            "Volume por tipo: "
            + " · ".join(f"{t} **{fmt.inteiro(n)}** ({fmt.percentual(n, len(dados))})" for t, n in totais.items())
        )
    with direita:
        tipos_obra = (
            dados["Tipo de obra"].fillna("Não informado").value_counts().rename_axis("tipo").reset_index(name="obras")
        )
        grafico(
            charts.barras_horizontais(tipos_obra, "tipo", "obras", titulo="Obras por tipo de intervenção"),
            chave="c7-tipo-obra",
        )


CONSULTA_7 = Consulta(
    numero=7,
    titulo="Empreendimento → obra → módulo",
    pergunta="Quais obras compõem cada empreendimento e quais módulos estão envolvidos?",
    descricao=(
        "Junta Empreendimento, Obra e Modulo pelos identificadores IdeEpd e IdeMdl para detalhar "
        "as obras, sua situação de execução e o tipo da unidade funcional (módulo) associada."
    ),
    categoria=Categoria.JUNCAO_MULTIPLA,
    relacoes=("Empreendimento", "Obra", "Modulo"),
    sql="""
SELECT e.IdeEpd AS "ID do empreendimento",
       e.NomEpd AS "Empreendimento",
       o.IdeObr AS "ID da obra",
       o.DscTipObr AS "Tipo de obra",
       o.DscSitObr AS "Situação da obra",
       m.IdeMdl AS "ID do módulo",
       m.NomMdl AS "Módulo",
       m.DscTipMdl AS "Tipo de módulo",
       m.DscClfMdl AS "Classificação do módulo"
FROM Empreendimento AS e
JOIN Obra AS o ON o.IdeEpd = e.IdeEpd
JOIN Modulo AS m ON m.IdeMdl = o.IdeMdl
WHERE :tipo_modulo IS NULL OR m.DscTipMdl = :tipo_modulo
ORDER BY e.IdeEpd, o.IdeObr;
""".strip(),
    parametros=(
        Parametro(
            "tipo_modulo",
            "Tipo de módulo",
            "escolha",
            padrao=None,
            opcoes_sql="SELECT DscTipMdl FROM Modulo GROUP BY 1 ORDER BY COUNT(*) DESC",
        ),
    ),
    visualizar=_visualizar_c7,
)


# ── Consulta 8 ──────────────────────────────────────────────────────────────
def _visualizar_c8(dados: pd.DataFrame, valores: dict[str, Any]) -> None:
    if dados.empty:
        st.info("Nenhum módulo de linha no intervalo de tensão escolhido.")
        return
    validos = dados[(dados["Extensão (km)"] > 0) & (dados["Torres"] > 0)].copy()
    validos["Torres por km"] = validos["Torres"] / validos["Extensão (km)"]
    linha_metricas(
        [
            Metrica("Módulos de linha", fmt.inteiro(len(dados))),
            Metrica(
                "Extensão somada",
                f"{fmt.decimal(dados['Extensão (km)'].sum() / 1000, 1)} mil km",
                f"{fmt.decimal(dados['Extensão (km)'].sum(), 1)} km",
            ),
            Metrica("Torres somadas", fmt.inteiro(dados["Torres"].sum())),
            Metrica(
                "Mediana torres/km",
                fmt.decimal(validos["Torres por km"].median(), 2),
                f"Média {fmt.decimal(validos['Torres por km'].mean(), 2)} · {fmt.inteiro(len(validos))} módulos com km e torres > 0",
            ),
        ]
    )

    esquerda, direita = st.columns([1.55, 1], gap="large")
    with esquerda:
        validos["classe"] = validos["Tensão (kV)"].map(classe_tensao)
        fig = go.Figure()
        for classe in ORDEM_CLASSES:
            parte = validos[validos["classe"] == classe]
            if parte.empty:
                continue
            fig.add_scatter(
                x=parte["Extensão (km)"],
                y=parte["Torres"],
                mode="markers",
                name=classe,
                marker=dict(color=CORES_CLASSES[classe], size=7, opacity=0.78, line=dict(width=0.5, color="#FFFFFF")),
                customdata=np.stack(
                    [parte["Linha de transmissão"], parte["Circuitos"].astype("Int64").astype(str)], axis=-1
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>%{x:,.1f} km · %{y:,.0f} torres"
                    "<br>Circuitos: %{customdata[1]}<extra></extra>"
                ),
            )
        mediana = validos["Torres por km"].median()
        xs = np.geomspace(max(validos["Extensão (km)"].min(), 0.1), validos["Extensão (km)"].max(), 50)
        fig.add_scatter(
            x=xs,
            y=xs * mediana,
            mode="lines",
            name=f"Mediana: {fmt.decimal(mediana, 2)} torres/km",
            line=dict(color=COR.tinta, dash="dot", width=1.5),
            hoverinfo="skip",
        )
        fig.update_layout(
            title="Extensão × torres por módulo (escala log)",
            height=460,
            showlegend=False,
            xaxis=dict(type="log", dtick=1, title="Extensão (km)"),
            yaxis=dict(type="log", dtick=1, title="Torres"),
        )
        legenda_tensao()
        grafico(fig, chave="c8-dispersao")
        st.caption(f"Linha pontilhada: densidade mediana de {fmt.decimal(mediana, 2)} torres/km.")
    with direita:
        circuitos = (
            dados.groupby("Circuitos", dropna=False)
            .agg(modulos=("ID do módulo", "count"), extensao=("Extensão (km)", "mean"))
            .reset_index()
        )
        circuitos["Circuitos"] = circuitos["Circuitos"].map(lambda c: "n/d" if pd.isna(c) else str(int(c)))
        circuitos = circuitos.sort_values("modulos", ascending=False)
        st.markdown("**Módulos por número de circuitos**")
        st.dataframe(
            circuitos.rename(columns={"modulos": "Módulos", "extensao": "Extensão média (km)"}),
            hide_index=True,
            width="stretch",
            column_config={
                "Módulos": st.column_config.ProgressColumn(
                    format="%d", min_value=0, max_value=int(circuitos["modulos"].max())
                ),
                "Extensão média (km)": st.column_config.NumberColumn(format="%.1f"),
            },
        )
        st.caption("Os códigos 0 e 99 são registros atípicos do cadastro original.")


CONSULTA_8 = Consulta(
    numero=8,
    titulo="Módulos de linha",
    pergunta="Quais módulos pertencem às linhas de transmissão e quais são suas características técnicas?",
    descricao=(
        "Junta Modulo, ModuloLinha e LinhaTransmissao pelos identificadores IdeMdl e IdeLinTms para "
        "recuperar tensão, extensão, número de circuitos e quantidade de torres de cada módulo de linha."
    ),
    categoria=Categoria.JUNCAO_MULTIPLA,
    relacoes=("Modulo", "ModuloLinha", "LinhaTransmissao"),
    sql="""
SELECT lt.IdeLinTms AS "ID da linha",
       lt.NomLinTms AS "Linha de transmissão",
       lt.NumTensaoBaseLinhaTransm AS "Tensão (kV)",
       m.IdeMdl AS "ID do módulo",
       m.NomMdl AS "Módulo",
       m.DscSituacaoModulo AS "Situação do módulo",
       ml.NumCcuLinTms AS "Circuitos",
       ml.QtdTorLinTms AS "Torres",
       ml.NumEtnLinTms AS "Extensão (km)"
FROM Modulo AS m
JOIN ModuloLinha AS ml ON ml.IdeMdl = m.IdeMdl
JOIN LinhaTransmissao AS lt ON lt.IdeLinTms = ml.IdeLinTms
WHERE lt.NumTensaoBaseLinhaTransm BETWEEN :tensao_min AND :tensao_max
ORDER BY ml.NumEtnLinTms DESC, lt.NumTensaoBaseLinhaTransm DESC, m.IdeMdl;
""".strip(),
    parametros=(
        Parametro(
            "tensao",
            "Faixa de tensão-base",
            "intervalo",
            padrao=(69.0, 800.0),
            opcoes_sql=NIVEIS_TENSAO_SQL,
            formatar=lambda v: f"{v:g} kV",
        ),
    ),
    visualizar=_visualizar_c8,
)
