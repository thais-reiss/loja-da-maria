import streamlit as st

st.set_page_config(page_title="Loja da Maria", page_icon="🛍️", layout="wide")

paginas = [
    st.Page("paginas/registrar.py", title="Registrar venda", icon="➕", default=True),
    st.Page("paginas/vendas.py", title="Minhas vendas", icon="📋"),
]

st.navigation(paginas, position="top").run()
