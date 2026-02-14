import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Dashboard Financiero", layout="wide")

st.title("📈 Backtesting de Estrategia: Cruce de Medias Móviles")
st.markdown("""
Esta herramienta compara una estrategia de inversión activa (Cruce de Medias) 
contra la estrategia pasiva de comprar y mantener (Buy & Hold).
""")

# --- SIDEBAR (PANEL LATERAL PARA INPUTS) ---
st.sidebar.header("Parámetros")
ticker = st.sidebar.text_input("Símbolo de la Acción (Yahoo Finance)", value="AAPL")
start_date = st.sidebar.date_input("Fecha de Inicio", value=date(2020, 1, 1))
end_date = st.sidebar.date_input("Fecha Final", value=date.today())

# Medias móviles personalizables
short_window = st.sidebar.slider("Media Rápida (Días)", 10, 100, 50)
long_window = st.sidebar.slider("Media Lenta (Días)", 100, 300, 200)

# --- FUNCIÓN DE CARGA DE DATOS (CON CACHÉ) ---
@st.cache_data
def load_data(ticker, start, end):
    data = yf.download(ticker, start=start, end=end)
    if data.empty:
        return None
    # Aplanar MultiIndex si es necesario (fix para versiones nuevas de yfinance)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data

# Mensaje de "Cargando..."
data_load_state = st.text('Cargando datos...')
data = load_data(ticker, start_date, end_date)
data_load_state.text('¡Datos cargados exitosamente!')

if data is None:
    st.error("No se encontraron datos. Revisa el símbolo (ej: AAPL, TSLA, BTC-USD).")
else:
    # --- CÁLCULOS (LÓGICA DEL BACKEND) ---
    # 1. Indicadores
    data['SMA_Short'] = data['Close'].rolling(window=short_window).mean()
    data['SMA_Long'] = data['Close'].rolling(window=long_window).mean()
    
    # 2. Señales (0 o 1)
    data['Signal'] = 0.0
    data['Signal'] = np.where(data['SMA_Short'] > data['SMA_Long'], 1.0, 0.0)
    
    # 3. Retornos
    data['Market_Returns'] = data['Close'].pct_change()
    data['Strategy_Returns'] = data['Market_Returns'] * pd.Series(data['Signal']).shift(1)
    
    # 4. Acumulados
    data['Cum_Market'] = (1 + data['Market_Returns']).cumprod()
    data['Cum_Strategy'] = (1 + data['Strategy_Returns']).cumprod()

    # --- METRICAS CLAVE ---
    total_return_market = (data['Cum_Market'].iloc[-1] - 1) * 100
    total_return_strategy = (data['Cum_Strategy'].iloc[-1] - 1) * 100
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Retorno Mercado (Buy & Hold)", f"{total_return_market:.2f}%")
    col2.metric("Retorno Estrategia", f"{total_return_strategy:.2f}%", 
                delta=f"{total_return_strategy - total_return_market:.2f}%")
    
    final_signal = "COMPRA (Mercado Alcista)" if data['Signal'].iloc[-1] == 1 else "VENTA (En Efectivo)"
    col3.metric("Estado Actual", final_signal)

    # --- VISUALIZACIÓN CON PLOTLY (INTERACTIVO) ---
    st.subheader("Evolución de la Inversión (Base 1.0)")
    
    fig = go.Figure()
    # Línea del Mercado
    fig.add_trace(go.Scatter(x=data.index, y=data['Cum_Market'], 
                             mode='lines', name='Mercado (Buy & Hold)',
                             line=dict(color='gray', width=1, dash='dash')))
    # Línea de la Estrategia
    fig.add_trace(go.Scatter(x=data.index, y=data['Cum_Strategy'], 
                             mode='lines', name='Mi Estrategia',
                             line=dict(color='purple', width=2)))
    
    # Añadir marcadores de Cruce (Opcional pero visualmente genial)
    # Detectar cambios de señal
    data['Position_Change'] = data['Signal'].diff()
    buys = data[data['Position_Change'] == 1]
    sells = data[data['Position_Change'] == -1]
    
    fig.add_trace(go.Scatter(x=buys.index, y=data.loc[buys.index]['Cum_Strategy'], 
                             mode='markers', name='Señal Compra',
                             marker=dict(color='green', symbol='triangle-up', size=10)))
    
    fig.add_trace(go.Scatter(x=sells.index, y=data.loc[sells.index]['Cum_Strategy'], 
                             mode='markers', name='Señal Venta',
                             marker=dict(color='red', symbol='triangle-down', size=10)))

    fig.update_layout(height=500, xaxis_title="Fecha", yaxis_title="Multiplicador de Retorno")
    st.plotly_chart(fig, use_container_width=True)

    # --- EXPLICACIÓN DE LA ESTRATEGIA ---
    with st.expander("¿Cómo funciona esta estrategia?"):
        st.write(f"""
        Esta estrategia utiliza el cruce de dos medias móviles:
        * **Media Rápida ({short_window} días):** Reacciona rápido a los cambios de precio.
        * **Media Lenta ({long_window} días):** Indica la tendencia a largo plazo.
        
        **Reglas:**
        1. Cuando la rápida cruza por encima de la lenta, **COMPRAMOS**.
        2. Cuando la rápida cruza por debajo de la lenta, **VENDEMOS** y nos quedamos en efectivo.
        """)
