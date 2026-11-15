"""Laboratório SQL: consultas livres, em modo somente leitura, sobre o banco normalizado."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from siget import settings
from siget.data.database import ErroConsulta, esquema, executar_livre
from siget.data.report import trechos_consultas
from siget.ui import formatting as fmt
from siget.ui.components import Metrica, cabecalho_pagina, grafico, linha_metricas, secao, tabela
from siget.ui.theme import COR

CHAVE_SQL = "lab-sql"

EXEMPLOS: dict[str, str] = {
    "Linhas por classe de tensão": """SELECT NumTensaoBaseLinhaTransm AS tensao_kv,
       COUNT(*) AS linhas,
       SUM(DscSitLinTms = 'Ativa') AS ativas
FROM LinhaTransmissao
GROUP BY tensao_kv
ORDER BY tensao_kv;""",
    "Obras por tipo e situação": """SELECT o.DscTipObr AS tipo_obra,
       o.DscSitObr AS situacao,
       COUNT(*) AS obras
FROM Obra AS o
GROUP BY 1, 2
ORDER BY obras DESC;""",
    "Potência instalada por UF": """SELECT s.SigUFSubestacao AS uf,
       COUNT(*) AS transformadores,
       ROUND(SUM(e.MdaPotAtvMdlEqp), 0) AS potencia_mva
FROM ModuloEquipamento AS e
JOIN Subestacao AS s ON s.IdeSbe = e.IdeSbe
WHERE e.DscTipEqp LIKE 'Transformador de Pot%'
GROUP BY uf
ORDER BY potencia_mva DESC;""",
    "Linhas interestaduais (auto-junção)": """SELECT lt.NomLinTms AS linha,
       lt.NumTensaoBaseLinhaTransm AS kv,
       so.SigUFSubestacao AS uf_origem,
       sd.SigUFSubestacao AS uf_destino
FROM LinhaTransmissao AS lt
JOIN LinhaSubestacao AS o ON o.IdeLinTms = lt.IdeLinTms AND o.Papel = 'Origem'
JOIN LinhaSubestacao AS d ON d.IdeLinTms = lt.IdeLinTms AND d.Papel = 'Destino'
JOIN Subestacao AS so ON so.IdeSbe = o.IdeSbe
JOIN Subestacao AS sd ON sd.IdeSbe = d.IdeSbe
WHERE so.SigUFSubestacao <> sd.SigUFSubestacao
ORDER BY kv DESC;""",
    "Contratos que vencem até 2030": """SELECT a.DscRazaoSocial AS agente,
       c.NumCnaCcd AS contrato,
       c.DatFimCcd AS termino
FROM Contrato AS c
JOIN Agente AS a ON a.IdAgente = c.IdAgente
WHERE c.DatFimCcd <= '2030-12-31'
ORDER BY c.DatFimCcd;""",
}


def _usar_exemplo() -> None:
    escolha = st.session_state.get("lab-exemplo")
    if escolha in EXEMPLOS:
        st.session_state[CHAVE_SQL] = EXEMPLOS[escolha]
    elif escolha and escolha.startswith("Consulta "):
        numero = int(escolha.split()[1])
        st.session_state[CHAVE_SQL] = trechos_consultas()[numero].sql + ";"


def _referencia_esquema() -> None:
    st.markdown("**Esquema**")
    for tabela_ in esquema():
        with st.expander(f"{tabela_.nome} · {fmt.inteiro(tabela_.linhas)}"):
            linhas = [
                f"`{c.nome}` {c.tipo.lower()}"
                + (" · **PK**" if c.pk else "")
                + (f" · FK → `{c.fk_para}`" if c.fk_para else "")
                for c in tabela_.colunas
            ]
            st.markdown("  \n".join(linhas))


def _grafico_rapido(dados) -> None:
    numericas = dados.select_dtypes("number").columns.tolist()
    if not numericas or len(dados.columns) < 2:
        return
    with st.expander("Visualizar como gráfico de barras", icon=":material/bar_chart:"):
        col_x, col_y = st.columns(2)
        eixo_x = col_x.selectbox("Categoria", dados.columns.tolist(), key="lab-x")
        eixo_y = col_y.selectbox("Valor", numericas, index=len(numericas) - 1, key="lab-y")
        recorte = dados.head(60)
        fig = go.Figure(
            go.Bar(
                x=recorte[eixo_x].astype(str), y=recorte[eixo_y], marker=dict(color=COR.petroleo, line=dict(width=0))
            )
        )
        fig.update_layout(
            height=380, xaxis=dict(type="category", showgrid=False, title=eixo_x), yaxis=dict(title=eixo_y)
        )
        grafico(fig, chave="lab-grafico")
        if len(dados) > 60:
            st.caption("Mostrando as 60 primeiras linhas do resultado.")


def render() -> None:
    cabecalho_pagina(
        "Ferramentas",
        "Laboratório SQL",
        "Escreva consultas sobre o banco normalizado. O acesso é somente leitura, um comando por vez, "
        f"com limite de {fmt.inteiro(settings.SQL_LAB_MAX_ROWS)} linhas e {settings.SQL_LAB_TIMEOUT_S:g} s de execução.",
    )
    st.session_state.setdefault(CHAVE_SQL, EXEMPLOS["Linhas por classe de tensão"])

    editor_col, esquema_col = st.columns([2.6, 1], gap="large")
    with esquema_col:
        _referencia_esquema()
    with editor_col:
        opcoes = list(EXEMPLOS) + [f"Consulta {n} do relatório" for n in sorted(trechos_consultas())]
        st.selectbox(
            "Partir de um exemplo",
            opcoes,
            index=None,
            placeholder="Escolha um exemplo ou uma consulta do relatório…",
            key="lab-exemplo",
            on_change=_usar_exemplo,
        )
        with st.form("lab-form", border=False):
            st.text_area("Consulta SQL", key=CHAVE_SQL, height=260, label_visibility="collapsed")
            executar = st.form_submit_button("Executar", icon=":material/play_arrow:", type="primary")
        st.caption("Atalho: Ctrl + Enter dentro do editor.")

        if executar:
            try:
                st.session_state["lab-resultado"] = executar_livre(st.session_state[CHAVE_SQL])
                st.session_state.pop("lab-erro", None)
            except ErroConsulta as erro:
                st.session_state["lab-erro"] = str(erro)
                st.session_state.pop("lab-resultado", None)

        if erro := st.session_state.get("lab-erro"):
            st.error(erro, icon=":material/error:")
        elif resultado := st.session_state.get("lab-resultado"):
            secao("Resultado")
            linha_metricas(
                [
                    Metrica("Linhas", fmt.inteiro(len(resultado.dados)) + ("+" if resultado.truncado else "")),
                    Metrica("Colunas", fmt.inteiro(len(resultado.dados.columns))),
                    Metrica("Tempo", f"{fmt.decimal(resultado.duracao_ms, 0)} ms"),
                ]
            )
            if resultado.truncado:
                st.warning(
                    f"Resultado limitado às primeiras {fmt.inteiro(settings.SQL_LAB_MAX_ROWS)} linhas. Use LIMIT ou filtros.",
                    icon=":material/warning:",
                )
            tabela(resultado.dados, chave="lab-tabela", altura=400, nome_arquivo="consulta_livre")
            _grafico_rapido(resultado.dados)
