import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="Painel de Contas a Receber", layout="wide")

st.title("📊 Painel de Contas a Receber")


df = pd.read_csv('contas_receber.csv', sep=';')

data_cols = ['DAT_EMISSAO', 'DAT_VENCIMENTO', 'DAT_QUITACAO', 'DAT_CANCEL']
for col in data_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce')

df['STATUS'] = df['STATUS'].str.lower().fillna('indefinido')
df['STATUS_CATEGORIA'] = df['STATUS'].map({
    'quitado': 'Recebido',
    'aberto': 'Em Aberto',
    'cancelado': 'Cancelado'
}).fillna('Outro')

df['VLR_SALDO'] = df['VLR_SALDO'].fillna(0)
df['MES_ANO'] = df['DAT_VENCIMENTO'].dt.to_period('M')


mes_atual = pd.Period(datetime.today(), 'M')
meses_disponiveis = ['Todos'] + df['MES_ANO'].dropna().sort_values().unique().astype(str).tolist()


try:
    default_index = meses_disponiveis.index(str(mes_atual))
except ValueError:
    default_index = 0 


mes_selecionado = st.selectbox("Selecione o Mês de Referência:", options=meses_disponiveis, index=default_index)


df_filtrado_mes = df.copy() 
if mes_selecionado != 'Todos':
    df_filtrado_mes = df_filtrado_mes[df_filtrado_mes['MES_ANO'] == pd.Period(mes_selecionado, 'M')]

def formatar_moeda(valor, simbolo_moeda="R$"):
    if pd.isna(valor):
        return ''
    try:
        return f"{simbolo_moeda} {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"


if mes_selecionado == 'Todos':
    st.subheader("📅 Análise de Contas a Receber - Todos os Meses")
else:
    st.subheader(f"📅 Análise de Contas a Receber - {pd.Period(mes_selecionado, 'M').strftime('%B/%Y')}")


valor_total = df_filtrado_mes['VLR_DOCUMENTO'].sum()
valor_aberto = df_filtrado_mes.loc[df_filtrado_mes['STATUS_CATEGORIA'] == 'Em Aberto', 'VLR_SALDO'].sum()
valor_vencido = df_filtrado_mes.loc[(df_filtrado_mes['STATUS_CATEGORIA'] == 'Em Aberto') & (df_filtrado_mes['DAT_VENCIMENTO'] < pd.Timestamp.now()), 'VLR_SALDO'].sum()
qtde_documentos = len(df_filtrado_mes)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Títulos", qtde_documentos)
col2.metric("Valor Total a Receber", formatar_moeda(valor_total))
col3.metric("Em Aberto", formatar_moeda(valor_aberto))
col4.metric("Vencido", formatar_moeda(valor_vencido))

st.markdown("---")


if mes_selecionado == 'Todos':
    
    recebimentos_periodo = df_filtrado_mes.groupby(df_filtrado_mes['MES_ANO'])['VLR_SALDO'].sum().reset_index()
    recebimentos_periodo['MES_ANO'] = recebimentos_periodo['MES_ANO'].astype(str)
    recebimentos_periodo['VLR_SALDO_FORMATADO'] = recebimentos_periodo['VLR_SALDO'].apply(formatar_moeda)
    title_graph = "📅 Recebimentos por Mês"
    x_axis = 'MES_ANO'
else:
    recebimentos_periodo = df_filtrado_mes.groupby(df_filtrado_mes['DAT_VENCIMENTO'].dt.date)['VLR_SALDO'].sum().reset_index()
    recebimentos_periodo['VLR_SALDO_FORMATADO'] = recebimentos_periodo['VLR_SALDO'].apply(formatar_moeda)
    title_graph = "📅 Recebimentos por Dia"
    x_axis = 'DAT_VENCIMENTO'

fig_venc = px.bar(
    recebimentos_periodo,
    x=x_axis,
    y='VLR_SALDO',
    title=title_graph,
    text='VLR_SALDO_FORMATADO',
    height=700,
    width=1100
)

fig_venc.update_traces(
    texttemplate='%{text}',
    textposition='outside',
    textfont=dict(size=22) 
)

fig_venc.update_layout(uniformtext_minsize=8, uniformtext_mode='show')
fig_venc.update_yaxes(tickprefix="R$ ")

st.plotly_chart(fig_venc, use_container_width=True)

st.markdown("---")


# 📈 Top 10 Clientes (FANTASIA) (usando df_filtrado_mes)
forn_resumo = df_filtrado_mes.groupby('FANTASIA')['VLR_SALDO'].sum().reset_index().sort_values(by='VLR_SALDO', ascending=False).head(10)
forn_resumo['VLR_SALDO_FORMATADO'] = forn_resumo['VLR_SALDO'].apply(formatar_moeda)

fig_forn = px.bar(
    forn_resumo,
    x='VLR_SALDO',
    y='FANTASIA',
    orientation='h',
    title="🏆 Top 10 Clientes Devedores",
    text='VLR_SALDO_FORMATADO'
)

fig_forn.update_traces(texttemplate='%{text}', textposition='outside')
fig_forn.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
fig_forn.update_xaxes(tickprefix="R$ ")

st.plotly_chart(fig_forn, use_container_width=True)

st.markdown("---")


### **Concentração de Recebimentos por Dia do Mês**

if mes_selecionado != 'Todos': 
    df_filtrado_mes['DIA_MES'] = df_filtrado_mes['DAT_VENCIMENTO'].dt.day
    heat_data = df_filtrado_mes.pivot_table(index='DIA_MES', values='VLR_SALDO', aggfunc='sum').fillna(0)

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(heat_data, annot=True, fmt=".0f", cmap="YlOrRd", ax=ax)
    plt.title("🔥 Concentração de Recebimentos por Dia do Mês")
    st.pyplot(fig)
    st.markdown("---")
else:
    st.info("O Heatmap de Concentração de Recebimentos por Dia do Mês está disponível apenas quando um mês específico é selecionado.")
    st.markdown("---")


def highlight_overdue(row, col_name='DAT_VENCIMENTO'):
    today = pd.to_datetime('today').normalize()
    if (row['STATUS_CATEGORIA'] == 'Em Aberto') and (col_name in row.index) and pd.notna(row[col_name]) and row[col_name] < today:
        return ['background-color: #f8230f'] * len(row)
    return [''] * len(row)


### **Tabela Detalhada**

# 📋 Tabela Detalhada (usando df_filtrado_mes)
st.markdown("### 📋 Tabela Detalhada")

colunas_exibir = ['STATUS_CATEGORIA', 'DAT_EMISSAO', 'DAT_VENCIMENTO', 'VLR_SALDO', 'FANTASIA', 'NOME_GUERRA']


status_selecionado = st.multiselect(
    "Filtrar por Status",
    options=df_filtrado_mes['STATUS_CATEGORIA'].unique(),
    default=df_filtrado_mes['STATUS_CATEGORIA'].unique()
)
df_tabela = df_filtrado_mes[df_filtrado_mes['STATUS_CATEGORIA'].isin(status_selecionado)].copy()
df_tabela = df_tabela.sort_values(by='DAT_VENCIMENTO', ascending=True)
df_tabela = df_tabela[colunas_exibir]
df_tabela['DAT_EMISSAO'] = df_tabela['DAT_EMISSAO'].dt.strftime('%d/%m/%Y')
df_tabela['DAT_VENCIMENTO'] = df_tabela['DAT_VENCIMENTO'].dt.strftime('%d/%m/%Y')
df_tabela['VLR_SALDO'] = df_tabela['VLR_SALDO'].apply(formatar_moeda)

df_tabela.rename(columns={
    'STATUS_CATEGORIA': 'Status',
    'DAT_EMISSAO': 'Data Emissão',
    'DAT_VENCIMENTO': 'Data Vencimento',
    'VLR_SALDO': 'Valor Saldo',
    'FANTASIA': 'Cliente',
    'NOME_GUERRA': 'Vendedor'
}, inplace=True)


def highlight_overdue_renamed(row):
    today = pd.to_datetime('today').normalize()
    try:
        dt_venc = pd.to_datetime(row['Data Vencimento'], dayfirst=True)
    except:
        return [''] * len(row)
    if (row['Status'] == 'Em Aberto') and (dt_venc < today):
        return ['background-color: #f8230f'] * len(row)
    return [''] * len(row)

styled_df = df_tabela.style.apply(highlight_overdue_renamed, axis=1)

st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)


st.caption("Desenvolvido por Christian Roque")