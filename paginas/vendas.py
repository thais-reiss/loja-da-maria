import io
from datetime import date

import pandas as pd
import streamlit as st

from loja import banco
from loja.limpeza import ENTREGAS, PAGAMENTOS, limpar_produto, sem_acento

CARTOES = ["Visa", "Mastercard", "Elo", "Outro"]


def reais(valor):
    if pd.isna(valor):
        return ""
    return f"R$ {valor:.2f}".replace(".", ",")


def texto_pagamento(venda):
    """Junta forma, cartão e parcelas: 'Crédito Visa 2x'."""
    partes = [venda["pagamento"], venda["cartao"]]
    if pd.notna(venda["parcelas"]):
        partes.append(f"{int(venda['parcelas'])}x")
    return " ".join(parte for parte in partes if pd.notna(parte))


def texto_produto(venda):
    """Deixa claro quando a linha não é uma venda."""
    if venda["tipo"] == "Venda":
        return venda["produto"]
    return f"{venda['produto']} ({venda['tipo'].lower()})"


def planilha_para_baixar(vendas):
    """Monta um arquivo Excel com todas as vendas, para a Maria guardar."""
    copia = vendas.drop(columns=["id", "original"]).rename(columns={
        "data": "Data", "produto": "Produto", "cliente": "Cliente", "valor": "Valor",
        "pagamento": "Pagamento", "cartao": "Cartão", "parcelas": "Parcelas",
        "entrega": "Entrega", "rastreio": "Rastreio", "obs": "Observação",
        "tipo": "Tipo", "conferir": "Conferir",
    })
    copia["Data"] = pd.to_datetime(copia["Data"]).dt.date  # data de verdade, não texto
    arquivo = io.BytesIO()
    with pd.ExcelWriter(arquivo, engine="openpyxl") as escritor:
        copia.to_excel(escritor, index=False, sheet_name="Vendas")
        for celula in escritor.sheets["Vendas"]["A"][1:]:  # coluna Data, sem o título
            celula.number_format = "DD/MM/YYYY"
    return arquivo.getvalue()


def concluir(mensagem):
    """Depois de salvar ou apagar: guarda o aviso, desmarca a linha e recarrega a tela."""
    st.session_state.aviso_vendas = mensagem
    st.session_state.versao_tabela += 1
    st.rerun()


def editar(venda):
    """Mostra os campos da venda escolhida, com os botões Salvar, Está certo assim e Apagar."""
    numero = venda["id"]  # entra na chave de cada campo, para não misturar uma venda com outra

    with st.container(border=True):
        st.subheader(f"Corrigir: {venda['produto'] or 'sem produto'} – {venda['cliente'] or 'sem nome'}")
        if venda["conferir"]:
            st.warning(f"Para conferir: {venda['conferir']}", icon="⚠️")
        if venda["original"]:
            st.caption(f"Como estava na planilha: {venda['original']}")

        coluna_produto, coluna_valor = st.columns([2, 1])
        with coluna_produto:
            produto = st.text_input("Produto", venda["produto"] or "", key=f"produto_{numero}")
        with coluna_valor:
            valor = st.number_input(
                "Valor (R$)", value=venda["valor"], step=1.0, format="%.2f",
                placeholder="0,00", key=f"valor_{numero}",
            )

        nome = st.text_input("Nome", venda["cliente"] or "", key=f"nome_{numero}")
        dia = st.date_input(
            "Data", value=date.fromisoformat(venda["data"]) if venda["data"] else None,
            format="DD/MM/YYYY", key=f"data_{numero}",
        )

        pagamento = st.segmented_control(
            "Forma de pagamento", PAGAMENTOS, default=venda["pagamento"], key=f"pagamento_{numero}"
        )
        cartao, parcelas = None, None
        if pagamento in ("Débito", "Crédito"):
            cartao = st.segmented_control(
                "Cartão", CARTOES, default=venda["cartao"], key=f"cartao_{numero}"
            )
            parcelas = 1
        if pagamento == "Crédito":
            parcelas = st.number_input(
                "Parcelas", min_value=1, max_value=12, value=int(venda["parcelas"] or 1),
                key=f"parcelas_{numero}",
            )

        entrega = st.segmented_control(
            "Entrega", ENTREGAS, default=venda["entrega"], key=f"entrega_{numero}"
        )
        rastreio = None
        if entrega == "Correios":
            rastreio = st.text_input(
                "Código de rastreio", venda["rastreio"] or "", key=f"rastreio_{numero}",
                placeholder="Se ainda não tem, deixe em branco",
            )
        obs = st.text_input("Observação", venda["obs"] or "", key=f"obs_{numero}")

        botao_salvar, botao_certo, botao_apagar = st.columns(3)

        with botao_salvar:
            if st.button("Salvar", type="primary", width="stretch", key=f"salvar_{numero}"):
                # se ainda faltar o básico, a venda continua na lista de conferir
                faltando = []
                if dia is None:
                    faltando.append("sem data")
                if valor is None:
                    faltando.append("sem valor")
                if pagamento is None:
                    faltando.append("sem forma de pagamento")
                banco.atualizar(numero, {
                    "data": dia,
                    "produto": limpar_produto(produto)[0],
                    "cliente": nome.strip() or None,
                    "valor": valor,
                    "pagamento": pagamento,
                    "cartao": cartao,
                    "parcelas": parcelas,
                    "entrega": entrega,
                    "rastreio": (rastreio or "").strip().upper() or None,
                    "obs": obs.strip() or None,
                    "conferir": "; ".join(faltando) or None,
                })
                concluir("Venda corrigida.")

        with botao_certo:
            if venda["conferir"] and st.button(
                "Está certo assim", width="stretch", key=f"certo_{numero}"
            ):
                banco.atualizar(numero, {"conferir": None})
                concluir("Pronto, essa venda saiu da lista de conferir.")

        with botao_apagar:
            with st.popover("Apagar", width="stretch"):
                st.write("Tem certeza? A venda some de vez.")
                if st.button("Sim, apagar esta venda", key=f"apagar_{numero}"):
                    banco.apagar(numero)
                    concluir("Venda apagada.")


st.title("Minhas vendas")

if "aviso_vendas" in st.session_state:
    st.success(st.session_state.pop("aviso_vendas"), icon="✅")
st.session_state.setdefault("versao_tabela", 0)

banco.criar_tabela()
registros = banco.listar()
vendas = pd.DataFrame(registros)

if vendas.empty:
    st.warning("Ainda não há nenhuma venda guardada.")
    st.stop()

# ------------------------------------------------------------ filtros

filtros = {
    "Todas": pd.Series(True, index=vendas.index),
    "Para conferir": vendas["conferir"].notna(),
    "Quem me deve": vendas["pagamento"] == "Fiado",
    "Envios sem rastreio": (vendas["entrega"] == "Correios") & vendas["rastreio"].isna(),
}

busca = st.text_input(
    "Procurar", placeholder="Digite um nome, um produto ou um código de rastreio"
)
escolha = st.segmented_control(
    "Mostrar",
    list(filtros),
    # as contagens mudam a cada correção e o botão se refaz: volta para o filtro em que ela estava
    default=st.session_state.get("filtro_escolhido", "Todas"),
    format_func=lambda nome: f"{nome} ({int(filtros[nome].sum())})",
) or "Todas"
st.session_state.filtro_escolhido = escolha

mostrar = filtros[escolha]

if busca:
    # junta tudo o que dá para procurar em um texto só, sem acentos
    datas = pd.to_datetime(vendas["data"]).dt.strftime("%d/%m/%Y").fillna("")
    colunas = vendas[["produto", "cliente", "rastreio", "obs", "pagamento", "entrega", "original"]]
    textos = (colunas.fillna("").agg(" ".join, axis=1) + " " + datas).map(sem_acento)
    palavras = sem_acento(busca).split()
    mostrar = mostrar & textos.map(lambda texto: all(palavra in texto for palavra in palavras))

achadas = vendas[mostrar]

# ------------------------------------------------------------- tabela

if achadas.empty:
    st.info("Não achei nenhuma venda com isso.")
else:
    if escolha == "Quem me deve":
        st.metric("Total a receber", reais(achadas["valor"].sum()))

    st.caption(
        f"{len(achadas)} de {len(vendas)} registros. "
        "Para corrigir ou completar uma venda, marque o quadradinho no começo da linha."
    )

    tabela = pd.DataFrame({
        "Data": pd.to_datetime(achadas["data"]),
        "Produto": achadas.apply(texto_produto, axis=1),
        "Cliente": achadas["cliente"],
        "Valor": achadas["valor"].map(reais),
        "Pagamento": achadas.apply(texto_pagamento, axis=1),
        "Entrega": achadas["entrega"],
        "Rastreio": achadas["rastreio"],
        "Observação": achadas["obs"],
    })
    if escolha == "Para conferir":
        tabela.insert(0, "O que conferir", achadas["conferir"])
        tabela["Como estava na planilha"] = achadas["original"]

    # célula sem informação aparece em branco, e não como "None"
    textos = tabela.columns.drop("Data")
    tabela[textos] = tabela[textos].fillna("")

    evento = st.dataframe(
        tabela,
        hide_index=True,
        width="stretch",
        column_config={"Data": st.column_config.DateColumn(format="DD/MM/YYYY")},
        on_select="rerun",
        selection_mode="single-row",
        # a chave muda quando a lista muda, para a linha marcada não apontar para outra venda
        key=f"tabela_{st.session_state.versao_tabela}_{escolha}_{busca}",
    )

    if evento.selection.rows:
        numero_escolhido = int(achadas.iloc[evento.selection.rows[0]]["id"])
        editar(next(venda for venda in registros if venda["id"] == numero_escolhido))

st.download_button(
    "Baixar planilha com todas as vendas",
    data=planilha_para_baixar(vendas),
    file_name="vendas_da_maria.xlsx",
    icon="⬇️",
)
