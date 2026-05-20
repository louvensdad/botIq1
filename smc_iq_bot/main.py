import os
import time
from datetime import datetime

import pandas as pd
import yfinance as yf
import yaml

from core.indicators import get_all_indicators, check_smc_confluence
from execution.iq_option_executor import IQOptionExecutor
from alerts.telegram_bot import TelegramAlerter


def _load_yaml_config():
    config_path = os.path.join("config", "settings.yaml")
    if not os.path.exists(config_path):
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


def load_config():
    yaml_config = _load_yaml_config()

    default_symbols = yaml_config.get("symbols", ["EURUSD", "GBPUSD", "USDJPY", "AUDCAD", "BTCUSD"])
    default_timeframe = yaml_config.get("timeframe", "5m")
    default_risk_amount = yaml_config.get("risk_amount", 4.0)
    default_expiry_minutes = yaml_config.get("expiry_minutes", 3)

    iq_defaults = yaml_config.get("iq_option", {})
    tg_defaults = yaml_config.get("telegram", {})

    return {
        "symbols": _get_env_list("SYMBOLS", default_symbols),
        "timeframe": os.getenv("TIMEFRAME", default_timeframe),
        "risk_amount": _get_env_float("RISK_AMOUNT", default_risk_amount),
        "expiry_minutes": _get_env_int("EXPIRY_MINUTES", default_expiry_minutes),
        "iq_option": {
            "email": os.getenv("IQ_OPTION_EMAIL", iq_defaults.get("email", "")),
            "password": os.getenv("IQ_OPTION_PASSWORD", iq_defaults.get("password", "")),
            "mode": os.getenv("IQ_OPTION_MODE", iq_defaults.get("mode", "REAL")),
        },
        "telegram": {
            "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", tg_defaults.get("bot_token", "")),
            "chat_id": os.getenv("TELEGRAM_CHAT_ID", tg_defaults.get("chat_id", "")),
        },
    }


def map_to_yfinance(iq_symbol: str) -> str:
    mapping = {
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X",
        "USDCAD": "USDCAD=X",
        "NZDUSD": "NZDUSD=X",
        "USDCHF": "USDCHF=X",
        "AUDCAD": "AUDCAD=X",
        "EURGBP": "EURGBP=X",
        "BTCUSD": "BTC-USD",
        "ETHUSD": "ETH-USD",
    }
    return mapping.get(iq_symbol.upper(), f"{iq_symbol.upper()}=X")


def get_market_data(yf_symbol, timeframe):
    try:
        df = yf.download(yf_symbol, period="5d", interval=timeframe, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return None


def main():
    config = load_config()

    tg = TelegramAlerter(config["telegram"]["bot_token"], config["telegram"]["chat_id"])
    tg.send_message(
        f" *Bot SMC Institucional (v2.0) Iniciado!* \nMonitorando: {', '.join(config['symbols'])}\nFiltro: Sweep + CHoCH + FVG"
    )

    iq_config = config["iq_option"]
    executor = IQOptionExecutor(
        email=iq_config["email"],
        password=iq_config["password"],
        mode=iq_config["mode"],
    )

    symbols = config["symbols"]
    timeframe = config["timeframe"]
    amount = config["risk_amount"]
    expiry = config["expiry_minutes"]

    last_trade_time = {sym: 0 for sym in symbols}
    cooldown_seconds = 600  # 10 minutos de cooldown (setups institucionais demoram a se formar)

    print(" Loop institucional iniciado. Aguardando setups de alta probabilidade...")

    try:
        while True:
            now = datetime.now()
            current_time = time.time()
            print(f"\n⏳ Escaneando mercado... {now.strftime('%H:%M:%S')}")

            for iq_symbol in symbols:
                if current_time - last_trade_time[iq_symbol] < cooldown_seconds:
                    continue

                yf_symbol = map_to_yfinance(iq_symbol)
                df = get_market_data(yf_symbol, timeframe)

                if df is None or df.empty or len(df) < 30:
                    continue

                df = get_all_indicators(df, swing_order=5)

                # A MÁGICA ACONTECE AQUI: Verifica a confluência completa
                signal = check_smc_confluence(df, lookback=15)

                if signal:
                    msg = (
                        f" *SETUP INSTITUCIONAL CONFIRMADO!* \n"
                        f" Ativo: *{iq_symbol}*\n"
                        f" Direção: *{signal.upper()}*\n"
                        f" Valor: ${amount}\n"
                        f"⏱️ Expiração: {expiry}m\n"
                        f" *Lógica:* Captura de Liquidez (Sweep) + Quebra de Estrutura (CHoCH) + Retração no FVG."
                    )
                    order_id = executor.execute_trade(iq_symbol, signal, amount, expiry)

                    if order_id:
                        last_trade_time[iq_symbol] = current_time
                        print(f"✅ Trade executado em {iq_symbol}. Cooldown ativado.")

                time.sleep(2)  # Evita bloqueio do Yahoo Finance

            time.sleep(15)

    except KeyboardInterrupt:
        print("\n Bot encerrado.")
        tg.send_message(" *Bot SMC Institucional Encerrado.*")


if __name__ == "__main__":
    main()
