"""Acesso ao banco SQLite normalizado.

O banco gerado pelo notebook guarda textos UTF-8 que foram lidos como Latin-1
("OperaÃ§Ã£o" em vez de "Operação"). Em vez de corrigir cada resultado, a
aplicação cria uma *réplica* do banco com os textos já corrigidos e passa a
consultar somente essa réplica, sempre em modo leitura. Assim:

* o banco original do grupo nunca é alterado;
* filtros com acento (``WHERE DscSitObr = 'Em operação'``) funcionam no SQL;
* o laboratório SQL devolve textos legíveis sem pós-processamento.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from siget import settings

Params = Mapping[str, object] | Sequence[object] | None


# ── Correção de codificação ─────────────────────────────────────────────────
def corrigir_texto(valor: object) -> object:
    """Desfaz o mojibake UTF-8→Latin-1, preservando valores já corretos."""
    if isinstance(valor, str):
        try:
            return valor.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return valor
    return valor


def _colunas_texto(conexao: sqlite3.Connection) -> dict[str, list[str]]:
    tabelas = [
        nome
        for (nome,) in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    return {
        tabela: [
            coluna[1] for coluna in conexao.execute(f'PRAGMA table_info("{tabela}")') if coluna[2].upper() == "TEXT"
        ]
        for tabela in tabelas
    }


def _construir_replica(origem: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    temporario.unlink(missing_ok=True)

    with closing(sqlite3.connect(f"{origem.resolve().as_uri()}?mode=ro", uri=True)) as fonte:
        with closing(sqlite3.connect(temporario)) as replica:
            fonte.backup(replica)

    with closing(sqlite3.connect(temporario)) as replica:
        replica.create_function("corrigir", 1, corrigir_texto, deterministic=True)
        replica.execute("PRAGMA foreign_keys = OFF")
        for tabela, colunas in _colunas_texto(replica).items():
            if colunas:
                atribuicoes = ", ".join(f'"{c}" = corrigir("{c}")' for c in colunas)
                replica.execute(f'UPDATE "{tabela}" SET {atribuicoes}')
        replica.commit()
        replica.execute("VACUUM")

    temporario.replace(destino)


@st.cache_resource(show_spinner="Preparando o banco de dados…")
def caminho_banco() -> Path:
    """Garante que a réplica UTF-8 exista e esteja atualizada; devolve seu caminho."""
    origem, replica = settings.SOURCE_DB, settings.REPLICA_DB
    if not origem.exists():
        raise FileNotFoundError(
            f"Banco normalizado não encontrado em {origem}. Execute a Seção 3 do notebook tp2.ipynb para gerá-lo."
        )
    if not replica.exists() or replica.stat().st_mtime < origem.stat().st_mtime:
        _construir_replica(origem, replica)
    return replica


def _conectar() -> sqlite3.Connection:
    uri = f"{caminho_banco().resolve().as_uri()}?mode=ro"
    conexao = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conexao.execute("PRAGMA query_only = ON")
    return conexao


# ── Consultas da aplicação ──────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def consultar(sql: str, params: Params = None) -> pd.DataFrame:
    """Executa uma consulta de leitura e devolve um DataFrame (resultado em cache)."""
    with closing(_conectar()) as conexao:
        return pd.read_sql_query(sql, conexao, params=params)


def escalar(sql: str, params: Params = None) -> object:
    """Atalho para consultas que devolvem um único valor."""
    resultado = consultar(sql, params)
    return None if resultado.empty else resultado.iat[0, 0]


# ── Laboratório SQL (consultas livres do usuário) ───────────────────────────
class ErroConsulta(Exception):
    """Erro apresentável ao usuário do laboratório SQL."""


@dataclass(frozen=True, slots=True)
class ResultadoLivre:
    dados: pd.DataFrame
    truncado: bool
    duracao_ms: float


def executar_livre(
    sql: str,
    limite: int = settings.SQL_LAB_MAX_ROWS,
    tempo_maximo_s: float = settings.SQL_LAB_TIMEOUT_S,
) -> ResultadoLivre:
    """Executa SQL arbitrário com proteções: somente leitura, um comando e tempo limite."""
    comando = sql.strip().rstrip(";").strip()
    if not comando:
        raise ErroConsulta("Escreva uma consulta antes de executar.")

    inicio = time.perf_counter()
    prazo = inicio + tempo_maximo_s

    with closing(_conectar()) as conexao:
        # Interrompe consultas longas: o SQLite chama o handler a cada N instruções.
        conexao.set_progress_handler(lambda: int(time.perf_counter() > prazo), 10_000)
        try:
            cursor = conexao.execute(comando)
        except sqlite3.ProgrammingError as erro:
            raise ErroConsulta("Execute um comando por vez (apenas uma instrução SQL).") from erro
        except sqlite3.OperationalError as erro:
            if "interrupted" in str(erro):
                raise ErroConsulta(
                    f"A consulta passou de {tempo_maximo_s:.0f} s e foi interrompida. "
                    "Restrinja o resultado com WHERE ou LIMIT."
                ) from erro
            if "readonly" in str(erro) or "query_only" in str(erro):
                raise ErroConsulta("O laboratório é somente leitura: use SELECT, WITH ou PRAGMA de consulta.") from erro
            raise ErroConsulta(f"Erro do SQLite: {erro}") from erro

        if cursor.description is None:
            raise ErroConsulta("O comando não devolveu linhas. Use uma consulta SELECT.")

        colunas = [d[0] for d in cursor.description]
        linhas = cursor.fetchmany(limite + 1)

    truncado = len(linhas) > limite
    dados = pd.DataFrame(linhas[:limite], columns=colunas)
    return ResultadoLivre(dados, truncado, (time.perf_counter() - inicio) * 1000)


# ── Introspecção do esquema ─────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Coluna:
    nome: str
    tipo: str
    pk: int
    not_null: bool
    fk_para: str | None


@dataclass(frozen=True, slots=True)
class Tabela:
    nome: str
    linhas: int
    colunas: tuple[Coluna, ...]

    @property
    def chave_primaria(self) -> tuple[str, ...]:
        return tuple(c.nome for c in sorted(self.colunas, key=lambda c: c.pk) if c.pk)


@st.cache_data(show_spinner=False)
def esquema() -> tuple[Tabela, ...]:
    """Lê tabelas, colunas, chaves e cardinalidades diretamente do SQLite."""
    with closing(_conectar()) as conexao:
        nomes = [
            nome
            for (nome,) in conexao.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"
            )
        ]
        tabelas = []
        for nome in nomes:
            fks = {fk[3]: f"{fk[2]}.{fk[4]}" for fk in conexao.execute(f'PRAGMA foreign_key_list("{nome}")')}
            colunas = tuple(
                Coluna(c[1], c[2], c[5], bool(c[3]), fks.get(c[1]))
                for c in conexao.execute(f'PRAGMA table_info("{nome}")')
            )
            (linhas,) = conexao.execute(f'SELECT COUNT(*) FROM "{nome}"').fetchone()
            tabelas.append(Tabela(nome, linhas, colunas))
    return tuple(tabelas)


@st.cache_data(show_spinner=False)
def ddl() -> str:
    """Devolve o DDL (CREATE TABLE) do banco, formatado para leitura."""
    with closing(_conectar()) as conexao:
        comandos = [
            sql
            for (sql,) in conexao.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"
            )
        ]
    return "\n\n".join(_formatar_ddl(c) + ";" for c in comandos)


def _formatar_ddl(comando: str) -> str:
    cabecalho, _, corpo = comando.partition("(")
    corpo = corpo.rsplit(")", 1)[0]
    partes, nivel, atual = [], 0, ""
    for caractere in corpo:
        if caractere == "," and nivel == 0:
            partes.append(atual.strip())
            atual = ""
            continue
        nivel += caractere == "("
        nivel -= caractere == ")"
        atual += caractere
    partes.append(atual.strip())
    return cabecalho.strip() + " (\n    " + ",\n    ".join(partes) + "\n)"
