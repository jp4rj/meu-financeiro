import streamlit as st
import requests
from datetime import date

API = "http://127.0.0.1:8000"

st.title("💰 Meu Financeiro")

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

st.subheader("Transações")
dados = requests.get(f"{API}/transacoes").json()
if dados:
    st.dataframe(dados, use_container_width=True)
else:
    st.info("Nenhuma transação ainda.")
