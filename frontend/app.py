import streamlit as st
import requests
import pandas as pd
from datetime import date, datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.legends import Legend

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

TIPOS_DESPESA_MAP = {
    "Cartão": "Cartao",
    "Débito Automático": "Debito Automatico",
    "PIX/Espécie": "PIX/Especie",
}

TIPOS_MOV = ["Aporte", "Resgate"]

MESES_ABREV = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

st.set_page_config(page_title="Meu Financeiro", layout="wide", page_icon="💰")

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 17px; }
    h1 { color: #1F6F8B; font-size: 2.4rem !important; font-weight: 700; margin-bottom: 0.2rem !important; }
    h2 { color: #1F6F8B; font-size: 1.7rem !important; margin-top: 1.2rem !important; }
    h3 { font-size: 1.3rem !important; margin-top: 1rem !important; }
    [data-testid="stMetric"] {
        background-color: #FFFFFF; border-radius: 12px; padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(31, 111, 139, 0.08); border-left: 4px solid #1F6F8B;
    }
    [data-testid="stMetricLabel"] { font-size: 0.95rem !important; color: #5A6B75 !important; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; color: #1A2B34 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #FFFFFF; border-radius: 8px 8px 0 0;
        padding: 10px 18px; font-size: 1rem; font-weight: 500;
    }
    .stTabs [aria-selected="true"] { background-color: #1F6F8B !important; color: #FFFFFF !important; }
    .stButton > button {
        background-color: #1F6F8B; color: #FFFFFF; border-radius: 8px;
        border: none; padding: 0.5rem 1.2rem; font-weight: 600;
    }
    .stButton > button:hover { background-color: #175466; color: #FFFFFF; }
    .card-receita {
        background: linear-gradient(135deg, #E8F6EE 0%, #FFFFFF 100%);
        border-left: 5px solid #2E9E5B; border-radius: 12px; padding: 16px 20px; margin: 8px 0;
    }
    .card-despesa {
        background: linear-gradient(135deg, #FDECEA 0%, #FFFFFF 100%);
        border-left: 5px solid #D9534F; border-radius: 12px; padding: 16px 20px; margin: 8px 0;
    }
    .card-investimento {
        background: linear-gradient(135deg, #FBF3DA 0%, #FFFFFF 100%);
        border-left: 5px solid #C9A227; border-radius: 12px; padding: 16px 20px; margin: 8px 0;
    }
    .card-neutro {
        background: linear-gradient(135deg, #EEF3F7 0%, #FFFFFF 100%);
        border-left: 5px solid #5A6B75; border-radius: 12px; padding: 16px 20px; margin: 8px 0;
    }
    .card-label { font-size: 0.9rem; color: #5A6B75; margin-bottom: 4px; }
    .card-value { font-size: 1.5rem; font-weight: 700; }
    .card-receita .card-value { color: #2E9E5B; }
    .card-despesa .card-value { color: #D9534F; }
    .card-investimento .card-value { color: #C9A227; }
    .card-neutro .card-value { color: #1A2B34; }
    [data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ==================== HELPERS DE PDF ====================

def _tabela_padrao(linhas, cor_cabecalho, larguras, linhas_destaque=None):
    t = Table(linhas, colWidths=larguras)
    estilos = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(cor_cabecalho)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D9E0")),
    ]
    if linhas_destaque:
        for idx in linhas_destaque:
            estilos.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#FBF3DA")))
            estilos.append(("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold"))
    t.setStyle(TableStyle(estilos))
    return t


def calcular_rendimento_carteira_mes(ano, mes, ativos):
    linhas = []
    total_rend = 0.0
    total_base = 0.0

    for a in ativos:
        atualizacoes = requests.get(f"{API}/atualizacoes-saldo?ativo_id={a['id']}").json()
        no_mes = []
        for u in atualizacoes:
            d = datetime.strptime(u["data"], "%Y-%m-%d")
            if d.year == ano and d.month == mes:
                no_mes.append(u)

        if not no_mes:
            continue

        rend_ativo = sum(u["rendimento_liquido"] for u in no_mes if u["rendimento_liquido"] is not None)
        base_ativo = None
        for u in sorted(no_mes, key=lambda x: (x["data"], x["id"])):
            if u["saldo_anterior"] is not None:
                base_ativo = u["saldo_anterior"]
                break

        pct_ativo = (rend_ativo / base_ativo * 100) if base_ativo and base_ativo > 0 else None

        linhas.append({
            "ativo": a["nome"],
            "rendimento": rend_ativo,
            "percentual": pct_ativo,
        })
        total_rend += rend_ativo
        if base_ativo and base_ativo > 0:
            total_base += base_ativo

    pct_total = (total_rend / total_base * 100) if total_base > 0 else None
    return linhas, total_rend, pct_total


def calcular_evolucao_patrimonio(ano, mes, ativos):
    """Retorna lista de (rotulo_mes, patrimonio_total) nos últimos 12 meses até o mês dado."""
    pontos = []
    for offset in range(11, -1, -1):
        m = mes - offset
        y = ano
        while m <= 0:
            m += 12
            y -= 1
        total = 0.0
        for a in ativos:
            # pega a atualização de saldo mais recente até o fim deste mês
            atualizacoes = requests.get(f"{API}/atualizacoes-saldo?ativo_id={a['id']}").json()
            saldo_ref = None
            for u in sorted(atualizacoes, key=lambda x: (x["data"], x["id"])):
                d = datetime.strptime(u["data"], "%Y-%m-%d")
                if (d.year < y) or (d.year == y and d.month <= m):
                    saldo_ref = u["saldo_informado"]
                else:
                    break
            if saldo_ref is not None:
                total += saldo_ref
        pontos.append((f"{MESES_ABREV[m]}/{str(y)[2:]}", total))
    return pontos


def grafico_rendimento_por_ativo(linhas_rend, largura=15 * cm, altura=7 * cm):
    """Barras horizontais: rendimento (R$) de cada ativo. Verde positivo, vermelho negativo."""
    if not linhas_rend:
        return None

    # ordenar por rendimento (para o gráfico ficar legível)
    linhas_ord = sorted(linhas_rend, key=lambda r: r["rendimento"])
    nomes = [r["ativo"][:25] for r in linhas_ord]
    valores = [round(r["rendimento"], 2) for r in linhas_ord]

    d = Drawing(largura, altura)
    chart = HorizontalBarChart()
    chart.x = 5.5 * cm
    chart.y = 0.8 * cm
    chart.width = largura - 6 * cm
    chart.height = altura - 1.5 * cm
    chart.data = [valores]
    chart.categoryAxis.categoryNames = nomes
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = min(0, min(valores)) * 1.1
    chart.valueAxis.valueMax = max(0, max(valores)) * 1.1
    chart.valueAxis.valueStep = (max(valores) - min(valores)) / 5 if valores else 1
    chart.bars[0].strokeColor = None

    # colorir cada barra
    for i, v in enumerate(valores):
        if v >= 0:
            chart.bars[(0, i)].fillColor = colors.HexColor("#2E9E5B")
        else:
            chart.bars[(0, i)].fillColor = colors.HexColor("#D9534F")

    chart.barSpacing = 3
    d.add(chart)
    return d


def grafico_evolucao_patrimonio(pontos, largura=15 * cm, altura=7 * cm):
    """Linha: evolução do patrimônio total nos últimos 12 meses."""
    if not pontos:
        return None

    rotulos = [p[0] for p in pontos]
    valores = [round(p[1], 2) for p in pontos]

    d = Drawing(largura, altura)
    chart = HorizontalLineChart()
    chart.x = 2 * cm
    chart.y = 1 * cm
    chart.width = largura - 3 * cm
    chart.height = altura - 2 * cm
    chart.data = [valores]
    chart.categoryAxis.categoryNames = rotulos
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 0
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(valores) * 1.15 if max(valores) > 0 else 1
    chart.lines[0].strokeColor = colors.HexColor("#1F6F8B")
    chart.lines[0].strokeWidth = 2
    chart.lines[0].symbol = None
    d.add(chart)
    return d


def gerar_pdf(ano, mes, transacoes, resumo_inv, saldo_ant, saldo_atual, ativos, movimentacoes_mes):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Resumo Financeiro {mes:02d}/{ano}",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="H1Custom", parent=styles["Heading1"],
        textColor=colors.HexColor("#1F6F8B"), fontSize=18, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="H2Custom", parent=styles["Heading2"],
        textColor=colors.HexColor("#1F6F8B"), fontSize=13, spaceBefore=12, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Sub", parent=styles["Normal"],
        textColor=colors.HexColor("#5A6B75"), fontSize=9, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Nota", parent=styles["Normal"],
        textColor=colors.HexColor("#7A8A94"), fontSize=7.5, spaceBefore=4,
    ))

    story = []
    meses_nome = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    story.append(Paragraph(f"Resumo Financeiro — {meses_nome[mes]} de {ano}", styles["H1Custom"]))
    story.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles["Sub"]))
    story.append(Spacer(1, 12))

    # ---- Totais do mês ----
    story.append(Paragraph("Totais do mês", styles["H2Custom"]))
    df = pd.DataFrame(transacoes) if transacoes else pd.DataFrame()
    total_rec = df[df["valor"] > 0]["valor"].sum() if not df.empty else 0
    total_desp = df[df["valor"] < 0]["valor"].sum() if not df.empty else 0

    dados_totais = [
        ["Item", "Valor"],
        ["Receitas do mês", f"R$ {total_rec:,.2f}"],
        ["Despesas do mês", f"R$ {abs(total_desp):,.2f}"],
        ["Aportes do mês", f"R$ {resumo_inv.get('aportes', 0):,.2f}"],
        ["Resgates do mês", f"R$ {resumo_inv.get('resgates', 0):,.2f}"],
        ["Rendimentos do mês", f"R$ {resumo_inv.get('rendimentos', 0):,.2f}"],
        ["Prejuízos do mês", f"R$ {resumo_inv.get('prejuizos', 0):,.2f}"],
        ["Saldo vindo do mês anterior", f"R$ {saldo_ant:,.2f}"],
        ["Saldo atual (acumulado)", f"R$ {saldo_atual:,.2f}"],
    ]
    story.append(_tabela_padrao(dados_totais, "#1F6F8B", [9 * cm, 6 * cm],
                                linhas_destaque=[len(dados_totais) - 1]))
    story.append(Spacer(1, 14))

    # ---- Despesas ----
    story.append(Paragraph("Despesas do mês", styles["H2Custom"]))
    desp = [t for t in transacoes if t["valor"] < 0] if transacoes else []
    if not desp:
        story.append(Paragraph("Nenhuma despesa neste mês.", styles["Normal"]))
    else:
        linhas = [["Data", "Descrição", "Categoria", "Tipo", "Valor"]]
        for t in sorted(desp, key=lambda x: x["data"]):
            data_br = datetime.strptime(t["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
            linhas.append([data_br, t["descricao"][:40], t["categoria"], t["tipo"], f"R$ {abs(t['valor']):,.2f}"])
        story.append(_tabela_padrao(linhas, "#D9534F", [2.2 * cm, 5.5 * cm, 3.5 * cm, 2 * cm, 2.3 * cm]))
    story.append(Spacer(1, 14))

    # ---- Receitas ----
    story.append(Paragraph("Receitas do mês", styles["H2Custom"]))
    rec = [t for t in transacoes if t["valor"] > 0] if transacoes else []
    if not rec:
        story.append(Paragraph("Nenhuma receita neste mês.", styles["Normal"]))
    else:
        linhas = [["Data", "Descrição", "Categoria", "Tipo", "Valor"]]
        for t in sorted(rec, key=lambda x: x["data"]):
            data_br = datetime.strptime(t["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
            linhas.append([data_br, t["descricao"][:40], t["categoria"], t["tipo"], f"R$ {t['valor']:,.2f}"])
        story.append(_tabela_padrao(linhas, "#2E9E5B", [2.2 * cm, 5.5 * cm, 3.5 * cm, 2 * cm, 2.3 * cm]))
    story.append(Spacer(1, 14))

    # ---- Posição de investimentos ----
    story.append(Paragraph("Posição de investimentos", styles["H2Custom"]))
    if not ativos:
        story.append(Paragraph("Nenhum ativo cadastrado.", styles["Normal"]))
    else:
        linhas = [["Ativo", "Categoria", "Saldo"]]
        total_inv = 0
        for a in ativos:
            linhas.append([a["nome"], a["categoria"], f"R$ {a['saldo']:,.2f}"])
            total_inv += a["saldo"]
        linhas.append(["TOTAL", "", f"R$ {total_inv:,.2f}"])
        story.append(_tabela_padrao(linhas, "#C9A227", [8 * cm, 4.5 * cm, 3 * cm],
                                     linhas_destaque=[len(linhas) - 1]))
    story.append(Spacer(1, 14))

    # ---- Rendimento da carteira no mês ----
    story.append(Paragraph("Rendimento da carteira no mês", styles["H2Custom"]))
    linhas_rend, total_rend, pct_total = calcular_rendimento_carteira_mes(ano, mes, ativos)

    if not linhas_rend:
        story.append(Paragraph(
            "Nenhum ativo teve atualização de saldo neste mês — rendimento não calculado.",
            styles["Normal"],
        ))
    else:
        dados_rend = [["Ativo", "Rendimento no mês", "Percentual no mês"]]
        for r in linhas_rend:
            rend = r["rendimento"]
            pct = r["percentual"]
            sinal = "+" if rend >= 0 else "−"
            tipo_str = "Rendimento" if rend >= 0 else "Prejuízo"
            pct_str = f"{pct:+.2f}%" if pct is not None else "—"
            dados_rend.append([
                r["ativo"][:35],
                f"{sinal}R$ {abs(rend):,.2f} ({tipo_str})",
                pct_str,
            ])
        sinal_tot = "+" if total_rend >= 0 else "−"
        tipo_tot = "Rendimento" if total_rend >= 0 else "Prejuízo"
        pct_tot_str = f"{pct_total:+.2f}%" if pct_total is not None else "—"
        dados_rend.append([
            "TOTAL DA CARTEIRA",
            f"{sinal_tot}R$ {abs(total_rend):,.2f} ({tipo_tot})",
            pct_tot_str,
        ])
        story.append(_tabela_padrao(
            dados_rend, "#C9A227", [8 * cm, 5 * cm, 3 * cm],
            linhas_destaque=[len(dados_rend) - 1],
        ))
        story.append(Paragraph(
            "Nota: o rendimento considera apenas ativos com atualização de saldo registrada neste mês. "
            "Aportes e resgates do período são desconsiderados no cálculo do rendimento.",
            styles["Nota"],
        ))

        # ---- Gráficos ----
        story.append(Spacer(1, 10))
        story.append(Paragraph("Gráfico — Rendimento por ativo no mês", styles["H2Custom"]))
        g1 = grafico_rendimento_por_ativo(linhas_rend)
        if g1 is not None:
            story.append(g1)

        story.append(Spacer(1, 10))
        story.append(Paragraph("Gráfico — Evolução do patrimônio (últimos 12 meses)", styles["H2Custom"]))
        pontos_patrimonio = calcular_evolucao_patrimonio(ano, mes, ativos)
        g2 = grafico_evolucao_patrimonio(pontos_patrimonio)
        if g2 is not None:
            story.append(g2)

    story.append(Spacer(1, 14))

    # ---- Movimentações de investimento ----
    story.append(Paragraph("Movimentações de investimento no mês", styles["H2Custom"]))
    if not movimentacoes_mes:
        story.append(Paragraph("Nenhuma movimentação de investimento neste mês.", styles["Normal"]))
    else:
        mapa_ativos = {a["id"]: a["nome"] for a in ativos}
        linhas = [["Data", "Ativo", "Tipo", "Valor", "Observação"]]
        for m in sorted(movimentacoes_mes, key=lambda x: x["data"]):
            data_br = datetime.strptime(m["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
            nome = mapa_ativos.get(m["ativo_id"], f"Ativo {m['ativo_id']}")
            obs = (m.get("observacao") or "")[:25]
            linhas.append([data_br, nome[:30], m["tipo"], f"R$ {m['valor']:,.2f}", obs])
        story.append(_tabela_padrao(linhas, "#C9A227", [2.2 * cm, 5 * cm, 2.5 * cm, 2.5 * cm, 3.3 * cm]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ==================== INÍCIO DO APP ====================

st.title("💰 Meu Financeiro")
st.caption("Controle de gastos, despesas fixas, investimentos e parcelamentos")

aba_lancar, aba_mes, aba_graficos, aba_recorrentes, aba_invest, aba_relatorios = st.tabs(
    ["➕ Lançar", "📊 Resumo do mês", "📈 Gráficos", "🔁 Recorrentes", "💼 Investimentos", "📄 Relatórios"]
)

# ============ ABA LANÇAR ============
with aba_lancar:
    st.subheader("Nova transação")

    natureza = st.radio(
        "Natureza", ["Despesa", "Receita"], index=0, horizontal=True,
        key="natureza_lancar",
    )

    if natureza == "Despesa":
        tipo_label = st.selectbox(
            "Tipo", list(TIPOS_DESPESA_MAP.keys()), index=0,
            help="Cartão = compras no cartão. Débito Automático = cobranças automáticas. PIX/Espécie = pagamentos à vista.",
            key="tipo_lancar",
        )
        tipo = TIPOS_DESPESA_MAP[tipo_label]
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

            if enviar:
                if not descricao or valor <= 0:
                    st.warning("Preencha descrição e valor antes de lançar.")
                else:
                    valor_final = -valor if natureza == "Despesa" else valor
                    r = requests.post(f"{API}/transacoes", json={
                        "data": str(data), "descricao": descricao, "valor": valor_final,
                        "categoria": categoria, "tipo": tipo, "recorrente": False,
                    })
                    if r.status_code == 200:
                        st.toast(
                            f"Lançamento de R$ {valor:,.2f} ({descricao}, {data.strftime('%d/%m/%Y')}) efetivado.",
                            icon="✅",
                        )
                    else:
                        st.error(f"Erro ao salvar: {r.text}")
    else:
        with st.form("form_parcelada"):
            data = st.date_input("Data da 1ª parcela", value=date.today(), format="DD/MM/YYYY")
            descricao = st.text_input("Descrição da compra")
            valor_total = st.number_input("Valor total", step=None, min_value=0.0, format="%.2f")
            num_parcelas = st.number_input("Nº de parcelas", min_value=2, max_value=48, value=2, step=1)
            categoria = st.selectbox("Categoria", categorias)
            enviar = st.form_submit_button("Lançar parcelado")

            if enviar:
                if not descricao or valor_total <= 0:
                    st.warning("Preencha descrição e valor antes de lançar.")
                else:
                    r = requests.post(f"{API}/parcelamentos", json={
                        "descricao": descricao, "valor_total": valor_total,
                        "categoria": categoria, "tipo": tipo,
                        "data_primeira_parcela": str(data), "num_parcelas": int(num_parcelas),
                    })
                    if r.status_code == 200:
                        st.toast(
                            f"Parcelamento de R$ {valor_total:,.2f} em {int(num_parcelas)}x ({descricao}) efetivado.",
                            icon="✅",
                        )
                    else:
                        st.error(f"Erro ao salvar: {r.text}")

# ============ ABA RESUMO DO MÊS ============
with aba_mes:
    st.subheader("Resumo do mês")

    hoje = date.today()
    col1, col2 = st.columns(2)
    ano = col1.number_input("Ano", min_value=2020, max_value=2100, value=hoje.year, step=1, key="ano_mes")
    mes = col2.number_input("Mês", min_value=1, max_value=12, value=hoje.month, step=1, key="mes_mes")

    dados = requests.get(f"{API}/transacoes/mes/{int(ano)}/{int(mes)}").json()
    resumo_inv = requests.get(f"{API}/movimentacoes/mes/{int(ano)}/{int(mes)}").json()
    acumulado = requests.get(f"{API}/saldo-acumulado/{int(ano)}/{int(mes)}").json()

    ano_ant = int(ano) - 1 if int(mes) == 1 else int(ano)
    mes_ant = 12 if int(mes) == 1 else int(mes) - 1
    acumulado_ant = requests.get(f"{API}/saldo-acumulado/{ano_ant}/{mes_ant}").json()

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
        prejuizos = resumo_inv.get("prejuizos", 0)

        saldo_anterior = acumulado_ant.get("saldo", 0)
        saldo_atual = acumulado.get("saldo", 0)

        st.markdown("##### O que aconteceu neste mês")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="card-receita">
                <div class="card-label">🟢 Receitas do mês</div>
                <div class="card-value">R$ {total_rec:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="card-despesa">
                <div class="card-label">🔴 Despesas do mês</div>
                <div class="card-value">R$ {abs(total_desp):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="card-investimento">
                <div class="card-label">🟡 Aportes do mês</div>
                <div class="card-value">R$ {aportes:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("##### Evolução do caixa")
        c4, c5 = st.columns(2)
        with c4:
            sinal_ant = "" if saldo_anterior >= 0 else "-"
            st.markdown(f"""
            <div class="card-neutro">
                <div class="card-label">📥 Saldo vindo do mês anterior</div>
                <div class="card-value">{sinal_ant}R$ {abs(saldo_anterior):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with c5:
            cor_atual = "card-receita" if saldo_atual >= 0 else "card-despesa"
            sinal_at = "" if saldo_atual >= 0 else "-"
            st.markdown(f"""
            <div class="{cor_atual}">
                <div class="card-label">💰 Saldo atual (acumulado)</div>
                <div class="card-value">{sinal_at}R$ {abs(saldo_atual):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        infos = []
        if resgates > 0:
            infos.append(f"🟡 Resgates no mês: R$ {resgates:,.2f} (entrada em caixa)")
        if rendimentos > 0:
            infos.append(f"📈 Rendimentos no mês: R$ {rendimentos:,.2f} (não entram no caixa)")
        if prejuizos > 0:
            infos.append(f"📉 Prejuízos no mês: R$ {prejuizos:,.2f} (não entram no caixa)")
        if infos:
            st.caption(" · ".join(infos))

        st.divider()

        st.markdown("### 🔴 Despesas do mês")
        if df_desp.empty:
            st.info("Nenhuma despesa neste mês.")
        else:
            st.write(f"**Total: R$ {abs(total_desp):,.2f}**")
            st.write("**Total por tipo:**")
            nomes_tipo = {"Fixo": "Fixo (legado)", "Cartao": "Cartão", "Extra": "Extra (legado)",
                          "Debito Automatico": "Débito Automático", "PIX/Especie": "PIX/Espécie",
                          "Investimento": "Investimento"}
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
                st.toast("Alterações de despesas salvas.", icon="✅")
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
                st.toast("Alterações de receitas salvas.", icon="✅")
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
            nomes_tipo = {"Fixo": "Fixo (legado)", "Cartao": "Cartão", "Extra": "Extra (legado)",
                          "Debito Automatico": "Débito Automático", "PIX/Especie": "PIX/Espécie",
                          "Investimento": "Investimento"}
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
            st.toast(f"Recorrente '{descricao}' cadastrado.", icon="✅")
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
            st.toast("Alterações salvas.", icon="✅")
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
                st.toast(f"Ativo '{nome_ativo}' cadastrado.", icon="✅")
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

        nomes_ativos = {a["nome"]: a["id"] for a in ativos}

        st.markdown("### Atualizar saldo do ativo")
        st.caption("Informe o saldo atual do ativo. O rendimento (ou prejuízo) será calculado automaticamente, desconsiderando aportes e resgates do período.")

        with st.form("form_atualizacao"):
            ativo_sel_u = st.selectbox("Ativo", list(nomes_ativos.keys()), key="ativo_atualizacao")
            data_u = st.date_input("Data da atualização", value=date.today(), format="DD/MM/YYYY", key="data_atualizacao")
            saldo_u = st.number_input("Saldo atual informado", step=None, min_value=0.0, format="%.2f", key="saldo_atualizacao")
            enviar_u = st.form_submit_button("Atualizar saldo")

            if enviar_u and saldo_u >= 0:
                r = requests.post(f"{API}/atualizacoes-saldo", json={
                    "ativo_id": nomes_ativos[ativo_sel_u],
                    "data": str(data_u),
                    "saldo_informado": saldo_u,
                })
                if r.status_code == 200:
                    resp = r.json()
                    if resp.get("rendimento_liquido") is None:
                        st.toast(f"Saldo inicial de R$ {saldo_u:,.2f} registrado.", icon="✅")
                    else:
                        rend = resp["rendimento_liquido"]
                        pct = resp.get("rendimento_percentual") or 0
                        if rend > 0:
                            st.toast(f"Rendimento de R$ {rend:,.2f} ({pct:+.2f}%) calculado.", icon="📈")
                        elif rend < 0:
                            st.toast(f"Prejuízo de R$ {abs(rend):,.2f} ({pct:+.2f}%) calculado.", icon="📉")
                        else:
                            st.toast("Saldo atualizado. Sem rendimento no período.", icon="✅")
                    st.rerun()
                else:
                    st.error(f"Erro: {r.text}")

        st.divider()

        st.markdown("### Nova movimentação")
        st.caption("Apenas Aporte e Resgate. Rendimento e Prejuízo vêm da atualização de saldo.")

        with st.form("form_mov"):
            ativo_sel = st.selectbox("Ativo", list(nomes_ativos.keys()), key="ativo_mov")
            tipo_mov = st.selectbox("Tipo", TIPOS_MOV, key="tipo_mov")
            data_mov = st.date_input("Data", value=date.today(), format="DD/MM/YYYY", key="data_mov")
            valor_mov = st.number_input("Valor", step=None, min_value=0.0, format="%.2f", key="valor_mov")
            obs_mov = st.text_input("Observação (opcional)", key="obs_mov")
            enviar_mov = st.form_submit_button("Lançar movimentação")

            if enviar_mov and valor_mov > 0:
                requests.post(f"{API}/movimentacoes", json={
                    "ativo_id": nomes_ativos[ativo_sel],
                    "data": str(data_mov), "tipo": tipo_mov,
                    "valor": valor_mov,
                    "observacao": obs_mov if obs_mov else None,
                })
                st.toast(f"{tipo_mov} de R$ {valor_mov:,.2f} em '{ativo_sel}' efetivado.", icon="✅")
                st.rerun()

        st.divider()

        st.markdown("### Histórico de atualizações de saldo")
        ativo_hist_u = st.selectbox("Ver atualizações de:", list(nomes_ativos.keys()), key="hist_ativo_u")
        atualizacoes = requests.get(f"{API}/atualizacoes-saldo?ativo_id={nomes_ativos[ativo_hist_u]}").json()

        if not atualizacoes:
            st.info("Nenhuma atualização de saldo para este ativo.")
        else:
            rows = []
            for a in atualizacoes:
                data_br = datetime.strptime(a["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
                if a["rendimento_liquido"] is None:
                    rows.append({
                        "Data": data_br,
                        "Saldo informado": f"R$ {a['saldo_informado']:,.2f}",
                        "Aportes": "—",
                        "Resgates": "—",
                        "Rendimento": "Saldo inicial",
                        "Percentual": "—",
                    })
                else:
                    rend = a["rendimento_liquido"]
                    pct = a["rendimento_percentual"]
                    sinal = "+" if rend >= 0 else "−"
                    tipo_rend = "Rendimento" if rend >= 0 else "Prejuízo"
                    rows.append({
                        "Data": data_br,
                        "Saldo informado": f"R$ {a['saldo_informado']:,.2f}",
                        "Aportes": f"R$ {a['aportes_periodo']:,.2f}",
                        "Resgates": f"R$ {a['resgates_periodo']:,.2f}",
                        f"{tipo_rend}": f"{sinal}R$ {abs(rend):,.2f}",
                        "Percentual": f"{pct:+.2f}%" if pct is not None else "—",
                    })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.divider()

        st.markdown("### Histórico de movimentações (Aporte / Resgate / Rendimento / Prejuízo)")
        ativo_hist = st.selectbox("Ver movimentações de:", list(nomes_ativos.keys()), key="hist_ativo")
        movs = requests.get(f"{API}/movimentacoes?ativo_id={nomes_ativos[ativo_hist]}").json()

        if not movs:
            st.info("Nenhuma movimentação para este ativo.")
        else:
            dfm = pd.DataFrame(movs)
            dfm["data_br"] = pd.to_datetime(dfm["data"]).dt.strftime("%d-%m-%Y")
            dfm["editavel"] = dfm["automatica"].apply(lambda x: "Não (auto)" if x else "Sim")
            dfm = dfm[["id", "data_br", "tipo", "valor", "observacao", "editavel"]]

            editado_m = st.data_editor(
                dfm, use_container_width=True, hide_index=True, disabled=["id", "editavel"],
                column_config={
                    "data_br": st.column_config.TextColumn("Data (DD-MM-AAAA)"),
                    "valor": st.column_config.NumberColumn("Valor", format="%.2f"),
                },
                key="editor_movimentacoes",
            )

            if st.button("Salvar alterações de movimentações"):
                originais = {m["id"]: m for m in movs}
                for _, linha in editado_m.iterrows():
                    mid = int(linha["id"])
                    original = originais.get(mid)
                    if not original or original.get("automatica"):
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
                st.toast("Alterações salvas.", icon="✅")
                st.rerun()

# ============ ABA RELATÓRIOS ============
with aba_relatorios:
    st.subheader("Relatórios em PDF")
    st.caption("Gera um PDF completo do mês: totais, despesas, receitas, posição e movimentações de investimentos, rendimento da carteira e gráficos.")

    hoje = date.today()
    col1, col2 = st.columns(2)
    ano_r = col1.number_input("Ano (relatório)", min_value=2020, max_value=2100, value=hoje.year, step=1, key="ano_rel")
    mes_r = col2.number_input("Mês (relatório)", min_value=1, max_value=12, value=hoje.month, step=1, key="mes_rel")

    if st.button("Gerar PDF do resumo"):
        dados_r = requests.get(f"{API}/transacoes/mes/{int(ano_r)}/{int(mes_r)}").json()
        resumo_inv_r = requests.get(f"{API}/movimentacoes/mes/{int(ano_r)}/{int(mes_r)}").json()
        acumulado_r = requests.get(f"{API}/saldo-acumulado/{int(ano_r)}/{int(mes_r)}").json()

        ano_ant_r = int(ano_r) - 1 if int(mes_r) == 1 else int(ano_r)
        mes_ant_r = 12 if int(mes_r) == 1 else int(mes_r) - 1
        acumulado_ant_r = requests.get(f"{API}/saldo-acumulado/{ano_ant_r}/{mes_ant_r}").json()

        ativos_r = requests.get(f"{API}/ativos").json()

        movs_mes = []
        for a in ativos_r:
            movs_ativo = requests.get(f"{API}/movimentacoes?ativo_id={a['id']}").json()
            for m in movs_ativo:
                try:
                    d = datetime.strptime(m["data"], "%Y-%m-%d")
                    if d.year == int(ano_r) and d.month == int(mes_r):
                        movs_mes.append(m)
                except Exception:
                    pass

        if not dados_r and not resumo_inv_r and not movs_mes:
            st.warning("Nenhum dado neste mês para gerar o relatório.")
        else:
            pdf_bytes = gerar_pdf(
                ano=int(ano_r), mes=int(mes_r),
                transacoes=dados_r,
                resumo_inv=resumo_inv_r,
                saldo_ant=acumulado_ant_r.get("saldo", 0),
                saldo_atual=acumulado_r.get("saldo", 0),
                ativos=ativos_r,
                movimentacoes_mes=movs_mes,
            )
            st.download_button(
                label="⬇️ Baixar PDF",
                data=pdf_bytes,
                file_name=f"resumo_{int(ano_r)}_{int(mes_r):02d}.pdf",
                mime="application/pdf",
            )
