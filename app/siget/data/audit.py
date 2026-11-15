"""Leitura dos artefatos de auditoria produzidos pela limpeza dos dados (Seção 3)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from siget import settings


@st.cache_data(show_spinner=False)
def auditoria() -> pd.DataFrame:
    """Registro das etapas de extração, rejeição e limpeza, na ordem em que ocorreram."""
    dados = pd.read_csv(settings.AUDIT_CSV, encoding="utf-8-sig")
    dados.insert(0, "ordem", range(1, len(dados) + 1))
    return dados


@dataclass(frozen=True, slots=True)
class ArquivoRejeicao:
    rotulo: str
    caminho: Path


def arquivos_rejeicao() -> tuple[ArquivoRejeicao, ...]:
    """Arquivos `revisar_*.csv` com os registros removidos, com rótulos legíveis."""
    arquivos = sorted(settings.RESULTS_DIR.glob("revisar_*.csv"))
    arquivos += sorted(settings.RESULTS_DIR.glob("contratos_*.csv"))
    return tuple(ArquivoRejeicao(_rotulo(a), a) for a in arquivos)


@st.cache_data(show_spinner=False)
def ler_rejeicao(caminho: Path) -> pd.DataFrame:
    return pd.read_csv(caminho, encoding="utf-8-sig", dtype="string")


def _rotulo(caminho: Path) -> str:
    # O nome do arquivo perdeu os acentos; o motivo legível fica na 1ª coluna.
    try:
        motivo = pd.read_csv(caminho, encoding="utf-8-sig", nrows=1)
        if "motivo" in motivo.columns and not motivo.empty:
            origem = caminho.stem.removeprefix("revisar_").split("_", 1)[0].capitalize()
            return f"{origem} — {motivo.at[0, 'motivo']}"
    except (pd.errors.ParserError, UnicodeDecodeError):
        pass
    return caminho.stem.replace("_", " ").capitalize()
