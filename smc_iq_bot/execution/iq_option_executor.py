import logging
import time

try:
    from iqoptionapi.constants import ACTIVES as IQ_ACTIVES
    from iqoptionapi.stable_api import IQ_Option

    IQ_API_AVAILABLE = True
except ImportError:
    IQ_API_AVAILABLE = False
    IQ_ACTIVES = {}


class IQOptionExecutor:
    def __init__(self, email: str, password: str, mode: str = "PRACTICE"):
        if not IQ_API_AVAILABLE:
            raise ImportError(
                "iqoptionapi nao instalada. Rode: pip install git+https://github.com/Lu-Yi-Hsun/iqoptionapi.git"
            )

        normalized_mode = mode.upper().strip()
        if normalized_mode not in {"PRACTICE", "REAL"}:
            raise ValueError("Modo invalido. Use 'PRACTICE' ou 'REAL'.")

        self.mode = normalized_mode
        self.email = email
        self.password = password
        self.api = IQ_Option(email, password)
        self.api.connect()

        if not self.api.check_connect():
            raise ConnectionError("Falha na conexao com a IQ Option. Verifique email/senha.")

        self.api.change_balance(normalized_mode)
        self._open_cache = None
        self._open_cache_time = 0

        balance = self.api.get_balance()
        print(f"Conectado a IQ Option | Modo: {normalized_mode} | Saldo: ${balance}", flush=True)
        logging.info("Conectado a IQ Option | Modo=%s | Saldo=%s", normalized_mode, balance)

    def get_balance(self) -> float:
        self._ensure_connection()
        return self.api.get_balance()

    def _ensure_connection(self):
        try:
            if self.api.check_connect():
                return
        except Exception:
            pass

        logging.warning("Conexao IQ fechada. Reconectando...")
        self.api = IQ_Option(self.email, self.password)
        self.api.connect()
        if not self.api.check_connect():
            raise ConnectionError("Falha ao reconectar com a IQ Option.")
        self.api.change_balance(self.mode)
        self._open_cache = None

    def _normalize_asset(self, asset: str) -> str:
        return asset.replace("=", "").replace("_", "-").upper().strip()

    def _asset_candidates(self, asset_iq: str) -> list[str]:
        candidates = [asset_iq]

        if not asset_iq.endswith("-OTC"):
            candidates.append(f"{asset_iq}-OTC")

        if asset_iq == "BTCUSD":
            candidates.append("BTCUSD-L")

        return [candidate for candidate in candidates if candidate in IQ_ACTIVES]

    def _extract_open_assets(self) -> dict[str, set[str]]:
        self._ensure_connection()
        now = time.time()
        if self._open_cache and now - self._open_cache_time < 60:
            return self._open_cache

        open_assets = {"turbo": set(), "binary": set()}

        try:
            init_data = self.api.get_all_init_v2()
        except Exception as exc:
            logging.exception("Falha ao consultar ativos abertos na IQ Option: %s", exc)
            self._open_cache = open_assets
            self._open_cache_time = now
            return open_assets

        for market in ("turbo", "binary"):
            try:
                actives = init_data.get(market, {}).get("actives", {})
                for active in actives.values():
                    name = str(active.get("name", "")).split(".")[-1]
                    enabled = bool(active.get("enabled"))
                    suspended = bool(active.get("is_suspended"))
                    if name and enabled and not suspended:
                        open_assets[market].add(name)
            except Exception as exc:
                logging.warning("Falha ao ler mercado %s: %s", market, exc)

        self._open_cache = open_assets
        self._open_cache_time = now
        logging.info(
            "Ativos abertos IQ | turbo=%s | binary=%s",
            sorted(open_assets["turbo"]),
            sorted(open_assets["binary"]),
        )
        return open_assets

    def _resolve_trade_asset(self, asset_iq: str) -> tuple[str | None, str | None]:
        open_assets = self._extract_open_assets()
        candidates = self._asset_candidates(asset_iq)

        for market in ("turbo", "binary"):
            for candidate in candidates:
                if candidate in open_assets[market]:
                    return candidate, market

        logging.warning(
            "Nenhum ativo aberto encontrado para %s. Candidatos=%s",
            asset_iq,
            candidates,
        )
        return None, None

    def execute_trade(self, asset: str, direction: str, amount: float, expiry_minutes: int):
        self._ensure_connection()
        asset_iq = self._normalize_asset(asset)
        action = "call" if direction.lower() == "buy" else "put"

        trade_asset, market = self._resolve_trade_asset(asset_iq)
        if not trade_asset:
            print(f"Ativo {asset_iq} fechado/indisponivel na IQ Option.", flush=True)
            return None

        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                print(
                    f"Enviando ordem {market.upper()}: {trade_asset} | {action.upper()} | ${amount} | {expiry_minutes}m | tentativa {attempt}/{max_retries}",
                    flush=True,
                )
                status, order_id = self.api.buy(amount, trade_asset, action, expiry_minutes)
                print(f"Retorno IQ: status={status} order_id={order_id}", flush=True)
                logging.info(
                    "Retorno IQ | market=%s | asset=%s | action=%s | status=%s | order_id=%s",
                    market,
                    trade_asset,
                    action,
                    status,
                    order_id,
                )

                if status:
                    print(f"Ordem executada com sucesso! ID: {order_id}", flush=True)
                    return order_id

                message = str(order_id)
                logging.error("Ordem rejeitada pela IQ Option: %s", message)
                if "asset is not available" in message.lower():
                    self._open_cache = None
                    break
            except Exception as exc:
                logging.exception("Erro ao executar ordem em %s: %s", trade_asset, exc)
                print(f"Erro ao executar ordem em {trade_asset}: {exc}", flush=True)

            if attempt < max_retries:
                time.sleep(2)

        return None
