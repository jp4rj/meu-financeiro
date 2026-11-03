import streamlit as st
import requests
import pandas as pd
from datetime import date

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="Meu Financeiro", layout="wide")
st.title("💰 Meu Financeiro")

aba_lancar, aba_mes, aba_fixas = st.tabs(
    ["Lançar", "Resumo do mês", "Despesas fixas"]
)

# ============ ABA LANÇAR ============
with aba_lancar:
    st.subheader("Nova transação")

    modo = st.radio("Tipo de lançamento", ["Única", "Parcelada"], horizontal=True)

    if modo == "Única":
        with st.form("form_unica"):
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
    else:
        with st.form("form_parcelada"):
            data = st.date_input("Data da 1ª parcela", value=date.today())
            descricao = st.text_input("Descrição da compra")
            valor_total = st.number_input("Valor total (positivo)", step=0.01, min_value=0.0)
            num_parcelas = st.number_input("Nº de parcelas", min_value=2, max_value=48, value=2, step=1)
            categoria = st.selectbox("Categoria",
                ["Moradia", "Alimentação", "Cartão", "Seguro", "Lazer", "Outros"])
            tipo = st.selectbox("Tipo", ["Cartao", "Extra", "Fixo"])
            enviar = st.form_submit_button("Lançar parcelado")

            if enviar and descricao and valor_total > 0:
                requests.post(f"{API}/parcelamentos", json={
                    "descricao": descricao,
                    "valor_total": valor_total,
                    "categoria": categoria,
                    "tipo": tipo,
                    "data_primeira_parcela": str(data),
                    "num_parcelas": int(num_parcelas),
                })
                st.success(f"{int(num_parcelas)} parcelas criadas.")

# ============ ABA RESUMO DO MÊS ============
with aba_mes:
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
        df["data"] = pd.to_datetime(df["data"]).dt.date
        st.metric("Saldo do mês", f"R$ {df['valor'].sum():,.2f}")

        st.write("**Total por tipo:**")
        st.dataframe(df.groupby("tipo")["valor"].sum().reset_index()
                     .rename(columns={"valor": "total"}), use_container_width=True)

        st.write("**Total por categoria:**")
        st.bar_chart(df.groupby("categoria")["valor"].sum().sort_values())

        st.write("**Transações (edite selecionando uma linha):**")
        editado = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=["id"],
            column_config={
                "data": st.column_config.DateColumn("Data"),
                "valor": st.column_config.NumberColumn("Valor", format="%.2f"),
            },
            key="editor_transacoes",
        )

        if st.button("Salvar alterações"):
            originais = {t["id"]: t for t in dados}
            for _, linha in editado.iterrows():
                tid = int(linha["id"])
                original = originais.get(tid)
                if not original:
                    continue
                payload = {
                    "data": str(linha["data"]),
                    "descricao": linha["descricao"],
                    "valor": float(linha["valor"]),
                    "categoria": linha["categoria"],
                    "tipo": linha["tipo"],
                    "recorrente": bool(linha["recorrente"]),
                }
                if any(str(payload[k]) != str(original[k]) for k in payload):
                    requests.put(f"{API}/transacoes/{tid}", json=payload)
            st.success("Alterações salvas.")
            st.rerun()

# ============ ABA DESPESAS FIXAS ============
with aba_fixas:
    st.subheader("Despesas fixas recorrentes")
    st.caption("Cadastre uma vez. O app gera automaticamente no mês ao abrir o resumo.")

    with st.form("form_fixa"):
        descricao = st.text_input("Descrição (ex: Luz, Internet, Condomínio)")
        valor = st.number_input("Valor mensal (positivo)", min_value=0.0, step=0.01)
        categoria = st.selectbox("Categoria",
            ["Moradia", "Alimentação", "Cartão", "Seguro", "Lazer", "Outros"])
        dia = st.number_input("Dia do vencimento", min_value=1, max_value=31, value=1, step=1)
        criar = st.form_submit_button("Cadastrar despesa fixa")

        if criar and descricao and valor > 0:
            requests.post(f"{API}/despesas-fixas", json={
                "descricao": descricao,
                "valor": valor,
                "categoria": categoria,
                "dia_vencimento": int(dia),
            })
            st.success("Despesa fixa cadastrada.")
            st.rerun()

    st.write("**Cadastradas:**")
    fixas = requests.get(f"{API}/despesas-fixas").json()
    if not fixas:
        st.info("Nenhuma despesa fixa cadastrada.")
    else:
        df_fixas = pd.DataFrame(fixas)
        editado_fixas = st.data_editor(
            df_fixas,
            use_container_width=True,
            hide_index=True,
            disabled=["id"],
            key="editor_fixas",
        )
        if st.button("Salvar alterações das fixas"):
            originais = {f["id"]: f for f in fixas}
            for _, linha in editado_fixas.iterrows():
                fid = int(linha["id"])
                original = originais.get(fid)
                if not original:
                    continue
                payload = {
                    "descricao": linha["descricao"],
                    "valor": float(linha["valor"]),
                    "categoria": linha["categoria"],
                    "dia_vencimento": int(linha["dia_vencimento"]),
                    "ativa": bool(linha["ativa"]),
                }
                if any(str(payload[k]) != str(original[k]) for k in payload):
                    requests.put(f"{API}/despesas-fixas/{fid}", json=payload)
            st.success("Alterações salvas.")
            st.rerun()
