from collections import Counter
from datetime import date, timedelta

import streamlit as st

from loja import banco
from loja.limpeza import ENTREGAS, PAGAMENTOS, limpar_produto

CARTOES = ["Visa", "Mastercard", "Elo", "Outro"]


def reais(valor):
    return f"R$ {valor:.2f}".replace(".", ",")


# O que já foi vendido alimenta as listas: ela escolhe em vez de digitar.
banco.criar_tabela()
vendas = [venda for venda in banco.listar() if venda["tipo"] == "Venda"]
produtos = sorted({venda["produto"] for venda in vendas if venda["produto"]})

# preço mais comum de cada produto, para já vir preenchido
preco_normal = {}
for produto in produtos:
    precos = [v["valor"] for v in vendas if v["produto"] == produto and v["valor"]]
    if precos:
        preco_normal[produto] = Counter(precos).most_common(1)[0][0]


def preencher_preco():
    """Quando ela escolhe o produto, o preço de sempre aparece sozinho."""
    escolhido = st.session_state.produto
    if escolhido in preco_normal:
        st.session_state.valor = float(preco_normal[escolhido])


def salvar():
    campos = st.session_state
    produto, _ = limpar_produto(campos.produto)
    valor = campos.valor
    nome = campos.cliente.strip()

    faltando = []
    if not produto:
        faltando.append("o produto")
    if not valor:
        faltando.append("o valor")
    if not nome:
        faltando.append("o nome")
    if faltando:
        campos.aviso = ("erro", "Falta preencher: " + ", ".join(faltando) + ".")
        return

    if campos.quando == "Ontem":
        dia = date.today() - timedelta(days=1)
    elif campos.quando == "Outro dia":
        dia = campos.outro_dia
    else:
        dia = date.today()

    pagamento = campos.pagamento
    cartao, parcelas = None, None
    if pagamento in ("Débito", "Crédito"):
        cartao = campos.get("cartao")
        parcelas = campos.get("parcelas") if pagamento == "Crédito" else 1

    entrega = campos.entrega
    rastreio = (campos.get("rastreio") or "").strip().upper() if entrega == "Correios" else ""

    banco.inserir({
        "data": dia,
        "produto": produto,
        "cliente": nome,
        "valor": valor,
        "pagamento": pagamento,
        "cartao": cartao,
        "parcelas": parcelas,
        "entrega": entrega,
        "rastreio": rastreio or None,
        "obs": campos.obs.strip() or None,
        "tipo": "Venda",
        "conferir": None if pagamento else "sem forma de pagamento",
    })
    campos.aviso = ("ok", f"Venda guardada: {produto}, {reais(valor)}.")

    # limpa o formulário para a próxima venda
    campos.produto = None
    campos.valor = None
    campos.cliente = ""
    campos.quando = "Hoje"
    campos.pagamento = None
    campos.entrega = None
    campos.obs = ""
    for campo in ("cartao", "parcelas", "rastreio", "outro_dia"):
        campos.pop(campo, None)


st.title("Registrar venda")

if "aviso" in st.session_state:
    tipo, mensagem = st.session_state.pop("aviso")
    if tipo == "ok":
        st.success(mensagem, icon="✅")
    else:
        st.error(mensagem, icon="⚠️")

st.session_state.setdefault("quando", "Hoje")

coluna_produto, coluna_valor = st.columns([2, 1])
with coluna_produto:
    st.selectbox(
        "Produto",
        produtos,
        index=None,
        key="produto",
        placeholder="Escolha na lista ou digite um produto novo",
        accept_new_options=True,
        on_change=preencher_preco,
    )
with coluna_valor:
    st.number_input(
        "Valor (R$)", min_value=0.0, step=1.0, format="%.2f",
        value=None, key="valor", placeholder="0,00",
    )

st.text_input("Nome", key="cliente", placeholder="Nome de quem comprou")

st.segmented_control("Data", ["Hoje", "Ontem", "Outro dia"], key="quando")
if st.session_state.quando == "Outro dia":
    st.date_input(
        "Que dia?", value=date.today(), max_value=date.today(),
        format="DD/MM/YYYY", key="outro_dia",
    )

st.segmented_control("Forma de pagamento", PAGAMENTOS, key="pagamento")
if st.session_state.pagamento in ("Débito", "Crédito"):
    st.segmented_control("Cartão", CARTOES, key="cartao")
if st.session_state.pagamento == "Crédito":
    st.number_input("Parcelas", min_value=1, max_value=12, value=1, key="parcelas")

st.segmented_control("Entrega", ENTREGAS, key="entrega")
if st.session_state.entrega == "Correios":
    st.text_input(
        "Código de rastreio", key="rastreio",
        placeholder="Se ainda não tem, deixe em branco",
    )

st.text_input("Observação", key="obs", placeholder="Ex.: pediu embrulho")

st.button("Salvar venda", type="primary", width="stretch", on_click=salvar)
