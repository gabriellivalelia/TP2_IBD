"""Página principal de avaliação: as 10 consultas SQL do relatório.

Ordem de leitura igual à do notebook: pergunta → SQL → destaques → resultado →
leitura dos resultados. Cada consulta aceita parâmetros; com os valores padrão
o resultado é idêntico ao do relatório.
"""

from __future__ import annotations

import time
from itertools import groupby
from typing import Any

import streamlit as st

from siget.data.report import trechos_consultas
from siget.queries import CONSULTAS, POR_NUMERO, TODOS, Categoria, Consulta, Parametro
from siget.ui import formatting as fmt
from siget.ui.components import cabecalho_pagina, chips, destaque_markdown, secao, tabela

CHAVE_SELECAO = "consulta_atual"


# ── Estado ──────────────────────────────────────────────────────────────────
def _numero_inicial() -> int:
    try:
        numero = int(st.query_params.get("c", 1))
    except (TypeError, ValueError):
        numero = 1
    return numero if numero in POR_NUMERO else 1


def _selecionar(numero: int) -> None:
    st.session_state[CHAVE_SELECAO] = numero
    st.query_params["c"] = str(numero)


def _chave_widget(consulta: Consulta, parametro: Parametro) -> str:
    return f"param-c{consulta.numero}-{parametro.nome}"


def _restaurar_padrao(consulta: Consulta) -> None:
    for p in consulta.parametros:
        st.session_state.pop(_chave_widget(consulta, p), None)


# ── Índice lateral ──────────────────────────────────────────────────────────
def _indice(atual: int) -> None:
    with st.container(key="sg-indice"):
        for categoria, grupo in groupby(CONSULTAS, key=lambda c: c.categoria):
            itens = list(grupo)
            st.html(f'<div class="sg-index-group"><span>{categoria.rotulo}</span><em>{len(itens)}</em></div>')
            for c in itens:
                st.button(
                    f"{c.numero:02d} · {c.titulo}",
                    key=f"indice-{c.numero}",
                    type="primary" if c.numero == atual else "tertiary",
                    width="stretch",
                    on_click=_selecionar,
                    args=(c.numero,),
                )


# ── Parâmetros ──────────────────────────────────────────────────────────────
def _widget(consulta: Consulta, p: Parametro) -> Any:
    chave = _chave_widget(consulta, p)
    formatar = p.formatar or str
    match p.widget:
        case "escolha":
            opcoes = ([TODOS] if p.permite_todos else []) + p.listar_opcoes()
            padrao = TODOS if p.padrao is None else p.padrao
            return st.selectbox(
                p.rotulo,
                opcoes,
                index=opcoes.index(padrao),
                key=chave,
                help=p.ajuda,
                format_func=lambda v: v if v == TODOS else formatar(v),
            )
        case "multipla":
            return st.multiselect(
                p.rotulo, p.listar_opcoes(), default=p.padrao, key=chave, help=p.ajuda, placeholder="Todos"
            )
        case "degraus":
            return st.select_slider(
                p.rotulo, p.listar_opcoes(), value=p.padrao, key=chave, help=p.ajuda, format_func=formatar
            )
        case "intervalo":
            return st.select_slider(
                p.rotulo, p.listar_opcoes(), value=p.padrao, key=chave, help=p.ajuda, format_func=formatar
            )
        case "texto":
            return st.text_input(p.rotulo, value=p.padrao, key=chave, help=p.ajuda, placeholder="ex.: AXIA")
    raise ValueError(f"Widget desconhecido: {p.widget}")


def _painel_parametros(consulta: Consulta) -> tuple[dict[str, Any], bool]:
    """Desenha os parâmetros e informa se os valores diferem do relatório."""
    if not consulta.parametros:
        return {}, False
    with st.container(border=True):
        st.html('<div class="sg-callout-title">Parâmetros da consulta</div>')
        valores = {p.nome: _widget(consulta, p) for p in consulta.parametros}
        alterado = consulta.parametros_sql(valores) != consulta.parametros_sql(consulta.valores_padrao())
        if alterado:
            st.button(
                "Voltar aos valores do relatório",
                icon=":material/restart_alt:",
                on_click=_restaurar_padrao,
                args=(consulta,),
                key=f"restaurar-{consulta.numero}",
                type="tertiary",
            )
        else:
            st.caption("Valores do relatório. Altere para explorar outros recortes.")
    return valores, alterado


# ── Detalhe da consulta ─────────────────────────────────────────────────────
def _detalhe(consulta: Consulta) -> None:
    trecho = trechos_consultas().get(consulta.numero)

    st.html(
        f'<div class="sg-eyebrow">Consulta {consulta.numero:02d} · {consulta.categoria.rotulo}</div>'
        f'<h2 class="sg-query-title">{consulta.pergunta}</h2>'
    )

    st.markdown(consulta.descricao)
    chips([*consulta.relacoes], juncao=len(consulta.relacoes) > 1, destaque=True)

    if consulta.parametros:
        esquerda, direita = st.columns([1, 1.75], gap="large")
    else:
        esquerda, direita = None, st.container()
    valores, alterado = {}, False
    if esquerda is not None:
        with esquerda:
            valores, alterado = _painel_parametros(consulta)

    inicio = time.perf_counter()
    dados = consulta.executar(valores or None)
    duracao = (time.perf_counter() - inicio) * 1000

    with direita:
        if not alterado and trecho and trecho.sql:
            sql, legenda = trecho.sql, "SQL do relatório (tp2.ipynb)"
        else:
            sql, legenda = consulta.sql_com_valores(valores), "SQL executado com os parâmetros escolhidos"
        st.code(sql, language="sql", wrap_lines=True)
        st.caption(f"{legenda} · {fmt.inteiro(len(dados))} linhas · {fmt.decimal(duracao, 0)} ms")

    secao("Destaques", "Calculados sobre o resultado completo")
    consulta.visualizar(dados, valores)

    secao("Resultado", f"{fmt.inteiro(len(dados))} linhas × {len(dados.columns)} colunas")
    tabela(dados, chave=f"resultado-c{consulta.numero}", altura=380, nome_arquivo=f"consulta_{consulta.numero:02d}")

    if trecho and trecho.analise:
        secao("Leitura dos resultados", "Texto do relatório")
        if alterado:
            st.info(
                "Os parâmetros foram alterados: a leitura abaixo descreve o resultado com os valores do relatório.",
                icon=":material/info:",
            )
        destaque_markdown("Análise", trecho.analise, chave=f"analise-{consulta.numero}")

    _navegacao_vizinhas(consulta)


def _navegacao_vizinhas(consulta: Consulta) -> None:
    st.space("medium")
    anterior = POR_NUMERO.get(consulta.numero - 1)
    seguinte = POR_NUMERO.get(consulta.numero + 1)
    esquerda, _, direita = st.columns([1, 0.4, 1])
    if anterior:
        esquerda.button(
            f"Consulta {anterior.numero:02d}",
            icon=":material/arrow_back:",
            help=f"{anterior.titulo}: {anterior.pergunta}",
            on_click=_selecionar,
            args=(anterior.numero,),
            width="stretch",
            key="sg-vizinha-anterior",
        )
    if seguinte:
        direita.button(
            f"Consulta {seguinte.numero:02d}",
            icon=":material/arrow_forward:",
            icon_position="right",
            help=f"{seguinte.titulo}: {seguinte.pergunta}",
            on_click=_selecionar,
            args=(seguinte.numero,),
            width="stretch",
            key="sg-vizinha-seguinte",
        )


# ── Página ──────────────────────────────────────────────────────────────────
def render() -> None:
    if CHAVE_SELECAO not in st.session_state:
        st.session_state[CHAVE_SELECAO] = _numero_inicial()
    atual = st.session_state[CHAVE_SELECAO]

    cabecalho_pagina(
        "Seção 6 do relatório",
        "Consultas SQL",
        "Dez consultas em quatro famílias de operações. Cada uma mostra o SQL, o resultado completo "
        "e a leitura do grupo — e aceita parâmetros para explorar outros recortes da base.",
    )
    _resumo_categorias()

    indice, conteudo = st.columns([1.05, 3.2], gap="large")
    with indice:
        _indice(atual)
    with conteudo:
        _seletor_compacto(atual)
        _detalhe(POR_NUMERO[atual])


def _seletor_compacto(atual: int) -> None:
    """Substitui o índice lateral quando falta largura (exibido apenas via CSS)."""
    chave = "consulta-compacta"
    st.session_state[chave] = atual
    with st.container(key="sg-seletor-compacto"):
        st.selectbox(
            "Consulta",
            [c.numero for c in CONSULTAS],
            key=chave,
            format_func=lambda n: f"{n:02d} · {POR_NUMERO[n].titulo} — {POR_NUMERO[n].categoria.rotulo}",
            on_change=lambda: _selecionar(st.session_state[chave]),
        )


def _resumo_categorias() -> None:
    contagem = {cat: sum(c.categoria is cat for c in CONSULTAS) for cat in Categoria}
    blocos = "".join(
        f"<div><b>{n}</b><span>{cat.rotulo}</span><code>{cat.notacao}</code></div>" for cat, n in contagem.items()
    )
    st.html(f'<div class="sg-categories">{blocos}</div>')
