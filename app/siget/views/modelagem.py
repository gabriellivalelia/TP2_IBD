"""Seções 4 e 5 do relatório: diagramas ER e relacional e o esquema navegável."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from siget import settings
from siget.data.database import Tabela, consultar, ddl, esquema
from siget.ui import formatting as fmt
from siget.ui.components import cabecalho_pagina, secao
from siget.ui.theme import COR

PAPEIS = {
    "Agente": "Entidade",
    "Contrato": "Entidade",
    "Empreendimento": "Entidade",
    "Obra": "Entidade",
    "Modulo": "Entidade",
    "LinhaTransmissao": "Entidade",
    "Subestacao": "Entidade",
    "ModuloLinha": "Especialização",
    "ModuloEquipamento": "Especialização",
    "ModuloManobra": "Especialização",
    "LinhaSubestacao": "Associativa (M:N)",
}
CORES_PAPEL = {"Entidade": COR.tinta, "Especialização": COR.petroleo, "Associativa (M:N)": "#B7811A"}

RELACIONAMENTOS = pd.DataFrame(
    [
        ("Agente — Contrato", "1:N", "Um agente detém vários contratos; cada contrato tem um agente."),
        ("Contrato — Empreendimento", "1:N", "Um contrato abrange vários empreendimentos."),
        ("Empreendimento — Obra", "1:N", "Um empreendimento reúne várias obras."),
        ("Modulo — Obra", "1:N", "Um módulo pode receber obras sucessivas."),
        (
            "Modulo — ModuloLinha / Equipamento / Manobra",
            "1:0..1",
            "Especialização parcial com sobreposição permitida.",
        ),
        ("LinhaTransmissao — ModuloLinha", "1:N", "Uma linha pode ter vários módulos de linha."),
        ("Subestacao — ModuloEquipamento", "1:N", "Uma subestação abriga vários equipamentos."),
        ("Subestacao — ModuloManobra", "1:N", "Uma subestação abriga vários módulos de manobra."),
        (
            "LinhaTransmissao — Subestacao",
            "M:N",
            "Cada linha liga uma origem e um destino; uma SE recebe várias linhas.",
        ),
    ],
    columns=["Relacionamento", "Cardinalidade", "Leitura"],
)


def _dot_esquema(tabelas: tuple[Tabela, ...], selecionada: str | None) -> str:
    """Gera o diagrama relacional em DOT diretamente das chaves do SQLite."""
    nos = []
    for t in tabelas:
        papel = PAPEIS.get(t.nome, "Entidade")
        cor = CORES_PAPEL[papel]
        borda = COR.ambar if t.nome == selecionada else cor
        largura = 3 if t.nome == selecionada else 1
        chaves = "".join(
            f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="9" COLOR="#5A6B7B">'
            f"{'PK ' if c.pk else ''}{'FK ' if c.fk_para else ''}</FONT>"
            f'<FONT POINT-SIZE="10">{escape(c.nome)}</FONT></TD></TR>'
            for c in t.colunas
            if c.pk or c.fk_para
        )
        rotulo = (
            f'<<TABLE BORDER="{largura}" COLOR="{borda}" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" BGCOLOR="#FFFFFF">'
            f'<TR><TD BGCOLOR="{cor}" ALIGN="LEFT"><FONT COLOR="#FFFFFF" POINT-SIZE="11"><B>{t.nome}</B></FONT></TD></TR>'
            f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="9" COLOR="#5A6B7B">{fmt.inteiro(t.linhas)} tuplas</FONT></TD></TR>'
            f"{chaves}</TABLE>>"
        )
        nos.append(f'"{t.nome}" [label={rotulo}];')
    arestas = [
        f'"{t.nome}" -> "{c.fk_para.split(".")[0]}" [tooltip="{t.nome}.{c.nome} → {c.fk_para}"];'
        for t in tabelas
        for c in t.colunas
        if c.fk_para
    ]
    return (
        "digraph esquema {"
        'graph [rankdir=LR, bgcolor="transparent", nodesep=0.35, ranksep=0.7, fontname="Helvetica"];'
        'node [shape=plain, fontname="Helvetica"];'
        f'edge [color="{COR.petroleo}", arrowsize=0.7, penwidth=1.2];' + "".join(nos) + "".join(arestas) + "}"
    )


def _detalhe_tabela(tabela: Tabela) -> None:
    papel = PAPEIS.get(tabela.nome, "Entidade")
    st.html(
        f'<div class="sg-eyebrow">{escape(papel)}</div>'
        f'<h3 class="sg-query-title" style="margin-bottom:.2rem">{tabela.nome}</h3>'
        f'<p class="sg-note">{fmt.inteiro(tabela.linhas)} tuplas · {len(tabela.colunas)} atributos · '
        f"chave primária ({', '.join(tabela.chave_primaria)})</p>"
    )
    colunas = pd.DataFrame(
        [
            {
                "Atributo": c.nome,
                "Tipo": c.tipo,
                "Chave": " ".join(filter(None, ["PK" if c.pk else "", "FK" if c.fk_para else ""])),
                "Referencia": c.fk_para or "",
                "NOT NULL": "sim" if c.not_null else "",
            }
            for c in tabela.colunas
        ]
    )
    st.dataframe(colunas, hide_index=True, width="stretch", height=min(38 * len(colunas) + 40, 460))
    st.caption("Amostra de tuplas")
    st.dataframe(consultar(f'SELECT * FROM "{tabela.nome}" LIMIT 8'), hide_index=True, width="stretch")


def render() -> None:
    cabecalho_pagina(
        "Seções 4 e 5 do relatório",
        "Modelagem",
        "Do modelo conceitual ao esquema implementado no SQLite. O esquema navegável é lido "
        "diretamente do banco: tabelas, chaves e contagens refletem o que está gravado.",
    )

    aba_er, aba_rel, aba_esquema, aba_ddl = st.tabs(["Diagrama ER", "Relacional", "Esquema", "DDL"])

    with aba_er:
        st.image(str(settings.ER_DIAGRAM), width="stretch")
        secao("Relacionamentos", "Tabela 3 do relatório")
        st.dataframe(
            RELACIONAMENTOS,
            hide_index=True,
            width="stretch",
            column_config={"Cardinalidade": st.column_config.TextColumn(width="small")},
        )

    with aba_rel:
        st.image(str(settings.RELATIONAL_DIAGRAM), width="stretch")

    with aba_esquema:
        tabelas = esquema()
        nomes = [t.nome for t in tabelas]
        escolhida = st.pills(
            "Relação",
            nomes,
            default="Obra",
            key="modelagem-tabela",
            label_visibility="collapsed",
        )
        legenda = "".join(
            f'<span><i style="background:{cor}"></i>{escape(papel)}</span>' for papel, cor in CORES_PAPEL.items()
        )
        st.html(f'<div class="sg-legend">{legenda}<span><i style="background:{COR.ambar}"></i>Selecionada</span></div>')
        st.graphviz_chart(_dot_esquema(tabelas, escolhida), width="content")
        if escolhida:
            _detalhe_tabela(next(t for t in tabelas if t.nome == escolhida))

    with aba_ddl:
        st.caption("CREATE TABLE extraído do sqlite_master, com chaves primárias, estrangeiras e restrições CHECK.")
        st.code(ddl(), language="sql", line_numbers=True)
