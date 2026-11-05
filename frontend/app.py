import streamlit as st
import requests
import pandas as pd
from datetime import date

API = "http://127.0.0.1:8000"

CATEGORIAS_DESPESA = sorted([
    "Plano de Saúde", "Alimentação - Restaurantes", "Alimentação - Supermercados",
    "Luz", "Gás", "Condomínio", "Telefonia", "Cartão Adicional (mãe)",
    "Estacionamento", "Diversão", "Viagens", "Internet", "Academia",
    "Seguro", "Carro", "Outros",
])

CATEGORIAS_INVESTIMENTO = sorted([
    "Fundos", "Tesouro Direto", "Previdência Privada", "Outros",
])

CATEGORIAS_RECEITA = sorted([
    "Salário", "Adicionais do Salário", "Aluguel",
    "Recebimento de Empréstimo", "Outros",
])

TIPOS_DESPESA = ["Fixo", "Cartao", "Extra"]
TIPOS_MOV = ["Aporte", "Rendimento", "Resgate"]

st.set_page_config(page_title="Meu Financeiro", layout="wide", page_icon="💰")

# ---------- CSS customizado ----------
st.markdown("""
<style>
    /* Fonte base maior e mais confortável */
    html, body, [class*="css"] {
        font-size: 17px;
    }

    /* Títulos */
    h1 {
        color: #1F6F8B;
        font-size: 2.4rem !important;
        font-weight: 700;
        margin-bottom: 0.2rem !important;
    }
    h2 {
        color: #1F6F8B;
        font-size: 1.7rem !important;
        margin-top: 1.2rem !important;
    }
    h3 {
        font-size: 1.3rem !important;
        margin-top: 1rem !important;
    }

    /* Cards de métrica com fundo branco e sombra */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(31, 111, 139, 0.08);
        border-left: 4px solid #1F6F8B;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.95rem !important;
        color: #5A6B75 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        color: #1A2B34 !important;
    }

    /* Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #FFFFFF;
        border-radius: 8px 8px 0 0;
        padding: 10px 18px;
        font-size: 1rem;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1F6F8B !important;
        color: #FFFFFF !important;
    }

    /* Botões */
    .stButton > button {
        background-color: #1F6F8B;
        color: #FFFFFF;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1.2rem;
        font-weight: 600;
    }
    .stButton > button:hover {
        background-color: #175466;
        color: #FFFFFF;
    }

    /* Cards coloridos semânticos */
    .card-receita {
        background: linear-gradient(135deg, #E8F6EE 0%, #FFFFFF 100%);
        border-left: 5px solid #2E9E5B;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 8px 0;
    }
    .card-despesa {
        background: linear-gradient(135deg, #FDECEA 0%, #FFFFFF 100%);
        border-left: 5px solid #D9534F;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 8px 0;
    }
    .card-investimento {
        background: linear-gradient(135deg, #FBF3DA 0%, #FFFFFF 100%);
        border-left: 5px solid #C9A227;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 8px 0;
    }
    .card-label {
        font-size: 0.9rem;
        color: #5A6B75;
        margin-bottom: 4px;
    }
    .card-value {
        font-size: 1.5rem;
        font-weight: 700;
    }
    .card-receita .card-value { color: #2E9E5B; }
    .card-despesa .card-value { color: #D9534F; }
    .card-investimento .card-value { color: #C9A227; }

    /* Dataframe mais leve */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

st.title("💰 Meu Financeiro")
st.caption("Controle de gastos, despesas fixas, investimentos e parcelamentos")

aba_lancar, aba_mes, aba_graficos, aba_recorrentes, aba_invest = st.tabs(
    ["➕ Lançar", "📊 Resumo do mês", "📈 Gráficos", "🔁 Recorrentes", "💼 Investimentos"]
)

# ============ ABA LANÇAR ============
with aba_lancar:
    st.subheader("Nova transação")

    natureza = st.radio(
        "Natureza", ["Despesa", "Receita"], index=0, horizontal=True,
        key="natureza_lancar",
    )

    if natureza == "Despesa":
        tipo = st.selectbox(
            "Tipo", TIPOS_DESPESA, index=1,
            help="Fixo = luz, internet, condomínio. Cartão = compras no cartão. Extra = seguros e eventuais.",
            key="tipo_lancar",
        )
        categorias = CATEGORIAS_DESPESA
        modo = st.radio(
            "Forma de lançamento", ["Única", "Parcelada"], horizontal=True,
            key="modo_lancar",
        )
        st.caption("💡 Aportes em investimento são lançados na aba **Investimentos**, não aqui.")
    else:
        tipo = "Receita"
        categorias = CATEGORIAS_RECEITA
        modo = "Única"
        st.caption("Receitas são lançadas como entrada única.")

    st.divider()

    if modo == "Única":
        with st.form("form_unica"):
            data = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
            descricao = st.text_input("Descrição")
            valor = st.number_input("Valor", step=None, min_value=0.0, format="%.2f")
            categoria = st.selectbox("Categoria", categorias)
            enviar = st.form_submit_button("Lançar")

            if enviar and descricao and valor > 0:
                valor_final = -valor if natureza == "Despesa" else valor
                requests.post(f"{API}/transacoes", json={
                    "data": str(data), "descricao": descricao, "valor": valor_final,
                    "categoria": categoria, "tipo": tipo, "recorrente": False,
                })
                st.success("Lançado!")
    else:
        with st.form("form_parcelada"):
            data = st.date_input("Data da 1ª parcela", value=date.today(), format="DD/MM/YYYY")
            descricao = st.text_input("Descrição da compra")
            valor_total = st.number_input("Valor total", step=None, min_value=0.0, format="%.2f")
            num_parcelas = st.number_input("Nº de parcelas", min_value=2, max_value=48, value=2, step=1)
            categoria = st.selectbox("Categoria", categorias)
            enviar = st.form_submit_button("Lançar parcelado")

            if enviar and descricao and valor_total > 0:
                requests.post(f"{API}/parcelamentos", json={
                    "descricao": descricao, "valor_total": valor_total,
                    "categoria": categoria, "tipo": tipo,
                    "data_primeira_parcela": str(data), "num_parcelas": int(num_parcelas),
                })
                st.success(f"{int(num_parcelas)} parcelas criadas.")

# ============ ABA RESUMO DO MÊS ============
with aba_mes:
    st.subheader("Resumo do mês")

    hoje = date.today()
    col1, col2 = st.columns(2)
    ano = col1.number_input("Ano", min_value=2020, max_value=2100, value=hoje.year, step=1, key="ano_mes")
    mes = col2.number_input("Mês", min_value=1, max_value=12, value=hoje.month, step=1, key="mes_mes")

    dados = requests.get(f"{API}/transacoes/mes/{int(ano)}/{int(mes)}").json()
    resumo_inv = requests.get(f"{API}/movimentacoes/mes/{int(ano)}/{int(mes)}").json()

    if not dados and not resumo_inv:
        st.info("Nenhuma transação neste mês.")
    else:
        df = pd.DataFrame(dados) if dados else pd.DataFrame()
        if not df.empty:
            df["data"] = pd.to_datetime(df["data"]).dt.date

        df_desp = df[df["valor"] < 0].copy() if not df.empty else pd.DataFrame()
        df_rec = df[df["valor"] > 0].copy() if not df.empty else pd.DataFrame()

        total_desp = df_desp["valor"].sum() if not df_desp.empty else 0
        total_rec = df_rec["valor"].sum() if not df_rec.empty else 0
        aportes = resumo_inv.get("aportes", 0)
        resgates = resumo_inv.get("resgates", 0)
        rendimentos = resumo_inv.get("rendimentos", 0)

        saldo_caixa = total_rec - abs(total_desp)

        # Cards coloridos
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="card-despesa">
                <div class="card-label">🔴 Despesas</div>
                <div class="card-value">R$ {abs(total_desp):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="card-receita">
                <div class="card-label">🟢 Receitas</div>
                <div class="card-value">R$ {total_rec:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="card-investimento">
                <div class="card-label">🟡 Aportes</div>
                <div class="card-value">R$ {aportes:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            cor_saldo = "card-receita" if saldo_caixa >= 0 else "card-despesa"
            sinal = "" if saldo_caixa >= 0 else "-"
            st.markdown(f"""
            <div class="{cor_saldo}">
                <div class="card-label">💰 Saldo em caixa</div>
                <div class="card-value">{sinal}R$ {abs(saldo_caixa):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        if resgates > 0 or rendimentos > 0:
            infos = []
            if resgates > 0:
                infos.append(f"🟡 Resgates no mês: R$ {resgates:,.2f} (entrada em caixa)")
            if rendimentos > 0:
                infos.append(f"📈 Rendimentos no mês: R$ {rendimentos:,.2f} (não entram no caixa)")
            st.caption(" · ".join(infos))

        st.divider()

        st.markdown("### 🔴 Despesas do mês")
        if df_desp.empty:
            st.info("Nenhuma despesa neste mês.")
        else:
            st.write(f"**Total: R$ {abs(total_desp):,.2f}**")

            st.write("**Total por tipo:**")
            nomes_tipo = {"Fixo": "Fixo", "Cartao": "Cartão", "Extra": "Extra", "Investimento": "Investimento"}
            por_tipo = df_desp.groupby("tipo")["valor"].sum().reset_index()
            por_tipo["tipo"] = por_tipo["tipo"].map(lambda x: nomes_tipo.get(x, x))
            por_tipo["valor"] = por_tipo["valor"].abs()
            por_tipo = por_tipo.rename(columns={"tipo": "Tipo", "valor": "Total"})
            st.dataframe(por_tipo, use_container_width=True, hide_index=True)

            st.write("**Despesas (edite selecionando uma linha):**")
            df_edit_d = df_desp.copy()
            df_edit_d["valor"] = df_edit_d["valor"].abs()
            df_edit_d["data_br"] = pd.to_datetime(df_edit_d["data"]).dt.strftime("%d-%m-%Y")
            df_edit_d = df_edit_d.drop(columns=["data"])
            df_edit_d = df_edit_d[["id", "data_br", "descricao", "valor", "categoria", "tipo"]]

            editado_d = st.data_editor(
                df_edit_d, use_container_width=True, hide_index=True, disabled=["id"],
                column_config={
                    "data_br": st.column_config.TextColumn("Data (DD-MM-AAAA)"),
                    "valor": st.column_config.NumberColumn("Valor", format="%.2f"),
                },
                key="editor_despesas",
            )

            if st.button("Salvar alterações de despesas"):
                originais = {t["id"]: t for t in dados}
                for _, linha in editado_d.iterrows():
                    tid = int(linha["id"])
                    original = originais.get(tid)
                    if not original:
                        continue
                    data_iso = pd.to_datetime(linha["data_br"], format="%d-%m-%Y").strftime("%Y-%m-%d")
                    payload = {
                        "data": data_iso, "descricao": linha["descricao"],
                        "valor": -abs(float(linha["valor"])), "categoria": linha["categoria"],
                        "tipo": linha["tipo"], "recorrente": bool(original["recorrente"]),
                    }
                    if any(str(payload[k]) != str(original[k]) for k in payload if k != "recorrente"):
                        requests.put(f"{API}/transacoes/{tid}", json=payload)
                st.success("Alterações de despesas salvas.")
                st.rerun()

        st.divider()

        st.markdown("### 🟢 Receitas do mês")
        if df_rec.empty:
            st.info("Nenhuma receita neste mês.")
        else:
            st.write(f"**Total: R$ {total_rec:,.2f}**")

            st.write("**Receitas (edite selecionando uma linha):**")
            df_edit_r = df_rec.copy()
            df_edit_r["data_br"] = pd.to_datetime(df_edit_r["data"]).dt.strftime("%d-%m-%Y")
            df_edit_r = df_edit_r.drop(columns=["data"])
            df_edit_r = df_edit_r[["id", "data_br", "descricao", "valor", "categoria", "tipo"]]

            editado_r = st.data_editor(
                df_edit_r, use_container_width=True, hide_index=True, disabled=["id"],
                column_config={
                    "data_br": st.column_config.TextColumn("Data (DD-MM-AAAA)"),
                    "valor": st.column_config.NumberColumn("Valor", format="%.2f"),
                },
                key="editor_receitas",
            )

            if st.button("Salvar alterações de receitas"):
                originais = {t["id"]: t for t in dados}
                for _, linha in editado_r.iterrows():
                    tid = int(linha["id"])
                    original = originais.get(tid)
                    if not original:
                        continue
                    data_iso = pd.to_datetime(linha["data_br"], format="%d-%m-%Y").strftime("%Y-%m-%d")
                    payload = {
                        "data": data_iso, "descricao": linha["descricao"],
                        "valor": abs(float(linha["valor"])), "categoria": linha["categoria"],
                        "tipo": linha["tipo"], "recorrente": bool(original["recorrente"]),
                    }
                    if any(str(payload[k]) != str(original[k]) for k in payload if k != "recorrente"):
                        requests.put(f"{API}/transacoes/{tid}", json=payload)
                st.success("Alterações de receitas salvas.")
                st.rerun()

# ============ ABA GRÁFICOS ============
with aba_graficos:
    st.subheader("Gráficos do mês")

    hoje = date.today()
    col1, col2 = st.columns(2)
    ano_g = col1.number_input("Ano (gráficos)", min_value=2020, max_value=2100, value=hoje.year, step=1, key="ano_graf")
    mes_g = col2.number_input("Mês (gráficos)", min_value=1, max_value=12, value=hoje.month, step=1, key="mes_graf")

    dados_g = requests.get(f"{API}/transacoes/mes/{int(ano_g)}/{int(mes_g)}").json()

    if not dados_g:
        st.info("Nenhuma transação neste mês.")
    else:
        dfg = pd.DataFrame(dados_g)
        dfg_desp = dfg[dfg["valor"] < 0].copy()
        dfg_rec = dfg[dfg["valor"] > 0].copy()

        st.markdown("### 🔴 Despesas por categoria")
        if dfg_desp.empty:
            st.info("Nenhuma despesa neste mês.")
        else:
            por_cat = dfg_desp.groupby("categoria")["valor"].sum().abs().sort_values(ascending=False)
            st.bar_chart(por_cat, color="#D9534F")

            st.markdown("### 🔴 Despesas por tipo")
            nomes_tipo = {"Fixo": "Fixo", "Cartao": "Cartão", "Extra": "Extra", "Investimento": "Investimento"}
            por_tipo = dfg_desp.groupby("tipo")["valor"].sum().abs()
            por_tipo.index = [nomes_tipo.get(t, t) for t in por_tipo.index]
            st.bar_chart(por_tipo, color="#D9534F")

        st.divider()

        st.markdown("### 🟢 Receitas por categoria")
        if dfg_rec.empty:
            st.info("Nenhuma receita neste mês.")
        else:
            por_cat_r = dfg_rec.groupby("categoria")["valor"].sum().sort_values(ascending=False)
            st.bar_chart(por_cat_r, color="#2E9E5B")

# ============ ABA RECORRENTES ============
with aba_recorrentes:
    st.subheader("Lançamentos recorrentes")
    st.caption("Cadastre uma vez. O app gera automaticamente no mês ao abrir o resumo.")

    natureza_r = st.radio(
        "Natureza", ["Despesa", "Receita"], index=0, horizontal=True,
        key="natureza_recorrente",
    )

    categorias_r = CATEGORIAS_DESPESA if natureza_r == "Despesa" else CATEGORIAS_RECEITA

    with st.form("form_recorrente"):
        descricao = st.text_input("Descrição (ex: Luz, Internet, Salário)")
        valor = st.number_input("Valor mensal", step=None, min_value=0.0, format="%.2f")
        categoria = st.selectbox("Categoria", categorias_r)
        dia = st.number_input("Dia do vencimento/recebimento", min_value=1, max_value=31, value=1, step=1)
        criar = st.form_submit_button("Cadastrar recorrente")

        if criar and descricao and valor > 0:
            requests.post(f"{API}/recorrentes", json={
                "descricao": descricao, "valor": valor, "categoria": categoria,
                "natureza": natureza_r, "dia_vencimento": int(dia),
            })
            st.success("Recorrente cadastrado.")
            st.rerun()

    st.write("**Cadastrados:**")
    recorrentes = requests.get(f"{API}/recorrentes").json()
    if not recorrentes:
        st.info("Nenhum recorrente cadastrado.")
    else:
        df_rec = pd.DataFrame(recorrentes)
        df_rec["valor"] = df_rec["valor"].abs()
        editado_rec = st.data_editor(
            df_rec, use_container_width=True, hide_index=True, disabled=["id"],
            column_config={
                "valor": st.column_config.NumberColumn("Valor", format="%.2f"),
                "natureza": st.column_config.SelectboxColumn("Natureza", options=["Despesa", "Receita"]),
            },
            key="editor_recorrentes",
        )
        if st.button("Salvar alterações dos recorrentes"):
            originais = {r["id"]: r for r in recorrentes}
            for _, linha in editado_rec.iterrows():
                rid = int(linha["id"])
                original = originais.get(rid)
                if not original:
                    continue
                payload = {
                    "descricao": linha["descricao"], "valor": float(linha["valor"]),
                    "categoria": linha["categoria"], "natureza": linha["natureza"],
                    "dia_vencimento": int(linha["dia_vencimento"]), "ativa": bool(linha["ativa"]),
                }
                if any(str(payload[k]) != str(original[k]) for k in payload):
                    requests.put(f"{API}/recorrentes/{rid}", json=payload)
            st.success("Alterações salvas.")
            st.rerun()

# ============ ABA INVESTIMENTOS ============
with aba_invest:
    st.subheader("Investimentos")

    with st.expander("➕ Cadastrar novo ativo", expanded=False):
        with st.form("form_ativo"):
            nome_ativo = st.text_input("Nome do ativo (ex: Tesouro Selic 2029)")
            categoria_ativo = st.selectbox("Categoria", CATEGORIAS_INVESTIMENTO)
            criar_ativo_btn = st.form_submit_button("Cadastrar ativo")

            if criar_ativo_btn and nome_ativo:
                requests.post(f"{API}/ativos", json={"nome": nome_ativo, "categoria": categoria_ativo})
                st.success("Ativo cadastrado.")
                st.rerun()

    ativos = requests.get(f"{API}/ativos").json()

    if not ativos:
        st.info("Nenhum ativo cadastrado. Cadastre um ativo acima para começar.")
    else:
        total_geral = sum(a["saldo"] for a in ativos)
        st.markdown(f"""
        <div class="card-investimento">
            <div class="card-label">💼 Total investido</div>
            <div class="card-value">R$ {total_geral:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

        st.write("**Posição atual:**")
        df_ativos = pd.DataFrame(ativos)[["id", "nome", "categoria", "saldo"]]
        df_ativos["saldo"] = df_ativos["saldo"].apply(lambda v: f"R$ {v:,.2f}")
        st.dataframe(df_ativos, use_container_width=True, hide_index=True)

        st.divider()

        st.markdown("### Nova movimentação")
        nomes_ativos = {a["nome"]: a["id"] for a in ativos}

        with st.form("form_mov"):
            ativo_sel = st.selectbox("Ativo", list(nomes_ativos.keys()))
            tipo_mov = st.selectbox("Tipo", TIPOS_MOV)
            data_mov = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
            valor_mov = st.number_input("Valor", step=None, min_value=0.0, format="%.2f")
            obs_mov = st.text_input("Observação (opcional)")
            enviar_mov = st.form_submit_button("Lançar movimentação")

            if enviar_mov and valor_mov > 0:
                requests.post(f"{API}/movimentacoes", json={
                    "ativo_id": nomes_ativos[ativo_sel],
                    "data": str(data_mov), "tipo": tipo_mov,
                    "valor": valor_mov,
                    "observacao": obs_mov if obs_mov else None,
                })
                st.success("Movimentação lançada.")
                st.rerun()

        st.divider()

        st.markdown("### Histórico e edição")
        ativo_hist = st.selectbox("Ver movimentações de:", list(nomes_ativos.keys()), key="hist_ativo")
        movs = requests.get(f"{API}/movimentacoes?ativo_id={nomes_ativos[ativo_hist]}").json()

        if not movs:
            st.info("Nenhuma movimentação para este ativo.")
        else:
            dfm = pd.DataFrame(movs)
            dfm["data_br"] = pd.to_datetime(dfm["data"]).dt.strftime("%d-%m-%Y")
            dfm = dfm[["id", "data_br", "tipo", "valor", "observacao"]]

            editado_m = st.data_editor(
                dfm, use_container_width=True, hide_index=True, disabled=["id"],
                column_config={
                    "data_br": st.column_config.TextColumn("Data (DD-MM-AAAA)"),
                    "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_MOV),
                    "valor": st.column_config.NumberColumn("Valor", format="%.2f"),
                },
                key="editor_movimentacoes",
            )

            if st.button("Salvar alterações de movimentações"):
                originais = {m["id"]: m for m in movs}
                for _, linha in editado_m.iterrows():
                    mid = int(linha["id"])
                    original = originais.get(mid)
                    if not original:
                        continue
                    data_iso = pd.to_datetime(linha["data_br"], format="%d-%m-%Y").strftime("%Y-%m-%d")
                    payload = {
                        "data": data_iso,
                        "tipo": linha["tipo"],
                        "valor": float(linha["valor"]),
                        "observacao": linha["observacao"] if pd.notna(linha["observacao"]) else None,
                    }
                    if any(str(payload[k]) != str(original[k]) for k in ["data", "tipo", "valor", "observacao"]):
                        requests.put(f"{API}/movimentacoes/{mid}", json=payload)
                st.success("Alterações salvas.")
                st.rerun()
