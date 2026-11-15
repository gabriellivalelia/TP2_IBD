"""Consultas 3, 4 e 5 — junção de duas relações."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from siget.queries.base import Categoria, Consulta, Parametro
from siget.ui import charts
from siget.ui import formatting as fmt
from siget.ui.components import Metrica, grafico, linha_metricas
from siget.ui.theme import COR

UFS_SUBESTACAO_SQL = "SELECT DISTINCT SigUFSubestacao FROM Subestacao WHERE SigUFSubestacao IS NOT NULL ORDER BY 1"


def _rotulo_curto(texto: str, limite: int = 34) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


# ── Consulta 3 ──────────────────────────────────────────────────────────────
def _visualizar_c3(dados: pd.DataFrame, valores: dict[str, Any]) -> None:
    if dados.empty:
        st.info("Nenhum agente corresponde à busca. Tente parte da razão social, como “AXIA” ou “ISA”.")
        return

    por_agente = dados.groupby(["ID do agente", "Agente"]).size().sort_values(ascending=False)
    varios = por_agente[por_agente > 1]
    linha_metricas(
        [
            Metrica("Contratos", fmt.inteiro(len(dados))),
            Metrica("Agentes", fmt.inteiro(len(por_agente))),
            Metrica(
                "Agentes com 2+ contratos",
                fmt.inteiro(len(varios)),
                f"{fmt.percentual(len(varios), len(por_agente))} dos agentes",
            ),
            Metrica(
                "Contratos desse grupo",
                fmt.percentual(varios.sum(), len(dados)),
                f"{fmt.inteiro(varios.sum())} contratos",
            ),
        ]
    )

    esquerda, direita = st.columns([1, 1.2], gap="large")
    with esquerda:
        distribuicao = por_agente.value_counts().sort_index().rename_axis("contratos").reset_index(name="agentes")
        fig = go.Figure(
            go.Bar(
                x=distribuicao["contratos"].astype(str),
                y=distribuicao["agentes"],
                marker=dict(
                    color=[COR.nevoa if c == 1 else COR.petroleo for c in distribuicao["contratos"]],
                    line=dict(width=0),
                ),
                text=distribuicao["agentes"],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="%{y} agentes com %{x} contrato(s)<extra></extra>",
            )
        )
        fig.update_layout(
            title="Quantos contratos cada agente detém",
            height=360,
            xaxis=dict(title="Contratos por agente", showgrid=False, type="category"),
            yaxis=dict(title="Agentes"),
        )
        grafico(fig, chave="c3-distribuicao")
    with direita:
        topo = por_agente.head(10).reset_index(name="contratos")
        topo["Agente"] = topo["Agente"].map(_rotulo_curto)
        grafico(
            charts.barras_horizontais(topo, "Agente", "contratos", titulo="Agentes com mais contratos"),
            chave="c3-ranking",
        )


CONSULTA_3 = Consulta(
    numero=3,
    titulo="Contratos por agente",
    pergunta="Quais contratos pertencem a cada agente de transmissão?",
    descricao=(
        "Junta Agente e Contrato pelo identificador do agente para listar os contratos de cada "
        "agente de transmissão. A busca opcional restringe pela razão social."
    ),
    categoria=Categoria.JUNCAO_DUAS,
    relacoes=("Agente", "Contrato"),
    sql="""
SELECT a.IdAgente AS "ID do agente",
       a.DscRazaoSocial AS "Agente",
       c.IdeCcd AS "ID do contrato",
       c.NumCnaCcd AS "Nº do contrato"
FROM Agente AS a
JOIN Contrato AS c ON c.IdAgente = a.IdAgente
WHERE :agente IS NULL OR a.DscRazaoSocial LIKE '%' || :agente || '%'
ORDER BY a.DscRazaoSocial, a.IdAgente, c.IdeCcd;
""".strip(),
    parametros=(
        Parametro(
            "agente",
            "Buscar agente (razão social)",
            "texto",
            padrao="",
            ajuda="Busca parcial, sem diferenciar maiúsculas.",
        ),
    ),
    visualizar=_visualizar_c3,
)


# ── Consulta 4 ──────────────────────────────────────────────────────────────
def _visualizar_c4(dados: pd.DataFrame, valores: dict[str, Any]) -> None:
    terminais = dados.pivot(index="ID da linha", columns="Papel", values="UF")
    completos = terminais.dropna(subset=[c for c in ("Origem", "Destino") if c in terminais])
    if completos.empty or not {"Origem", "Destino"} <= set(completos.columns):
        st.info("Nenhuma linha com os dois terminais para o filtro escolhido.")
        return
    mesma_uf = completos["Origem"].eq(completos["Destino"])

    linha_metricas(
        [
            Metrica("Vínculos linha–subestação", fmt.inteiro(len(dados))),
            Metrica("Linhas", fmt.inteiro(dados["ID da linha"].nunique())),
            Metrica("Subestações", fmt.inteiro(dados["ID da subestação"].nunique())),
            Metrica(
                "Linhas interestaduais",
                fmt.percentual((~mesma_uf).sum(), len(completos)),
                f"{fmt.inteiro((~mesma_uf).sum())} de {fmt.inteiro(len(completos))} com as duas UFs",
            ),
        ]
    )

    matriz = pd.crosstab(completos["Origem"], completos["Destino"])
    ufs = sorted(set(matriz.index) | set(matriz.columns))
    matriz = matriz.reindex(index=ufs, columns=ufs, fill_value=0)
    fig = charts.mapa_calor(
        matriz,
        titulo="Origem × destino das linhas, por UF",
        rotulo_x="UF de destino",
        rotulo_y="UF de origem",
        nome_valor="Linhas",
        log=True,
    )
    grafico(fig, chave="c4-matriz", rolagem=True)
    st.caption(
        "A diagonal concentra as linhas internas a uma UF; fora dela estão as interligações. Cor em escala logarítmica."
    )

    inter = completos[~mesma_uf]
    pares = (
        inter.apply(lambda r: " ↔ ".join(sorted((r["Origem"], r["Destino"]))), axis=1)
        .value_counts()
        .head(10)
        .rename_axis("corredor")
        .reset_index(name="linhas")
    )
    esquerda, direita = st.columns([1.3, 1], gap="large")
    with esquerda:
        grafico(
            charts.barras_horizontais(
                pares, "corredor", "linhas", titulo="Principais corredores interestaduais", cores=COR.ambar
            ),
            chave="c4-corredores",
        )
    with direita:
        internas = completos[mesma_uf]["Origem"].value_counts().head(10).rename_axis("uf").reset_index(name="linhas")
        grafico(
            charts.barras_horizontais(internas, "uf", "linhas", titulo="UFs com mais linhas internas"),
            chave="c4-internas",
        )


CONSULTA_4 = Consulta(
    numero=4,
    titulo="Terminais das linhas",
    pergunta="Quais subestações estão conectadas a cada linha e qual o seu papel?",
    descricao=(
        "Junta LinhaSubestacao e Subestacao pelo identificador da subestação para mostrar, para "
        "cada linha, o nome e a UF da subestação e seu papel de origem ou destino. O filtro de UF "
        "mantém as linhas com ao menos um terminal na UF escolhida."
    ),
    categoria=Categoria.JUNCAO_DUAS,
    relacoes=("LinhaSubestacao", "Subestacao"),
    sql="""
SELECT ls.IdeLinTms AS "ID da linha",
       s.IdeSbe AS "ID da subestação",
       s.NomSubestacao AS "Subestação",
       s.SigUFSubestacao AS "UF",
       ls.Papel
FROM LinhaSubestacao AS ls
JOIN Subestacao AS s ON s.IdeSbe = ls.IdeSbe
WHERE :uf IS NULL
   OR ls.IdeLinTms IN (SELECT x.IdeLinTms
                         FROM LinhaSubestacao AS x
                         JOIN Subestacao AS y ON y.IdeSbe = x.IdeSbe
                        WHERE y.SigUFSubestacao = :uf)
ORDER BY ls.IdeLinTms, ls.Papel DESC;
""".strip(),
    parametros=(Parametro("uf", "UF de algum terminal", "escolha", padrao=None, opcoes_sql=UFS_SUBESTACAO_SQL),),
    visualizar=_visualizar_c4,
)


# ── Consulta 5 ──────────────────────────────────────────────────────────────
def _visualizar_c5(dados: pd.DataFrame, valores: dict[str, Any]) -> None:
    if dados.empty:
        st.info("Nenhum módulo para os tipos escolhidos.")
        return
    tipos = dados["Tipo de equipamento"].value_counts()
    tres = tipos.head(3).sum()
    linha_metricas(
        [
            Metrica("Módulos de equipamento", fmt.inteiro(len(dados))),
            Metrica("Tipos", fmt.inteiro(len(tipos))),
            Metrica("Subestações", fmt.inteiro(dados["ID da subestação"].nunique())),
            Metrica("Três tipos principais", fmt.percentual(tres, len(dados)), f"{fmt.inteiro(tres)} módulos"),
        ]
    )
    esquerda, direita = st.columns(2, gap="large")
    with esquerda:
        tabela_tipos = tipos.rename_axis("tipo").reset_index(name="módulos")
        cores = [COR.petroleo if i < 3 else "#9DB7C7" for i in range(len(tabela_tipos))]
        grafico(
            charts.barras_horizontais(
                tabela_tipos, "tipo", "módulos", titulo="Módulos por tipo de equipamento", cores=cores
            ),
            chave="c5-tipos",
        )
    with direita:
        por_se = (
            dados.assign(rotulo=dados["Subestação"] + " (" + dados["UF"].fillna("?") + ")")
            .groupby("rotulo")
            .size()
            .sort_values(ascending=False)
            .head(12)
            .rename_axis("subestação")
            .reset_index(name="módulos")
        )
        grafico(
            charts.barras_horizontais(
                por_se, "subestação", "módulos", titulo="Subestações com mais módulos de equipamento", cores=COR.ambar
            ),
            chave="c5-subestacoes",
        )


CONSULTA_5 = Consulta(
    numero=5,
    titulo="Equipamentos por subestação",
    pergunta="Quais equipamentos estão cadastrados em cada subestação?",
    descricao=(
        "Junta ModuloEquipamento e Subestacao pelo identificador da subestação para listar os "
        "módulos de equipamento cadastrados em cada local. O vínculo cadastrado não informa se o "
        "equipamento está em operação."
    ),
    categoria=Categoria.JUNCAO_DUAS,
    relacoes=("ModuloEquipamento", "Subestacao"),
    sql="""
SELECT s.IdeSbe AS "ID da subestação",
       s.NomSubestacao AS "Subestação",
       s.SigUFSubestacao AS "UF",
       e.IdeMdl AS "ID do módulo",
       e.DscTipEqp AS "Tipo de equipamento"
FROM ModuloEquipamento AS e
JOIN Subestacao AS s ON s.IdeSbe = e.IdeSbe
WHERE :tipos IS NULL OR e.DscTipEqp IN (SELECT value FROM json_each(:tipos))
ORDER BY s.NomSubestacao, s.IdeSbe, e.IdeMdl;
""".strip(),
    parametros=(
        Parametro(
            "tipos",
            "Tipos de equipamento",
            "multipla",
            padrao=[],
            opcoes_sql="SELECT DscTipEqp FROM ModuloEquipamento GROUP BY 1 ORDER BY COUNT(*) DESC",
            ajuda="Sem seleção, todos os tipos são incluídos.",
        ),
    ),
    visualizar=_visualizar_c5,
)
