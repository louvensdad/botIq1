import pandas as pd
import numpy as np
from scipy.signal import argrelextrema


def calculate_swings(df: pd.DataFrame, order: int = 5) -> pd.DataFrame:
    df = df.copy()
    df["swing_high"] = np.nan
    df["swing_low"] = np.nan

    highs = argrelextrema(df["High"].values, np.greater_equal, order=order)[0]
    lows = argrelextrema(df["Low"].values, np.less_equal, order=order)[0]

    df.iloc[highs, df.columns.get_loc("swing_high")] = df.iloc[highs]["High"]
    df.iloc[lows, df.columns.get_loc("swing_low")] = df.iloc[lows]["Low"]
    return df


def calculate_fvg(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["bull_fvg"] = df["Low"] > df["High"].shift(2)
    df["bull_fvg_top"] = np.where(df["bull_fvg"], df["Low"], np.nan)
    df["bull_fvg_bottom"] = np.where(df["bull_fvg"], df["High"].shift(2), np.nan)

    df["bear_fvg"] = df["High"] < df["Low"].shift(2)
    df["bear_fvg_top"] = np.where(df["bear_fvg"], df["Low"].shift(2), np.nan)
    df["bear_fvg_bottom"] = np.where(df["bear_fvg"], df["High"], np.nan)

    return df


def get_all_indicators(df: pd.DataFrame, swing_order: int = 5) -> pd.DataFrame:
    df = calculate_swings(df, swing_order)
    df = calculate_fvg(df)
    return df


def check_smc_confluence(df: pd.DataFrame, lookback: int = 15) -> str:
    """
    O 'Santo Graal' do SMC: Sweep (Manipulação) + CHoCH + FVG.
    Retorna 'buy', 'sell' ou None.
    """
    if len(df) < lookback + 5:
        return None

    recent = df.iloc[-lookback:]
    last_candle = df.iloc[-2]  # Vela fechada
    current_candle = df.iloc[-1]  # Vela atual (formando)

    # Pega os últimos Swings confirmados antes da vela atual
    past_swings = df.iloc[-(lookback + 5) : -2]
    last_swing_high = past_swings["swing_high"].dropna()
    last_swing_low = past_swings["swing_low"].dropna()

    if last_swing_high.empty or last_swing_low.empty:
        return None

    ref_high = last_swing_high.iloc[-1]
    ref_low = last_swing_low.iloc[-1]

    # --- 1. SETUP DE COMPRA (Bullish) ---
    # Condição A: Manipulação (Sweep). O preço furou o fundo anterior, mas fechou acima dele (pavio)
    swept_low = recent["Low"].min() < ref_low and recent.iloc[-1]["Close"] > ref_low

    # Condição B: CHoCH (Change of Character). O preço rompeu o último topo com força
    choch_bull = current_candle["Close"] > ref_high or last_candle["Close"] > ref_high

    # Condição C: Retração no FVG de Alta
    fvg_touch_bull = (
        pd.notna(last_candle["bull_fvg_top"])
        and current_candle["Low"] <= last_candle["bull_fvg_top"]
        and current_candle["Close"] > current_candle["Open"]
    )

    if swept_low and choch_bull and fvg_touch_bull:
        return "buy"

    # --- 2. SETUP DE VENDA (Bearish) ---
    # Condição A: Manipulação (Sweep). O preço furou o topo anterior, mas fechou abaixo (pavio)
    swept_high = recent["High"].max() > ref_high and recent.iloc[-1]["Close"] < ref_high

    # Condição B: CHoCH. O preço rompeu o último fundo com força
    choch_bear = current_candle["Close"] < ref_low or last_candle["Close"] < ref_low

    # Condição C: Retração no FVG de Baixa
    fvg_touch_bear = (
        pd.notna(last_candle["bear_fvg_bottom"])
        and current_candle["High"] >= last_candle["bear_fvg_bottom"]
        and current_candle["Close"] < current_candle["Open"]
    )

    if swept_high and choch_bear and fvg_touch_bear:
        return "sell"

    return None
