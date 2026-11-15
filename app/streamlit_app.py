"""SIGET Explorer — aplicação Streamlit do TP2 de Introdução a Banco de Dados.

Execução (a partir da raiz do repositório):

    uv run streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="SIGET · Rede de Transmissão",
    page_icon=":material/bolt:",
    layout="wide",
    initial_sidebar_state="auto",
)

from siget import settings  # noqa: E402
from siget.navigation import SECOES  # noqa: E402
from siget.ui.theme import aplicar_tema  # noqa: E402

aplicar_tema()
st.logo(
    str(settings.APP_DIR / "static" / "logo.svg"),
    size="large",
    icon_image=str(settings.APP_DIR / "static" / "marca.svg"),
)

pagina = st.navigation(SECOES, position="sidebar", expanded=True)

with st.sidebar:
    integrantes = "<br>".join(i.nome.split()[0] + " " + i.nome.split()[-1] for i in settings.INTEGRANTES)
    st.html(
        f'<div class="sg-sidebar-foot"><b>TP2 · DCC011 · UFMG</b><br>'
        f"Dados abertos SIGET/ANEEL, gerados em 24/10/2026.<br><br>{integrantes}</div>"
    )

pagina.run()
