"""Página inicial: tese do projeto, caminho dos dados e requisitos do enunciado."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

import pandas as pd
import streamlit as st

from siget import settings
from siget.data.audit import auditoria
from siget.data.database import consultar, esquema
from siget.queries import CONSULTAS, Categoria
from siget.ui import formatting as fmt
from siget.ui.components import Etapa, cabecalho_pagina, faixa_etapas, secao
from siget.ui.theme import cor_tensao

ENTIDADES = ("Agente", "Contrato", "Empreendimento", "Obra", "Modulo", "LinhaTransmissao", "Subestacao")
ESPECIALIZACOES = ("ModuloLinha", "ModuloEquipamento", "ModuloManobra")
ASSOCIATIVAS = ("LinhaSubestacao",)


# ── Diagrama unifilar (assinatura visual) ───────────────────────────────────
@dataclass(frozen=True, slots=True)
class LinhaDestaque:
    origem: str
    uf_origem: str
    destino: str
    uf_destino: str
    kv: float
    km: float
    torres: int


@st.cache_data(show_spinner=False)
def _maior_linha() -> LinhaDestaque | None:
    dados = consultar(
        """
        SELECT so.NomSubestacao AS origem, so.SigUFSubestacao AS uf_origem,
               sd.NomSubestacao AS destino, sd.SigUFSubestacao AS uf_destino,
               lt.NumTensaoBaseLinhaTransm AS kv, ml.NumEtnLinTms AS km, ml.QtdTorLinTms AS torres
        FROM ModuloLinha AS ml
        JOIN LinhaTransmissao AS lt ON lt.IdeLinTms = ml.IdeLinTms
        JOIN LinhaSubestacao AS lo ON lo.IdeLinTms = lt.IdeLinTms AND lo.Papel = 'Origem'
        JOIN LinhaSubestacao AS ld ON ld.IdeLinTms = lt.IdeLinTms AND ld.Papel = 'Destino'
        JOIN Subestacao AS so ON so.IdeSbe = lo.IdeSbe
        JOIN Subestacao AS sd ON sd.IdeSbe = ld.IdeSbe
        ORDER BY ml.NumEtnLinTms DESC
        LIMIT 1
        """
    )
    if dados.empty:
        return None
    r = dados.iloc[0]
    return LinhaDestaque(r.origem, r.uf_origem, r.destino, r.uf_destino, float(r.kv), float(r.km), int(r.torres))


def _diagrama_unifilar(linha: LinhaDestaque) -> str:
    # Duas versões: a larga e uma compacta para telas estreitas (o CSS escolhe qual mostrar).
    html = f'<div class="sg-hero-diagram">{_svg_unifilar(linha)}{_svg_unifilar_compacto(linha)}</div>'
    return " ".join(html.split())


def _torres(x_inicio: int, x_fim: int, y: int, passo: int) -> str:
    return "".join(
        f'<path d="M{x - 7} {y + 1} L{x} {y - 15} L{x + 7} {y + 1} M{x - 4.5} {y - 6} H{x + 4.5}" '
        f'stroke="#93A3AF" stroke-width="1.4" fill="none"/>'
        for x in range(x_inicio, x_fim, passo)
    )


def _titulo_svg(linha: LinhaDestaque) -> str:
    return (
        f"Linha de {fmt.decimal(linha.km, 0)} km entre {linha.origem} ({linha.uf_origem}) "
        f"e {linha.destino} ({linha.uf_destino})"
    )


def _svg_unifilar_compacto(linha: LinhaDestaque) -> str:
    cor = cor_tensao(linha.kv)
    x0, x1, y = 24, 336, 78
    titulo = escape(_titulo_svg(linha))
    return f"""
<svg class="sg-oneline is-compact" viewBox="0 0 360 214" role="img" aria-label="{titulo}">
  <title>{titulo}</title>
  <line x1="{x0}" y1="30" x2="{x0}" y2="126" stroke="#12263A" stroke-width="6" stroke-linecap="round"/>
  <line x1="{x1}" y1="30" x2="{x1}" y2="126" stroke="#12263A" stroke-width="6" stroke-linecap="round"/>
  {_torres(x0 + 26, x1 - 20, y, 30)}
  <line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="#12263A" stroke-width="2"/>
  <line class="pulse" x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{cor}" stroke-width="4" stroke-linecap="round"/>
  <rect x="140" y="{y - 13}" width="80" height="26" rx="13" fill="{cor}"/>
  <text x="180" y="{y + 5}" text-anchor="middle" font-family="var(--display)" font-weight="800"
        font-size="14" fill="#12263A">{fmt.decimal(linha.kv, 0)} kV</text>
  <g font-family="var(--display)" font-weight="750" font-size="15" fill="#12263A">
    <text x="{x0 - 4}" y="152" text-anchor="start">{escape(linha.origem.title())} · {escape(linha.uf_origem)}</text>
    <text x="{x1 + 4}" y="152" text-anchor="end">{escape(linha.destino.title())} · {escape(linha.uf_destino)}</text>
  </g>
  <g font-family="var(--mono)" font-size="12" fill="#5A6B7B" text-anchor="middle">
    <text x="180" y="184">{fmt.decimal(linha.km, 0)} km · {fmt.inteiro(linha.torres)} torres</text>
    <text x="180" y="204">o maior módulo de linha da base</text>
  </g>
</svg>"""


def _svg_unifilar(linha: LinhaDestaque) -> str:
    """SVG de um diagrama unifilar: dois barramentos ligados pela linha, com fluxo animado."""
    cor = cor_tensao(linha.kv)
    x0, x1, y = 92, 908, 92
    torres = _torres(x0 + 46, x1 - 30, y, 42)
    titulo = escape(_titulo_svg(linha))
    return f"""
<svg class="sg-oneline is-wide" viewBox="0 0 1000 190" role="img" aria-label="{titulo}">
  <title>{titulo}</title>
  <g font-family="var(--mono)" font-size="12" fill="#5A6B7B" letter-spacing="1.5">
    <text x="{x0}" y="22" text-anchor="middle">ORIGEM</text>
    <text x="{x1}" y="22" text-anchor="middle">DESTINO</text>
  </g>
  <line x1="{x0}" y1="34" x2="{x0}" y2="150" stroke="#12263A" stroke-width="7" stroke-linecap="round"/>
  <line x1="{x1}" y1="34" x2="{x1}" y2="150" stroke="#12263A" stroke-width="7" stroke-linecap="round"/>
  {torres}
  <line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="#12263A" stroke-width="2.5"/>
  <line class="pulse" x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{cor}" stroke-width="5" stroke-linecap="round"/>
  <rect x="452" y="{y - 14}" width="96" height="28" rx="14" fill="{cor}"/>
  <text x="500" y="{y + 5}" text-anchor="middle" font-family="var(--display)" font-weight="800"
        font-size="15" fill="#12263A">{fmt.decimal(linha.kv, 0)} kV</text>
  <g font-family="var(--display)" font-weight="750" font-size="17" fill="#12263A">
    <text x="{x0}" y="176" text-anchor="middle">{escape(linha.origem.title())} · {escape(linha.uf_origem)}</text>
    <text x="{x1}" y="176" text-anchor="middle">{escape(linha.destino.title())} · {escape(linha.uf_destino)}</text>
  </g>
  <text x="500" y="138" text-anchor="middle" font-family="var(--mono)" font-size="13" fill="#5A6B7B">
    {fmt.decimal(linha.km, 0)} km · {fmt.inteiro(linha.torres)} torres · o maior módulo de linha da base
  </text>
</svg>"""


# ── Requisitos do enunciado ─────────────────────────────────────────────────
def _requisitos(tabelas: dict[str, int], total_tuplas: int) -> pd.DataFrame:
    estrutura = {t.nome: t for t in esquema()}
    atributos_min = min(len(estrutura[e].colunas) - len(estrutura[e].chave_primaria) for e in ENTIDADES)
    fks = sum(1 for t in estrutura.values() for c in t.colunas if c.fk_para)
    por_categoria = {cat: sum(c.categoria is cat for c in CONSULTAS) for cat in Categoria}
    return pd.DataFrame(
        [
            (
                "Tipos de entidade",
                "≥ 4, com 2+ atributos",
                f"{len(ENTIDADES)} entidades (mín. {atributos_min} atributos) + 3 especializações",
            ),
            ("Tipos de relacionamento", "≥ 3, ao menos 1 M:N", f"{fks} chaves estrangeiras · M:N Linha ⇄ Subestação"),
            (
                "Instâncias no banco",
                "≥ 10.000 tuplas",
                f"{fmt.inteiro(total_tuplas)} tuplas em {len(tabelas)} relações",
            ),
            ("Seleção e projeção", "2 consultas", f"{por_categoria[Categoria.SELECAO]} consultas"),
            ("Junção de duas relações", "3 consultas", f"{por_categoria[Categoria.JUNCAO_DUAS]} consultas"),
            ("Junção de três ou mais", "3 consultas", f"{por_categoria[Categoria.JUNCAO_MULTIPLA]} consultas"),
            ("Agregação sobre junção", "2 consultas", f"{por_categoria[Categoria.AGREGACAO]} consultas"),
            ("Conjunto de dados", "atualizado em 2026", "SIGET/ANEEL, gerado em 24/10/2026"),
        ],
        columns=["Requisito", "Enunciado", "Neste trabalho"],
    )


def _tabela_requisitos(requisitos: pd.DataFrame) -> str:
    linhas = "".join(
        f"<tr><th scope='row'>{escape(requisito)}</th><td>{escape(exigido)}</td>"
        f"<td><span class='sg-ok' aria-label='atendido'>✓</span>{escape(entregue)}</td></tr>"
        for requisito, exigido, entregue in requisitos.itertuples(index=False, name=None)
    )
    return (
        "<table class='sg-req'><thead><tr><th>Requisito</th><th>Enunciado</th><th>Neste trabalho</th>"
        f"</tr></thead><tbody>{linhas}</tbody></table>"
    )


# ── Página ──────────────────────────────────────────────────────────────────
def render() -> None:
    from siget import navigation  # import tardio: navigation importa esta view

    cabecalho_pagina(
        "Trabalho Prático 2 · DCC011 · UFMG",
        "A energia de Belo Monte chega ao Rio por 2.539 km. Aqui, por 11 tabelas.",
        "Organizamos os dados abertos do Sistema de Gestão da Transmissão (SIGET/ANEEL) em um banco "
        "relacional normalizado e o interrogamos com SQL: quem constrói a rede, onde ela se conecta "
        "e como ela se expande.",
    )

    if linha := _maior_linha():
        # st.html sanitiza SVG; st.markdown com HTML bruto preserva o desenho e a animação.
        st.markdown(_diagrama_unifilar(linha), unsafe_allow_html=True)

    tabelas = {t.nome: t.linhas for t in esquema()}
    total_tuplas = sum(tabelas.values())
    registros_originais = sum(n for _, n, _ in settings.ARQUIVOS_ORIGINAIS)
    log = auditoria()
    removidos = int(log.loc[log["etapa"].isin(["rejeicao", "limpeza"]), "quantidade"].sum())

    secao("Do arquivo aberto ao banco relacional", "Seção 3 do relatório")
    faixa_etapas(
        [
            Etapa(
                "Arquivos CSV",
                fmt.inteiro(registros_originais),
                f"{len(settings.ARQUIVOS_ORIGINAIS)} arquivos do SIGET, em registros",
            ),
            Etapa("Limpeza", f"−{fmt.inteiro(removidos)}", "registros sem chave, órfãos ou contraditórios", "loss"),
            Etapa("Normalização", f"{len(tabelas)} relações", "7 entidades, 3 especializações, 1 associativa"),
            Etapa("SQLite", fmt.inteiro(total_tuplas), "tuplas no banco normalizado", "final"),
        ]
    )

    esquerda, direita = st.columns([1.7, 1], gap="large")
    with esquerda:
        secao("O enunciado, verificado no banco")
        st.html(_tabela_requisitos(_requisitos(tabelas, total_tuplas)))
        st.caption("Contagens lidas do SQLite e do catálogo de consultas a cada execução, não digitadas.")
    with direita:
        secao("Por onde começar")
        atalhos = (
            (
                navigation.CONSULTAS,
                "As 10 consultas",
                "SQL, resultado, gráficos e a leitura do grupo para cada pergunta.",
            ),
            (navigation.MODELAGEM, "Modelagem", "Diagramas ER e relacional e o esquema navegável, tabela por tabela."),
            (navigation.REDE, "Rede elétrica", "Mapa por UF, subestações-polo e linhas por classe de tensão."),
            (navigation.LABORATORIO, "Laboratório SQL", "Escreva sua própria consulta sobre o banco, em modo leitura."),
        )
        for pagina, titulo, texto in atalhos:
            with st.container(border=True, key=f"sg-card-{pagina.url_path}"):
                st.page_link(pagina, label=titulo, icon=pagina.icon)
                st.caption(texto)

    secao("Integrantes")
    membros = "".join(
        f"<div class='sg-member'><b>{escape(i.nome)}</b><span>{i.matricula}</span></div>" for i in settings.INTEGRANTES
    )
    st.html(f"<div class='sg-team'>{membros}</div>")
    st.caption(f"Fonte: [Sistema de Gestão da Transmissão — dados.gov.br]({settings.DATASET_URL})")
