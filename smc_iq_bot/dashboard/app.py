import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.indicators import get_all_indicators


def normalize_yfinance_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if symbol.endswith("=X"):
        return symbol
    if len(symbol) == 6 and symbol.isalpha():
        return f"{symbol}=X"
    return symbol

st.set_page_config(page_title="SMC Dashboard IQ", layout="wide")
st.title(" SMC Dashboard (Focado em IQ Option)")

st.sidebar.header("Configurações")
symbol = st.sidebar.text_input("Ativo (ex: EURUSD=X)", "EURUSD=X")
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h"], index=1)

if st.sidebar.button("Carregar Dados"):
    with st.spinner("Processando..."):
        # Para 1m e 5m, o yfinance só permite 'period' de no máximo 7 dias
        df = yf.download(normalize_yfinance_symbol(symbol), period="5d", interval=timeframe, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty:
            st.error("Dados não encontrados.")
        else:
            df = get_all_indicators(df, swing_order=5)
            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=df.index,
                        open=df["Open"],
                        high=df["High"],
                        low=df["Low"],
                        close=df["Close"],
                    )
                ]
            )

            for i in df[df["bull_fvg"]].index:
                fig.add_shape(
                    type="rect",
                    x0=i,
                    x1=df.index[-1],
                    y0=df.loc[i, "bull_fvg_bottom"],
                    y1=df.loc[i, "bull_fvg_top"],
                    fillcolor="rgba(0, 255, 0, 0.2)",
                    line=dict(color="green", width=1),
                )

            for i in df[df["bear_fvg"]].index:
                fig.add_shape(
                    type="rect",
                    x0=i,
                    x1=df.index[-1],
                    y0=df.loc[i, "bear_fvg_bottom"],
                    y1=df.loc[i, "bear_fvg_top"],
                    fillcolor="rgba(255, 0, 0, 0.2)",
                    line=dict(color="red", width=1),
                )

            fig.update_layout(
                title=f"{symbol} - {timeframe} (Zonas de FVG)",
                template="plotly_dark",
                height=700,
            )
            st.plotly_chart(fig, use_container_width=True)
