import streamlit as st
import pandas as pd
import datetime as datetime
import locale
import plotly.express as px

# Configura locale para pt-BR (meses em português)
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')  # Linux / Mac
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')  # Windows
    except locale.Error:
        pass  # fallback para padrão en

st.set_page_config(layout="wide", page_title="Dashboard de Vendas")

# Carregamento e limpeza dos dados
df_vendas = pd.read_csv("C:\\Users\\andre\\Desktop\\Asimov\\catch.csv")

df_vendas["Valor Total"] = (
    df_vendas["Valor Total"]
    .astype(str)
    .str.replace("R$", "", regex=False)
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
    .str.strip()
)
df_vendas["Valor Total"] = pd.to_numeric(df_vendas["Valor Total"], errors='coerce').fillna(0.0)
df_vendas["Valor Numerico"] = df_vendas["Valor Total"]
df_vendas["Venda.Data"] = pd.to_datetime(df_vendas["Venda.Data"], format="%d/%m/%Y")

# Intervalo de datas
data_minima = df_vendas["Venda.Data"].min().date()
data_maxima = df_vendas["Venda.Data"].max().date()
valor_inicial = data_minima
valor_final = min(data_minima + datetime.timedelta(days=6), data_maxima)

# Sidebar: filtros com labels em pt-BR
periodo_selecionado = st.sidebar.date_input(
    "Selecione o período:",
    (valor_inicial, valor_final),
    min_value=data_minima,
    max_value=data_maxima,
    format="DD.MM.YYYY",
)

metodos_disponiveis = df_vendas["Pagamento"].dropna().unique().tolist()
metodos_selecionados = st.sidebar.multiselect(
    "Selecione um(s) método(s) de pagamento:",
    options=metodos_disponiveis,
    default=None
)

if isinstance(periodo_selecionado, tuple) and len(periodo_selecionado) == 2:
    data_inicio, data_fim = periodo_selecionado

    df_filtrado = df_vendas[
        (df_vendas["Venda.Data"].dt.date >= data_inicio) &
        (df_vendas["Venda.Data"].dt.date <= data_fim)
    ].copy()

    if metodos_selecionados:
        df_filtrado = df_filtrado[df_filtrado["Pagamento"].isin(metodos_selecionados)]
    else:
        st.warning("Nenhum método de pagamento selecionado — exibindo resultados vazios.")
        df_filtrado = df_filtrado.iloc[0:0]

    # Formatações para exibição
    df_filtrado["Data"] = df_filtrado["Venda.Data"].dt.strftime("%d/%m/%Y")
    df_filtrado["Valor Formatado"] = df_filtrado["Valor Numerico"].apply(
        lambda x: f'R$ {x:,.2f}'.replace(",", "v").replace(".", ",").replace("v", ".")
    )

    colunas = df_filtrado.columns.tolist()
    for col in ["Venda.Data", "Valor Total", "Valor Numerico"]:
        if col in colunas:
            colunas.remove(col)
    colunas.insert(0, colunas.pop(colunas.index("Data")))
    colunas.append(colunas.pop(colunas.index("Valor Formatado")))

    # Exibição da tabela e informações
    st.write(f"Exibindo vendas de **{data_inicio.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}**")
    if metodos_selecionados:
        st.write(f"Filtrado por método(s) de pagamento: {', '.join(metodos_selecionados)}")
    else:
        st.write("Filtrado por método(s) de pagamento: Nenhum selecionado")
    st.dataframe(df_filtrado[colunas])

    total_vendas = df_filtrado["Valor Numerico"].sum()
    total_formatado = f'R$ {total_vendas:,.2f}'.replace(",", "v").replace(".", ",").replace("v", ".")
    st.markdown(f"### Total das vendas no período selecionado: **{total_formatado}**")

    # Layout para gráficos lado a lado
    col1, col2 = st.columns(2)

    # Gráfico 1: Barras - Vendas por método de pagamento
    with col1:
        if not df_filtrado.empty:
            vendas_por_metodo = df_filtrado.groupby("Pagamento")["Valor Numerico"].sum().reset_index()
            fig1 = px.bar(
                vendas_por_metodo,
                x="Pagamento",
                y="Valor Numerico",
                title="Total de Vendas por Método de Pagamento",
                labels={"Pagamento": "Método de Pagamento", "Valor Numerico": "Valor (R$)"},
                text=vendas_por_metodo["Valor Numerico"].map(lambda x: f'R$ {x:,.2f}'.replace(",", "v").replace(".", ",").replace("v", ".")),
                color="Pagamento",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig1.update_traces(textposition='outside')
            fig1.update_layout(yaxis_tickprefix="R$ ", yaxis_tickformat=",", uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Sem dados para gráfico de métodos de pagamento.")

    # Gráfico 2: Pizza - Quantidade de vendas por produto + info produto mais vendido
    with col2:
        if not df_filtrado.empty and "Produto" in df_filtrado.columns:
            contagem_produtos = df_filtrado["Produto"].value_counts().reset_index()
            contagem_produtos.columns = ["Produto", "Quantidade"]

            # Produto mais vendido
            produto_mais_vendido = contagem_produtos.iloc[0]["Produto"]
            qtd_mais_vendido = contagem_produtos.iloc[0]["Quantidade"]
            st.markdown(f"**Produto mais vendido no período:** {produto_mais_vendido} ({qtd_mais_vendido} unidades)")

            fig2 = px.pie(
                contagem_produtos,
                values="Quantidade",
                names="Produto",
                title="Distribuição da Quantidade de Vendas por Produto",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig2.update_traces(textposition='inside', textinfo='percent+label', hoverinfo='label+value+percent')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sem dados para gráfico de produtos.")

    # Gráfico 3: Linha - Evolução das vendas ao longo do tempo
    st.markdown("---")
    if not df_filtrado.empty:
        vendas_por_data = df_filtrado.groupby("Venda.Data")["Valor Numerico"].sum().reset_index()
        vendas_por_data["Data"] = vendas_por_data["Venda.Data"].dt.strftime("%d/%m/%Y")
        fig3 = px.line(
            vendas_por_data,
            x="Data",
            y="Valor Numerico",
            title="Evolução das Vendas ao Longo do Tempo",
            labels={"Data": "Data", "Valor Numerico": "Valor (R$)"},
            markers=True,
        )
        fig3.update_traces(line=dict(color='purple', width=3), marker=dict(size=8))
        fig3.update_layout(
            xaxis_tickangle=-45,
            yaxis_tickprefix="R$ ",
            yaxis_tickformat=",",
            margin=dict(t=40, b=100),
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Sem dados para gráfico de evolução temporal.")

else:
    st.warning("Selecione um intervalo de datas válido.")