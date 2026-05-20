# SMC IQ Bot

Bot de analise SMC com execucao na IQ Option, alertas por Telegram e dashboard em Streamlit.

## Estrutura

```text
smc_iq_bot/
|-- main.py
|-- requirements.txt
|-- Dockerfile
|-- config/
|   |-- settings.example.yaml
|   `-- settings.yaml
|-- core/
|-- dashboard/
|-- execution/
`-- alerts/
```

## Configuracao

O arquivo real de configuracao nao deve ser enviado ao Git.

1. Use [`smc_iq_bot/config/settings.example.yaml`](smc_iq_bot/config/settings.example.yaml) como base.
2. Crie o arquivo local `smc_iq_bot/config/settings.yaml`.
3. Preencha as credenciais da IQ Option e do Telegram.

O exemplo mantem `mode: "REAL"`.

## Execucao local

Dentro da pasta `smc_iq_bot`:

```bash
pip install -r requirements.txt
pip install git+https://github.com/Lu-Yi-Hsun/iqoptionapi.git
python main.py
```

Para o dashboard:

```bash
streamlit run dashboard/app.py
```

## Docker

Subir apenas o bot:

```bash
docker compose up -d bot
```

Subir bot e dashboard:

```bash
docker compose up -d --build
```

Dashboard:

```text
http://localhost:8501
```

O `docker-compose.yml` monta:

- `./smc_iq_bot/config/settings.yaml` em modo somente leitura no container
- `./smc_iq_bot/logs` para persistencia de logs

## Git

Arquivos sensiveis e temporarios ja estao ignorados, incluindo:

- `smc_iq_bot/config/settings.yaml`
- logs e arquivos `.pid`
- caches Python

## Observacoes

- O bot usa `yfinance` para obter dados de mercado.
- O dashboard mostra candles e zonas de FVG.
