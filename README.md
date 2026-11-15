# Expansão da Rede de Transmissão Brasileira — TP2 DCC011

Banco de dados relacional construído a partir dos dados abertos do
[SIGET/ANEEL](https://dados.gov.br/dados/conjuntos-dados/sistema-de-gestao-da-transmissao-siget),
com 10 consultas analíticas em SQL e uma aplicação Streamlit para explorá-las.

| Entregável | Onde está |
|---|---|
| Relatório (seções 1–7) | `tp2.ipynb` |
| Banco SQLite normalizado | `resultado_siget/siget_normalizado.db` |
| Auditoria da limpeza | `resultado_siget/auditoria.csv` e `revisar_*.csv` |
| Diagramas ER e relacional | `images/` |
| Aplicação Streamlit (extra) | `app/` |

## Como executar

Requer [uv](https://docs.astral.sh/uv/) (instala o Python 3.13 e as dependências).

```bash
uv sync
uv run streamlit run app/streamlit_app.py
```

A aplicação abre em <http://localhost:8501>. Ela lê o banco gerado pela Seção 3 do
notebook; se `resultado_siget/siget_normalizado.db` não existir, execute o notebook antes.

Testes (equivalência com o notebook, renderização de todas as páginas e segurança do laboratório SQL):

```bash
uv run pytest
```

## A aplicação

| Página | O que mostra |
|---|---|
| **Visão geral** | Tese do projeto, caminho dos dados (CSV → limpeza → 11 relações) e os requisitos do enunciado conferidos no próprio banco. |
| **Dados e tratamento** | Arquivos originais, relações resultantes, regras de limpeza e cada registro removido para conferência. |
| **Modelagem** | Diagramas ER e relacional, esquema navegável gerado a partir das chaves do SQLite e o DDL. |
| **As 10 consultas** | Para cada consulta: pergunta, SQL, destaques com gráficos, resultado completo (busca e CSV) e a análise do relatório. Todas aceitam parâmetros. |
| **Rede elétrica** | Cartograma das UFs clicável, subestações-polo, classes de tensão, arranjos de manobra e ficha de cada subestação. |
| **Agentes** | Perfil de cada concessionária: vigência dos contratos, empreendimentos, obras e posição em receita. |
| **Prazos de implantação** | Data do ato legal × data efetiva de operação: ritmo da expansão por ano e distribuição dos atrasos. |
| **Laboratório SQL** | Editor de consultas livres, somente leitura, com exemplos e referência do esquema. |

## Decisões de projeto

- **O notebook é a fonte da verdade.** As análises textuais de cada consulta são lidas de
  `tp2.ipynb` em tempo de execução. Quando o grupo edita o relatório, a aplicação acompanha.
- **Consultas parametrizadas, resultados idênticos.** Cada consulta usa *bind parameters*
  (`:tensao_minima`, `:uf`…). Com os valores padrão, o resultado é igual ao do notebook,
  o que é verificado em `tests/test_consultas.py`.
- **Correção de acentuação sem tocar no banco.** Os textos foram gravados como UTF-8 lido
  em Latin-1 (`OperaÃ§Ã£o`). A aplicação cria uma réplica corrigida e somente leitura em
  `app/.cache/` e nunca altera o arquivo original.
- **Laboratório seguro.** Conexão `mode=ro` + `PRAGMA query_only`, um comando por vez,
  limite de linhas e interrupção por tempo.

## Estrutura do código

```
app/
├── streamlit_app.py        # ponto de entrada: tema, navegação, barra lateral
├── static/                 # logotipo
└── siget/
    ├── settings.py         # caminhos, integrantes, limites
    ├── navigation.py       # registro das páginas e seções
    ├── data/
    │   ├── database.py     # réplica UTF-8, consultas em cache, laboratório, introspecção
    │   ├── report.py       # extrai pergunta, SQL e análise do notebook
    │   └── audit.py        # auditoria e arquivos de rejeição
    ├── queries/            # catálogo declarativo das 10 consultas
    │   ├── base.py         # Consulta, Parametro, Categoria
    │   ├── selecao.py      # C1–C2
    │   ├── juncao_duas.py  # C3–C5
    │   ├── juncao_multipla.py  # C6–C8
    │   └── agregacao.py    # C9–C10
    ├── ui/
    │   ├── theme.py        # tokens de cor, tipografia, CSS e template Plotly
    │   ├── components.py   # cabeçalhos, métricas, legendas, tabelas
    │   ├── charts.py       # fábricas de gráficos (barras, Pareto, mapa de calor, cartograma)
    │   └── formatting.py   # números no padrão brasileiro
    └── views/              # uma função render() por página
tests/
├── test_consultas.py       # app × notebook, SQL exibido executável, laboratório somente leitura
└── test_app.py             # todas as páginas e consultas renderizam sem exceção
```

Para adicionar uma consulta, declare um `Consulta` em `app/siget/queries/` e inclua-o em
`CONSULTAS` (`queries/__init__.py`); a página e os testes passam a cobri-la automaticamente.

## Integrantes

- Gabrielli Valelia Sousa da Silva (2022055513)
- Lara Strutz Carvalho (2023039325)
- Pedro Henrique Silva Lima (2022061459)
- Rian Rero Lopes Jericó Vieira (2023039473)
- Talita Félix Lucio (2022061432)
