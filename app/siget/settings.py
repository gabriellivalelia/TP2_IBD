"""Configurações centrais da aplicação: caminhos, metadados do projeto e limites.

Todos os caminhos são resolvidos a partir da raiz do repositório, de modo que a
aplicação funcione independentemente do diretório de onde o Streamlit é iniciado.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ── Caminhos ────────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = APP_DIR.parent

RESULTS_DIR = ROOT_DIR / "resultado_siget"
SOURCE_DB = RESULTS_DIR / "siget_normalizado.db"
AUDIT_CSV = RESULTS_DIR / "auditoria.csv"
NOTEBOOK = ROOT_DIR / "tp2.ipynb"
# As imagens dos diagramas vêm das referências no próprio notebook (data/report.py).

CACHE_DIR = APP_DIR / ".cache"
REPLICA_DB = CACHE_DIR / "siget_utf8.db"


# ── Projeto ─────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Integrante:
    nome: str
    matricula: str


PROJECT_TITLE = "Expansão da Rede de Transmissão Brasileira"
PROJECT_SUBTITLE = "Banco de dados relacional construído a partir do SIGET/ANEEL"
COURSE = "DCC011 · Introdução a Banco de Dados · UFMG"
DATASET_URL = "https://dados.gov.br/dados/conjuntos-dados/sistema-de-gestao-da-transmissao-siget"

INTEGRANTES: tuple[Integrante, ...] = (
    Integrante("Gabrielli Valelia Sousa da Silva", "2022055513"),
    Integrante("Lara Strutz Carvalho", "2023039325"),
    Integrante("Pedro Henrique Silva Lima", "2022061459"),
    Integrante("Rian Rero Lopes Jericó Vieira", "2023039473"),
    Integrante("Talita Félix Lucio", "2022061432"),
)

# Arquivos originais do SIGET e seus tamanhos (Tabela 1 do relatório).
ARQUIVOS_ORIGINAIS: tuple[tuple[str, int, int], ...] = (
    ("Contrato Agente", 370, 14),
    ("Contrato Empreendimento Obra Módulo", 17_632, 32),
    ("Contrato Módulo Linha Transmissão Subestação", 1_671, 29),
    ("Contrato Módulo Equipamento Subestação", 4_135, 21),
    ("Contrato Módulo Manobra Subestação Tipo Arranjo", 9_552, 20),
)

# ── Laboratório SQL ─────────────────────────────────────────────────────────
SQL_LAB_MAX_ROWS = 5_000
SQL_LAB_TIMEOUT_S = 5.0
