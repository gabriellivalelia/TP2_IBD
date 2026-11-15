"""Registro das páginas da aplicação e sua organização na barra lateral."""

from __future__ import annotations

import streamlit as st

from siget.views import (
    agentes,
    consultas,
    dados,
    empreendimentos,
    inicio,
    laboratorio,
    modelagem,
    rede,
)

INICIO = st.Page(inicio.render, title="Visão geral", icon=":material/bolt:", url_path="inicio", default=True)
DADOS = st.Page(dados.render, title="Dados e tratamento", icon=":material/filter_alt:", url_path="dados")
MODELAGEM = st.Page(modelagem.render, title="Modelagem", icon=":material/schema:", url_path="modelagem")
CONSULTAS = st.Page(consultas.render, title="As 10 consultas", icon=":material/database_search:", url_path="consultas")
REDE = st.Page(rede.render, title="Rede elétrica", icon=":material/hub:", url_path="rede")
AGENTES = st.Page(agentes.render, title="Agentes", icon=":material/apartment:", url_path="agentes")
EMPREENDIMENTOS = st.Page(
    empreendimentos.render, title="Prazos de implantação", icon=":material/event_upcoming:", url_path="prazos"
)
LABORATORIO = st.Page(laboratorio.render, title="Laboratório SQL", icon=":material/terminal:", url_path="sql")

SECOES: dict[str, list[st.Page]] = {
    "Projeto": [INICIO, DADOS, MODELAGEM],
    "Relatório": [CONSULTAS],
    "Explorar a base": [REDE, AGENTES, EMPREENDIMENTOS],
    "Ferramentas": [LABORATORIO],
}
