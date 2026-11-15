"""Sistema visual: tokens de cor, tipografia, CSS global e template Plotly.

Direção: "sala de controle da transmissão". A base azul-marinho e petróleo vem
dos diagramas ER/relacional do grupo; o âmbar é o amarelo das placas de alta
tensão e é usado com parcimônia, só para o que está "energizado" (destaques,
seleção, o pulso do diagrama unifilar). Cada classe de tensão tem uma cor fixa,
usada em todos os gráficos da aplicação.
"""

from __future__ import annotations

from dataclasses import dataclass

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st


# ── Tokens ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Paleta:
    tinta: str = "#12263A"  # azul-marinho: texto, barra lateral
    petroleo: str = "#14606E"  # cor primária (mesma dos diagramas)
    petroleo_claro: str = "#DCEBEC"
    ambar: str = "#E3A21A"  # sinalização de alta tensão: único acento quente
    ambar_claro: str = "#FBF0D6"
    papel: str = "#F5F7F8"
    superficie: str = "#FFFFFF"
    ardosia: str = "#5A6B7B"  # texto secundário
    nevoa: str = "#93A3AF"  # texto terciário / séries apagadas
    fio: str = "#D6DEE3"  # linhas finas e bordas
    alerta: str = "#B4433A"


COR = Paleta()

FONTE_TITULO = "Archivo"
FONTE_TEXTO = "Public Sans"
FONTE_MONO = "JetBrains Mono"


@dataclass(frozen=True, slots=True)
class ClasseTensao:
    rotulo: str
    minimo: float
    maximo: float
    cor: str


# Classes de tensão da rede básica, das mais baixas (frias) às mais altas (quentes).
CLASSES_TENSAO: tuple[ClasseTensao, ...] = (
    ClasseTensao("≤ 138 kV", 0, 138, "#9DB7C7"),
    ClasseTensao("230 kV", 139, 230, "#3A7CA5"),
    ClasseTensao("345–440 kV", 231, 440, "#5B4B9A"),
    ClasseTensao("500–525 kV", 441, 525, "#C2413B"),
    ClasseTensao("≥ 600 kV", 526, 10_000, "#E3A21A"),
)
ORDEM_CLASSES = [c.rotulo for c in CLASSES_TENSAO]
CORES_CLASSES = {c.rotulo: c.cor for c in CLASSES_TENSAO}


def classe_tensao(kv: float | None) -> str | None:
    if kv is None or kv != kv:  # None ou NaN
        return None
    for classe in CLASSES_TENSAO:
        if classe.minimo <= kv <= classe.maximo:
            return classe.rotulo
    return None


def cor_tensao(kv: float | None) -> str:
    rotulo = classe_tensao(kv)
    return CORES_CLASSES.get(rotulo, COR.nevoa) if rotulo else COR.nevoa


# Situações cadastrais recorrentes (empreendimentos e obras).
CORES_SITUACAO = {
    "Em Operação": COR.petroleo,
    "Em operação": COR.petroleo,
    "Em andamento": COR.ambar,
    "Concluído": "#3A7CA5",
    "Planejado": "#5B4B9A",
    "Não informada": COR.nevoa,
}

SEQUENCIA_CATEGORICA = [COR.petroleo, COR.ambar, "#3A7CA5", "#C2413B", "#5B4B9A", "#7A8C99"]
ESCALA_SEQUENCIAL = [[0.0, "#EAF2F3"], [0.35, "#8DBBC1"], [0.7, COR.petroleo], [1.0, COR.tinta]]


# ── Plotly ──────────────────────────────────────────────────────────────────
def _registrar_template_plotly() -> None:
    eixo = dict(
        showgrid=True,
        gridcolor="#E7ECEF",
        gridwidth=1,
        zeroline=False,
        linecolor=COR.fio,
        ticks="",
        tickfont=dict(color=COR.ardosia, size=11.5),
        title=dict(font=dict(color=COR.ardosia, size=12)),
        automargin=True,
    )
    pio.templates["siget"] = go.layout.Template(
        layout=dict(
            font=dict(family=f"{FONTE_TEXTO}, system-ui, sans-serif", color=COR.tinta, size=13),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=SEQUENCIA_CATEGORICA,
            separators=",.",  # padrão brasileiro: vírgula decimal, ponto de milhar
            margin=dict(l=8, r=16, t=36, b=8),
            title=dict(
                font=dict(family=FONTE_TITULO, size=15, color=COR.tinta),
                x=0,
                xanchor="left",
                y=0.98,
            ),
            xaxis=eixo,
            yaxis=eixo,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.0,
                xanchor="left",
                x=0,
                title=None,
                font=dict(size=12, color=COR.ardosia),
                bgcolor="rgba(0,0,0,0)",
            ),
            hoverlabel=dict(
                bgcolor=COR.tinta,
                bordercolor=COR.tinta,
                font=dict(family=FONTE_TEXTO, color="#FFFFFF", size=12.5),
            ),
            bargap=0.28,
            coloraxis=dict(colorscale=ESCALA_SEQUENCIAL, colorbar=dict(thickness=10, outlinewidth=0)),
        )
    )
    pio.templates.default = "siget"


_registrar_template_plotly()

# A barra de ferramentas do Plotly flutua sobre o gráfico e cobre barras e rótulos em
# telas estreitas; o Streamlit já oferece tela cheia no próprio contêiner do gráfico.
PLOTLY_CONFIG = {
    "displaylogo": False,
    "displayModeBar": False,
    "responsive": True,
}


# ── CSS global ──────────────────────────────────────────────────────────────
_FONTES = (
    "https://fonts.googleapis.com/css2?"
    "family=Archivo:wdth,wght@62..125,400..900"
    "&family=Public+Sans:ital,wght@0,300..800;1,400"
    "&family=JetBrains+Mono:wght@400;500;600&display=swap"
)

_CSS = f"""
<style>
@import url('{_FONTES}');

:root {{
  --tinta: {COR.tinta};
  --petroleo: {COR.petroleo};
  --petroleo-claro: {COR.petroleo_claro};
  --ambar: {COR.ambar};
  --ambar-claro: {COR.ambar_claro};
  --papel: {COR.papel};
  --superficie: {COR.superficie};
  --ardosia: {COR.ardosia};
  --nevoa: {COR.nevoa};
  --fio: {COR.fio};
  --display: '{FONTE_TITULO}', '{FONTE_TEXTO}', sans-serif;
  --mono: '{FONTE_MONO}', ui-monospace, monospace;
}}

/* Estrutura ------------------------------------------------------------- */
.block-container, [data-testid="stMainBlockContainer"] {{
  max-width: 1240px;
  padding-top: 4.4rem;  /* altura do cabeçalho fixo (3,75rem) + respiro */
  padding-bottom: 5rem;
}}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
h1 {{ font-stretch: 112%; }}
/* O cabeçalho fixo do Streamlit precisa de fundo: sem ele, o conteúdo rola por baixo do logotipo. */
[data-testid="stHeader"] {{
  background: rgba(245, 247, 248, .92);
  backdrop-filter: blur(6px);
}}
/* Contêineres de consulta: o layout responde à largura disponível (barra lateral aberta ou não),
   não à largura da janela. */
[data-testid="stMainBlockContainer"] {{ container: principal / inline-size; }}
[data-testid="stColumn"] {{ container-type: inline-size; }}

/* Barra lateral --------------------------------------------------------- */
[data-testid="stSidebar"] {{
  background-image: linear-gradient(180deg, rgba(20,96,110,.18), transparent 38%);
}}
[data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"] {{
  font-family: var(--mono);
  font-size: .68rem;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: #8FA8B8;
}}

/* Métricas ---------------------------------------------------------------- */
/* Grade que quebra sozinha: cada cartão tem no mínimo 150px e nunca transborda. */
.sg-metrics {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 138px), 1fr));
  gap: .6rem;
  margin: .2rem 0 .9rem;
}}
.sg-metric {{
  background: var(--superficie);
  border: 1px solid var(--fio);
  border-radius: .6rem;
  padding: .75rem .95rem .7rem;
  min-width: 0;
}}
.sg-metric-label {{
  display: block; font-size: .8rem; font-weight: 600; color: var(--ardosia); line-height: 1.3;
}}
.sg-metric-value {{
  display: block;
  font-family: var(--display);
  font-stretch: 108%;
  font-weight: 700;
  font-size: 1.5rem;
  line-height: 1.2;
  margin-top: .15rem;
  color: var(--tinta);
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}}
.sg-metric-help {{ display: block; font-size: .75rem; color: var(--ardosia); line-height: 1.35; margin-top: .2rem; }}

/* Títulos de gráficos (em HTML: quebram linha e não disputam espaço com a barra do Plotly) */
.sg-chart-title {{
  font-family: var(--display); font-stretch: 104%; font-weight: 650; font-size: .98rem;
  line-height: 1.3; color: var(--tinta); margin: .5rem 0 .1rem;
}}
/* Gráficos densos (matrizes) rolam na horizontal em vez de encolher até ficar ilegíveis. */
[class*="st-key-sg-rolagem-"] {{ overflow-x: auto; overflow-y: hidden; }}
[class*="st-key-sg-rolagem-"] > div {{ min-width: 620px; }}

/* Abas ------------------------------------------------------------------ */
[data-baseweb="tab-list"] {{ gap: 1.25rem; }}
[data-baseweb="tab"] p {{ font-weight: 600; }}

/* Código ---------------------------------------------------------------- */
[data-testid="stCode"] pre {{ border: 1px solid var(--fio); }}

/* Componentes próprios ---------------------------------------------------- */
.sg-eyebrow {{
  font-family: var(--mono);
  font-size: .72rem;
  font-weight: 500;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: var(--petroleo);
  display: flex; align-items: center; gap: .6rem;
  margin-bottom: .35rem;
}}
.sg-eyebrow::before {{
  content: ""; width: 1.4rem; height: 2px; background: var(--ambar);
}}

.sg-page-title {{
  font-family: var(--display);
  font-stretch: 118%;
  font-weight: 800;
  font-size: clamp(1.9rem, 3.4vw, 2.7rem);
  line-height: 1.05;
  color: var(--tinta);
  margin: 0 0 .6rem;
  letter-spacing: -0.015em;
}}
.sg-lede {{
  font-size: 1.06rem;
  line-height: 1.6;
  color: var(--ardosia);
  max-width: 68ch;
  margin: 0 0 1.4rem;
}}

.sg-section {{
  display: flex; align-items: baseline; justify-content: space-between; gap: 1rem;
  border-top: 1px solid var(--fio);
  padding-top: 1.1rem;
  margin: 1.6rem 0 .4rem;
}}
.sg-section h3 {{
  font-family: var(--display);
  font-stretch: 110%;
  font-size: 1.22rem;
  font-weight: 700;
  margin: 0; padding: 0;
  color: var(--tinta);
}}
.sg-section span {{ color: var(--ardosia); font-size: .9rem; }}

.sg-chip {{
  display: inline-flex; align-items: center; gap: .35rem;
  font-family: var(--mono);
  font-size: .76rem;
  padding: .18rem .55rem;
  border-radius: 999px;
  border: 1px solid var(--fio);
  background: var(--superficie);
  color: var(--tinta);
  margin: 0 .3rem .35rem 0;
  white-space: nowrap;
}}
.sg-chip.is-accent {{ border-color: var(--petroleo); background: var(--petroleo-claro); color: var(--petroleo); }}
.sg-join {{ color: var(--ambar); font-weight: 700; margin: 0 .1rem .35rem 0; display: inline-block; }}

.sg-callout {{
  border-left: 3px solid var(--ambar);
  background: var(--superficie);
  border-radius: 0 .6rem .6rem 0;
  padding: 1rem 1.25rem;
  color: var(--tinta);
  line-height: 1.65;
}}
[class*="st-key-sg-callout"] {{
  border-left: 3px solid var(--ambar);
  background: var(--superficie);
  border-radius: 0 .6rem .6rem 0;
  padding: 1rem 1.3rem .4rem;
  gap: .2rem;
}}
[class*="st-key-sg-callout"] p {{ line-height: 1.7; }}
.sg-callout-title,
.sg-callout .sg-callout-title {{
  font-family: var(--mono); font-size: .7rem; letter-spacing: .14em;
  text-transform: uppercase; color: var(--ardosia); margin-bottom: .4rem;
}}

.sg-note {{
  font-size: .86rem; color: var(--ardosia); line-height: 1.5;
}}

/* Faixa de etapas do processamento (sequência real) */
.sg-pipeline {{
  display: grid;
  grid-template-columns: repeat(var(--n, 4), minmax(0, 1fr));
  border: 1px solid var(--fio);
  border-radius: .75rem;
  background: var(--superficie);
  overflow: hidden;
  margin: .4rem 0 1rem;
}}
.sg-step {{
  position: relative;
  padding: 1rem 1.1rem 1.05rem;
  border-right: 1px solid var(--fio);
}}
.sg-step:last-child {{ border-right: 0; }}
.sg-step:not(:last-child)::after {{
  content: ""; position: absolute; right: -6px; top: 50%;
  width: 10px; height: 10px; background: var(--superficie);
  border-top: 1px solid var(--fio); border-right: 1px solid var(--fio);
  transform: translateY(-50%) rotate(45deg); z-index: 1;
}}
.sg-step-label {{
  font-family: var(--mono); font-size: .68rem; letter-spacing: .12em;
  text-transform: uppercase; color: var(--ardosia);
}}
.sg-step-value {{
  font-family: var(--display); font-stretch: 112%; font-weight: 750;
  font-size: 1.65rem; color: var(--tinta); line-height: 1.15; margin: .2rem 0 .1rem;
  font-variant-numeric: tabular-nums;
}}
.sg-step-detail {{ font-size: .84rem; color: var(--ardosia); line-height: 1.4; }}
.sg-step.is-loss .sg-step-value {{ color: {COR.alerta}; }}
.sg-step.is-final {{ background: var(--petroleo-claro); }}
.sg-step.is-final .sg-step-value {{ color: var(--petroleo); }}

/* Diagrama unifilar da página inicial */
.sg-oneline {{ width: 100%; height: auto; display: block; margin: .3rem 0 .4rem; }}
.sg-oneline.is-compact {{ display: none; max-width: 460px; }}
.sg-oneline .pulse {{
  stroke-dasharray: 6 26;
  animation: sg-flow 1.6s linear infinite;
}}
@keyframes sg-flow {{ to {{ stroke-dashoffset: -64; }} }}
@media (prefers-reduced-motion: reduce) {{
  .sg-oneline .pulse {{ animation: none; }}
}}

/* Cartões de navegação */
.sg-card {{
  display: block; height: 100%;
  border: 1px solid var(--fio); border-radius: .75rem;
  background: var(--superficie); padding: 1rem 1.1rem;
}}
.sg-card h4 {{
  font-family: var(--display); font-stretch: 108%; font-size: 1.02rem; font-weight: 700;
  margin: 0 0 .3rem; padding: 0; color: var(--tinta);
}}
.sg-card p {{ margin: 0; font-size: .9rem; color: var(--ardosia); line-height: 1.5; }}

/* Integrantes */
.sg-team {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: .6rem; }}
.sg-member {{
  border: 1px solid var(--fio); border-radius: .6rem; padding: .7rem .9rem; background: var(--superficie);
}}
.sg-member b {{ display: block; font-weight: 600; font-size: .93rem; color: var(--tinta); }}
.sg-member span {{ font-family: var(--mono); font-size: .76rem; color: var(--ardosia); }}

/* Legenda de classes de tensão */
.sg-legend {{ display: flex; flex-wrap: wrap; gap: .25rem .9rem; margin: .1rem 0 .6rem; }}
.sg-legend span {{ display: inline-flex; align-items: center; gap: .4rem; font-size: .8rem; color: var(--ardosia); }}
.sg-legend i {{ width: .75rem; height: .75rem; border-radius: 2px; display: inline-block; }}

/* Página de consultas */
.sg-query-title {{
  font-family: var(--display);
  font-stretch: 106%;
  font-weight: 700;
  font-size: clamp(1.35rem, 2.2vw, 1.75rem);
  line-height: 1.2;
  color: var(--tinta);
  margin: 0 0 .9rem;
  padding: 0;
  max-width: 40ch;
}}
.sg-categories {{
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
  border-top: 1px solid var(--fio); border-bottom: 1px solid var(--fio);
  margin: 0 0 1.6rem;
}}
.sg-categories div {{
  display: grid; grid-template-columns: auto 1fr; column-gap: .7rem; align-items: baseline;
  padding: .8rem 1rem .8rem 0;
}}
.sg-categories div + div {{ border-left: 1px solid var(--fio); padding-left: 1rem; }}
.sg-categories b {{
  grid-row: span 2; font-family: var(--display); font-stretch: 115%;
  font-size: 2rem; font-weight: 800; color: var(--petroleo); line-height: 1;
}}
.sg-categories span {{ font-weight: 600; font-size: .9rem; color: var(--tinta); }}
.sg-categories code {{
  font-family: var(--mono); font-size: .75rem; color: var(--ardosia); background: none; padding: 0;
}}
.sg-index-group {{
  display: flex; justify-content: space-between; align-items: baseline;
  font-family: var(--mono); font-size: .66rem; letter-spacing: .12em; text-transform: uppercase;
  color: var(--ardosia); border-bottom: 1px solid var(--fio);
  padding: .9rem 0 .3rem; margin-bottom: .15rem;
}}
.sg-index-group em {{ font-style: normal; color: var(--nevoa); }}
.st-key-sg-indice {{ gap: .1rem; }}
.st-key-sg-indice button {{ justify-content: flex-start; text-align: left; min-height: 2.1rem; }}
.st-key-sg-indice button > div, .st-key-sg-indice button [data-testid="stMarkdownContainer"] {{
  justify-content: flex-start; text-align: left; width: 100%;
}}
.st-key-sg-indice button p {{ font-size: .86rem; line-height: 1.3; text-align: left; }}
.st-key-sg-indice [data-testid="stBaseButton-tertiary"] {{ padding-left: .55rem; }}
.st-key-sg-indice [data-testid="stBaseButton-tertiary"]:hover {{ background: var(--petroleo-claro); }}
.st-key-sg-seletor-compacto {{ display: none; }}
[class*="st-key-sg-vizinha-"] button p {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

/* Tabela de requisitos */
.sg-req {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
.sg-req th, .sg-req td {{ text-align: left; padding: .55rem .6rem; border-bottom: 1px solid var(--fio); vertical-align: top; }}
.sg-req thead th {{
  font-family: var(--mono); font-size: .66rem; letter-spacing: .12em; text-transform: uppercase;
  color: var(--ardosia); font-weight: 500; border-bottom: 1px solid var(--tinta);
}}
.sg-req tbody th {{ font-weight: 600; color: var(--tinta); white-space: nowrap; }}
.sg-req td:nth-child(2) {{ color: var(--ardosia); white-space: nowrap; }}
.sg-ok {{
  display: inline-grid; place-items: center; width: 1.15rem; height: 1.15rem; margin-right: .5rem;
  border-radius: 50%; background: var(--petroleo); color: #fff; font-size: .7rem; font-weight: 700;
}}

/* Cartões de atalho (page_link dentro de contêiner com borda) */
[class*="st-key-sg-card-"] {{ background: var(--superficie); gap: 0; padding: .7rem 1rem .75rem; }}
[class*="st-key-sg-card-"] [data-testid="stPageLink"] p {{
  font-family: var(--display); font-stretch: 108%; font-weight: 700; font-size: 1.02rem;
}}
[class*="st-key-sg-card-"]:hover {{ border-color: var(--petroleo); }}

/* Editor do laboratório SQL */
.st-key-lab-sql textarea {{
  font-family: var(--mono); font-size: .86rem; line-height: 1.55;
  background: var(--superficie); color: var(--tinta);
}}

/* Rodapé da barra lateral */
.sg-sidebar-foot {{
  font-size: .76rem; line-height: 1.5; color: #8FA8B8;
  border-top: 1px solid #24405C; padding-top: .8rem; margin-top: .6rem;
}}
.sg-sidebar-foot b {{ color: #DCE6EC; font-weight: 600; }}

/* Responsividade ------------------------------------------------------------ */
/* Colunas lado a lado empilham quando o espaço do contêiner fica estreito. */
@container (max-width: 700px) {{
  [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; row-gap: 1rem; }}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important;
  }}
}}
/* Página de consultas: o índice lateral dá lugar a um seletor compacto. */
@container principal (max-width: 980px) {{
  [data-testid="stColumn"]:has(.st-key-sg-indice) {{ display: none; }}
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-sg-indice) > [data-testid="stColumn"] {{
    width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important;
  }}
  .st-key-sg-seletor-compacto {{ display: block; }}
}}
@container (max-width: 760px) {{
  .sg-pipeline {{ grid-template-columns: 1fr 1fr; }}
  .sg-step {{ border-bottom: 1px solid var(--fio); }}
  .sg-step:nth-child(2n) {{ border-right: 0; }}
  .sg-step::after {{ display: none; }}
  .sg-categories {{ grid-template-columns: 1fr 1fr; }}
  .sg-categories div:nth-child(3) {{ border-left: 0; padding-left: 0; }}
  .sg-categories div:nth-child(-n+2) {{ border-bottom: 1px solid var(--fio); }}
}}
@container (max-width: 560px) {{
  .sg-oneline.is-wide {{ display: none; }}
  .sg-oneline.is-compact {{ display: block; }}
  .sg-step {{ padding: .8rem .85rem .85rem; }}
  .sg-step-value {{ font-size: 1.35rem; }}
  .sg-section {{ flex-wrap: wrap; row-gap: .2rem; }}
  /* Tabela de requisitos vira lista: uma linha por requisito, sem cabeçalho. */
  .sg-req thead {{ display: none; }}
  .sg-req tr {{ display: grid; grid-template-columns: 1fr auto; column-gap: .8rem; padding: .55rem 0; border-bottom: 1px solid var(--fio); }}
  .sg-req th, .sg-req td {{ border: 0; padding: .1rem 0; white-space: normal !important; }}
  .sg-req td:nth-child(2) {{ text-align: right; font-size: .8rem; }}
  .sg-req td:nth-child(3) {{ grid-column: 1 / -1; }}
}}
@media (max-width: 640px) {{
  .block-container, [data-testid="stMainBlockContainer"] {{ padding-top: 4.2rem; padding-left: 1rem; padding-right: 1rem; }}
  .sg-lede {{ font-size: 1rem; }}
}}
</style>
"""


def aplicar_tema() -> None:
    """Injeta fontes e CSS globais. Deve ser chamado uma vez por execução."""
    st.html(_CSS)
