import streamlit as st
import requests
import pandas as pd
from datetime import date

API = "http://127.0.0.1:8000"

st.title("💰 Meu Financeiro")

# --- Formulário de lançamento ---
with st.form("nova_transacao"):
    data = st.date_input("Data", value=date.today())
    descricao = st.text_input("Descrição")
    valor = st.number_input("Valor (negativo = despesa)", step=0.01)
    categoria = st.selectbox("Categoria",
        ["Moradia", "Alimentação", "Cartão", "Seguro", "Lazer", "Outros"])
    tipo = st.selectbox("Tipo", ["Fixo", "Cartao", "Extra", "Investimento"])
    enviar = st.form_submit_button("Lançar")

    if enviar and descricao:
        requests.post(f"{API}/transacoes", json={
            "data": str(data), "descricao": descricao, "valor": valor,
            "categoria": categoria, "tipo": tipo, "recorrente": False
        })
        st.success("Lançado!")

# --- Resumo do mês ---
st.subheader("Resumo do mês")

hoje = date.today()
col1, col2 = st.columns(2)
ano = col1.number_input("Ano", min_value=2020, max_value=2100, value=hoje.year, step=1)
mes = col2.number_input("Mês", min_value=1, max_value=12, value=hoje.month, step=1)

dados = requests.get(f"{API}/transacoes/mes/{int(ano)}/{int(mes)}").json()

if not dados:
    st.info("Nenhuma transação neste mês.")
else:
    df = pd.DataFrame(dados)
    st.metric("Saldo do mês", f"R$ {df['valor'].sum():,.2f}")

    st.write("**Total por tipo:**")
    st.dataframe(df.groupby("tipo")["valor"].sum().reset_index()
                 .rename(columns={"valor": "total"}), use_container_width=True)

    st.write("**Total por categoria:**")
    st.bar_chart(df.groupby("categoria")["valor"].sum().sort_values())

    st.write("**Transações:**")
    st.dataframe(df, use_container_width=True)
