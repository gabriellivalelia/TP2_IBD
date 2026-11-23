"""Seção 3 do relatório: origem dos dados, limpeza e auditoria das rejeições."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from siget import settings
from siget.data.audit import arquivos_rejeicao, auditoria, ler_rejeicao
from siget.data.database import esquema
from siget.ui import charts
from siget.ui import formatting as fmt
from siget.ui.components import (
    Etapa,
    cabecalho_pagina,
    destaque_markdown,
    faixa_etapas,
    grafico,
    secao,
    tabela,
)
from siget.ui.theme import COR
from siget.views.modelagem import CORES_PAPEL, PAPEIS

ROTULO_ETAPA = {"extracao": "Extração", "rejeicao": "Rejeição", "limpeza": "Limpeza"}


def render() -> None:
    cabecalho_pagina(
        "Seção 3 do relatório",
        "Dados e tratamento",
        "Cinco arquivos CSV do SIGET viraram onze relações. Esta página mostra de onde os dados "
        "vieram, o que a limpeza removeu e por quê — com cada registro descartado disponível para conferência.",
    )

    log = auditoria()
    perdas = log[log["etapa"].isin(["rejeicao", "limpeza"])]
    tabelas = esquema()
    originais = sum(n for _, n, _ in settings.ARQUIVOS_ORIGINAIS)

    faixa_etapas(
        [
            Etapa(
                "Registros originais",
                fmt.inteiro(originais),
                "em 5 arquivos CSV (Latin-1, separador ;)",
            ),
            Etapa(
                "Removidos",
                f"−{fmt.inteiro(perdas['quantidade'].sum())}",
                f"{len(perdas)} regras de rejeição e limpeza",
                "loss",
            ),
            Etapa(
                "Relações",
                fmt.inteiro(len(tabelas)),
                "após decomposição por dependências funcionais",
            ),
            Etapa(
                "Tuplas",
                fmt.inteiro(sum(t.linhas for t in tabelas)),
                "no banco SQLite normalizado",
                "final",
            ),
        ]
    )

    esquerda, direita = st.columns([1, 1.1], gap="large")
    with esquerda:
        secao("Arquivos originais", "Tabela 1")
        arquivos = pd.DataFrame(
            settings.ARQUIVOS_ORIGINAIS, columns=["Arquivo", "Registros", "Atributos"]
        )
        st.dataframe(
            arquivos,
            hide_index=True,
            width="stretch",
            column_config={
                "Arquivo": st.column_config.TextColumn(width="large"),
                "Registros": st.column_config.ProgressColumn(
                    format="%d",
                    min_value=0,
                    max_value=int(arquivos["Registros"].max()),
                    width="medium",
                ),
                "Atributos": st.column_config.NumberColumn(width="small"),
            },
        )
        st.caption(f"Total: {fmt.inteiro(arquivos['Registros'].sum())} registros.")
        st.caption(
            f"[Conjunto de dados no portal dados.gov.br]({settings.DATASET_URL})"
        )
    with direita:
        secao("Relações resultantes", "Tabela 2")
        relacoes = pd.DataFrame(
            [(t.nome, t.linhas, PAPEIS.get(t.nome, "Entidade")) for t in tabelas],
            columns=["Relação", "Tuplas", "Papel"],
        ).sort_values("Tuplas", ascending=False)
        legenda = "".join(
            f'<span><i style="background:{c}"></i>{p}</span>'
            for p, c in CORES_PAPEL.items()
        )
        st.html(f'<div class="sg-legend">{legenda}</div>')
        grafico(
            charts.barras_horizontais(
                relacoes,
                "Relação",
                "Tuplas",
                cores=[CORES_PAPEL[p] for p in relacoes["Papel"]],
            ),
            chave="dados-relacoes",
        )

    secao("O que a limpeza removeu", "Registro de auditoria (auditoria.csv)")
    texto_col, grafico_col = st.columns([1, 2], gap="large")
    with texto_col:
        destaque_markdown(
            "Critério adotado",
            "Registros inválidos foram **excluídos**, não corrigidos por suposição, e a exclusão se "
            "propaga aos dependentes.\n\n"
            "- 1 contrato sem agente identificado;\n"
            "- 293 linhas do arquivo central apontavam para 14 contratos inexistentes;\n"
            "- módulos especializados que ficaram sem obra válida;\n"
            "- 6 subestações com atributos contraditórios, e tudo o que dependia delas.",
            chave="dados-criterio",
        )
    with grafico_col:
        resumo = perdas.assign(
            regra=perdas["tabela"] + " · " + perdas["motivo"]
        ).sort_values("quantidade", ascending=False)
        grafico(
            charts.barras_horizontais(
                resumo,
                "regra",
                "quantidade",
                cores=COR.alerta,
                titulo="Registros removidos por regra",
            ),
            chave="dados-perdas",
        )

    with st.expander("Registro completo de auditoria, na ordem de execução"):
        exibicao = log.assign(etapa=log["etapa"].map(ROTULO_ETAPA).fillna(log["etapa"]))
        st.dataframe(
            exibicao,
            hide_index=True,
            width="stretch",
            column_config={
                "ordem": st.column_config.NumberColumn("#", width="small"),
                "quantidade": st.column_config.ProgressColumn(
                    "Quantidade",
                    format="%d",
                    min_value=0,
                    max_value=int(log["quantidade"].max()),
                ),
            },
        )

    secao("Conferir registros removidos", "Arquivos revisar_*.csv")
    arquivos_rej = arquivos_rejeicao()
    escolhido = st.selectbox(
        "Arquivo de rejeição",
        arquivos_rej,
        format_func=lambda a: a.rotulo,
        key="dados-rejeicao",
    )
    if escolhido:
        tabela(
            ler_rejeicao(escolhido.caminho),
            chave="dados-rejeitados",
            altura=340,
            nome_arquivo=escolhido.caminho.stem,
        )

    secao("Uma correção feita pela aplicação")
    st.markdown(
        "Os textos do banco foram gravados com acentuação corrompida (UTF-8 lido como Latin-1: "
        "`OperaÃ§Ã£o`). O notebook corrige isso ao exibir cada resultado. A aplicação faz a mesma "
        "correção uma única vez, em uma **réplica somente leitura** do banco, sem alterar "
        "o arquivo original. Assim, filtros com acento funcionam no próprio SQL."
    )
