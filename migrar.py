"""Leva a planilha da Maria para o banco. Roda uma vez só:

    python migrar.py

A planilha original não é alterada.
"""
import sys
from collections import Counter
from pathlib import Path

import openpyxl

from loja import banco
from loja.limpeza import limpar_linha

PASTA = Path(__file__).parent


def ler_planilha(caminho):
    """Devolve as linhas preenchidas como dicionários {título: célula}."""
    aba = openpyxl.load_workbook(caminho).active
    linhas = list(aba.iter_rows(values_only=True))
    titulos = [str(titulo).strip() for titulo in linhas[0]]
    preenchidas = []
    for celulas in linhas[1:]:
        if any(celula is not None and str(celula).strip() for celula in celulas):
            preenchidas.append(dict(zip(titulos, celulas)))
    return preenchidas


def marcar(venda, motivo):
    """Acrescenta um motivo na lista de conferir da venda."""
    venda["conferir"] = "; ".join(parte for parte in (venda["conferir"], motivo) if parte)


def marcar_repetidas(vendas):
    """Duas linhas iguais podem ser a mesma venda anotada duas vezes. Não apaga: só avisa."""
    vistas = set()
    for venda in vendas:
        chave = (venda["data"], venda["produto"], venda["cliente"], venda["valor"], venda["pagamento"])
        if venda["data"] and chave in vistas:
            marcar(venda, "igual a outra linha; pode ter sido anotada duas vezes")
        vistas.add(chave)


def marcar_precos_diferentes(vendas):
    """Avisa quando o preço foge do que o produto costuma custar."""
    precos = {}
    for venda in vendas:
        if venda["tipo"] == "Venda" and venda["valor"] is not None:
            precos.setdefault(venda["produto"], []).append(venda["valor"])

    for venda in vendas:
        lista = precos.get(venda["produto"], [])
        if venda["tipo"] != "Venda" or venda["valor"] is None or len(lista) < 3:
            continue
        normal = Counter(lista).most_common(1)[0][0]
        if venda["valor"] != normal:
            marcar(venda, f"preço diferente do normal (R$ {normal:.2f})".replace(".", ","))


def migrar():
    planilhas = list(PASTA.rglob("Vendas_da_maria*.xlsx"))  # procura na raiz e nas subpastas
    if not planilhas:
        sys.exit("Não achei a planilha Vendas_da_maria*.xlsx na pasta do projeto.")

    banco.criar_tabela()
    if banco.contar() > 0:
        sys.exit("O banco já tem vendas. Para migrar de novo, apague o arquivo dados/vendas.db antes.")

    linhas = ler_planilha(planilhas[0])

    vendas = []
    vizinha = None  # última data confiável, usada para 'ontem', 'hj' e datas fora do lugar
    for linha in linhas:
        venda = limpar_linha(linha, vizinha)
        if venda["data"] and not venda["conferir"]:
            vizinha = venda["data"]
        vendas.append(venda)

    marcar_repetidas(vendas)
    marcar_precos_diferentes(vendas)

    for venda in vendas:
        banco.inserir(venda)

    para_conferir = [venda for venda in vendas if venda["conferir"]]
    print(f"Planilha: {planilhas[0].name}")
    print(f"Linhas lidas: {len(linhas)}")
    print(f"Gravadas no banco: {banco.contar()}")
    for tipo, quantidade in Counter(venda["tipo"] for venda in vendas).items():
        print(f"  {tipo}: {quantidade}")
    print(f"Para conferir: {len(para_conferir)}")
    for venda in para_conferir:
        print(f"  - {venda['produto']} / {venda['cliente'] or 'sem nome'}: {venda['conferir']}")


if __name__ == "__main__":
    migrar()
