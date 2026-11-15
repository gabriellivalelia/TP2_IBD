"""Exploração da rede: subestações por UF, classes de tensão, arranjos e ficha da subestação."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from siget.data.database import consultar
from siget.ui import charts
from siget.ui import formatting as fmt
from siget.ui.components import Metrica, cabecalho_pagina, grafico, legenda_tensao, linha_metricas, secao
from siget.ui.theme import COR, CORES_CLASSES, ORDEM_CLASSES, classe_tensao

BRASIL = "Brasil"
CHAVE_UF = "rede-uf"

INDICADORES = {
    "Subestações": ("subestacoes", ",.0f"),
    "Terminais de linha": ("terminais", ",.0f"),
    "Subestações-polo (5+ linhas)": ("hubs", ",.0f"),
    "Potência de transformação (MVA)": ("potencia", ",.0f"),
    "Módulos de manobra": ("manobras", ",.0f"),
}


@st.cache_data(show_spinner=False)
def _por_subestacao() -> pd.DataFrame:
    return consultar(
        """
        SELECT s.IdeSbe AS id, s.NomSubestacao AS nome, s.SigUFSubestacao AS uf,
               COALESCE(l.n, 0) AS linhas,
               COALESCE(l.kv, 0) AS maior_kv,
               COALESCE(e.n, 0) AS equipamentos,
               COALESCE(e.mva, 0) AS potencia,
               COALESCE(m.n, 0) AS manobras
        FROM Subestacao AS s
        LEFT JOIN (SELECT ls.IdeSbe, COUNT(*) AS n, MAX(lt.NumTensaoBaseLinhaTransm) AS kv
                     FROM LinhaSubestacao AS ls
                     JOIN LinhaTransmissao AS lt ON lt.IdeLinTms = ls.IdeLinTms
                    GROUP BY ls.IdeSbe) AS l ON l.IdeSbe = s.IdeSbe
        LEFT JOIN (SELECT IdeSbe, COUNT(*) AS n,
                          SUM(CASE WHEN DscTipEqp LIKE 'Transformador de Pot%'
                                   THEN MdaPotAtvMdlEqp ELSE 0 END) AS mva
                     FROM ModuloEquipamento GROUP BY IdeSbe) AS e ON e.IdeSbe = s.IdeSbe
        LEFT JOIN (SELECT IdeSbe, COUNT(*) AS n FROM ModuloManobra GROUP BY IdeSbe) AS m ON m.IdeSbe = s.IdeSbe
        """
    )


def _por_uf(subestacoes: pd.DataFrame) -> pd.DataFrame:
    return (
        subestacoes.groupby("uf")
        .agg(
            subestacoes=("id", "count"),
            terminais=("linhas", "sum"),
            hubs=("linhas", lambda s: int((s >= 5).sum())),
            potencia=("potencia", "sum"),
            manobras=("manobras", "sum"),
        )
        .reset_index()
    )


def _sincronizar_selecao_mapa(evento) -> None:
    """Aplica o clique no mapa à UF em foco (somente quando o clique muda)."""
    pontos = (evento or {}).get("selection", {}).get("points", []) if evento else []
    assinatura = tuple(p.get("point_index") for p in pontos)
    if assinatura == st.session_state.get("rede-ultimo-clique"):
        return
    st.session_state["rede-ultimo-clique"] = assinatura
    if pontos:
        st.session_state[CHAVE_UF] = list(charts.GRADE_UF)[pontos[0]["point_index"]]


def render() -> None:
    cabecalho_pagina(
        "Explorar a base",
        "Rede elétrica",
        "Onde estão as subestações, quais concentram linhas e como a rede se distribui pelas classes "
        "de tensão. Clique em uma UF no mapa para focar a análise.",
    )
    subestacoes = _por_subestacao()
    por_uf = _por_uf(subestacoes)

    indicador = (
        st.segmented_control("Indicador do mapa", list(INDICADORES), default="Terminais de linha", key="rede-indicador")
        or "Terminais de linha"
    )
    coluna, formato = INDICADORES[indicador]

    mapa_col, foco_col = st.columns([1, 1.25], gap="large")
    with mapa_col:
        uf_atual = st.session_state.get(CHAVE_UF, BRASIL)
        evento = grafico(
            charts.mapa_ufs(
                por_uf,
                "uf",
                coluna,
                nome_valor=indicador,
                formato=formato,
                selecionadas=[uf_atual] if uf_atual != BRASIL else [],
            ),
            chave="rede-mapa",
            selecionavel=True,
        )
        _sincronizar_selecao_mapa(evento)
        st.caption("Cartograma: cada ladrilho é uma UF, na posição aproximada do mapa.")

    with foco_col:
        opcoes = [BRASIL, *sorted(por_uf["uf"])]
        uf = st.selectbox("UF em foco", opcoes, key=CHAVE_UF)
        recorte = subestacoes if uf == BRASIL else subestacoes[subestacoes["uf"] == uf]
        linha_metricas(
            [
                Metrica("Subestações", fmt.inteiro(len(recorte))),
                Metrica("Terminais de linha", fmt.inteiro(recorte["linhas"].sum())),
                Metrica("Polos (5+ linhas)", fmt.inteiro((recorte["linhas"] >= 5).sum())),
                Metrica(
                    "Transformação",
                    f"{fmt.inteiro(recorte['potencia'].sum())} MVA",
                    "Soma da potência dos transformadores de potência",
                ),
            ],
        )
        legenda_tensao()
        topo = recorte.sort_values(["linhas", "equipamentos"], ascending=False).head(10).copy()
        topo["rotulo"] = topo["nome"].str.title() + " · " + topo["uf"].fillna("?")
        grafico(
            charts.barras_horizontais(
                topo,
                "rotulo",
                "linhas",
                titulo=f"Subestações mais conectadas — {uf}",
                cores=[CORES_CLASSES.get(classe_tensao(k), COR.nevoa) for k in topo["maior_kv"]],
                hover="<b>%{y}</b><br>%{x} linhas<extra></extra>",
            ),
            chave="rede-topo",
        )
        st.caption("Cor da barra = maior classe de tensão que chega à subestação.")

    filtro_uf = None if uf == BRASIL else uf
    secao("Classes de tensão e arranjos", f"Recorte: {uf}")
    tensao_col, arranjo_col = st.columns(2, gap="large")
    with tensao_col:
        linhas = consultar(
            """
            SELECT DISTINCT lt.IdeLinTms, lt.NumTensaoBaseLinhaTransm AS kv
            FROM LinhaTransmissao AS lt
            JOIN LinhaSubestacao AS ls ON ls.IdeLinTms = lt.IdeLinTms
            JOIN Subestacao AS s ON s.IdeSbe = ls.IdeSbe
            WHERE :uf IS NULL OR s.SigUFSubestacao = :uf
            """,
            {"uf": filtro_uf},
        )
        classes = (
            linhas["kv"]
            .map(classe_tensao)
            .value_counts()
            .reindex(ORDEM_CLASSES)
            .dropna()
            .rename_axis("classe")
            .reset_index(name="linhas")
            .iloc[::-1]
        )
        legenda_tensao()
        grafico(
            charts.barras_horizontais(
                classes,
                "classe",
                "linhas",
                titulo="Linhas por classe de tensão",
                cores=[CORES_CLASSES[c] for c in classes["classe"]],
            ),
            chave="rede-classes",
        )
    with arranjo_col:
        arranjos = consultar(
            """
            SELECT COALESCE(m.DscTipAnj, 'Não informado') AS arranjo, COUNT(*) AS modulos
            FROM ModuloManobra AS m
            JOIN Subestacao AS s ON s.IdeSbe = m.IdeSbe
            WHERE :uf IS NULL OR s.SigUFSubestacao = :uf
            GROUP BY 1 ORDER BY 2 DESC LIMIT 10
            """,
            {"uf": filtro_uf},
        )
        grafico(
            charts.barras_horizontais(arranjos, "arranjo", "modulos", titulo="Arranjos de manobra mais frequentes"),
            chave="rede-arranjos",
        )

    _ficha_subestacao(recorte)


def _ficha_subestacao(recorte: pd.DataFrame) -> None:
    secao("Ficha da subestação", "Linhas, equipamentos e manobras de uma instalação")
    ordenadas = recorte.sort_values("linhas", ascending=False)
    if ordenadas.empty:
        st.info("Nenhuma subestação nesta UF.")
        return
    escolha = st.selectbox(
        "Subestação",
        ordenadas["id"].tolist(),
        format_func=lambda i: (
            f"{ordenadas.set_index('id').at[i, 'nome'].title()} · {ordenadas.set_index('id').at[i, 'uf']}"
        ),
        key="rede-ficha",
    )
    se = ordenadas.set_index("id").loc[escolha]
    linha_metricas(
        [
            Metrica("Linhas conectadas", fmt.inteiro(se["linhas"])),
            Metrica("Maior tensão", f"{se['maior_kv']:g} kV" if se["maior_kv"] else "—"),
            Metrica("Módulos de equipamento", fmt.inteiro(se["equipamentos"])),
            Metrica("Módulos de manobra", fmt.inteiro(se["manobras"])),
        ]
    )
    ligacoes = consultar(
        """
        SELECT lt.NomLinTms AS "Linha",
               lt.NumTensaoBaseLinhaTransm AS "Tensão (kV)",
               ls.Papel AS "Papel desta SE",
               outra.NomSubestacao AS "Outra ponta",
               outra.SigUFSubestacao AS "UF",
               lt.DscSitLinTms AS "Situação"
        FROM LinhaSubestacao AS ls
        JOIN LinhaTransmissao AS lt ON lt.IdeLinTms = ls.IdeLinTms
        LEFT JOIN LinhaSubestacao AS lo ON lo.IdeLinTms = ls.IdeLinTms AND lo.IdeSbe <> ls.IdeSbe
        LEFT JOIN Subestacao AS outra ON outra.IdeSbe = lo.IdeSbe
        WHERE ls.IdeSbe = :id
        ORDER BY lt.NumTensaoBaseLinhaTransm DESC, lt.NomLinTms
        """,
        {"id": escolha},
    )
    equipamentos = consultar(
        """
        SELECT DscTipEqp AS "Tipo", COUNT(*) AS "Módulos",
               ROUND(SUM(COALESCE(MdaPotAtvMdlEqp, 0)), 1) AS "Potência (MVA)"
        FROM ModuloEquipamento WHERE IdeSbe = :id GROUP BY 1 ORDER BY 2 DESC
        """,
        {"id": escolha},
    )
    esquerda, direita = st.columns([1.7, 1], gap="large")
    with esquerda:
        st.markdown("**Linhas de transmissão**")
        if ligacoes.empty:
            st.caption("Sem linhas cadastradas: a subestação aparece apenas por equipamentos ou manobras.")
        else:
            st.dataframe(ligacoes, hide_index=True, width="stretch")
    with direita:
        st.markdown("**Equipamentos**")
        if equipamentos.empty:
            st.caption("Sem módulos de equipamento cadastrados.")
        else:
            st.dataframe(equipamentos, hide_index=True, width="stretch")
