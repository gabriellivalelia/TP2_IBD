"""Consultas 1 e 2 — seleção (σ) e projeção (π) sobre uma única relação."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from siget.data.database import consultar, escalar
from siget.queries.base import Categoria, Consulta, Parametro
from siget.ui import charts
from siget.ui import formatting as fmt
from siget.ui.components import Metrica, grafico, legenda_tensao, linha_metricas
from siget.ui.theme import COR, cor_tensao

NIVEIS_TENSAO_SQL = (
    "SELECT DISTINCT NumTensaoBaseLinhaTransm FROM LinhaTransmissao "
    "WHERE NumTensaoBaseLinhaTransm IS NOT NULL ORDER BY 1"
)


# ── Consulta 1 ──────────────────────────────────────────────────────────────
def _visualizar_c1(dados: pd.DataFrame, valores: dict[str, Any]) -> None:
    minimo = valores["tensao_minima"]
    total = int(escalar("SELECT COUNT(*) FROM LinhaTransmissao"))
    contagem = dados["Tensão (kV)"].value_counts().sort_index()

    linha_metricas(
        [
            Metrica("Linhas selecionadas", fmt.inteiro(len(dados))),
            Metrica("Fração da base", fmt.percentual(len(dados), total), f"Sobre {fmt.inteiro(total)} linhas"),
            Metrica("Níveis de tensão", fmt.inteiro(len(contagem))),
            Metrica(
                "Nível mais frequente",
                f"{contagem.idxmax():g} kV" if len(contagem) else "—",
                f"{fmt.percentual(contagem.max(), len(dados))} das linhas selecionadas" if len(contagem) else None,
            ),
        ]
    )

    # Escada de tensões: toda a base, com os níveis selecionados "energizados".
    base = consultar(
        "SELECT NumTensaoBaseLinhaTransm AS kv, COUNT(*) AS linhas FROM LinhaTransmissao GROUP BY 1 ORDER BY 1"
    )
    base["nivel"] = base["kv"].map(lambda v: f"{v:g} kV")
    cores = [cor_tensao(kv) if kv >= minimo else "#E3E8EB" for kv in base["kv"]]
    fig = charts.barras_horizontais(
        base.iloc[::-1],
        "nivel",
        "linhas",
        cores=cores[::-1],
        titulo=f"Linhas por tensão-base — em cor, os níveis ≥ {minimo:g} kV",
        hover="<b>%{y}</b><br>%{x} linhas<extra></extra>",
    )
    legenda_tensao()
    grafico(fig, chave="c1-escada")


CONSULTA_1 = Consulta(
    numero=1,
    titulo="Linhas de alta tensão",
    pergunta="Quais linhas de transmissão possuem tensão nominal igual ou superior a um limite?",
    descricao=(
        "Filtra as linhas de transmissão com tensão-base cadastrada de pelo menos o limite "
        "escolhido (500 kV no relatório) e exibe o código, o nome e a tensão de cada linha."
    ),
    categoria=Categoria.SELECAO,
    relacoes=("LinhaTransmissao",),
    sql="""
SELECT IdeLinTms AS "ID da linha",
       NomLinTms AS "Linha",
       NumTensaoBaseLinhaTransm AS "Tensão (kV)"
FROM LinhaTransmissao
WHERE NumTensaoBaseLinhaTransm >= :tensao_minima
ORDER BY NumTensaoBaseLinhaTransm DESC, NomLinTms, IdeLinTms;
""".strip(),
    parametros=(
        Parametro(
            "tensao_minima",
            "Tensão mínima",
            "degraus",
            padrao=500.0,
            opcoes_sql=NIVEIS_TENSAO_SQL,
            formatar=lambda v: f"{v:g} kV",
            ajuda="Níveis de tensão-base existentes na base normalizada.",
        ),
    ),
    visualizar=_visualizar_c1,
)


# ── Consulta 2 ──────────────────────────────────────────────────────────────
# Famílias de termos que indicam a natureza da intervenção descrita no nome.
TERMOS_INTERVENCAO: dict[str, str] = {
    "Substituição": r"substitu",
    "Instalação / implantação": r"instala|implant",
    "Adequação": r"adequa",
    "Ampliação": r"amplia",
    "Reforço": r"refor[çc]",
    "Seccionamento": r"secciona",
    "Recapacitação": r"recapacita",
    "Transformação (TR/AT)": r"transformador|autotransformador|\bat\b|\btr\b",
    "Compensação reativa": r"reator|capacitor|compensador",
}


def _visualizar_c2(dados: pd.DataFrame, valores: dict[str, Any]) -> None:
    total = int(escalar("SELECT COUNT(*) FROM Empreendimento"))
    nomes = dados["Empreendimento"].fillna("").str.lower()
    frequencia = pd.DataFrame(
        {
            "termo": list(TERMOS_INTERVENCAO),
            "empreendimentos": [
                int(nomes.str.contains(padrao, regex=True).sum()) for padrao in TERMOS_INTERVENCAO.values()
            ],
        }
    ).sort_values("empreendimentos", ascending=False)
    substituicoes = int(nomes.str.contains("substitui", regex=False).sum())

    linha_metricas(
        [
            Metrica("Empreendimentos", fmt.inteiro(len(dados))),
            Metrica("Fração da base", fmt.percentual(len(dados), total), f"Sobre {fmt.inteiro(total)}"),
            Metrica(
                "Citam “substitui”",
                fmt.inteiro(substituicoes),
                f"{fmt.percentual(substituicoes, len(dados))} dos selecionados",
            ),
        ]
    )

    esquerda, direita = st.columns([1.25, 1], gap="large")
    with esquerda:
        fig = charts.barras_horizontais(
            frequencia,
            "termo",
            "empreendimentos",
            titulo="Natureza da intervenção, segundo o nome",
            destaque="Substituição",
        )
        grafico(fig, chave="c2-termos")
    with direita:
        st.caption("COMO LER")
        st.markdown(
            "Cada barra conta os empreendimentos cujo **nome** contém o termo. "
            "Um nome pode citar mais de um termo, então as barras não somam o total. "
            "A classificação é textual e complementa a situação cadastral."
        )
        situacoes = consultar(
            "SELECT COALESCE(DscSituacaoEpd, 'Não informada') AS s, COUNT(*) AS n "
            "FROM Empreendimento GROUP BY 1 ORDER BY 2 DESC"
        )
        atual = valores.get("situacao") or ""
        for s, n in situacoes.itertuples(index=False):
            marcador = "●" if s == atual else "○"
            st.markdown(
                f"<span style='color:{COR.ambar if s == atual else COR.nevoa}'>{marcador}</span> "
                f"{s} — **{fmt.inteiro(n)}** ({fmt.percentual(n, total)})",
                unsafe_allow_html=True,
            )


CONSULTA_2 = Consulta(
    numero=2,
    titulo="Empreendimentos por situação",
    pergunta="Quais empreendimentos estão em determinada situação cadastral?",
    descricao=(
        "Filtra os empreendimentos pela situação cadastral (Em andamento no relatório) e exibe "
        "o código, o nome e a situação de cada um."
    ),
    categoria=Categoria.SELECAO,
    relacoes=("Empreendimento",),
    sql="""
SELECT IdeEpd AS "ID",
       NomEpd AS "Empreendimento",
       DscSituacaoEpd AS "Situação"
FROM Empreendimento
WHERE DscSituacaoEpd = :situacao
ORDER BY NomEpd, IdeEpd;
""".strip(),
    parametros=(
        Parametro(
            "situacao",
            "Situação do empreendimento",
            "escolha",
            permite_todos=False,
            padrao="Em andamento",
            opcoes_sql=(
                "SELECT DscSituacaoEpd FROM Empreendimento WHERE DscSituacaoEpd IS NOT NULL "
                "GROUP BY 1 ORDER BY COUNT(*) DESC"
            ),
        ),
    ),
    visualizar=_visualizar_c2,
)
