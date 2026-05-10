# Binance Futures Testnet Trading Bot

A clean, well-structured Python CLI application for placing orders on the **Binance Futures Testnet (USDT-M)**. Supports Market, Limit, and Stop-Market orders with full logging, input validation, and error handling.

---

## Features

- ✅ **Market** and **Limit** orders (core)
- ✅ **Stop-Market** orders (bonus)
- ✅ **BUY** and **SELL** sides
- ✅ CLI via `argparse` with clear validation messages
- ✅ Structured project layout (client / orders / validators / CLI layers)
- ✅ Rotating daily log files (DEBUG to file, INFO to console)
- ✅ Graceful exception handling for API errors, network failures, and bad input
- ✅ Colourised terminal output
- ✅ Account info command
- ✅ Connectivity ping command

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance REST client (signing, HTTP)
│   ├── orders.py            # Order placement logic & data classes
│   ├── validators.py        # Input validation
│   └── logging_config.py   # Logging setup (file + console)
├── logs/
│   ├── market_order_sample.log
│   └── limit_order_sample.log
├── cli.py                   # CLI entry point (argparse)
├── .env.example             # Credentials template
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Get Testnet API Credentials

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in (GitHub OAuth or Google)
3. Go to **API Key** section and click **Generate**
4. Copy your **API Key** and **Secret Key**

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Requires Python 3.8+. Dependencies:
- `requests` — HTTP client
- `python-dotenv` — `.env` file loading

### 3. Configure Credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```dotenv
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

> **Note:** These credentials are for the **testnet only** — no real funds involved.

---

## Running the Bot

### Check Connectivity

```bash
python cli.py ping
```

### View Account Information

```bash
python cli.py account
```

### Place a Market Order

```bash
# Market BUY 0.001 BTC
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Market SELL 0.01 ETH
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --quantity 0.01
```

### Place a Limit Order

```bash
# Limit BUY 0.001 BTC at $90,000
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 90000

# Limit SELL 0.001 BTC at $100,000 (IOC)
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000 --tif IOC
```

### Place a Stop-Market Order (Bonus)

```bash
# Stop-Market SELL — triggers at $75,000
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 75000
```

### Using CLI Flags for Credentials (no .env)

```bash
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET place \
    --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Custom Log Directory

```bash
python cli.py --log-dir /tmp/my_logs place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

---

## CLI Reference

```
usage: trading_bot [-h] [--log-dir DIR] [--api-key KEY] [--api-secret SECRET]
                   COMMAND ...

Commands:
  place     Place a new order
  account   Display futures account summary
  ping      Check connectivity to Binance Futures Testnet

place arguments:
  --symbol    SYMBOL      Trading pair (e.g. BTCUSDT)          [required]
  --side      BUY|SELL    Order side                           [required]
  --type      MARKET|LIMIT|STOP_MARKET                         [required]
  --quantity  QTY         Order quantity                       [required]
  --price     PRICE       Limit price (required for LIMIT)
  --stop-price PRICE      Stop price (required for STOP_MARKET)
  --tif       GTC|IOC|FOK Time-in-force for LIMIT (default: GTC)
```

---

## Logging

Log files are written to `logs/trading_bot_YYYYMMDD.log` (daily rotation).

| Level   | Destination   | Content                                      |
|---------|--------------|----------------------------------------------|
| DEBUG   | File only     | Full request params, raw API responses        |
| INFO    | File + console| Order submissions, results, connectivity      |
| WARNING | File + console| Non-fatal issues (e.g. ignored price param)  |
| ERROR   | File + console| API errors, network failures, exceptions      |

Sample log entries are included in `logs/`.

---

## Error Handling

| Scenario                | Behaviour                                               |
|-------------------------|---------------------------------------------------------|
| Missing required field  | Validation error printed, exit code 1                   |
| Invalid symbol/side/type| Clear message with valid options                        |
| Non-positive quantity   | Validation error                                        |
| Missing price (LIMIT)   | Validation error before any API call                   |
| API error (e.g. -1121)  | Prints Binance error code + message, logs full response |
| Network timeout         | Catches `ConnectionError`, logs and exits cleanly       |
| Missing credentials     | Clear setup instructions printed                        |

---

## Assumptions

1. The bot targets **USDT-M Futures Testnet** only — base URL is hardcoded to `https://testnet.binancefuture.com`.
2. All quantities are passed as strings to preserve decimal precision.
3. LIMIT orders default to `timeInForce=GTC` unless `--tif` is specified.
4. For MARKET orders, any `--price` argument is silently ignored (not an error).
5. `recvWindow` is set to 5000ms — increase in `client.py` if clock skew is an issue.
6. Testnet balances are virtual and reset periodically by Binance.

---

## Sample Output

```
┌─ Order Request ─────────────────────────
│  Symbol     : BTCUSDT
│  Side       : BUY
│  Type       : MARKET
│  Quantity   : 0.001
└─────────────────────────────────────────

┌─ Order Response ────────────────────────
│  Order ID    : 3987654321
│  Symbol      : BTCUSDT
│  Status      : FILLED
│  Side        : BUY
│  Type        : MARKET
│  Orig Qty    : 0.001
│  Executed Qty: 0.001
│  Avg Price   : 96842.50000
│  Price       : 0
└─────────────────────────────────────────

✔  Order placed successfully! Order ID: 3987654321
```
