"""Guarda e busca as vendas no arquivo dados/vendas.db (SQLite)."""
import sqlite3
from contextlib import closing
from pathlib import Path

ARQUIVO = Path(__file__).parent.parent / "dados" / "vendas.db"

COLUNAS = [
    "data", "produto", "cliente", "valor", "pagamento", "cartao", "parcelas",
    "entrega", "rastreio", "obs", "tipo", "conferir", "original",
]


def conectar():
    conexao = sqlite3.connect(ARQUIVO)
    conexao.row_factory = sqlite3.Row  # permite ler cada linha como dicionário
    return conexao


def criar_tabela():
    ARQUIVO.parent.mkdir(exist_ok=True)  # cria a pasta dados, se ainda não existir
    with closing(conectar()) as conexao, conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                data      TEXT,     -- AAAA-MM-DD
                produto   TEXT,
                cliente   TEXT,
                valor     REAL,
                pagamento TEXT,
                cartao    TEXT,
                parcelas  INTEGER,
                entrega   TEXT,
                rastreio  TEXT,
                obs       TEXT,
                tipo      TEXT,     -- Venda, Devolução ou Compra
                conferir  TEXT,     -- motivo da dúvida; vazio quando está tudo certo
                original  TEXT      -- a linha como a Maria escreveu na planilha
            )
        """)


def inserir(venda):
    """Grava uma venda (dicionário com as chaves de COLUNAS)."""
    valores = [venda.get(coluna) for coluna in COLUNAS]
    if valores[0] is not None:
        valores[0] = str(valores[0])  # data vira texto AAAA-MM-DD
    marcadores = ", ".join("?" for _ in COLUNAS)
    with closing(conectar()) as conexao, conexao:
        conexao.execute(
            f"INSERT INTO vendas ({', '.join(COLUNAS)}) VALUES ({marcadores})", valores
        )


def atualizar(id_venda, campos):
    """Altera só os campos informados de uma venda já gravada."""
    campos = {coluna: valor for coluna, valor in campos.items() if coluna in COLUNAS}
    if campos.get("data") is not None:
        campos["data"] = str(campos["data"])
    trocas = ", ".join(f"{coluna} = ?" for coluna in campos)
    with closing(conectar()) as conexao, conexao:
        conexao.execute(f"UPDATE vendas SET {trocas} WHERE id = ?", [*campos.values(), id_venda])


def apagar(id_venda):
    with closing(conectar()) as conexao, conexao:
        conexao.execute("DELETE FROM vendas WHERE id = ?", [id_venda])


def listar():
    """Todas as vendas, da mais recente para a mais antiga."""
    with closing(conectar()) as conexao:
        linhas = conexao.execute("SELECT * FROM vendas ORDER BY data DESC, id DESC").fetchall()
    return [dict(linha) for linha in linhas]


def contar():
    with closing(conectar()) as conexao:
        return conexao.execute("SELECT COUNT(*) FROM vendas").fetchone()[0]
