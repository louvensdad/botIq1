import yaml
import time
import pandas as pd
import yfinance as yf
from datetime import datetime

from core.indicators import get_all_indicators, check_smc_confluence
from execution.iq_option_executor import IQOptionExecutor
from alerts.telegram_bot import TelegramAlerter


def load_config():
    with open("config/settings.yaml", "r") as f:
        return yaml.safe_load(f)


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
