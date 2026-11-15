"""Modelo declarativo das consultas do relatório.

Cada consulta é descrita uma única vez — SQL, parâmetros, relações envolvidas e
visualização — e a página de consultas apenas percorre o catálogo. Os valores
padrão dos parâmetros reproduzem exatamente a consulta do notebook; o teste
``tests/test_consultas.py`` garante essa equivalência.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

import pandas as pd

from siget.data.database import consultar

TODOS = "Todas"


class Categoria(Enum):
    SELECAO = ("Seleção e projeção", "σ · π", "Filtram e projetam atributos de uma única relação.")
    JUNCAO_DUAS = ("Junção de duas relações", "R ⋈ S", "Combinam duas relações por chave estrangeira.")
    JUNCAO_MULTIPLA = (
        "Junção de três ou mais relações",
        "R ⋈ S ⋈ T",
        "Percorrem caminhos de chaves estrangeiras pelo esquema.",
    )
    AGREGACAO = (
        "Agregação sobre junção",
        "γ (R ⋈ S)",
        "Agrupam e resumem o resultado de junções.",
    )

    def __init__(self, rotulo: str, notacao: str, descricao: str) -> None:
        self.rotulo = rotulo
        self.notacao = notacao
        self.descricao = descricao


TipoWidget = Literal["escolha", "multipla", "degraus", "intervalo", "texto"]


@dataclass(frozen=True, slots=True)
class Parametro:
    """Parâmetro exposto ao usuário e enviado ao SQLite como *bind parameter*.

    * ``escolha``  → valor único; a opção "Todas" envia ``NULL`` (sem filtro).
    * ``multipla`` → lista enviada como JSON e lida com ``json_each``; vazia = ``NULL``.
    * ``degraus``  → um valor dentre opções ordenadas.
    * ``intervalo``→ par (mín., máx.) enviado como ``:<nome>_min`` e ``:<nome>_max``.
    * ``texto``    → busca parcial; vazio = ``NULL``.
    """

    nome: str
    rotulo: str
    widget: TipoWidget
    padrao: Any = None
    opcoes: Sequence[Any] = ()
    opcoes_sql: str | None = None
    ajuda: str | None = None
    formatar: Callable[[Any], str] | None = None
    permite_todos: bool = True  # só para "escolha": inclui a opção "Todas" (= sem filtro)

    def listar_opcoes(self) -> list[Any]:
        if self.opcoes_sql:
            return consultar(self.opcoes_sql).iloc[:, 0].dropna().tolist()
        return list(self.opcoes)

    def para_sql(self, valor: Any) -> dict[str, Any]:
        match self.widget:
            case "escolha":
                return {self.nome: None if valor in (None, TODOS) else valor}
            case "multipla":
                return {self.nome: json.dumps(list(valor), ensure_ascii=False) if valor else None}
            case "intervalo":
                minimo, maximo = valor
                return {f"{self.nome}_min": minimo, f"{self.nome}_max": maximo}
            case "texto":
                return {self.nome: valor.strip() or None if isinstance(valor, str) else None}
            case _:
                return {self.nome: valor}


Visualizador = Callable[[pd.DataFrame, dict[str, Any]], None]


@dataclass(frozen=True, slots=True)
class Consulta:
    numero: int
    titulo: str  # rótulo curto para navegação
    pergunta: str
    descricao: str
    categoria: Categoria
    relacoes: tuple[str, ...]
    sql: str
    visualizar: Visualizador
    parametros: tuple[Parametro, ...] = field(default_factory=tuple)

    @property
    def codigo(self) -> str:
        return f"C{self.numero:02d}"

    def valores_padrao(self) -> dict[str, Any]:
        return {p.nome: p.padrao for p in self.parametros}

    def parametros_sql(self, valores: dict[str, Any]) -> dict[str, Any]:
        resultado: dict[str, Any] = {}
        for p in self.parametros:
            resultado |= p.para_sql(valores.get(p.nome, p.padrao))
        return resultado

    def executar(self, valores: dict[str, Any] | None = None) -> pd.DataFrame:
        valores = valores or self.valores_padrao()
        return consultar(self.sql, self.parametros_sql(valores))

    def sql_com_valores(self, valores: dict[str, Any]) -> str:
        """SQL com os parâmetros substituídos por literais — apenas para exibição."""
        texto = self.sql
        for nome, valor in sorted(self.parametros_sql(valores).items(), key=lambda kv: -len(kv[0])):
            texto = texto.replace(f":{nome}", _literal_sql(valor))
        return texto


def _literal_sql(valor: Any) -> str:
    if valor is None:
        return "NULL"
    if isinstance(valor, (int, float)):
        return f"{valor:g}"
    return "'" + str(valor).replace("'", "''") + "'"
